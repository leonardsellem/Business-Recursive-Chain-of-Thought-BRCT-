# analysis/project_analyzer.py

from collections import defaultdict
import json
import os
from typing import Any, Dict, Optional, List, Tuple

# Added imports
from cline_utils.dependency_system.core.dependency_grid import decompress
from cline_utils.dependency_system.io.tracker_io import read_tracker_file, sort_keys, get_tracker_path, update_tracker # Added get_tracker_path, update_tracker
import uuid
import logging
# logging.basicConfig(level=logging.DEBUG) # Removed: Configured in dependency_processor.py
from cline_utils.dependency_system.analysis.dependency_analyzer import analyze_file
from cline_utils.dependency_system.utils.batch_processor import BatchProcessor, process_items
from cline_utils.dependency_system.analysis.dependency_suggester import suggest_dependencies
from cline_utils.dependency_system.analysis.embedding_manager import generate_embeddings
from cline_utils.dependency_system.core.key_manager import get_key_from_path, generate_keys
# Removed tracker_io imports already covered above
from cline_utils.dependency_system.utils.cache_manager import cached, file_modified, clear_all_caches # Added clear_all_caches
from cline_utils.dependency_system.utils.config_manager import ConfigManager
from cline_utils.dependency_system.utils.path_utils import is_subpath, normalize_path, get_project_root

logger = logging.getLogger(__name__)

