# io/update_main_tracker.py

"""
IO module for main tracker specific data, including key filtering
and dependency aggregation logic.
"""
import os
from collections import defaultdict
from typing import Dict, List, Optional, Set, Tuple
import logging

# Import necessary functions from other modules
from cline_utils.dependency_system.core.dependency_grid import decompress, PLACEHOLDER_CHAR, DIAGONAL_CHAR
from cline_utils.dependency_system.core.key_manager import sort_keys, get_key_from_path
# *** REMOVED CIRCULAR IMPORT FROM TOP LEVEL ***
# from cline_utils.dependency_system.io.tracker_io import read_tracker_file, get_tracker_path as get_any_tracker_path
from cline_utils.dependency_system.utils.path_utils import is_subpath, normalize_path, join_paths, get_project_root
from cline_utils.dependency_system.utils.config_manager import ConfigManager

logger = logging.getLogger(__name__)

# --- Main Tracker Path ---

def get_main_tracker_path(project_root: str) -> str:
    """Gets the path to the main tracker file (module_relationship_tracker.md)."""
    config_manager = ConfigManager()
    # Default relative path, can be overridden in .clinerules
    memory_dir_rel = config_manager.get_path("memory_dir", "cline_docs/memory")
    memory_dir_abs = join_paths(project_root, memory_dir_rel)

    # *** Use get_path for the filename as well, providing a default ***
    # This assumes you might want to configure 'main_tracker_filename' in the [paths] section of .clinerules
    tracker_filename = config_manager.get_path("main_tracker_filename", "module_relationship_tracker.md")

    # Ensure tracker_filename is just the filename, not potentially a nested path
    tracker_filename = os.path.basename(tracker_filename)

    return join_paths(memory_dir_abs, tracker_filename)

# --- Key Filtering Logic ---

def main_key_filter(project_root: str, key_map: Dict[str, str]) -> Dict[str, str]:
    """
    Logic for determining which keys (representing directories) to include
    in the main tracker. Includes only directories within configured code roots.
    """
    config_manager = ConfigManager()
    root_directories_rel: List[str] = config_manager.get_code_root_directories()
    filtered_keys: Dict[str, str] = {}
    abs_code_roots: Set[str] = {normalize_path(os.path.join(project_root, p)) for p in root_directories_rel}

    if not abs_code_roots:
        logger.warning("No code root directories defined for main tracker key filtering.")
        return {}

    for key, path in key_map.items():
        norm_path: str = normalize_path(path)
        # Check if the path is a directory
        if os.path.isdir(norm_path):
            # Check if the directory is equal to or within any of the code roots
            if any(norm_path == root_dir or is_subpath(norm_path, root_dir) for root_dir in abs_code_roots):
                filtered_keys[key] = path # Use original path from key_map

    logger.debug(f"Main key filter selected {len(filtered_keys)} module keys.")
    return filtered_keys

# --- Hierarchical Helper ---

def _get_descendants(parent_key: str, hierarchy: Dict[str, List[str]]) -> Set[str]:
    """Helper to get all descendant keys (INCLUDING self) for hierarchical check."""
    descendants = {parent_key}
    # Use a proper queue/stack for BFS/DFS to avoid deep recursion issues
    queue = list(hierarchy.get(parent_key, []))
    processed = {parent_key}

    while queue:
        child = queue.pop(0) # BFS style
        if child not in processed:
            descendants.add(child)
            processed.add(child)
            # Add grandchildren to the queue
            queue.extend(hierarchy.get(child, []))
    return descendants

# --- Dependency Aggregation Logic ---

