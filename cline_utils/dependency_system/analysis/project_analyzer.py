# analysis/project_analyzer.py

from collections import defaultdict
import fnmatch
import json
import os
from typing import Any, Dict, Optional, List, Tuple
from cline_utils.dependency_system.core.dependency_grid import decompress
from cline_utils.dependency_system.io import tracker_io
from cline_utils.dependency_system.core import key_manager
import uuid
import logging
from cline_utils.dependency_system.analysis.dependency_analyzer import analyze_file
from cline_utils.dependency_system.utils.batch_processor import BatchProcessor, process_items
from cline_utils.dependency_system.analysis.dependency_suggester import suggest_dependencies
from cline_utils.dependency_system.analysis.embedding_manager import generate_embeddings
from cline_utils.dependency_system.utils.cache_manager import cached, file_modified, clear_all_caches
from cline_utils.dependency_system.utils.config_manager import ConfigManager
from cline_utils.dependency_system.utils.path_utils import is_subpath, normalize_path, get_project_root
from cline_utils.dependency_system.utils.template_generator import generate_final_review_checklist

logger = logging.getLogger(__name__)

# Caching for analyze_project (Consider if key_func needs more refinement)
# @cached("project_analysis",
#        key_func=lambda force_analysis=False, force_embeddings=False, **kwargs:
#        f"analyze_project:{normalize_path(get_project_root())}:{(os.path.getmtime(ConfigManager().config_path) if os.path.exists(ConfigManager().config_path) else 0)}:{force_analysis}:{force_embeddings}")
def analyze_project(force_analysis: bool = False, force_embeddings: bool = False) -> Dict[str, Any]:
    """
    Analyzes all files in a project to identify dependencies between them,
    initialize trackers, suggest dependencies using the new contextual key system,
    and generate relevant project templates like the final review checklist.

    Args:
        force_analysis: Bypass cache and force reanalysis of files
        force_embeddings: Force regeneration of embeddings
    Returns:
        Dictionary containing project-wide analysis results and status
    """
    # --- Initial Setup ---
    config = ConfigManager()
    project_root = get_project_root()
    logger.info(f"Starting project analysis in directory: {project_root}")

    analyzer_batch_processor = BatchProcessor()
    # Clear relevant caches if forcing re-analysis
    if force_analysis:
        logger.info("Force analysis requested. Clearing all caches.")
        clear_all_caches()

    results = { 
        "status": "success", "message": "", "tracker_initialization": {},
        "embedding_generation": {}, "dependency_suggestion": {},
        "tracker_update": {}, "file_analysis": {},
        "template_generation": {} 
    }

    # --- Exclusion Setup ---
    excluded_dirs_rel = config.get_excluded_dirs()
    excluded_paths_rel = config.get_excluded_paths() # This now returns resolved absolute paths
    excluded_extensions = set(config.get_excluded_extensions())
    # excluded_file_patterns = config.config.get("excluded_file_patterns", []) # Already handled by get_excluded_paths

    excluded_dirs_abs_set = {normalize_path(os.path.join(project_root, p)) for p in excluded_dirs_rel}
    # Use the resolved absolute paths from get_excluded_paths directly
    all_excluded_paths_abs_set = set(excluded_paths_rel).union(excluded_dirs_abs_set)


    norm_project_root = normalize_path(project_root)
    # Check if norm_project_root itself is excluded by checking if it starts with or equals any excluded path
    if any(norm_project_root == excluded_path or norm_project_root.startswith(excluded_path + os.sep) 
           for excluded_path in all_excluded_paths_abs_set):
        logger.info(f"Skipping analysis of excluded project root: {project_root}"); results["status"] = "skipped"; results["message"] = "Project root is excluded"; return results

    # --- Root Directories Setup ---
    code_root_directories_rel = config.get_code_root_directories()
    doc_directories_rel = config.get_doc_directories()
    all_roots_rel = list(set(code_root_directories_rel + doc_directories_rel)) 
    all_roots_rel.sort()
    logger.debug(f"Processing root directories in stable order: {all_roots_rel}")

    if not code_root_directories_rel:
        logger.error("No code root directories configured.")
        results["status"] = "error"; results["message"] = "No code root directories configured."; return results
    if not doc_directories_rel:
        logger.warning("No documentation directories configured. Proceeding without doc analysis.")

    abs_code_roots = {normalize_path(os.path.join(project_root, r)) for r in code_root_directories_rel}
    abs_doc_roots = {normalize_path(os.path.join(project_root, r)) for r in doc_directories_rel}
    abs_all_roots = {normalize_path(os.path.join(project_root, r)) for r in all_roots_rel}

    old_map_existed_before_gen = False
    try:
        # Determine the expected path for the old map file RELATIVE to key_manager.py
        # Use the imported key_manager module to find its location
        key_manager_dir = os.path.dirname(os.path.abspath(key_manager.__file__))
        old_map_path = normalize_path(os.path.join(key_manager_dir, key_manager.OLD_GLOBAL_KEY_MAP_FILENAME))
        old_map_existed_before_gen = os.path.exists(old_map_path)
        if old_map_existed_before_gen:
            logger.info(f"Found existing '{key_manager.OLD_GLOBAL_KEY_MAP_FILENAME}' before key generation. Grid migration will prioritize it.")
        else:
            logger.info(f"'{key_manager.OLD_GLOBAL_KEY_MAP_FILENAME}' not found before key generation. Grid migration will use tracker definitions as fallback.")
    except Exception as path_err:
        logger.error(f"Error determining path or checking existence of old key map file: {path_err}. Assuming it didn't exist.")
        old_map_existed_before_gen = False

    # --- Key Generation ---
    logger.info("Generating/Regenerating keys...")
    path_to_key_info: Dict[str, key_manager.KeyInfo] = {}
    newly_generated_keys: List[key_manager.KeyInfo] = []

    try:
        # Call generate_keys using the module reference
        path_to_key_info, newly_generated_keys = key_manager.generate_keys(
            all_roots_rel,
            excluded_dirs=excluded_dirs_rel,
            excluded_extensions=excluded_extensions,
            precomputed_excluded_paths=all_excluded_paths_abs_set # Pass the combined set
        )
        results["tracker_initialization"]["key_generation"] = "success"
        logger.info(f"Generated {len(path_to_key_info)} keys for {len(path_to_key_info)} files/dirs.")
        if newly_generated_keys: logger.info(f"Assigned {len(newly_generated_keys)} new keys.")
    except key_manager.KeyGenerationError as kge:
        results["status"] = "error"; results["message"] = f"Key generation failed: {kge}"; logger.critical(results["message"]); return results
    except Exception as e:
        results["status"] = "error"; results["message"] = f"Key generation failed unexpectedly: {e}"; logger.exception(results["message"]); return results

    # --- File Identification and Filtering ---
    config_manager_instance = ConfigManager()
    logger.info("Identifying files for analysis...")
    files_to_analyze_abs = []
    excluded_file_patterns_config = config_manager_instance.config.get("excluded_file_patterns", []) # From .clinerules.config.json

    # Use abs_all_roots for finding files, order doesn't strictly matter here
    for abs_root_dir in abs_all_roots:
        if not os.path.isdir(abs_root_dir):
            logger.warning(f"Configured root directory not found: {abs_root_dir}")
            continue
        # Use os.walk - order within walk is OS-dependent but shouldn't affect analysis results
        for root, dirs, files in os.walk(abs_root_dir, topdown=True):
            norm_root = normalize_path(root)
            
            # Directory filtering
            dirs[:] = [
                d for d in dirs 
                if d not in excluded_dirs_rel # Check against simple dir names
                and normalize_path(os.path.join(norm_root, d)) not in all_excluded_paths_abs_set # Check against resolved abs paths
            ]

            # Check if the current directory itself is excluded by path/pattern
            is_root_excluded_by_path = False
            if norm_root in all_excluded_paths_abs_set or \
               any(is_subpath(norm_root, excluded) for excluded in all_excluded_paths_abs_set):
                 is_root_excluded_by_path = True

            if is_root_excluded_by_path:
                logger.debug(f"Skipping files in excluded directory: {norm_root}")
                dirs[:] = [] 
                continue

            for file_name in files: # Renamed 'file' to 'file_name' to avoid conflict
                file_path_abs = normalize_path(os.path.join(norm_root, file_name))
                file_basename = os.path.basename(file_path_abs) # Use file_name directly
                _, file_ext = os.path.splitext(file_name)
                file_ext = file_ext.lower()

                # Check all exclusion criteria
                is_excluded = (
                    file_path_abs in all_excluded_paths_abs_set
                    or any(is_subpath(file_path_abs, excluded) for excluded in all_excluded_paths_abs_set)
                    or file_ext in excluded_extensions
                    or any(fnmatch.fnmatch(file_basename, pattern) for pattern in excluded_file_patterns_config)
                )

                if is_excluded:
                    logger.debug(f"Skipping excluded file: {file_path_abs}")
                    continue

                if file_path_abs in path_to_key_info:
                    files_to_analyze_abs.append(file_path_abs)
                else:
                    logger.warning(f"File found but no key generated: {file_path_abs}")

    logger.info(f"Found {len(files_to_analyze_abs)} files to analyze.")

    # --- File Analysis ---
    logger.info("Starting file analysis...")
    # Use process_items for potential parallelization
    # Pass force_analysis flag down to analyze_file if caching is implemented there
    analysis_results_list = process_items(
        files_to_analyze_abs,
        analyze_file,
        force=force_analysis
    )
    file_analysis_results: Dict[str, Any] = {}
    analyzed_count, skipped_count, error_count = 0, 0, 0
    for file_path_abs, analysis_result in zip(files_to_analyze_abs, analysis_results_list):
        if analysis_result:
            if "error" in analysis_result: logger.warning(f"Analysis error for {file_path_abs}: {analysis_result['error']}"); error_count += 1
            elif "skipped" in analysis_result: skipped_count += 1
            else: file_analysis_results[file_path_abs] = analysis_result; analyzed_count += 1
        else: logger.warning(f"Analysis returned no result for {file_path_abs}"); error_count += 1
    results["file_analysis"] = file_analysis_results
    logger.info(f"File analysis complete. Analyzed: {analyzed_count}, Skipped: {skipped_count}, Errors: {error_count}")

    # --- Create file_to_module mapping (Adapted for path_to_key_info) ---
    # Maps normalized absolute file path -> normalized absolute parent directory path (module path)
    logger.info("Creating file-to-module mapping...")
    file_to_module: Dict[str, str] = {}
    # Iterate through all the generated key information from path_to_key_info
    for key_info_obj in path_to_key_info.values(): # Iterate over KeyInfo objects
        # We only care about mapping files
        if not key_info_obj.is_directory:
            # Ensure the file has a parent path recorded
            if key_info_obj.parent_path:
                file_path = key_info_obj.norm_path
                module_path = key_info_obj.parent_path # Direct parent directory path
                file_to_module[file_path] = module_path
                logger.debug(f"Mapped file '{file_path}' to module '{module_path}'") # Optional debug log

            else:
                logger.warning(f"File '{key_info_obj.norm_path}' (Key: {key_info_obj.key_string}) has no parent path in KeyInfo. Cannot map to a module.")
    logger.info(f"File-to-module mapping created with {len(file_to_module)} entries.")

    # --- Embedding generation ---
    logger.info("Starting embedding generation...")
    try:
        # Pass path_to_key_info instead of key_map
        success = generate_embeddings(all_roots_rel, path_to_key_info, force=force_embeddings)
        results["embedding_generation"]["status"] = "success" if success else "partial_failure"
        if not success: results["message"] += " Warning: Embedding generation failed for some paths."; logger.warning("Embedding generation failed or skipped for some paths.")
        else: logger.info("Embedding generation completed successfully.")
    except Exception as e:
        results["embedding_generation"]["status"] = "error"
        results["status"] = "error" # Upgrade status to error if embedding process fails critically
        results["message"] = f"Embedding generation process failed critically: {e}"
        logger.exception(results["message"]); return results

    # --- Dependency Suggestion ---
    logger.info("Starting dependency suggestion...")
    try:
        # Start with initial suggestions (e.g., from key generation if any)
        # Use defaultdict for easier merging
        all_suggestions: Dict[str, List[Tuple[str, str]]] = defaultdict(list)
        # Merge initial suggestions if they exist
        # for src, targets in initial_suggestions.items():
        #    all_suggestions[src].extend(targets)

        # Add suggestions based on file analysis
        suggestion_count = 0
        # Use list of keys corresponding to analyzed files
        analyzed_file_paths = list(file_analysis_results.keys())
        # Use configured threshold for doc_similarity
        doc_similarity_threshold = config.get_threshold("doc_similarity") 
        for file_path_abs in analyzed_file_paths:
            file_key_info = path_to_key_info.get(file_path_abs)
            if not file_key_info:
                logger.warning(f"No key info found for analyzed file {file_path_abs}, skipping suggestion.")
                continue
            file_key_string = file_key_info.key_string # Get the actual key string

            # Pass path_to_key_info instead of key_map
            suggestions_for_file = suggest_dependencies(
                file_path_abs,
                path_to_key_info, # Pass the main map
                project_root,
                file_analysis_results, # Pass the collected analysis results
                threshold=doc_similarity_threshold
            )

            if suggestions_for_file:
                # Suggestions are returned as (target_key_string, dep_char)
                all_suggestions[file_key_string].extend(suggestions_for_file)
                suggestion_count += len(suggestions_for_file)
        logger.info(f"Generated {suggestion_count} raw suggestions from file analysis.")

        # --- Combine suggestions within each source key using priority ---
        # This step is crucial before adding reciprocal ones
        logger.debug("Combining suggestions per source key using priorities...")
        combined_suggestions_per_source: Dict[str, List[Tuple[str, str]]] = defaultdict(list)
        # Import helper here to avoid potential circular dependencies at module level
        from cline_utils.dependency_system.analysis.dependency_suggester import _combine_suggestions_with_char_priority
        for source_key, suggestion_list in all_suggestions.items():
             combined_suggestions_per_source[source_key] = _combine_suggestions_with_char_priority(suggestion_list)
        all_suggestions = combined_suggestions_per_source # Replace raw with combined
        results["dependency_suggestion"]["status"] = "success"
        logger.info("Dependency suggestion combining completed.")
    except Exception as e:
        results["status"] = "error"; results["message"] = f"Dependency suggestion failed critically: {e}"; logger.exception(results["message"]); return results

    # --- Update Trackers ---
    logger.info("Updating trackers...")
    # --- Update Mini Trackers FIRST ---
    results["tracker_update"]["mini"] = {}
    mini_tracker_paths_updated = set() # Track paths to avoid duplicates if structure overlaps

    potential_mini_tracker_dirs: Dict[str, key_manager.KeyInfo] = {}
    for code_root_abs in abs_code_roots:
        for path, key_info_obj in path_to_key_info.items(): # Iterate over KeyInfo objects
            if key_info_obj.is_directory and key_info_obj.parent_path == code_root_abs:
               potential_mini_tracker_dirs[path] = key_info_obj
            elif key_info_obj.is_directory and path == code_root_abs:
                 potential_mini_tracker_dirs[path] = key_info_obj

    logger.info(f"Identified {len(potential_mini_tracker_dirs)} potential directories for mini-trackers.")

    # Iterate through the identified module paths
    for norm_module_path, module_key_info_obj in potential_mini_tracker_dirs.items(): # Iterate over KeyInfo objects
        module_key_string = module_key_info_obj.key_string # Get key string for logging if needed
        # Check if directory is NOT empty before trying to update/create tracker
        if os.path.isdir(norm_module_path) and not _is_empty_dir(norm_module_path):
            if norm_module_path in mini_tracker_paths_updated: continue # Skip if already processed
            mini_tracker_path = tracker_io.get_tracker_path(project_root, tracker_type="mini", module_path=norm_module_path)
            logger.info(f"Updating mini tracker for module '{norm_module_path}' (Key: {module_key_string}) at: {mini_tracker_path}")
            mini_tracker_paths_updated.add(norm_module_path)
            try:
                # Update the mini-tracker. Suggestions are applied internally by update_tracker.
                # Pass the GLOBAL suggestions here. update_tracker will filter them based on the module.
                tracker_io.update_tracker(
                    output_file_suggestion=mini_tracker_path,
                    path_to_key_info=path_to_key_info, # Pass the main map
                    tracker_type="mini",
                    suggestions=all_suggestions, # Pass combined & reciprocal suggestions (keyed by key strings)
                    file_to_module=file_to_module,
                    new_keys=newly_generated_keys, # Pass list of KeyInfo objects
                    force_apply_suggestions=False,
                    use_old_map_for_migration=old_map_existed_before_gen
                )
                results["tracker_update"]["mini"][norm_module_path] = "success"
            except Exception as mini_err:
                 logger.error(f"Error updating mini tracker {mini_tracker_path}: {mini_err}", exc_info=True)
                 results["tracker_update"]["mini"][norm_module_path] = "failure"; results["status"] = "warning"
        elif os.path.isdir(norm_module_path): logger.debug(f"Skipping mini-tracker update for empty directory: {norm_module_path}")

    # --- Update Doc Tracker ---
    doc_tracker_path = tracker_io.get_tracker_path(project_root, tracker_type="doc") if doc_directories_rel else None
    if doc_tracker_path:
        logger.info(f"Updating doc tracker: {doc_tracker_path}")
        try:
            tracker_io.update_tracker(
                output_file_suggestion=doc_tracker_path,
                path_to_key_info=path_to_key_info,
                tracker_type="doc",
                suggestions=all_suggestions,
                file_to_module=file_to_module,
                new_keys=newly_generated_keys,
                force_apply_suggestions=False,
                use_old_map_for_migration=old_map_existed_before_gen
            )
            results["tracker_update"]["doc"] = "success"
        except Exception as doc_err:
            logger.error(f"Error updating doc tracker {doc_tracker_path}: {doc_err}", exc_info=True)
            results["tracker_update"]["doc"] = "failure"; results["status"] = "warning"

    # --- Update Main Tracker LAST (using aggregation) ---
    main_tracker_path = tracker_io.get_tracker_path(project_root, tracker_type="main")
    logger.info(f"Updating main tracker (with aggregation): {main_tracker_path}")
    try:
        # update_tracker for "main" will call the aggregation function internally.
        # Aggregation needs path_to_key_info and file_to_module.
        tracker_io.update_tracker(
            output_file_suggestion=main_tracker_path,
            path_to_key_info=path_to_key_info, # Pass the main map
            tracker_type="main",
            suggestions=None, # Aggregation happens internally
            file_to_module=file_to_module, # Needed by aggregation
            new_keys=newly_generated_keys, # Pass list of KeyInfo objects
            force_apply_suggestions=False,
            use_old_map_for_migration=old_map_existed_before_gen
        )
        results["tracker_update"]["main"] = "success"
    except Exception as main_err:
        logger.error(f"Error updating main tracker {main_tracker_path}: {main_err}", exc_info=True)
        results["tracker_update"]["main"] = "failure"; results["status"] = "warning"


    # --- Template Generation (e.g., Final Review Checklist) ---
    # This should be one of the last steps, after all analysis and tracker updates.
    logger.info("Starting template generation (e.g., final review checklist)...")
    try:
        checklist_generated_successfully = generate_final_review_checklist()
        if checklist_generated_successfully:
            results["template_generation"]["final_review_checklist"] = "success"
            logger.info("Final review checklist generated successfully.")
        else:
            results["template_generation"]["final_review_checklist"] = "failure"
            logger.warning("Final review checklist generation failed. Check logs for details.")
            # Optionally, change overall status to warning if checklist fails
            if results["status"] == "success":
                 results["status"] = "warning"
                 results["message"] += " Warning: Failed to generate final review checklist."

    except Exception as template_err:
        results["template_generation"]["final_review_checklist"] = "error"
        logger.error(f"Critical error during template generation: {template_err}", exc_info=True)
        if results["status"] == "success":
             results["status"] = "warning" # Or "error" if this is critical
        results["message"] += f" Critical error during template generation: {template_err}."


    # --- Final Status Check & Return ---
    if results["status"] == "success": print("Project analysis completed successfully."); results["message"] = "Project analysis completed successfully."
    elif results["status"] == "warning": print(f"Project analysis completed with warnings: {results.get('message', '')} Check logs."); # results["message"] already appended to
    else: print(f"Project analysis failed: {results.get('message', '')}. Check logs.") # For "error" status
    return results

def _is_empty_dir(dir_path: str) -> bool:
    """
    Checks if a directory is empty (contains no files or subdirectories).
    Handles potential permission errors.
    """
    try: return not os.listdir(dir_path)
    except FileNotFoundError:
        logger.warning(f"Directory not found while checking if empty: {dir_path}")
        return True # Treat non-existent as empty for skipping purposes
    except NotADirectoryError:
         logger.warning(f"Path is not a directory while checking if empty: {dir_path}")
         return True # Treat non-directory as empty for skipping purposes
    except OSError as e:
        logger.error(f"OS error checking if directory is empty {dir_path}: {e}")
        return False # Assume not empty on permission error etc. to be safe

# --- End of project_analyzer.py ---