# Caching for analyze_project (Consider if key_func needs more refinement)
# @cached("project_analysis",
#         key_func=lambda force_analysis=False, force_embeddings=False, **kwargs:
#         f"analyze_project:{normalize_path(get_project_root())}:{(os.path.getmtime(ConfigManager().config_path) if os.path.exists(ConfigManager().config_path) else 0)}:{force_analysis}:{force_embeddings}")
def analyze_project(force_analysis: bool = False, force_embeddings: bool = False) -> Dict[str, Any]:
    """
    Analyzes all files in a project to identify dependencies between them,
    initialize trackers, and suggest dependencies.

    Args:
        force_analysis: Bypass cache and force reanalysis of files (does not bypass project analysis cache itself yet)
        force_embeddings: Force regeneration of embeddings
    Returns:
        Dictionary containing project-wide analysis results and status
    """
    # --- Initial Setup ---
    config = ConfigManager()
    project_root = get_project_root()
    logger.info(f"Starting project analysis in directory: {project_root}")

    analyzer_batch_processor = BatchProcessor()
    # Clear relevant caches if forcing re-analysis (more targeted cache clearing might be needed)
    if force_analysis:
        logger.info("Force analysis requested. Clearing relevant caches.")
        # Clear caches related to file analysis and suggestions
        clear_all_caches(categories=["file_analysis", "path_normalization", "file_types", "import_map", "resolve_source", "python_imports", "js_imports", "md_links", "html_resources", "css_imports"]) # Add more as needed
        # Note: Embedding cache clearing is handled by force_embeddings flag

    results = {
        "status": "success",
        "message": "",
        "tracker_initialization": {},
        "embedding_generation": {},
        "dependency_suggestion": {},
        "tracker_update": {},
        "file_analysis": {} # Store results keyed by normalized absolute path
    }

    # --- Exclusion Setup ---
    excluded_dirs_rel = config.get_excluded_dirs()
    excluded_paths_rel = config.get_excluded_paths() # This now includes wildcard patterns
    excluded_extensions = set(config.get_excluded_extensions())

    excluded_dirs_abs = {normalize_path(os.path.join(project_root, p)) for p in excluded_dirs_rel}
    excluded_paths_abs = {normalize_path(os.path.join(project_root, p)) for p in excluded_paths_rel}
    all_excluded_paths_abs = excluded_dirs_abs.union(excluded_paths_abs)

    # Early exit if project root itself is excluded
    norm_project_root = normalize_path(project_root)
    if any(norm_project_root == excluded_path or norm_project_root.startswith(excluded_path + '/')
           for excluded_path in all_excluded_paths_abs):
        logger.info(f"Skipping analysis of excluded project root: {project_root}")
        results["status"] = "skipped"
        results["message"] = "Project root is excluded"
        return results

    # --- Root Directories Setup ---
    code_root_directories_rel = config.get_code_root_directories()
    doc_directories_rel = config.get_doc_directories()
    # Combine unique roots
    all_roots_rel = list(set(code_root_directories_rel + doc_directories_rel)) # Use set for uniqueness

    # <<< START FIX >>>
    # Sort the relative root paths alphabetically to ensure stable order
    all_roots_rel.sort()
    logger.debug(f"Processing root directories in stable order: {all_roots_rel}")
    # <<< END FIX >>>

    if not code_root_directories_rel:
        logger.error("No code root directories configured.")
        results["status"] = "error"; results["message"] = "No code root directories configured."; return results
    if not doc_directories_rel:
        logger.warning("No documentation directories configured. Proceeding without doc analysis.")

    abs_code_roots = {normalize_path(os.path.join(project_root, r)) for r in code_root_directories_rel}
    abs_doc_roots = {normalize_path(os.path.join(project_root, r)) for r in doc_directories_rel}
    abs_all_roots = {normalize_path(os.path.join(project_root, r)) for r in all_roots_rel}


    # --- Key Generation ---
    logger.info("Generating keys...")
    try:
        # Pass the SORTED relative roots and the precomputed absolute excluded paths
        key_map, new_keys, initial_suggestions = generate_keys(
            all_roots_rel, # Pass the sorted list
            precomputed_excluded_paths=all_excluded_paths_abs
        )
        results["tracker_initialization"]["key_generation"] = "success"
        logger.info(f"Generated {len(key_map)} keys for {len(key_map)} files/dirs.")
        if new_keys:
            logger.info(f"Assigned {len(new_keys)} new keys: {', '.join(new_keys)}")
    except Exception as e:
        results["status"] = "error"; results["message"] = f"Key generation failed: {e}"; logger.exception(results["message"]); return results

    path_to_key = {v: k for k, v in key_map.items()} # Reverse map for lookups

    # --- File Identification and Filtering for Analysis ---
    logger.info("Identifying files for analysis...")
    files_to_analyze_abs = []
    # Use abs_all_roots for finding files, order doesn't strictly matter here
    for abs_root_dir in abs_all_roots:
        if not os.path.isdir(abs_root_dir):
            logger.warning(f"Configured root directory not found: {abs_root_dir}")
            continue
        # Use os.walk - order within walk is OS-dependent but shouldn't affect analysis results
        for root, dirs, files in os.walk(abs_root_dir, topdown=True):
            norm_root = normalize_path(root)
            # Filter directories based on *absolute* paths
            # Note: This filtering might affect subsequent walks if not careful, but topdown=True helps.
            dirs[:] = [d for d in dirs if normalize_path(os.path.join(norm_root, d)) not in excluded_dirs_abs]

            # Check if the current directory itself is excluded by path/pattern
            is_root_excluded_by_path = False
            # Check against the comprehensive exclusion set
            if norm_root in all_excluded_paths_abs or \
               any(is_subpath(norm_root, excluded) for excluded in excluded_dirs_abs): # Check subpath for dirs
                 is_root_excluded_by_path = True

            if is_root_excluded_by_path:
                logger.debug(f"Skipping files in excluded directory: {norm_root}")
                dirs[:] = [] # Prevent recursion into excluded directories
                continue

            # Process files in the current directory
            for file in files:
                file_path_abs = normalize_path(os.path.join(norm_root, file))
                # Check specific path exclusions, extension exclusions, and tracker naming
                if file_path_abs in all_excluded_paths_abs or \
                   os.path.splitext(file)[1].lower().lstrip('.') in excluded_extensions or \
                   file.endswith("_module.md"):
                    logger.debug(f"Skipping analysis for excluded/tracker file: {file_path_abs}")
                    pass
                else:
                    # Only analyze files that have a key assigned (meaning they weren't excluded during key gen)
                    if file_path_abs in path_to_key:
                         files_to_analyze_abs.append(file_path_abs)
                    # else: # This case should be rare if generate_keys worked correctly
                    #     logger.warning(f"File found but no key generated (might be excluded implicitly): {file_path_abs}")


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
    analyzed_count = 0
    skipped_count = 0
    error_count = 0
    for file_path_abs, analysis_result in zip(files_to_analyze_abs, analysis_results_list):
        if analysis_result:
            if "error" in analysis_result:
                logger.warning(f"Analysis error for {file_path_abs}: {analysis_result['error']}")
                error_count += 1
            elif "skipped" in analysis_result:
                # logger.debug(f"Analysis skipped for {file_path_abs}: {analysis_result.get('reason', 'No reason given')}")
                skipped_count += 1
            else:
                file_analysis_results[file_path_abs] = analysis_result
                analyzed_count += 1
        else:
            logger.warning(f"Analysis returned no result for {file_path_abs}")
            error_count += 1

    results["file_analysis"] = file_analysis_results
    logger.info(f"File analysis complete. Analyzed: {analyzed_count}, Skipped: {skipped_count}, Errors: {error_count}")

    # --- Create file_to_module mapping ---
    # Maps absolute file path -> absolute module directory path
    file_to_module: Dict[str, str] = {}
    sorted_code_roots = sorted(list(abs_code_roots), key=len, reverse=True) # Sort by length descending
    # Ensure correct mapping even for files directly in code roots
    for file_abs_path in key_map.values(): # Iterate through all known absolute paths
        found_module = False
        # Check against code roots first (most specific match)
        # Sort roots by length descending to match deepest path first
        sorted_code_roots = sorted(list(abs_code_roots), key=len, reverse=True)
        for code_root_abs in sorted_code_roots:
            if is_subpath(file_abs_path, code_root_abs):
                 # Find the *direct* child directory of code_root_abs that contains file_abs_path
                 # Or if the file is directly in code_root_abs, use code_root_abs
                 relative_path = os.path.relpath(file_abs_path, code_root_abs)
                 path_parts = relative_path.split(os.sep)

                 if len(path_parts) == 1 and os.path.isfile(file_abs_path): # File directly in code root
                      module_path = code_root_abs
                 elif len(path_parts) > 1: # File in a subdirectory
                      module_path = normalize_path(os.path.join(code_root_abs, path_parts[0]))
                 else: # Should not happen for files, but handle directories if needed
                      module_path = code_root_abs # Treat directory itself as its module path

                 # Only map if the determined module path actually exists and has a key
                 if module_path in path_to_key:
                      file_to_module[file_abs_path] = module_path
                      found_module = True
                      break # Found the most specific code module
            # Special case: the file path IS a code root directory
            elif file_abs_path == code_root_abs:
                 file_to_module[file_abs_path] = code_root_abs
                 found_module = True
                 break

        # If not found in code roots, check doc roots (less common for modules)
        # if not found_module:
        #     for doc_root_abs in abs_doc_roots:
        #         if is_subpath(file_abs_path, doc_root_abs):
        #             file_to_module[file_abs_path] = doc_root_abs # Map to the doc root itself
        #             found_module = True
        #             break


    logger.info(f"File-to-module mapping created with {len(file_to_module)} entries.")


    # --- Embedding generation ---
    logger.info("Starting embedding generation...")
    try:
        # Pass relative root paths and the global key_map
        success = generate_embeddings(all_roots_rel, key_map, force=force_embeddings)
        results["embedding_generation"]["status"] = "success" if success else "partial_failure" # More nuanced status
        if not success:
             # Don't change overall status to error, but log warning
             results["message"] += " Warning: Embedding generation failed for some paths."
             logger.warning("Embedding generation failed or skipped for some paths.")
        else:
             logger.info("Embedding generation completed successfully.")
    except Exception as e:
        results["embedding_generation"]["status"] = "error"
        results["status"] = "error" # Upgrade status to error if embedding process fails critically
        results["message"] = f"Embedding generation process failed critically: {e}"
        logger.exception(results["message"])
        return results # Halt on critical embedding error

    # --- Dependency Suggestion ---
    logger.info("Starting dependency suggestion...")
    try:
        # Start with initial suggestions (e.g., from key generation if any)
        # Use defaultdict for easier merging
        all_suggestions: Dict[str, List[Tuple[str, str]]] = defaultdict(list)
        # Merge initial suggestions if they exist
        for src, targets in initial_suggestions.items():
            all_suggestions[src].extend(targets)

        # Add suggestions based on file analysis
        suggestion_count = 0
        # Use list of keys corresponding to analyzed files
        analyzed_file_paths = list(file_analysis_results.keys())
        for file_path_abs in analyzed_file_paths:
            file_key = path_to_key.get(file_path_abs)
            if not file_key:
                logger.warning(f"No key found for analyzed file {file_path_abs}, skipping suggestion.")
                continue

            # Call suggest_dependencies using absolute path & analysis results
            suggestions_for_file = suggest_dependencies(
                file_path_abs,
                key_map,
                project_root,
                file_analysis_results, # Pass the collected analysis results
                threshold=0.65 # This threshold is primarily for semantic fallback
            )

            if suggestions_for_file:
                all_suggestions[file_key].extend(suggestions_for_file)
                suggestion_count += len(suggestions_for_file)

        logger.info(f"Generated {suggestion_count} raw suggestions from file analysis.")

        # --- Combine suggestions within each source key using priority ---
        # This step is crucial before adding reciprocal ones
        logger.debug("Combining suggestions per source key using priorities...")
        combined_suggestions_per_source: Dict[str, List[Tuple[str, str]]] = defaultdict(list)
        for source_key, suggestion_list in all_suggestions.items():
             # Use the _combine_suggestions_with_char_priority helper from suggester
             from cline_utils.dependency_system.analysis.dependency_suggester import _combine_suggestions_with_char_priority
             for source_key, suggestion_list in all_suggestions.items(): combined_suggestions_per_source[source_key] = _combine_suggestions_with_char_priority(suggestion_list)

        all_suggestions = combined_suggestions_per_source # Replace raw with combined

        # --- Add reciprocal '<'/'x' dependencies ---
        logger.debug("Adding/Merging reciprocal dependencies ('<' or 'x')...")
        get_priority = config.get_char_priority # Get priority func
        keys_with_suggestions = list(all_suggestions.keys())

        for source_key in keys_with_suggestions:
            # Use list() to avoid modifying dict during iteration if suggestion list changes
            current_source_suggestions = list(all_suggestions.get(source_key, []))

            for target_key, dep_char in current_source_suggestions:
                # Check if target exists and is not the source itself
                 if target_key not in path_to_key or target_key == source_key:
                       continue

                 target_suggestions = all_suggestions.setdefault(target_key, [])
                 # Use a map for quick lookup of existing char from target back to source
                 target_suggestion_map = {t: c for t, c in target_suggestions}
                 existing_char_in_target = target_suggestion_map.get(source_key)
                 existing_priority = get_priority(existing_char_in_target) if existing_char_in_target else -1

                 reciprocal_char = None
                 reciprocal_priority = -1

                 if dep_char == '>':
                      reciprocal_char = '<'
                      reciprocal_priority = get_priority('<')
                 elif dep_char == '<':
                      reciprocal_char = '>'
                      reciprocal_priority = get_priority('>')
                 # Add other reciprocal pairs if needed (e.g., 'd'?)

                 if reciprocal_char:
                     if reciprocal_priority > existing_priority:
                          # Remove existing lower priority char if present
                          target_suggestions[:] = [(t, c) for t, c in target_suggestions if t != source_key]
                          # Add the new reciprocal dependency
                          logger.debug(f"Reciprocal: Adding {target_key} -> {source_key} ('{reciprocal_char}') based on {source_key}->{target_key} ('{dep_char}')")
                          target_suggestions.append((source_key, reciprocal_char))
                     elif reciprocal_priority == existing_priority and existing_char_in_target != reciprocal_char:
                          # If priorities are equal and chars are opposing direct dependencies (< vs >), make it mutual 'x'
                          if {existing_char_in_target, reciprocal_char} == {'<', '>'} :
                               if existing_char_in_target != 'x': # Avoid redundant logs
                                    # Update target -> source to 'x'
                                    target_suggestions[:] = [(t, 'x' if t == source_key else c) for t, c in target_suggestions]
                                    logger.debug(f"Reciprocal: Merging {target_key} -> {source_key} to 'x' due to opposing '{existing_char_in_target}' and '{reciprocal_char}'")
                                    # Also update the original source -> target to 'x'
                                    # Need to refetch the source list as it might have been modified
                                    current_source_suggestions_for_update = all_suggestions.get(source_key, [])
                                    current_source_suggestions_for_update[:] = [(orig_t, 'x' if orig_t == target_key else orig_c) for orig_t, orig_c in current_source_suggestions_for_update]

                          # else: Keep existing for other equal priority conflicts
        results["dependency_suggestion"]["status"] = "success"
        logger.info("Dependency suggestion and reciprocal handling completed.")

        # --- Update Trackers ---
        logger.info("Updating trackers...")

        # --- Update Mini Trackers FIRST ---
        results["tracker_update"]["mini"] = {}
        mini_tracker_keys = set() # Keep track of which modules have mini-trackers
        # Iterate through module directories identified by the main tracker filter
        from cline_utils.dependency_system.io.update_main_tracker import main_tracker_data
        module_keys_for_main = main_tracker_data["key_filter"](project_root, key_map)

        for module_key, norm_path in module_keys_for_main.items():
            # Check if directory is NOT empty before trying to update/create tracker
            if os.path.isdir(norm_path) and not _is_empty_dir(norm_path):
                mini_tracker_path = get_tracker_path(project_root, tracker_type="mini", module_path=norm_path)
                logger.info(f"Updating mini tracker: {mini_tracker_path}")
                mini_tracker_keys.add(module_key) # Record that this module has a tracker
                try:
                    # Update the mini-tracker. Suggestions are applied internally by update_tracker.
                    # Pass the GLOBAL suggestions here. update_tracker will filter them based on the module.
                    update_tracker(
                        mini_tracker_path, # Suggestion for path, will be recalculated inside
                        key_map,
                        tracker_type="mini",
                        suggestions=all_suggestions, # Pass combined & reciprocal suggestions
                        file_to_module=file_to_module,
                        new_keys=new_keys
                    )
                    results["tracker_update"]["mini"][module_key] = "success"
                except Exception as mini_err:
                     logger.error(f"Error updating mini tracker {mini_tracker_path}: {mini_err}", exc_info=True)
                     results["tracker_update"]["mini"][module_key] = "failure"
                     results["status"] = "warning" # Downgrade overall status
            elif os.path.isdir(norm_path):
                logger.debug(f"Skipping mini-tracker update for empty directory: {norm_path}")
            # else: logger.warning(f"Module key {module_key} path {norm_path} is not a directory.")


        # --- Update Doc Tracker ---
        doc_tracker_path = get_tracker_path(project_root, tracker_type="doc") if doc_directories_rel else None
        if doc_tracker_path:
            logger.info(f"Updating doc tracker: {doc_tracker_path}")
            try:
                # Pass combined/reciprocal suggestions; update_tracker filters internally
                update_tracker(doc_tracker_path, key_map, "doc", suggestions=all_suggestions, file_to_module=file_to_module, new_keys=new_keys)
                results["tracker_update"]["doc"] = "success"
            except Exception as doc_err:
                logger.error(f"Error updating doc tracker {doc_tracker_path}: {doc_err}", exc_info=True)
                results["tracker_update"]["doc"] = "failure"
                results["status"] = "warning" # Downgrade overall status

        # --- Update Main Tracker LAST (using aggregation) ---
        main_tracker_path = get_tracker_path(project_root, tracker_type="main")
        logger.info(f"Updating main tracker (with aggregation): {main_tracker_path}")
        try:
            # update_tracker for "main" will call the aggregation function internally.
            # Aggregation function reads mini-trackers. We pass None for suggestions here.
            update_tracker(
                main_tracker_path,
                key_map,
                "main",
                suggestions=None, # Aggregation happens internally
                file_to_module=file_to_module, # Needed by aggregation
                new_keys=new_keys
            )
            results["tracker_update"]["main"] = "success"
        except Exception as main_err:
            logger.error(f"Error updating main tracker {main_tracker_path}: {main_err}", exc_info=True)
            results["tracker_update"]["main"] = "failure"
            results["status"] = "warning" # Downgrade overall status

    except Exception as e:
        results["status"] = "error" # Critical error during suggestions/updates
        results["message"] = f"Dependency suggestion or tracker update failed critically: {e}"
        logger.exception(results["message"])
        return results

    # --- Final Status Check & Return ---
    if results["status"] == "success": print("Project analysis completed successfully."); results["message"] = "Project analysis completed successfully."
    elif results["status"] == "warning": print("Project analysis completed with warnings. Check logs."); results["message"] = results.get("message", "") + " Project analysis completed with warnings."
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