def aggregate_dependencies(project_root: str,
                           key_map: Dict[str, str], # Global key map
                           filtered_keys: Dict[str, str], # Module keys for the main tracker {key: path}
                           file_to_module: Optional[Dict[str, str]] = None # {file_abs_path: module_abs_path}
                           ) -> Dict[str, List[Tuple[str, str]]]:
    """
    Aggregates dependencies from mini-trackers to the main tracker,
    including hierarchical rollup based on directory structure.

    Args:
        project_root: Absolute path to the project root.
        key_map: Global mapping of keys to absolute paths.
        filtered_keys: The keys and paths representing modules (directories) in the main tracker.
        file_to_module: Mapping from absolute file paths to their containing module's absolute path.

    Returns:
        A dictionary where keys are source module keys and values are lists of
        (target_module_key, aggregated_dependency_char) tuples.
    """
    from cline_utils.dependency_system.io.tracker_io import read_tracker_file, get_tracker_path as get_any_tracker_path

    if not file_to_module:
        logger.error("File-to-module mapping missing, cannot perform main tracker aggregation.")
        return {}
    if not filtered_keys:
        logger.warning("No module keys provided for main tracker aggregation.")
        return {}

    config = ConfigManager()
    get_priority = config.get_char_priority
    path_to_key = {v: k for k, v in key_map.items()} # Reverse map {norm_path: key}

    # Stores module -> target_module -> (highest_priority_char, highest_priority)
    aggregated_deps_prio = defaultdict(lambda: defaultdict(lambda: (PLACEHOLDER_CHAR, -1)))

    logger.info(f"Starting aggregation for {len(filtered_keys)} main tracker modules...")

    # --- Step 1: Gather direct foreign dependencies from all relevant mini-trackers ---
    processed_mini_trackers = 0
    for source_module_key, source_module_path in filtered_keys.items():
        # Make sure source_module_path is normalized
        norm_source_module_path = normalize_path(source_module_path)
        mini_tracker_path = get_any_tracker_path(project_root, tracker_type="mini", module_path=norm_source_module_path) # Use the imported function

        if not os.path.exists(mini_tracker_path):
            # This is expected for modules without their own mini-tracker (e.g., empty dirs, or top-level code roots)
            # logger.debug(f"Mini tracker not found for module {source_module_key} at {mini_tracker_path}, skipping direct aggregation for it.")
            continue

        processed_mini_trackers += 1
        try:
            mini_data = read_tracker_file(mini_tracker_path)
            mini_grid = mini_data.get("grid", {})
            mini_keys_defined = mini_data.get("keys", {}) # Keys DEFINED in this mini-tracker {key: path}
            mini_grid_keys_list = sort_keys(list(mini_keys_defined.keys())) # Sorted list of keys in the grid

            if not mini_grid or not mini_grid_keys_list:
                logger.debug(f"Mini tracker {os.path.basename(mini_tracker_path)} grid or keys empty.")
                continue

            key_to_idx_mini = {k: i for i, k in enumerate(mini_grid_keys_list)}

            # Iterate through rows (sources) of the mini-tracker grid
            for mini_source_key, compressed_row in mini_grid.items():
                 # Ensure the source key is actually defined in this mini-tracker's grid keys
                 if mini_source_key not in key_to_idx_mini:
                     # This might happen if the tracker file is inconsistent
                     # logger.warning(f"Source key '{mini_source_key}' found in grid but not in keys list of {mini_tracker_path}")
                     continue

                 # Determine the module the source file/dir belongs to
                 mini_source_path = mini_keys_defined.get(mini_source_key)
                 if not mini_source_path: continue # Skip if path not found for source key

                 actual_source_module_path = file_to_module.get(mini_source_path)
                 if not actual_source_module_path: continue # Skip if source file has no module mapping
                 actual_source_module_key = path_to_key.get(actual_source_module_path)
                 if not actual_source_module_key: continue # Skip if source module has no key

                 # IMPORTANT CHECK: Aggregate only if the source file's module *is* the module this mini-tracker represents.
                 # This prevents double-counting if a parent's mini-tracker includes grid rows for child files.
                 if actual_source_module_key != source_module_key:
                     # logger.debug(f"Skipping row for '{mini_source_key}' in '{os.path.basename(mini_tracker_path)}' as it belongs to module '{actual_source_module_key}'")
                     continue

                 # Now process the columns (targets) for this valid source row
                 try:
                     decompressed_row = list(decompress(compressed_row))
                     if len(decompressed_row) != len(mini_grid_keys_list):
                          logger.warning(f"Row length mismatch for key '{mini_source_key}' in {mini_tracker_path}. Skipping row.")
                          continue

                     for col_idx, dep_char in enumerate(decompressed_row):
                         if dep_char in (PLACEHOLDER_CHAR, DIAGONAL_CHAR): continue # Skip non-dependencies

                         mini_target_key = mini_grid_keys_list[col_idx]
                         target_file_path = mini_keys_defined.get(mini_target_key) # Get target path from mini-tracker's defs
                         if not target_file_path: continue # Skip if target path not defined in mini-tracker

                         # Find the module the target belongs to using the GLOBAL mapping
                         target_module_path = file_to_module.get(target_file_path)
                         if not target_module_path: continue # Skip if target has no module mapping

                         target_module_key = path_to_key.get(target_module_path)
                         if not target_module_key: continue # Skip if target module has no key

                         # --- Check for FOREIGN relationship (source module != target module) ---
                         if target_module_key != source_module_key:
                             current_priority = get_priority(dep_char)
                             _stored_char, stored_priority = aggregated_deps_prio[source_module_key][target_module_key]

                             if current_priority > stored_priority:
                                 logger.debug(f"Agg Step 1: {source_module_key} -> {target_module_key} set to '{dep_char}' (prio {current_priority}) over '{_stored_char}' (prio {stored_priority}) from {os.path.basename(mini_tracker_path)}")
                                 aggregated_deps_prio[source_module_key][target_module_key] = (dep_char, current_priority)
                             elif current_priority == stored_priority and current_priority > -1:
                                  # Handle equal priority conflicts (e.g., < vs > becomes x)
                                  if {dep_char, _stored_char} == {'<', '>'}:
                                       if aggregated_deps_prio[source_module_key][target_module_key][0] != 'x':
                                           logger.debug(f"Agg Step 1: Merging '{_stored_char}'/'{dep_char}' to 'x' for {source_module_key}->{target_module_key}")
                                           aggregated_deps_prio[source_module_key][target_module_key] = ('x', current_priority)
                                  # else: Keep existing on other equal priority conflicts
                 except Exception as decomp_err:
                      logger.warning(f"Error decompressing/processing row for '{mini_source_key}' in {mini_tracker_path}: {decomp_err}")

        except Exception as read_err:
            logger.error(f"Error reading or processing mini tracker {mini_tracker_path} during aggregation: {read_err}", exc_info=True)

    logger.info(f"Processed {processed_mini_trackers} mini-trackers for direct dependencies.")

    # --- Step 2: Perform Hierarchical Rollup ---
    logger.info("Performing hierarchical rollup...")
    # Build parent -> direct children map using the filtered_keys (module keys)
    hierarchy = defaultdict(list)
    module_paths = {key: normalize_path(path) for key, path in filtered_keys.items()} # Use normalized paths for comparison
    sorted_module_keys = sort_keys(list(filtered_keys.keys()))
    for p_key in sorted_module_keys:
        p_path = module_paths[p_key]
        for c_key in sorted_module_keys:
            if p_key == c_key: continue
            c_path = module_paths[c_key]
            # Check if c_path is DIRECTLY inside p_path
            if c_path.startswith(p_path + '/') and os.path.dirname(c_path) == p_path:
                 hierarchy[p_key].append(c_key)

    # Iteratively propagate dependencies up the hierarchy
    changed_in_pass = True
    max_passes = len(sorted_module_keys) # Safety break for potential cycles
    current_pass = 0
    while changed_in_pass and current_pass < max_passes:
        changed_in_pass = False
        current_pass += 1
        logger.debug(f"Hierarchy Rollup Pass {current_pass}")
        # Iterate from potential parents down (or reverse sorted_module_keys for bottom-up)
        for parent_key in sorted_module_keys:
             # Calculate all descendants ONCE per parent per pass
             all_descendants_of_parent = _get_descendants(parent_key, hierarchy)

             # Check direct children for inheritance
             for child_key in hierarchy.get(parent_key, []):
                 # Inherit dependencies *from* the child
                 # Iterate over a copy in case the dictionary is modified elsewhere (shouldn't be here, but safer)
                 child_deps = list(aggregated_deps_prio.get(child_key, {}).items())
                 for target_key, (dep_char, priority) in child_deps:
                      # Inherit if:
                      # 1. Dependency is meaningful (priority > -1)
                      # 2. Target is NOT the parent itself
                      # 3. Target is NOT another descendant of the parent (avoid internal rollups appearing external)
                      if priority > -1 and target_key != parent_key and target_key not in all_descendants_of_parent:
                          _parent_stored_char, parent_stored_priority = aggregated_deps_prio[parent_key][target_key]

                          if priority > parent_stored_priority:
                               logger.debug(f"Rollup: {parent_key} inherits {child_key}->{target_key} ('{dep_char}' P{priority}) over ('{_parent_stored_char}' P{parent_stored_priority})")
                               aggregated_deps_prio[parent_key][target_key] = (dep_char, priority)
                               changed_in_pass = True # Mark change occurred
                          elif priority == parent_stored_priority and priority > -1:
                               # Merge < > to x on equal priority during rollup
                               if {_parent_stored_char, dep_char} == {'<', '>'}:
                                   if aggregated_deps_prio[parent_key][target_key][0] != 'x':
                                       logger.debug(f"Rollup: Merging '{_parent_stored_char}'/'{dep_char}' to 'x' for {parent_key} inheriting {child_key}->{target_key}")
                                       aggregated_deps_prio[parent_key][target_key] = ('x', priority)
                                       changed_in_pass = True
                               # else: keep existing if priorities equal and not < > conflict

    if current_pass == max_passes and changed_in_pass:
        logger.warning("Hierarchical rollup reached max passes, potentially indicating a cycle or very deep nesting.")

    # --- Step 3: Convert to final output format ---
    final_suggestions = defaultdict(list)
    for source_key, targets in aggregated_deps_prio.items():
        # Ensure source_key is actually a module key we care about
        if source_key not in filtered_keys: continue
        for target_key, (dep_char, _priority) in targets.items():
            # Ensure target key is also a module key and dependency is not placeholder
             if target_key in filtered_keys and dep_char != PLACEHOLDER_CHAR:
                final_suggestions[source_key].append((target_key, dep_char))
        final_suggestions[source_key].sort()
    logger.info("Main tracker aggregation finished.")
    # Return a standard dict, not defaultdict
    return dict(final_suggestions)

# --- Data Structure Export ---

# This structure is imported by tracker_io.py to dispatch calls
main_tracker_data = {
    "key_filter": main_key_filter,
    "dependency_aggregation": aggregate_dependencies, # Use the new aggregation function
    "get_tracker_path": get_main_tracker_path
}
# --- End of update_main_tracker.py ---