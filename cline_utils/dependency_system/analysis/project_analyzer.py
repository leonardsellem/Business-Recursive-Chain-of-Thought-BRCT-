from collections import defaultdict
import json
import os
from typing import Any, Dict, Optional, List, Tuple
import uuid
import logging
# logging.basicConfig(level=logging.DEBUG) # Removed: Configured in dependency_processor.py
from cline_utils.dependency_system.analysis.dependency_analyzer import analyze_file
from cline_utils.dependency_system.utils.batch_processor import BatchProcessor, process_items
from cline_utils.dependency_system.analysis.dependency_suggester import suggest_dependencies
from cline_utils.dependency_system.analysis.embedding_manager import generate_embeddings
from cline_utils.dependency_system.core.key_manager import get_key_from_path, generate_keys
from cline_utils.dependency_system.io.tracker_io import read_tracker_file, update_tracker, get_tracker_path
from cline_utils.dependency_system.utils.cache_manager import cached, file_modified
from cline_utils.dependency_system.utils.config_manager import ConfigManager
from cline_utils.dependency_system.utils.path_utils import is_subpath, normalize_path, get_project_root

logger = logging.getLogger(__name__)

# @cached("project_analysis",
#         key_func=lambda force_analysis=False, force_embeddings=False, **kwargs:
#         f"analyze_project:{normalize_path(get_project_root())}:{os.path.getmtime(ConfigManager().config_path)}:{force_analysis}:{force_embeddings}")
def analyze_project(force_analysis: bool = False, force_embeddings: bool = False) -> Dict[str, Any]:
    """
    Analyzes all files in a project to identify dependencies between them,
    initialize trackers, and suggest dependencies.

    Args:
        force_analysis: Bypass cache and force reanalysis
        force_embeddings: Force regeneration of embeddings
    Returns:
        Dictionary containing project-wide analysis results and status
    """
    config = ConfigManager()
    project_root = get_project_root()
    logger.info(f"Analyzing project in directory: {project_root}")

    analyzer_batch_processor = BatchProcessor()

    results = {
        "status": "success",
        "message": "",
        "tracker_initialization": {},
        "embedding_generation": {},
        "dependency_suggestion": {},
        "tracker_update": {},
        "file_analysis": {}
    }

    # Combine excluded_dirs and excluded_paths
    excluded_dirs = [normalize_path(os.path.join(project_root, p)) for p in config.get_excluded_dirs()]
    excluded_paths = config.get_excluded_paths()  # Get specific excluded paths
    all_excluded_paths = excluded_dirs + excluded_paths  # Combine both lists

    if any(normalize_path(project_root).startswith(excluded_path) for excluded_path in all_excluded_paths):
        logger.info(f"Skipping analysis of excluded project root: {project_root}")
        results["status"] = "skipped"
        results["message"] = "Project root is excluded"
        return results

    results["file_analysis"] = {}

    code_root_directories = config.get_code_root_directories() # Relative paths
    doc_directories = config.get_doc_directories() # Relative paths

    if not code_root_directories:
        results["status"] = "error"
        results["message"] = "No code root directories configured."
        logger.error(results["message"])
        return results

    if not doc_directories:
        logger.warning("No documentation directories configured. Proceeding without doc analysis.")
        # Continue analysis without doc directories if desired, or handle as error:
        # results["status"] = "error"
        # results["message"] = "No documentation directories configured."
        # logger.error(results["message"])
        # return results

    # Combine roots for key generation and analysis
    all_roots = code_root_directories + doc_directories

    # Generate keys for ALL relevant files first
    try:
        # Pass precomputed list of excluded paths (absolute) to generate_keys
        key_map, new_keys, initial_suggestions = generate_keys(all_roots, precomputed_excluded_paths=set(all_excluded_paths))
        results["tracker_initialization"]["key_generation"] = "success"
        logger.info(f"Generated {len(key_map)} keys.")
    except Exception as e:
        results["status"] = "error"
        results["message"] = f"Key generation failed: {e}"
        logger.exception(results["message"]) # Use exception for stack trace
        return results

    # Identify absolute paths for analysis based on generated key_map
    files_to_analyze_abs = []
    for root_dir_rel in all_roots:
        abs_root_dir = normalize_path(os.path.join(project_root, root_dir_rel))
        for root, _, files in os.walk(abs_root_dir):
            # Check against all excluded paths (dirs and specific paths)
            if any(normalize_path(root).startswith(excluded_path) for excluded_path in all_excluded_paths):
                logger.debug(f"Skipping excluded directory: {root}")
                continue
            for file in files:
                files_to_analyze_abs.append(normalize_path(os.path.join(root, file)))

    # Filter out files with excluded extensions BEFORE analysis
    excluded_extensions = set(config.get_excluded_extensions())
    filtered_files_to_analyze = []
    skipped_count = 0
    skipped_module_md = 0
    for file_path in files_to_analyze_abs:
        filename = os.path.basename(file_path)
        _, ext = os.path.splitext(filename)

        # Check extension first
        if ext in excluded_extensions:
            logger.debug(f"Filtering excluded extension '{ext}' for analysis: {file_path}")
            skipped_count += 1
        # Then check for mini-tracker pattern
        elif filename.endswith("_module.md"):
            logger.debug(f"Filtering mini-tracker file for analysis: {file_path}")
            skipped_module_md += 1
        else:
            filtered_files_to_analyze.append(file_path)

    logger.info(f"Collected {len(files_to_analyze_abs)} potential files. Skipped {skipped_count} by extension, {skipped_module_md} by module pattern.")
    logger.info(f"Analyzing {len(filtered_files_to_analyze)} files...")

    # Pass the FILTERED list of absolute paths to analyze_file
    file_analysis_results = process_items(filtered_files_to_analyze, analyze_file)

    # Store results using absolute paths as keys (using the filtered list for zipping)
    for file_path_abs, analysis_result in zip(filtered_files_to_analyze, file_analysis_results):
        if analysis_result and "error" not in analysis_result and "skipped" not in analysis_result:
            results["file_analysis"][file_path_abs] = analysis_result
        # else:
            # logger.warning(f"Analysis failed or skipped for {file_path_abs}: {analysis_result.get('error') if analysis_result else 'No result'}")

    logger.info(f"Completed file analysis. {len(results['file_analysis'])} files analyzed successfully.")
    # --- TEMP DEBUG ---
    import random
    sample_keys = random.sample(list(results['file_analysis'].keys()), min(5, len(results['file_analysis'])))
    for k in sample_keys:
        logger.debug(f"Sample analysis for {k}:\n{json.dumps(results['file_analysis'][k], indent=2)}")
    # --- END TEMP DEBUG ---
    # Create file_to_module mapping using absolute paths
    file_to_module = {}
    abs_code_roots = [normalize_path(os.path.join(project_root, r)) for r in code_root_directories]
    for abs_module_path in abs_code_roots:
        module_key = get_key_from_path(abs_module_path, key_map) # Use absolute path
        if module_key:
            for abs_file_path in key_map.values(): # Iterate through absolute paths from key_map
                 # Check if file is within the module path (and not the module path itself)
                if abs_file_path.startswith(abs_module_path) and abs_file_path != abs_module_path:
                    file_to_module[abs_file_path] = abs_module_path # Map absolute file path to absolute module path
        # Add module_path itself to file_to_module mapping (absolute paths)
        file_to_module[abs_module_path] = abs_module_path
    logger.debug(f"File-to-module mapping created: {len(file_to_module)} entries.")

    # Tracker initialization is now handled implicitly by the update step below

    # --- Embedding generation (Moved outside the loop) ---
    logger.info("Starting embedding generation...")
    try:
        # Pass relative root paths to generate_embeddings as it expects them
        success, _ = generate_embeddings(all_roots, force=force_embeddings)
        results["embedding_generation"]["status"] = "success" if success else "failure"
        if not success:
             results["status"] = "warning" # Downgrade status to warning if embeddings fail but rest succeeds
             results["message"] += " Embedding generation failed for some paths."
             logger.warning(results["message"])
        else:
             logger.info("Embedding generation completed.")
    except Exception as e:
        results["status"] = "error" # Upgrade status to error if embedding generation throws exception
        results["message"] = f"Embedding generation process failed: {e}"
        logger.exception(results["message"])
        # Decide whether to return or continue despite embedding failure
        # return results # Option: halt on embedding error
        logger.warning("Continuing analysis despite embedding generation failure.") # Option: continue


    # Suggest dependencies and update trackers
    logger.info("Starting dependency suggestion...")
    try:
        # Start with initial suggestions from key generation (parent-child links)
        all_suggestions: Dict[str, List[Tuple[str, str]]] = initial_suggestions # {source_key: [(target_key, char)]}

        # Add suggestions based on file analysis
        for file_key, file_path_abs in key_map.items():
            if not os.path.isfile(file_path_abs): # Skip directories for suggestion generation
                 continue

            # Call suggest_dependencies using absolute path & file analysis results
            # Returns List[Tuple[target_key, dependency_character]] now
            suggestions_for_file_with_char = suggest_dependencies(
                file_path_abs,
                key_map,
                project_root,
                results["file_analysis"], # Pass the collected analysis results
                threshold=0.65 # Semantic threshold (still used by suggest_semantic_dependencies)
            )

            # Merge results into all_suggestions, handling character priorities
            if file_key:  # Ensure source key exists
                current_suggestions = all_suggestions.setdefault(file_key, [])
                # Use a dictionary for efficient lookup and update based on priority
                target_map = {t_key: (i, t_char) for i, (t_key, t_char) in enumerate(current_suggestions)}
                priority = {'<': 3, '>': 3, 'x': 3, 'd': 3, 's': 2, '-': 1} # Higher number = higher priority

                for target_key, new_char in suggestions_for_file_with_char:
                    new_priority = priority.get(new_char, 0)
                    if target_key in target_map:
                        index, existing_char = target_map[target_key]
                        existing_priority = priority.get(existing_char, 0)
                        # Update if new char has higher priority, or if priorities are equal but chars differ (prefer explicit)
                        if new_priority > existing_priority:
                            logger.debug(f"Updating suggestion {file_key}->{target_key} from '{existing_char}' (prio {existing_priority}) to '{new_char}' (prio {new_priority})")
                            current_suggestions[index] = (target_key, new_char)
                            target_map[target_key] = (index, new_char) # Update map too
                        elif new_priority == existing_priority and new_char != existing_char and existing_char == 's':
                             # If priorities are equal but new is not 's' and old was 's', prefer the new non-'s' char
                             logger.debug(f"Prioritizing explicit char: Updating suggestion {file_key}->{target_key} from '{existing_char}' to '{new_char}'")
                             current_suggestions[index] = (target_key, new_char)
                             target_map[target_key] = (index, new_char)
                    else:
                        # Add new suggestion
                        current_suggestions.append((target_key, new_char))
                        target_map[target_key] = (len(current_suggestions) - 1, new_char) # Add to map
 
        # --- Add reciprocal '<' dependencies ---
        logger.debug("Adding reciprocal '<' dependencies...")
        priority = {'<': 3, '>': 3, 'x': 3, 'd': 3, 's': 2, '-': 1} # Ensure priority map is available
        keys_with_suggestions = list(all_suggestions.keys()) # Avoid modifying dict while iterating
        for source_key in keys_with_suggestions:
            suggestions_list = all_suggestions.get(source_key, [])
            for target_key, dep_char in suggestions_list:
                # If A > B exists...
                if dep_char == '>':
                    # Check B's suggestions for A
                    target_suggestions = all_suggestions.setdefault(target_key, [])
                    target_suggestion_map = {t: c for t, c in target_suggestions}
                    existing_char_in_target = target_suggestion_map.get(source_key)
                    existing_priority = priority.get(existing_char_in_target, 0)
                    
                    # Add B < A only if no higher/equal priority char exists from B to A
                    if existing_priority < priority['<']:
                        # Remove existing lower priority char if present
                        if existing_char_in_target:
                             target_suggestions[:] = [(t, c) for t, c in target_suggestions if t != source_key]
                        # Add the reciprocal dependency
                        logger.debug(f"Adding reciprocal suggestion: {target_key} -> {source_key} (<)")
                        target_suggestions.append((source_key, '<'))
                    elif existing_priority == priority['<'] and existing_char_in_target != '<' and existing_char_in_target != 'x':
                         # If priorities are equal (e.g., both >) make it mutual 'x'
                         logger.debug(f"Found reciprocal '>': Changing {target_key} -> {source_key} to 'x'")
                         target_suggestions[:] = [(t, 'x' if t == source_key else c) for t, c in target_suggestions]
                         # Also change the original A > B to A x B
                         original_suggestions_list = all_suggestions.get(source_key, [])
                         original_suggestions_list[:] = [(orig_t, 'x' if orig_t == target_key else orig_c) for orig_t, orig_c in original_suggestions_list]

        results["dependency_suggestion"]["status"] = "success"
        logger.info("Dependency suggestion completed.")
 
        # --- Update Trackers (Single Pass) ---
        logger.info("Updating trackers...")

        # Define tracker paths once
        main_tracker_path = get_tracker_path(project_root, tracker_type="main")
        doc_tracker_path = get_tracker_path(project_root, tracker_type="doc") if doc_directories else None

        # Update Main Tracker
        logger.info(f"Updating main tracker: {main_tracker_path}")
        # Pass all_suggestions (now with correct chars); update_tracker filters/aggregates
        update_tracker(main_tracker_path, key_map, "main", suggestions=all_suggestions, file_to_module=file_to_module, new_keys=new_keys)
        results["tracker_update"]["main"] = "success"

        # Update Doc Tracker
        if doc_tracker_path:
            logger.info(f"Updating doc tracker: {doc_tracker_path}")
            # Pass all_suggestions; update_tracker filters
            update_tracker(doc_tracker_path, key_map, "doc", suggestions=all_suggestions, new_keys=new_keys)
            results["tracker_update"]["doc"] = "success"

        # Update Mini Trackers
        results["tracker_update"]["mini"] = {}
        abs_code_roots = [normalize_path(os.path.join(project_root, r)) for r in code_root_directories] # Calculate once
        # Iterate through all keys that represent directories within code roots
        for key, path in key_map.items():
            norm_path = normalize_path(path)
            if os.path.isdir(norm_path) and any(is_subpath(norm_path, code_root) for code_root in abs_code_roots):
                if not _is_empty_dir(norm_path): # Check if directory is NOT empty
                    mini_tracker_path = get_tracker_path(project_root, tracker_type="mini", module_path=norm_path) # Use normalized path
                    logger.info(f"Updating mini tracker: {mini_tracker_path}")
                    # Pass all_suggestions; update_tracker filters using module_path ('norm_path')
                    update_tracker(mini_tracker_path, key_map, tracker_type="mini", suggestions=all_suggestions, file_to_module=file_to_module, new_keys=new_keys)
                    results["tracker_update"]["mini"][key] = "success" # Use the directory's key
                else:
                    logger.debug(f"Skipping mini-tracker creation for empty directory: {norm_path}")
    except Exception as e:
        results["status"] = "error"
        results["message"] = f"Dependency suggestion or tracker update failed: {e}"
        logger.exception(results["message"]) # Use exception for stack trace
        return results

    print("Project analysis completed.") # Changed from logger.info to print for user visibility
    results["message"] = "Project analysis completed successfully." # Add success message
    return results
def _is_empty_dir(dir_path: str) -> bool:
    """
    Checks if a directory is empty (contains no files or subdirectories).
    """
    return not os.listdir(dir_path)
# --- End of project_analyzer.py modifications ---