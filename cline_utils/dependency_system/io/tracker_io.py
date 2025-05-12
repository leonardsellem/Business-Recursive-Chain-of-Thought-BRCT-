# io/tracker_io.py

"""
IO module for tracker file operations using contextual keys.
Handles reading, writing, merging and exporting tracker files.
"""

from collections import defaultdict
import datetime
import io
import json
import os
import re
import shutil
from typing import Dict, List, Tuple, Any, Optional, Set
from cline_utils.dependency_system.core.key_manager import (
    KeyInfo,
    load_global_key_map,
    load_old_global_key_map,
    validate_key,
    sort_keys as sort_key_info, # Renamed for clarity - only use for List[KeyInfo]
    get_key_from_path as get_key_string_from_path,
    sort_key_strings_hierarchically
)
from cline_utils.dependency_system.utils.path_utils import get_project_root, is_subpath, normalize_path, join_paths
from cline_utils.dependency_system.utils.config_manager import ConfigManager
from cline_utils.dependency_system.io.update_doc_tracker import doc_tracker_data
from cline_utils.dependency_system.io.update_mini_tracker import get_mini_tracker_data
from cline_utils.dependency_system.io.update_main_tracker import main_tracker_data
from cline_utils.dependency_system.utils.cache_manager import cached, check_file_modified, invalidate_dependent_entries
from cline_utils.dependency_system.core.dependency_grid import compress, create_initial_grid, decompress, validate_grid, PLACEHOLDER_CHAR, EMPTY_CHAR, DIAGONAL_CHAR
from cline_utils.dependency_system.utils.tracker_utils import aggregate_all_dependencies, find_all_tracker_paths, read_tracker_file

import logging
logger = logging.getLogger(__name__)

# --- Path Finding ---
# Caching for get_tracker_path (consider config mtime)
@cached("tracker_paths",
        key_func=lambda project_root, tracker_type="main", module_path=None:
         f"tracker_path:{normalize_path(project_root)}:{tracker_type}:{normalize_path(module_path) if module_path else 'none'}:{(os.path.getmtime(ConfigManager().config_path) if os.path.exists(ConfigManager().config_path) else 0)}")
def get_tracker_path(project_root: str, tracker_type: str = "main", module_path: Optional[str] = None) -> str:
    """
    Get the path to the appropriate tracker file based on type. Ensures path uses forward slashes.

    Args:
        project_root: Project root directory
        tracker_type: Type of tracker ('main', 'doc', or 'mini')
        module_path: The module path (required for mini-trackers)
    Returns:
        Normalized path to the tracker file using forward slashes
    """
    project_root = normalize_path(project_root)
    norm_module_path = normalize_path(module_path) if module_path else None

    if tracker_type == "main":
        return normalize_path(main_tracker_data["get_tracker_path"](project_root))
    elif tracker_type == "doc":
        return normalize_path(doc_tracker_data["get_tracker_path"](project_root))
    elif tracker_type == "mini":
        if not norm_module_path:
            raise ValueError("module_path must be provided for mini-trackers")
        # Use the dedicated function from the mini tracker data structure if available
        if "get_tracker_path" in get_mini_tracker_data():
             return normalize_path(get_mini_tracker_data()["get_tracker_path"](norm_module_path))
        else:
             # Fallback logic if get_tracker_path is not in mini_tracker_data
             module_name = os.path.basename(norm_module_path)
             raw_path = os.path.join(norm_module_path, f"{module_name}_module.md")
             return normalize_path(raw_path)
    else:
        raise ValueError(f"Unknown tracker type: {tracker_type}")

# --- File Writing ---
def write_tracker_file(tracker_path: str,
                       key_defs_to_write: Dict[str, str], # Key string -> Path string map
                       grid_to_write: Dict[str, str], # Key string -> Compressed row map
                       last_key_edit: str,
                       last_grid_edit: str = "") -> bool:
    """
    Write tracker data to a file in markdown format. Ensures directory exists.
    Performs validation before writing. Uses standard sorting for key strings.

    Args:
        tracker_path: Path to the tracker file
        key_defs_to_write: Dictionary of keys strings to path strings for definitions.
        grid_to_write: Dictionary of grid rows (compressed strings), keyed by key strings.
        last_key_edit: Last key edit identifier
        last_grid_edit: Last grid edit identifier
    Returns:
        True if successful, False otherwise
    """
    tracker_path = normalize_path(tracker_path)
    try:
        dirname = os.path.dirname(tracker_path); os.makedirs(dirname, exist_ok=True)

        # Sort key strings using standard sorting
        sorted_keys_list = sort_key_strings_hierarchically(list(key_defs_to_write.keys()))

        # --- Validate grid before writing ---
        if not validate_grid(grid_to_write, sorted_keys_list):
            logger.error(f"Aborting write to {tracker_path} due to grid validation failure.")
            return False

        # Rebuild/Fix Grid to ensure consistency with sorted_keys_list
        final_grid = {}
        expected_len = len(sorted_keys_list)
        key_to_idx = {key: i for i, key in enumerate(sorted_keys_list)}
        for row_key in sorted_keys_list:
            compressed_row = grid_to_write.get(row_key); row_list = None
            if compressed_row is not None:
                try:
                    decompressed_row = decompress(compressed_row)
                    if len(decompressed_row) == expected_len: row_list = list(decompressed_row)
                    else: logger.warning(f"Correcting grid row length for key '{row_key}' in {tracker_path} (expected {expected_len}, got {len(decompressed_row)}).")
                except Exception as decomp_err: logger.warning(f"Error decompressing row for key '{row_key}' in {tracker_path}: {decomp_err}. Re-initializing.")
            if row_list is None:
                row_list = [PLACEHOLDER_CHAR] * expected_len
                row_idx = key_to_idx.get(row_key)
                if row_idx is not None: row_list[row_idx] = DIAGONAL_CHAR
                else: logger.error(f"Key '{row_key}' not found in index map during grid rebuild!")
            final_grid[row_key] = compress("".join(row_list))

        # --- Write Content ---
        with open(tracker_path, 'w', encoding='utf-8', newline='\n') as f:
            f.write("---KEY_DEFINITIONS_START---\n"); f.write("Key Definitions:\n")
            for key in sorted_keys_list:
                f.write(f"{key}: {normalize_path(key_defs_to_write[key])}\n") # Ensure path uses forward slashes
            f.write("---KEY_DEFINITIONS_END---\n\n")

            # Write metadata
            f.write(f"last_KEY_edit: {last_key_edit}\n"); f.write(f"last_GRID_edit: {last_grid_edit}\n\n")

            # Write grid using the validated/rebuilt grid
            f.write("---GRID_START---\n")
            if sorted_keys_list:
                f.write(f"X {' '.join(sorted_keys_list)}\n")
                for key in sorted_keys_list:
                    f.write(f"{key} = {final_grid.get(key, '')}\n") # Use final_grid
            else: f.write("X \n")
            f.write("---GRID_END---\n")

        logger.info(f"Successfully wrote tracker file: {tracker_path} with {len(sorted_keys_list)} keys.")
        # Invalidate cache for this specific tracker file after writing
        invalidate_dependent_entries('tracker_data', f"tracker_data:{tracker_path}:.*")
        return True
    except IOError as e:
        logger.error(f"I/O Error writing tracker file {tracker_path}: {e}", exc_info=True); return False
    except Exception as e:
        logger.exception(f"Unexpected error writing tracker file {tracker_path}: {e}"); return False

# --- Backup ---
def backup_tracker_file(tracker_path: str) -> str:
    """
    Create a backup of a tracker file, keeping the 2 most recent backups.

    Args:
        tracker_path: Path to the tracker file
    Returns:
        Path to the backup file or empty string on failure
    """
    tracker_path = normalize_path(tracker_path)
    if not os.path.exists(tracker_path): logger.warning(f"Tracker file not found for backup: {tracker_path}"); return ""
    try:
        config = ConfigManager(); project_root = get_project_root()
        backup_dir_rel = config.get_path("backups_dir", "cline_docs/backups")
        backup_dir_abs = normalize_path(os.path.join(project_root, backup_dir_rel))
        os.makedirs(backup_dir_abs, exist_ok=True)
        timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S_%f")
        base_name = os.path.basename(tracker_path)
        backup_filename = f"{base_name}.{timestamp}.bak"
        backup_path = os.path.join(backup_dir_abs, backup_filename)
        shutil.copy2(tracker_path, backup_path)
        logger.info(f"Backed up tracker '{base_name}' to: {os.path.basename(backup_path)}")
        # --- Cleanup old backups ---
        try:
            # Find all backups for this specific base name
            backup_files = []
            for filename in os.listdir(backup_dir_abs):
                if filename.startswith(base_name + ".") and filename.endswith(".bak"):
                    # Extract timestamp (handle potential variations if needed)
                    # Assuming format base_name.YYYYMMDD_HHMMSS_ffffff.bak
                    match = re.search(r'\.(\d{8}_\d{6}_\d{6})\.bak$', filename)
                    if match:
                        timestamp_str = match.group(1)
                        try:
                            # Use timestamp object for reliable sorting
                            file_timestamp = datetime.datetime.strptime(timestamp_str, "%Y%m%d_%H%M%S_%f")
                            backup_files.append((file_timestamp, os.path.join(backup_dir_abs, filename)))
                        except ValueError: logger.warning(f"Could not parse timestamp for backup: {filename}")
            backup_files.sort(key=lambda x: x[0], reverse=True)
            if len(backup_files) > 2:
                files_to_delete = backup_files[2:]
                logger.debug(f"Cleaning up {len(files_to_delete)} older backups for '{base_name}'.")
                for _, file_path_to_delete in files_to_delete:
                    try: os.remove(file_path_to_delete)
                    except OSError as delete_error: logger.error(f"Error deleting old backup {file_path_to_delete}: {delete_error}")
        except Exception as cleanup_error: logger.error(f"Error during backup cleanup for {base_name}: {cleanup_error}")
        return backup_path
    except Exception as e:
        logger.error(f"Error backing up tracker file {tracker_path}: {e}", exc_info=True); return ""

# --- Merge Helpers ---
# _merge_grids: Replace sort_keys with sort_key_strings_hierarchically
def _merge_grids(primary_grid: Dict[str, str], secondary_grid: Dict[str, str],
                 primary_keys_list: List[str], secondary_keys_list: List[str],
                 merged_keys_list: List[str]) -> Dict[str, str]:
    """Merges two decompressed grids based on the merged key list. Primary overwrites secondary."""
    merged_decompressed_grid = {}; merged_size = len(merged_keys_list)
    key_to_merged_idx = {key: i for i, key in enumerate(merged_keys_list)}
    # Initialize merged grid with placeholders and diagonal
    for i, row_key in enumerate(merged_keys_list):
        row = [PLACEHOLDER_CHAR] * merged_size; row[i] = DIAGONAL_CHAR
        merged_decompressed_grid[row_key] = row
    config = ConfigManager(); get_priority = config.get_char_priority
    # Decompress input grids (handle potential errors)
    def safe_decompress(grid_data, keys_list):
        decomp_grid = {}; key_to_idx = {k: i for i, k in enumerate(keys_list)}; expected_len = len(keys_list)
        for key, compressed in grid_data.items():
            if key not in key_to_idx: continue
            try:
                decomp = list(decompress(compressed))
                if len(decomp) == expected_len: decomp_grid[key] = decomp
                else: logger.warning(f"Merge Prep: Incorrect length for key '{key}' (expected {expected_len}, got {len(decomp)}). Skipping row.")
            except Exception as e: logger.warning(f"Merge Prep: Failed to decompress row for key '{key}': {e}. Skipping row.")
        return decomp_grid
    primary_decomp = safe_decompress(primary_grid, primary_keys_list)
    secondary_decomp = safe_decompress(secondary_grid, secondary_keys_list)
    key_to_primary_idx = {key: i for i, key in enumerate(primary_keys_list)}
    key_to_secondary_idx = {key: i for i, key in enumerate(secondary_keys_list)}
    # Apply values based on merged keys
    for row_key in merged_keys_list:
        merged_row_idx = key_to_merged_idx[row_key]
        for col_key in merged_keys_list:
            merged_col_idx = key_to_merged_idx[col_key]
            if merged_row_idx == merged_col_idx: continue # Skip diagonal
            # Get values from original grids if they exist
            primary_val = None
            if row_key in primary_decomp and col_key in key_to_primary_idx:
                 pri_col_idx = key_to_primary_idx[col_key]
                 if pri_col_idx < len(primary_decomp[row_key]): primary_val = primary_decomp[row_key][pri_col_idx]
            secondary_val = None
            if row_key in secondary_decomp and col_key in key_to_secondary_idx:
                 sec_col_idx = key_to_secondary_idx[col_key]
                 if sec_col_idx < len(secondary_decomp[row_key]): secondary_val = secondary_decomp[row_key][sec_col_idx]
            # Determine final value (primary takes precedence over secondary, ignore placeholders)
            final_val = PLACEHOLDER_CHAR
            if primary_val is not None and primary_val != PLACEHOLDER_CHAR: final_val = primary_val
            elif secondary_val is not None and secondary_val != PLACEHOLDER_CHAR: final_val = secondary_val
            merged_decompressed_grid[row_key][merged_col_idx] = final_val
    compressed_grid = {key: compress("".join(row_list)) for key, row_list in merged_decompressed_grid.items()}
    return compressed_grid

# merge_trackers: Replace sort_keys with sort_key_strings_hierarchically
def merge_trackers(primary_tracker_path: str, secondary_tracker_path: str, output_path: Optional[str] = None) -> Optional[Dict[str, Any]]:
    """
    Merge two tracker files, with the primary taking precedence. Invalidates relevant caches.

    Args:
        primary_tracker_path: Path to the primary tracker file
        secondary_tracker_path: Path to the secondary tracker file
        output_path: Path to write the merged tracker. If None, overwrites primary.
    Returns:
        Merged tracker data as a dictionary, or None on failure.
    """
    primary_tracker_path = normalize_path(primary_tracker_path)
    secondary_tracker_path = normalize_path(secondary_tracker_path)
    output_path = normalize_path(output_path) if output_path else primary_tracker_path
    logger.info(f"Attempting to merge '{os.path.basename(primary_tracker_path)}' and '{os.path.basename(secondary_tracker_path)}' into '{os.path.basename(output_path)}'")
    # Backup before potentially overwriting
    backup_made = False
    if output_path == primary_tracker_path and os.path.exists(primary_tracker_path): backup_tracker_file(primary_tracker_path); backup_made = True
    elif output_path == secondary_tracker_path and os.path.exists(secondary_tracker_path): backup_tracker_file(secondary_tracker_path); backup_made = True
    if backup_made: logger.info(f"Backed up target file before merge: {os.path.basename(output_path)}")
    # Read both trackers (using cached read)
    primary_data = read_tracker_file(primary_tracker_path); secondary_data = read_tracker_file(secondary_tracker_path)
    # Check if data is valid
    primary_keys = primary_data.get("keys", {}); secondary_keys = secondary_data.get("keys", {})
    if not primary_keys and not secondary_keys: logger.warning("Both trackers are empty or unreadable. Cannot merge."); return None
    elif not primary_keys: logger.info(f"Primary tracker {os.path.basename(primary_tracker_path)} empty/unreadable. Using secondary tracker."); merged_data = secondary_data
    elif not secondary_keys: logger.info(f"Secondary tracker {os.path.basename(secondary_tracker_path)} empty/unreadable. Using primary tracker."); merged_data = primary_data
    else:
        logger.debug(f"Merging {len(primary_keys)} primary keys and {len(secondary_keys)} secondary keys.")
        # Merge keys (primary takes precedence for path if key exists in both)
        merged_keys_map = {**secondary_keys, **primary_keys}
        # <<< *** Use HIERARCHICAL SORT DIRECTLY *** >>>
        merged_keys_list = sort_key_strings_hierarchically(list(merged_keys_map.keys()))
        merged_compressed_grid = _merge_grids(
            primary_data.get("grid", {}), secondary_data.get("grid", {}),
            sort_key_strings_hierarchically(list(primary_keys.keys())),
            sort_key_strings_hierarchically(list(secondary_keys.keys())),
            merged_keys_list
        )
        # Merge metadata (simple precedence for now, consider timestamp comparison?)
        merged_last_key_edit = primary_data.get("last_key_edit", "") or secondary_data.get("last_key_edit", "")
        # Use a timestamp for the merge event itself?
        merged_last_grid_edit = f"Merged from {os.path.basename(primary_tracker_path)} and {os.path.basename(secondary_tracker_path)} on {datetime.datetime.now().isoformat()}"
        merged_data = {
            "keys": merged_keys_map, "grid": merged_compressed_grid,
            "last_key_edit": merged_last_key_edit, "last_grid_edit": merged_last_grid_edit,
        }
    # Write the merged tracker
    if write_tracker_file(output_path, merged_data["keys"], merged_data["grid"], merged_data["last_key_edit"], merged_data["last_grid_edit"]):
        logger.info(f"Successfully merged trackers into: {output_path}")
        # Invalidate caches related to the output file AND potentially source files if output overwrites
        invalidate_dependent_entries('tracker_data', f"tracker_data:{output_path}:.*")
        if output_path == primary_tracker_path: invalidate_dependent_entries('tracker_data', f"tracker_data:{primary_tracker_path}:.*")
        if output_path == secondary_tracker_path: invalidate_dependent_entries('tracker_data', f"tracker_data:{secondary_tracker_path}:.*")
        invalidate_dependent_entries('grid_decompress', '.*'); invalidate_dependent_entries('grid_validation', '.*'); invalidate_dependent_entries('grid_dependencies', '.*')
        return merged_data
    else:
        logger.error(f"Failed to write merged tracker to: {output_path}"); return None

# --- Read/Write Helpers ---
def _read_existing_keys(lines: List[str]) -> Dict[str, str]:
    """Reads existing key definitions from lines."""
    key_map = {}; in_section = False; key_def_start_pattern = re.compile(r'^---KEY_DEFINITIONS_START---$', re.IGNORECASE); key_def_end_pattern = re.compile(r'^---KEY_DEFINITIONS_END---$', re.IGNORECASE)
    for line in lines:
        if key_def_end_pattern.match(line.strip()): # Check stripped line for end marker
            break # Stop processing after end marker
        if in_section:
            line_content = line.strip()
            if not line_content or line_content.lower().startswith("key definitions:"): continue
            match = re.match(r'^([a-zA-Z0-9]+)\s*:\s*(.*)$', line_content)
            if match:
                k, v = match.groups()
                if validate_key(k): key_map[k] = normalize_path(v.strip())
        elif key_def_start_pattern.match(line.strip()): in_section = True
    return key_map

def _read_existing_grid(lines: List[str]) -> Dict[str, str]:
    """Reads the existing compressed grid data from lines."""
    grid_map = {}; in_section = False; grid_start_pattern = re.compile(r'^---GRID_START---$', re.IGNORECASE); grid_end_pattern = re.compile(r'^---GRID_END---$', re.IGNORECASE)
    for line in lines:
        if grid_end_pattern.match(line.strip()): break
        if in_section:
            line_content = line.strip()
            if line_content.upper().startswith("X ") or line_content == "X": continue
            match = re.match(r'^([a-zA-Z0-9]+)\s*=\s*(.*)$', line_content)
            if match:
                k, v = match.groups()
                if validate_key(k): grid_map[k] = v.strip()
        elif grid_start_pattern.match(line.strip()): in_section = True
    return grid_map

# _write_key_definitions, _write_grid: Replace sort_keys with sort_key_strings_hierarchically
def _write_key_definitions(file_obj: io.TextIOBase, key_map: Dict[str, str], sorted_keys_list: List[str]):
    """Writes the key definitions section using the pre-sorted list."""
    # <<< *** REMOVED INTERNAL SORT - Relies on passed list *** >>>
    file_obj.write("---KEY_DEFINITIONS_START---\n"); file_obj.write("Key Definitions:\n")
    for k in sorted_keys_list: # Iterate pre-sorted list
        v = key_map.get(k, "PATH_ERROR")
        if v != "PATH_ERROR": file_obj.write(f"{k}: {normalize_path(v)}\n")
        else: logger.error(f"Path error writing key def: {k}")
    file_obj.write("---KEY_DEFINITIONS_END---\n")

def _write_grid(file_obj: io.TextIOBase, sorted_keys_list: List[str], grid: Dict[str, str]):
    """Writes the grid section to the provided file object, ensuring correctness."""
    file_obj.write("---GRID_START---\n")
    if not sorted_keys_list: file_obj.write("X \n")
    else:
        file_obj.write(f"X {' '.join(sorted_keys_list)}\n")
        expected_len = len(sorted_keys_list); key_to_idx = {key: i for i, key in enumerate(sorted_keys_list)}
        for row_key in sorted_keys_list:
            compressed_row = grid.get(row_key); final_compressed_row = None
            if compressed_row is not None:
                try:
                    decompressed = decompress(compressed_row)
                    if len(decompressed) == expected_len: final_compressed_row = compressed_row
                    else: logger.warning(f"Correcting grid row length for key '{row_key}' before write...")
                except Exception: logger.warning(f"Error decompressing row for key '{row_key}' before write...")
            if final_compressed_row is None:
                 row_list = [PLACEHOLDER_CHAR] * expected_len
                 row_idx = key_to_idx.get(row_key)
                 if row_idx is not None: row_list[row_idx] = DIAGONAL_CHAR
                 final_compressed_row = compress("".join(row_list))
            file_obj.write(f"{row_key} = {final_compressed_row}\n")
    file_obj.write("---GRID_END---\n")

# --- Helper Function ---
def _is_file_key(key_string: str) -> bool:
    """Checks if a key string likely represents a file (ends with a digit)."""
    if not key_string:
        return False
    # Simple check: does the key string end with one or more digits?
    return bool(re.search(r'\d+$', key_string))

# --- Mini Tracker Specific Functions ---
def get_mini_tracker_path(module_path: str) -> str:
    """Gets the path to the mini tracker file using the function from mini_tracker_data."""
    norm_module_path = normalize_path(module_path)
    mini_data = get_mini_tracker_data()
    if "get_tracker_path" in mini_data:
        return normalize_path(mini_data["get_tracker_path"](norm_module_path))
    else:
        # Fallback if function is missing
        module_name = os.path.basename(norm_module_path)
        raw_path = os.path.join(norm_module_path, f"{module_name}_module.md")
        return normalize_path(raw_path)

# create_mini_tracker: Adapt to use path_to_key_info
def create_mini_tracker(module_path: str,
                        path_to_key_info: Dict[str, KeyInfo],
                        relevant_keys_for_grid: List[str], # Key strings needed in grid
                        new_key_strings_for_this_tracker: Optional[List[str]] = None): # Relevant NEW key STRINGS
    """Creates a new mini-tracker file with the template."""
    mini_tracker_info = get_mini_tracker_data()
    template = mini_tracker_info["template"]
    marker_start, marker_end = mini_tracker_info["markers"]
    norm_module_path = normalize_path(module_path)
    module_name = os.path.basename(norm_module_path)
    output_file = get_mini_tracker_path(norm_module_path)

    # Definitions include keys relevant to the grid, get paths from global map
    keys_to_write_defs: Dict[str, str] = {}
    for k_str in relevant_keys_for_grid:
         # Find the KeyInfo object associated with this key string
         # This is inefficient - ideally caller provides KeyInfo for relevant keys
         # For now, search the global map (can be slow for large projects)
         found_info = next((info for info in path_to_key_info.values() if info.key_string == k_str), None)
         if found_info:
              keys_to_write_defs[k_str] = found_info.norm_path
         else:
              keys_to_write_defs[k_str] = "PATH_NOT_FOUND_IN_GLOBAL_MAP"
              logger.warning(f"Key string '{k_str}' needed for mini-tracker '{os.path.basename(output_file)}' definitions not found in global path_to_key_info.")

    # Ensure module's own key is included if it exists
    module_key_string = get_key_string_from_path(norm_module_path, path_to_key_info)
    if module_key_string:
        if module_key_string not in relevant_keys_for_grid:
            relevant_keys_for_grid.append(module_key_string)
        if module_key_string not in keys_to_write_defs:
             keys_to_write_defs[module_key_string] = norm_module_path

    # Grid dimensions are based on relevant_keys_for_grid
    # <<< *** ASSUME relevant_keys_for_grid IS ALREADY SORTED HIERARCHICALLY *** >>>
    sorted_relevant_keys_list = relevant_keys_for_grid
    try:
        dirname = os.path.dirname(output_file); os.makedirs(dirname, exist_ok=True)
        with open(output_file, "w", encoding="utf-8", newline='\n') as f:
            try: f.write(template.format(module_name=module_name))
            except KeyError: f.write(template)
            if marker_start not in template: f.write("\n" + marker_start + "\n")
            f.write("\n")
            # --- Write the tracker data section ---
            _write_key_definitions(f, keys_to_write_defs, sorted_relevant_keys_list)
            f.write("\n")
            last_key_edit_msg = f"Assigned keys: {', '.join(new_key_strings_for_this_tracker)}" if new_key_strings_for_this_tracker else (f"Initial key: {module_key_string}" if module_key_string else "Initial creation")
            f.write(f"last_KEY_edit: {last_key_edit_msg}\n")
            f.write(f"last_GRID_edit: Initial creation\n\n")
            # Write the grid using the relevant keys and an initial empty grid
            initial_grid = create_initial_grid(sorted_relevant_keys_list)
            _write_grid(f, sorted_relevant_keys_list, initial_grid)
            f.write("\n")
            if marker_end not in template: f.write(marker_end + "\n")
        logger.info(f"Created new mini tracker: {output_file}")
        return True
    except IOError as e: logger.error(f"I/O Error creating mini tracker {output_file}: {e}", exc_info=True); return False
    except Exception as e: logger.exception(f"Unexpected error creating mini tracker {output_file}: {e}"); return False

# --- update_tracker (Main dispatcher) ---
def update_tracker(output_file_suggestion: str, # Path suggestion (may be ignored for mini/main)
                   path_to_key_info: Dict[str, KeyInfo], # GLOBAL path -> KeyInfo map
                   tracker_type: str = "main",
                   suggestions: Optional[Dict[str, List[Tuple[str, str]]]] = None, # Key STRINGS -> (Key STRING, char)
                   file_to_module: Optional[Dict[str, str]] = None, # norm_file_path -> norm_module_path
                   new_keys: Optional[List[KeyInfo]] = None, # GLOBAL list of new KeyInfo objects
                   force_apply_suggestions: bool = False,
                   keys_to_explicitly_remove: Optional[Set[str]] = None, # Keep this from previous step
                   use_old_map_for_migration: bool = True
                  ):
    """
    Updates or creates a tracker file based on type using contextual keys.
    Invalidates cache on changes.
    Calls tracker-specific logic for filtering, aggregation (main), and path determination.
    Uses hierarchical sorting for key strings.
    """
    project_root = get_project_root()
    config = ConfigManager()
    get_priority = config.get_char_priority

    # --- Determine Type-Specific Settings and Paths ---
    output_file = "" # Final path determined within type block
    final_key_defs: Dict[str, str] = {}
    # Key STRINGS relevant for GRID rows/columns in this tracker
    relevant_keys_for_grid: List[str] = []
    # Suggestions filtered/aggregated for THIS tracker (Key STRING -> List[(Key STRING, char)])
    final_suggestions_to_apply = defaultdict(list)
    module_path = ""
    min_positive_priority = get_priority('s')
    if min_positive_priority <= 1: logger.warning("Min priority ('s') <= 1. Using 2."); min_positive_priority = 2

    # --- Determine Type-Specific Settings and Paths---
    if tracker_type == "main":
        output_file = main_tracker_data["get_tracker_path"](project_root)
        # Filter returns Dict[norm_path, KeyInfo]
        filtered_modules_info = main_tracker_data["key_filter"](project_root, path_to_key_info)
        # Extract key strings for the grid
        relevant_keys_for_grid = [info.key_string for info in filtered_modules_info.values()]
        # Extract definitions (Key String -> Path String)
        final_key_defs = {info.key_string: info.norm_path for info in filtered_modules_info.values()}

        logger.info(f"Main tracker update for {len(relevant_keys_for_grid)} modules.")

        if not force_apply_suggestions:
            # Run aggregation ONLY if not forcing (i.e., called from analyze-project)
            logger.debug("Performing main tracker aggregation...")
            try:
                aggregated_result_paths = main_tracker_data["dependency_aggregation"](
                    project_root, path_to_key_info, filtered_modules_info, file_to_module
                )
                logger.debug("Converting aggregated path results to key string suggestions...")
                for src_path, targets in aggregated_result_paths.items():
                     src_key_info = path_to_key_info.get(src_path); src_key_string = src_key_info.key_string if src_key_info else None
                     if not src_key_string or src_key_string not in final_key_defs: continue
                     for target_path, dep_char in targets:
                          target_key_info = path_to_key_info.get(target_path); target_key_string = target_key_info.key_string if target_key_info else None
                          if target_key_string and target_key_string in final_key_defs:
                               final_suggestions_to_apply[src_key_string].append((target_key_string, dep_char))
                logger.info(f"Main tracker aggregation complete. Found {sum(len(v) for v in final_suggestions_to_apply.values())} relevant aggregated dependencies.")
            except Exception as agg_err:
                logger.error(f"Main tracker aggregation failed: {agg_err}", exc_info=True)
        else:
            # If forcing (add-dependency), use the provided suggestions directly
            logger.debug("Skipping aggregation for main tracker (force_apply=True). Using provided suggestions.")
            if suggestions:
                # Validate provided suggestions against relevant keys for the main tracker
                for src_key, deps in suggestions.items():
                    if src_key in final_key_defs:
                        valid_deps = [(tgt, char) for tgt, char in deps if tgt in final_key_defs]
                        if valid_deps:
                            final_suggestions_to_apply[src_key].extend(valid_deps)
                    else:
                         logger.warning(f"Source key '{src_key}' from forced suggestion not found in main tracker keys. Skipping.")
            else:
                 logger.warning("force_apply=True for main tracker but no suggestions provided.")
        pass

    elif tracker_type == "doc":
        output_file = doc_tracker_data["get_tracker_path"](project_root)
        # Filter returns Dict[norm_path, KeyInfo] for items under doc roots
        # This map includes KeyInfo for both files and directories within doc roots
        filtered_doc_info_map: Dict[str, KeyInfo] = doc_tracker_data["file_inclusion"](project_root, path_to_key_info)
        # Definitions include ALL filtered items (files and directories)
        final_key_defs = {info.key_string: info.norm_path for info in filtered_doc_info_map.values()}
        # Grid keys MUST match the definition keys
        relevant_keys_for_grid = list(final_key_defs.keys()) # Use all keys from definitions
        logger.info(f"Doc tracker update. Definitions: {len(final_key_defs)} items. Grid keys: {len(relevant_keys_for_grid)}.")

        # --- Filter semantic suggestions ---
        if suggestions:
             logger.debug("Pre-filtering semantic suggestions for relevance...")
             for src_key, targets in suggestions.items():
                  # Only include suggestions where source and target are in the final defs
                  if src_key in final_key_defs:
                       valid_targets = [(tgt, char) for tgt, char in targets if tgt in final_key_defs]
                       if valid_targets: final_suggestions_to_apply[src_key].extend(valid_targets)
        pass # Ensures fall-through is prevented

    # --- Mini Tracker Specific Logic ---
    elif tracker_type == "mini":
        if not file_to_module: logger.error("file_to_module mapping required for mini-tracker updates."); return
        if not path_to_key_info: logger.warning("Global path_to_key_info is empty."); return
        # Determine module path from the output file suggestion
        potential_module_path = os.path.dirname(normalize_path(output_file_suggestion))
        # Find the KeyInfo for this directory path
        module_key_info = path_to_key_info.get(potential_module_path)
        if not module_key_info or not module_key_info.is_directory:
             potential_module_path = os.path.dirname(potential_module_path)
             module_key_info = path_to_key_info.get(potential_module_path)
             if not module_key_info or not module_key_info.is_directory:
                  logger.error(f"Cannot determine valid module path/key from suggestion path: {output_file_suggestion} -> {potential_module_path}")
                  return

        module_path = potential_module_path
        module_key_string = module_key_info.key_string
        output_file = get_mini_tracker_path(module_path) # Get correct path here
        # Read existing grid data NOW, as it's needed for key determination
        existing_key_defs_mini = {}; existing_grid_mini = {}
        tracker_exists_mini = os.path.exists(output_file)
        if tracker_exists_mini:
            try:
                with open(output_file, "r", encoding="utf-8") as f_mini: mini_lines = f_mini.readlines()
                existing_key_defs_mini = _read_existing_keys(mini_lines)
                existing_grid_mini = _read_existing_grid(mini_lines)
            except Exception as e: logger.error(f"Mini Read Error: {e}"); tracker_exists_mini = False # Treat as non-existent if read fails

        # --- Determine Relevant Keys (Revised Logic) ---
        # 1. Identify Internal Keys
        internal_keys_info: Dict[str, KeyInfo] = { p: info for p, info in path_to_key_info.items() if info.parent_path == module_path or p == module_path }
        internal_keys_set = {info.key_string for info in internal_keys_info.values()}
        # Definitions include only internal keys/paths for writing later
        final_key_defs_internal = {info.key_string: info.norm_path for info in internal_keys_info.values()}
        # 2. Initialize Relevant Set with Internal Keys
        relevant_keys_strings_set = internal_keys_set.copy()
        logger.debug(f"Mini Tracker ({module_key_string}): Initial relevant keys (internal): {len(relevant_keys_strings_set)}")
        # Scan Existing Grid (uses existing_grid_mini read above)
        if tracker_exists_mini and existing_grid_mini and existing_key_defs_mini:
        # 3. Scan Existing Grid for Relevant Foreign Keys
            logger.debug(f"Scanning existing grid of '{os.path.basename(output_file)}' for relevant foreign keys (File-File links only)...") # Updated log message
            old_keys_list_mini = sort_key_strings_hierarchically(list(existing_key_defs_mini.keys()))
            old_key_to_idx_mini = {k: i for i, k in enumerate(old_keys_list_mini)}
            for row_key, compressed_row in existing_grid_mini.items():
                if row_key not in old_key_to_idx_mini: continue
                try:
                    decomp_row = list(decompress(compressed_row))
                    if len(decomp_row) != len(old_keys_list_mini):
                       logger.warning(f"Scan Existing: Length mismatch for row '{row_key}'. Skipping row scan.")
                       continue

                    row_is_internal = row_key in internal_keys_set
                    for col_idx, dep_char in enumerate(decomp_row):
                        if col_idx >= len(old_keys_list_mini): break # Safety break
                        col_key = old_keys_list_mini[col_idx]
                        if row_key == col_key: continue # Skip diagonal
                        col_is_internal = col_key in internal_keys_set

                        # --- Check if relationship should trigger foreign key persistence ---
                        # Condition 1: Not an 'n' relationship
                        if dep_char != 'n':
                            try:
                                dep_priority = get_priority(dep_char)
                                # Condition2: Link involves one internal and one external key,
                                # AND the priority meets the threshold for relevance (e.g., 's' or higher)
                                if dep_priority >= min_positive_priority:
                                    # Condition 3: Both keys represent files
                                    if _is_file_key(row_key) and _is_file_key(col_key):
                                        # Condition 4: One key is internal, the other is external
                                        if row_is_internal and not col_is_internal:
                                            if col_key not in relevant_keys_strings_set:
                                                logger.debug(f"  Adding persisted foreign FILE key '{col_key}' due to link from internal FILE '{row_key}' ('{dep_char}')")
                                                relevant_keys_strings_set.add(col_key)
                                        elif not row_is_internal and col_is_internal:
                                            if row_key not in relevant_keys_strings_set:
                                                 logger.debug(f"  Adding persisted foreign FILE key '{row_key}' due to link to internal FILE '{col_key}' ('{dep_char}')")
                                                 relevant_keys_strings_set.add(row_key)
                                    else: logger.debug(f" Skipping link ({row_key}, {col_key}): Not a file-file relationship.") # Optional detailed logging
                            except KeyError:
                                # Ignore characters not in the priority map during this scan
                                pass

                except Exception as e:
                    logger.warning(f"Scan Existing: Error processing row '{row_key}': {e}. Skipping row scan.")
            logger.debug(f"Mini Tracker ({module_key_string}): Relevant keys after scanning existing grid: {len(relevant_keys_strings_set)}")

        # 4. Process Incoming Suggestions
        config = ConfigManager(); project_root_for_exclude = get_project_root()
        excluded_dirs_abs = {normalize_path(os.path.join(project_root_for_exclude, p)) for p in config.get_excluded_dirs()}
        excluded_files_abs = set(config.get_excluded_paths())
        all_excluded_abs = excluded_dirs_abs.union(excluded_files_abs)
        abs_doc_roots: Set[str] = {normalize_path(os.path.join(project_root, p)) for p in config.get_doc_directories()}
        # Identify relevant external keys based on suggestions
        raw_suggestions = suggestions if suggestions else {}
        if raw_suggestions:
            logger.debug("Processing incoming suggestions to augment relevant keys...")
            for src_key_str, deps in raw_suggestions.items():
                source_is_internal = src_key_str in internal_keys_set
                if source_is_internal:
                    src_path = final_key_defs_internal.get(src_key_str)
                    if src_path and src_path in all_excluded_abs: continue
                    # Don't strictly need to add internal source again, but doesn't hurt
                    # relevant_keys_strings_set.add(src_key_str)
                    for target_key_str, dep_char in deps:
                        if get_priority(dep_char) >= min_positive_priority: # Only consider meaningful suggestions
                            target_info = next((info for info in path_to_key_info.values() if info.key_string == target_key_str), None)
                            if target_info and target_info.norm_path not in all_excluded_abs:
                                if target_key_str not in relevant_keys_strings_set:
                                    logger.debug(f"  Adding suggested foreign key '{target_key_str}' linked from internal '{src_key_str}'")
                                    relevant_keys_strings_set.add(target_key_str)

            all_target_keys_in_suggestions = {tgt for deps in raw_suggestions.values() for tgt, dep in deps if get_priority(dep) >= min_positive_priority}
            for target_key_str in all_target_keys_in_suggestions:
                if target_key_str in internal_keys_set:
                    target_path = final_key_defs_internal.get(target_key_str)
                    if target_path and target_path in all_excluded_abs: continue
                    for src_key_str, deps in raw_suggestions.items():
                        if any(t == target_key_str and get_priority(c) >= min_positive_priority for t, c in deps):
                            source_info = next((info for info in path_to_key_info.values() if info.key_string == src_key_str), None)
                            if source_info and source_info.norm_path not in all_excluded_abs:
                                if src_key_str not in relevant_keys_strings_set:
                                     logger.debug(f"  Adding suggested foreign key '{src_key_str}' linked to internal '{target_key_str}'")
                                     relevant_keys_strings_set.add(src_key_str)

            logger.debug(f"Mini Tracker ({module_key_string}): Relevant keys after processing suggestions: {len(relevant_keys_strings_set)}")

        # Validate relevant keys against provided map
        validated_relevant_keys_set = set()
        invalid_keys_found = set()
        logger.debug(f"Validating {len(relevant_keys_strings_set)} relevant keys against provided path_to_key_info map...")
        for k_str in relevant_keys_strings_set:
            # Check if key exists in the *input* path_to_key_info map
            # Using a generator expression for potentially better memory efficiency
            info = next((info for path, info in path_to_key_info.items() if info.key_string == k_str), None)
            if info:
                validated_relevant_keys_set.add(k_str)
            else:
                invalid_keys_found.add(k_str)

        if invalid_keys_found:
            logger.warning(f"Mini update ({os.path.basename(output_file)}): Excluding keys with no path found in provided map: {sorted(list(invalid_keys_found))}")
            # Optionally add more detail like which internal keys linked to them if needed for debugging

        # Explicitly remove keys requested for removal (e.g., from remove-key command)
        # This ensures they are removed even if they passed the path validation step
        if keys_to_explicitly_remove:
            initial_validated_count = len(validated_relevant_keys_set)
            keys_actually_removed_explicitly = validated_relevant_keys_set.intersection(keys_to_explicitly_remove)
            validated_relevant_keys_set -= keys_to_explicitly_remove # Use set difference
            if keys_actually_removed_explicitly:
                 logger.info(f"Mini update ({os.path.basename(output_file)}): Explicitly removing keys as requested: {keys_actually_removed_explicitly}")

        # 5. Finalize relevant keys and definitions based on the *validated* set
        # Use the validated set to build the final lists and definitions
        relevant_keys_for_grid = sort_key_strings_hierarchically(list(validated_relevant_keys_set))
        final_key_defs = {} # Definitions map for THIS tracker (internal + relevant VALID foreign)
        for k_str in relevant_keys_for_grid: # Iterate only validated keys
             # We know the key exists in the input map now, find its info again
             info = next((info for path, info in path_to_key_info.items() if info.key_string == k_str), None)
             if info: # Should always find info here now
                  final_key_defs[k_str] = info.norm_path
             # else: # This case should no longer happen
             #      final_key_defs[k_str] = "PATH_ERROR_POST_VALIDATION"
             #      logger.error(f"Logic Error: Key '{k_str}' passed validation but path not found.")

        logger.info(f"Mini tracker update for module {module_key_string} ({os.path.basename(module_path)}). Grid keys: {len(relevant_keys_for_grid)}.")

        # Filter suggestions: Keep only *validated* relevant for this mini-tracker's grid.
        # Relevant suggestions have:
        #   - Source internal to this module and not excluded.
        #   - Target relevant for this tracker's grid (internal or external) and not excluded.
        # This replaces the previous "foreign only" filtering.
        if raw_suggestions and file_to_module:
            logger.debug(f"Filtering mini-tracker suggestions against final valid keys ({os.path.basename(output_file)})...")
            filtered_suggestions_for_apply = defaultdict(list) # Create a new dict for filtered suggestions
            for src_key_str, deps in raw_suggestions.items():
                 # Check if source is valid and not excluded
                 source_info = next((info for info in path_to_key_info.values() if info.key_string == src_key_str), None)
                 if not source_info or source_info.norm_path in all_excluded_abs: continue
                 # Add source to final_suggestions_to_apply only if it's in the final grid keys
                 if src_key_str not in relevant_keys_for_grid: continue

                 valid_targets_for_source = []
                 for target_key_str, dep_char in deps:
                     # Check if target is valid for the final grid and not excluded
                     if target_key_str not in relevant_keys_for_grid: continue
                     if src_key_str == target_key_str or dep_char == PLACEHOLDER_CHAR: continue
                     target_info = next((info for info in path_to_key_info.values() if info.key_string == target_key_str), None)
                     # Path should exist if key is in relevant_keys_for_grid, but check defensively
                     if not target_info or target_info.norm_path in all_excluded_abs: continue
                     valid_targets_for_source.append((target_key_str, dep_char))

                     logger.debug(f"Mini filter: Adding suggestion {src_key_str} -> {target_key_str} ('{dep_char}')")

                 if valid_targets_for_source:
                     filtered_suggestions_for_apply[src_key_str].extend(valid_targets_for_source)

            final_suggestions_to_apply = filtered_suggestions_for_apply # Replace original with filtered

    else:
        raise ValueError(f"Unknown tracker type: {tracker_type}")

    # --- Read Existing Data (Common Logic) ---
    # output_file should have been determined by the type-specific blocks above
    if not output_file:
        logger.error("Output file path could not be determined for tracker update.")
        return
    check_file_modified(output_file)
    existing_key_defs = {}; existing_grid = {}; current_last_key_edit = ""; current_last_grid_edit = ""; lines = []
    tracker_exists = os.path.exists(output_file)
    if tracker_exists:
        try:
            with open(output_file, "r", encoding="utf-8") as f: lines = f.readlines()
            existing_key_defs = _read_existing_keys(lines); existing_grid = _read_existing_grid(lines)
            last_key_edit_line = next((l for l in lines if l.strip().lower().startswith("last_key_edit")), None)
            last_grid_edit_line = next((l for l in lines if l.strip().lower().startswith("last_grid_edit")), None)
            current_last_key_edit = last_key_edit_line.split(":", 1)[1].strip() if last_key_edit_line else "Unknown"
            current_last_grid_edit = last_grid_edit_line.split(":", 1)[1].strip() if last_grid_edit_line else "Unknown"
            logger.debug(f"Read existing tracker {os.path.basename(output_file)}: {len(existing_key_defs)} keys, {len(existing_grid)} grid rows.")
        except Exception as e: logger.error(f"Failed read existing tracker {output_file}: {e}. Proceeding cautiously.", exc_info=True); existing_key_defs={}; existing_grid={}; current_last_key_edit=""; current_last_grid_edit=""; lines=[]; tracker_exists=False

    # --- Create tracker if it doesn't exist ---
    if not tracker_exists:
        logger.info(f"Tracker file not found: {output_file}. Creating new file.")
        created_ok = False
        # Ensure keys for creation are sorted hierarchically
        # Use relevant_keys_for_grid determined by the type-specific logic earlier
        sorted_keys_list_for_create = sort_key_strings_hierarchically(relevant_keys_for_grid)

        # Determine relevant new keys (key STRINGS) for the creation message
        relevant_new_keys_str_list = []
        if new_keys:
            check_set = relevant_keys_strings_set if tracker_type == "mini" else set(relevant_keys_for_grid)
            relevant_new_keys_str_list = sort_key_strings_hierarchically([
                k_info.key_string for k_info in new_keys
                if k_info.key_string in check_set # Check against the set derived for this tracker
            ])

        # --- Variable to hold the newly created grid ---
        grid_after_creation = None

        if tracker_type == "mini":
            created_ok = create_mini_tracker(module_path, path_to_key_info, sorted_keys_list_for_create, relevant_new_keys_str_list)
            if created_ok:
                # Explicitly create the grid structure expected after creation
                grid_after_creation = create_initial_grid(sorted_keys_list_for_create)
        else: # Create main or doc tracker
            last_key_edit_msg = f"Assigned keys: {', '.join(relevant_new_keys_str_list)}" if relevant_new_keys_str_list else (f"Initial keys: {len(sorted_keys_list_for_create)}" if sorted_keys_list_for_create else "Initial creation")
            grid_after_creation = create_initial_grid(sorted_keys_list_for_create) # Create initial grid
            created_ok = write_tracker_file(output_file, final_key_defs, grid_after_creation, last_key_edit_msg, "Initial creation")

        if not created_ok:
            logger.error(f"Failed to create new tracker {output_file}. Aborting update.")
            return # Stop if creation failed

        # After successful creation, update state as if it existed
        existing_key_defs = final_key_defs # Use the definitions just written
        # *** Use the grid_after_creation variable ***
        existing_grid = grid_after_creation if grid_after_creation is not None else {}
        # Determine metadata message based on tracker type and keys
        if tracker_type == 'mini':
             current_last_key_edit = f"Assigned keys: {', '.join(relevant_new_keys_str_list)}" if relevant_new_keys_str_list else "Initial creation"
        else:
             current_last_key_edit = last_key_edit_msg # Use message generated in else block
        current_last_grid_edit = "Initial creation"
        tracker_exists = True # Mark as existing now

    # --- Update Existing Tracker ---
    logger.debug(f"Updating tracker: {output_file}")
    # Backup existing file (use the output_file determined correctly earlier)
    if tracker_exists: backup_tracker_file(output_file)

    # --- Key Definition Update & Sorting ---
    # Use hierarchical sort for the final list of keys determined for this tracker
    final_sorted_keys_list = sort_key_strings_hierarchically(list(final_key_defs.keys()))

    # --- Determine Key Changes for Metadata ---
    # Use existing_key_defs read from file (or after creation)
    existing_keys_in_file_set = set(existing_key_defs.keys())
    keys_in_final_grid_set = set(final_sorted_keys_list) # Keys determined relevant NOW
    added_keys = keys_in_final_grid_set - existing_keys_in_file_set
    removed_keys = existing_keys_in_file_set - keys_in_final_grid_set
    # Determine relevant new keys (key STRINGS) for metadata message
    relevant_new_keys_str_list = []
    if new_keys:
        relevant_new_keys_str_list = sort_key_strings_hierarchically([
            k_info.key_string for k_info in new_keys
            if k_info.key_string in keys_in_final_grid_set # Check against FINAL set
        ])
    # Update metadata message logic
    final_last_key_edit = current_last_key_edit
    if relevant_new_keys_str_list: final_last_key_edit = f"Assigned keys: {', '.join(relevant_new_keys_str_list)}" # Prioritize message about NEW keys added globally
    elif added_keys or removed_keys:
        change_parts = []
        if added_keys: change_parts.append(f"Added {len(added_keys)} keys")
        if removed_keys: change_parts.append(f"Removed {len(removed_keys)} keys")
        final_last_key_edit = f"Keys updated: {'; '.join(change_parts)}"

    # --- Grid Structure Update ---
    final_grid = {}
    grid_structure_changed = bool(added_keys or removed_keys)
    final_last_grid_edit = current_last_grid_edit # Start with existing
    if grid_structure_changed: final_last_grid_edit = f"Grid structure updated ({datetime.datetime.now().isoformat()})"
    temp_decomp_grid = {}
    # Use hierarchical sort for the list of keys that were in the old file
    old_keys_list = sort_key_strings_hierarchically(list(existing_key_defs.keys()))
    old_key_to_idx = {k: i for i, k in enumerate(old_keys_list)}; final_key_to_idx = {k: i for i, k in enumerate(final_sorted_keys_list)}

    # Initialize new grid structure based on the FINAL sorted list
    for row_key in final_sorted_keys_list:
        row_list = [PLACEHOLDER_CHAR] * len(final_sorted_keys_list); row_idx = final_key_to_idx.get(row_key)
        if row_idx is not None: row_list[row_idx] = DIAGONAL_CHAR
        temp_decomp_grid[row_key] = row_list

    # <<< --- COMMON Structural Dependency Calculation & Application --- >>>
    structural_deps = defaultdict(dict)
    if tracker_type == "doc" or tracker_type == "mini":
        # Build Key String -> KeyInfo map for keys in THIS grid
        key_string_to_info_local = {
            k_str: path_to_key_info.get(final_key_defs.get(k_str))
            for k_str in final_sorted_keys_list
            if final_key_defs.get(k_str) and path_to_key_info.get(final_key_defs.get(k_str))
        }
        if key_string_to_info_local: # Proceed only if map is not empty
            logger.debug(f"Calculating structural dependencies for {tracker_type} tracker...")
            for row_key in final_sorted_keys_list:
                row_info = key_string_to_info_local.get(row_key)
                if not row_info or not row_info.is_directory: continue # Rules originate from directories

                for col_key in final_sorted_keys_list:
                    if row_key == col_key: continue
                    col_info = key_string_to_info_local.get(col_key)
                    if not col_info: continue
                    # Skip if already processed (due to reciprocal setting)
                    if structural_deps.get(row_key, {}).get(col_key) is not None: continue
                    # Check parent-child relationship
                    if is_subpath(col_info.norm_path, row_info.norm_path):
                        structural_deps[row_key][col_key] = 'x'
                        structural_deps[col_key][row_key] = 'x'
                    # Apply 'n' rule ONLY for doc trackers for unrelated dir/file pairs
                    elif tracker_type == "doc":
                        structural_deps[row_key][col_key] = 'n'
                        structural_deps[col_key][row_key] = 'n'

            # Apply calculated rules to the temp_decomp_grid
            applied_count = 0
            logger.debug(f"Applying structural dependency rules to grid...")
            for row_key, cols in structural_deps.items():
                 if row_key in final_key_to_idx:
                     for col_key, dep_char in cols.items():
                          if col_key in final_key_to_idx:
                              row_idx = final_key_to_idx[row_key]; col_idx = final_key_to_idx[col_key]
                              if row_idx != col_idx:
                                   # Apply directly, overwriting placeholder
                                   temp_decomp_grid[row_key][col_idx] = dep_char
                                   applied_count += 1
            logger.debug(f"Applied {applied_count} structural rules.") # Count individual cell changes

    # --- Copy old values (REVISED LOGIC: Prioritize _old.json map) ---
    logger.info("Copying old grid values (prioritizing _old.json map)...")

    # 1. Determine the authoritative source for OLD key -> path mapping based on flag
    old_key_string_to_path: Optional[Dict[str, str]] = None
    using_old_map = False # Flag for logging method used

    if use_old_map_for_migration:
        logger.debug("Attempting to use '_old.json' map for migration as requested.")
        old_path_to_key_info = load_old_global_key_map()
        if old_path_to_key_info:
            old_key_string_to_path = {info.key_string: info.norm_path for info in old_path_to_key_info.values()}
            logger.info("Using 'global_key_map_old.json' as the primary source for old key-path mapping.")
            using_old_map = True
            if len(old_key_string_to_path) != len(old_path_to_key_info):
                 logger.warning("Potential duplicate key strings detected in 'global_key_map_old.json'. Mapping might be ambiguous.")
        else:
            logger.warning("'_old.json' map not found or failed to load, even though requested. Falling back to tracker's existing key definitions.")
            # Fall through to use existing_key_defs below
    else:
        logger.info("'_old.json' map explicitly skipped for migration (likely first run). Using tracker definitions.")
        # Flag indicates we should use fallback directly

    # Fallback logic (executed if use_old_map_for_migration was False OR if loading failed above)
    if old_key_string_to_path is None: # Check if primary method failed or was skipped
        if existing_key_defs:
            old_key_string_to_path = existing_key_defs.copy()
            logger.info(f"Using tracker's own definitions ({len(old_key_string_to_path)} keys) as fallback source.")
        else:
            logger.error("Cannot copy old grid values: Neither usable '_old.json' map nor tracker's existing definitions are available.")
            old_key_string_to_path = None # Ensure it's None if fallback also fails

    # 2. Create reverse map for NEW key definitions (Path -> New Index)
    path_to_final_idx: Dict[str, int] = {
        norm_path: final_key_to_idx[key_str]
        for key_str, norm_path in final_key_defs.items()
        if key_str in final_key_to_idx # Ensure key is actually in the final index map
    }

    # 3. Proceed with copy ONLY if we have a valid old key->path map
    copied_values_count = 0; skipped_due_to_no_old_path = 0; skipped_due_to_path_gone = 0; skipped_due_to_non_placeholder = 0; row_processing_errors = 0
    if old_key_string_to_path is not None:
        # Iterate through the OLD grid data (key -> compressed row)
        for old_row_key, compressed_row in existing_grid.items():
            # A. Find the path associated with the OLD row key using the chosen source
            old_row_path = old_key_string_to_path.get(old_row_key)
            if not old_row_path:
                # This row key existed in the old grid but not in the authoritative old key map
                skipped_due_to_no_old_path += 1
                logger.debug(f"  Skip row '{old_row_key}': Path not found in authoritative old map.")
                continue

            # Find the NEW index for this OLD path
            new_row_idx = path_to_final_idx.get(old_row_path)
            if new_row_idx is None:
                skipped_due_to_path_gone += 1
                logger.debug(f"  Skip row path '{old_row_path}' (old key '{old_row_key}'): Path no longer in final definitions.")
                continue

            # Find the corresponding NEW key string (needed for accessing temp_decomp_grid row)
            new_row_key = final_sorted_keys_list[new_row_idx] # Get key from index

            try:
                decomp_row = list(decompress(compressed_row))
                # Check length against the OLD key list
                if len(decomp_row) != len(old_keys_list):
                    logger.warning(f"Grid Copy: Row length mismatch for '{old_row_key}'! Expected {len(old_keys_list)}, Got {len(decomp_row)}. Skipping row copy.")
                    continue

                # Iterate through the OLD column indices
                for old_col_idx, value in enumerate(decomp_row):
                    if value in (DIAGONAL_CHAR, PLACEHOLDER_CHAR, EMPTY_CHAR): continue

                    # Get the OLD key and path for this column index
                    if old_col_idx >= len(old_keys_list): continue # Safety
                    old_col_key = old_keys_list[old_col_idx]
                    old_col_path = old_key_string_to_path.get(old_col_key)
                    if not old_col_path:
                        skipped_due_to_no_old_path += 1
                        logger.debug(f"  Skip cell ({old_row_key}[{old_col_idx}]): Old col key '{old_col_key}' path not found.")
                        continue

                    # Find the NEW index for this OLD path
                    new_col_idx = path_to_final_idx.get(old_col_path)
                    if new_col_idx is None:
                        skipped_due_to_path_gone += 1
                        logger.debug(f"  Skip cell ({old_row_key}[{old_col_idx}]): Col path '{old_col_path}' (old key '{old_col_key}') no longer in final definitions.")
                        continue

                    # *** THE CRITICAL COPY STEP ***
                    # Use the determined NEW indices to place the OLD value
                    # into the correct cell of the NEW grid structure.
                    if new_row_idx != new_col_idx: # Ensure not diagonal
                        target_cell_current_value = temp_decomp_grid[new_row_key][new_col_idx]
                        if target_cell_current_value == PLACEHOLDER_CHAR:
                            temp_decomp_grid[new_row_key][new_col_idx] = value
                            copied_values_count += 1
                            logger.debug(f"  Copied '{value}' from ({old_row_key},{old_col_key}) path ({old_row_path},{old_col_path}) to ({new_row_key},{new_col_idx})")
                        else:
                            skipped_due_to_non_placeholder += 1
                            logger.debug(f"  Skip cell ({old_row_key}[{old_col_idx}]): Target ({new_row_key},{new_col_idx}) already has '{target_cell_current_value}'.")

            except Exception as e:
                logger.warning(f"Grid Rebuild: Error processing row '{old_row_key}' in {output_file}: {e}. Skipping copy.", exc_info=False)
                row_processing_errors += 1
    else:
        # This block executes if old_key_string_to_path remained None
        logger.warning("Skipping grid value copy entirely as no authoritative old key-path mapping could be determined.")

    log_method = 'None'
    if old_key_string_to_path is not None: log_method = '_old.json map' if using_old_map else 'Tracker Fallback'
    logger.info(f"Finished copying old grid values. Method: {log_method}. Copied: {copied_values_count}, Skipped (No Old Path): {skipped_due_to_no_old_path}, Skipped (Path Gone): {skipped_due_to_path_gone}, Skipped (Target Filled): {skipped_due_to_non_placeholder}, RowErrors={row_processing_errors}")

    # Import Established Relationships for Foreign Keys (Mini-Trackers Only)
    imported_rels_count = 0
    auto_set_n_count = 0 # Counter for automatic 'n' settings
    if tracker_type == "mini" and module_path: # Ensure we have module_path
        logger.debug(f"Mini Tracker ({module_key_string}): Importing/Resolving relationships for foreign key pairs...")

        # Identify foreign keys in the current grid
        foreign_keys_in_grid: Dict[str, KeyInfo] = {} # key_string -> KeyInfo
        for key_str in final_sorted_keys_list:
            key_info = path_to_key_info.get(final_key_defs.get(key_str))
            # Check if key_info exists and if its parent is different from the current module
            if key_info and key_info.parent_path != module_path:
                foreign_keys_in_grid[key_str] = key_info

        foreign_key_list = list(foreign_keys_in_grid.keys())
        logger.debug(f"Found {len(foreign_key_list)} foreign keys in grid: {foreign_key_list}") # Uncomment for verbose logging

        # Get doc directories for checking home tracker type
        abs_doc_roots_set = {normalize_path(os.path.join(project_root, p)) for p in config.get_doc_directories()}

        # Helper function to check if a path is within ANY doc root
        def is_path_in_doc_roots(item_path: str) -> bool:
            norm_item_path = normalize_path(item_path)
            # Check if item path is equal to or a subpath of any doc root
            return any(is_subpath(norm_item_path, doc_root) or norm_item_path == doc_root
                       for doc_root in abs_doc_roots_set)

        # Define character sets for clarity in conditions
        OVERWRITABLE_CHARS = {'p', 's', 'S', 'n'}
        POSITIVE_IMPORT_CHARS = {'<', '>', 'x', 'd'}

        # Iterate through unique pairs of foreign keys
        for i in range(len(foreign_key_list)):
            fk1_str = foreign_key_list[i]
            info1 = foreign_keys_in_grid[fk1_str] # We know this key exists in the map
            fk1_idx = final_key_to_idx[fk1_str] # Get index in the current (final) grid

            for j in range(i + 1, len(foreign_key_list)):
                fk2_str = foreign_key_list[j]
                info2 = foreign_keys_in_grid[fk2_str] # We know this key exists in the map
                fk2_idx = final_key_to_idx[fk2_str] # Get index in the current (final) grid

                # Get current characters from the mini-tracker's temp grid
                current_char_12 = temp_decomp_grid[fk1_str][fk2_idx]
                current_char_21 = temp_decomp_grid[fk2_str][fk1_idx]

                # Determine the shared home tracker based on parent paths
                home_tracker_path: Optional[str] = None
                parent1 = info1.parent_path
                parent2 = info2.parent_path

                is_fk1_doc = is_path_in_doc_roots(info1.norm_path)
                is_fk2_doc = is_path_in_doc_roots(info2.norm_path)

                if is_fk1_doc and is_fk2_doc:
                    # Case 1: Both items are documentation items -> Home is doc_tracker.md
                    home_tracker_path = get_tracker_path(project_root, tracker_type="doc")
                    logger.debug(f"  Pair ({fk1_str}, {fk2_str}): Both in doc roots. Home: Doc Tracker.")
                elif not is_fk1_doc and not is_fk2_doc and parent1 and parent1 == parent2:
                    # Case 2: Both items are code items AND share the same direct parent directory
                    if parent1 != module_path: # Ensure shared parent isn't the current module itself
                        home_tracker_path = get_tracker_path(project_root, tracker_type="mini", module_path=parent1)
                        logger.debug(f"  Pair ({fk1_str}, {fk2_str}): Shared code parent '{parent1}'. Home: Mini Tracker.")
                # else: # Case 3: Mix or different parents -> No single shared home tracker
                    logger.debug(f"  Pair ({fk1_str}, {fk2_str}): No shared home tracker identified.")
                    home_tracker_path = None

                # Attempt to read relationship from home tracker
                home_char_12 = PLACEHOLDER_CHAR
                home_char_21 = PLACEHOLDER_CHAR
                found_home_rel_12 = False # Flag if non-'p' relation was found
                found_home_rel_21 = False

                if home_tracker_path and os.path.exists(home_tracker_path):
                    logger.debug(f"  Reading home tracker: {os.path.basename(home_tracker_path)}")
                    home_data = read_tracker_file(home_tracker_path)
                    home_keys = home_data.get("keys", {})
                    home_grid = home_data.get("grid", {})

                    # Check if BOTH keys exist in the home tracker's definitions
                    if home_keys and home_grid and fk1_str in home_keys and fk2_str in home_keys:
                        # Get sorted keys and index map for the home tracker
                        home_keys_list = sort_key_strings_hierarchically(list(home_keys.keys()))
                        home_key_to_idx = {k: idx for idx, k in enumerate(home_keys_list)}
                        home_fk1_idx = home_key_to_idx.get(fk1_str)
                        home_fk2_idx = home_key_to_idx.get(fk2_str)

                        # Ensure indices were found (should be if keys are in map)
                        if home_fk1_idx is not None and home_fk2_idx is not None:
                            # Extract char 1->2 safely
                            row1_comp = home_grid.get(fk1_str)
                            if row1_comp:
                                try:
                                    row1_decomp = decompress(row1_comp)
                                    if len(row1_decomp) == len(home_keys_list) and home_fk2_idx < len(row1_decomp):
                                        extracted_char = row1_decomp[home_fk2_idx]
                                        home_char_12 = extracted_char # Store extracted char
                                        if extracted_char != PLACEHOLDER_CHAR:
                                            found_home_rel_12 = True # Mark non-'p' found
                                except Exception as e: logger.warning(f"  Error decompressing home row {fk1_str}: {e}")

                            # Extract char 2->1 safely
                            row2_comp = home_grid.get(fk2_str)
                            if row2_comp:
                                try:
                                    row2_decomp = decompress(row2_comp)
                                    if len(row2_decomp) == len(home_keys_list) and home_fk1_idx < len(row2_decomp):
                                        extracted_char = row2_decomp[home_fk1_idx]
                                        home_char_21 = extracted_char # Store extracted char
                                        if extracted_char != PLACEHOLDER_CHAR:
                                            found_home_rel_21 = True # Mark non-'p' found
                                except Exception as e: logger.warning(f"  Error decompressing home row {fk2_str}: {e}")
                        # else: logger.warning(f"  Keys {fk1_str} or {fk2_str} missing index in home tracker {os.path.basename(home_tracker_path)}.")
                    # else: logger.debug(f"  Keys {fk1_str} or {fk2_str} not found in home tracker {os.path.basename(home_tracker_path)} keys/grid.")
                # elif home_tracker_path: logger.debug(f"  Home tracker not found or empty: {home_tracker_path}")

                # --- Determine Final Characters and Apply ---
                final_char_12 = current_char_12 # Start with current value
                final_char_21 = current_char_21
                changed_12 = False
                changed_21 = False

                # --- Determine final value for 1 -> 2 ---
                # Rule 1: Import positive relation from home over overwritable chars
                if current_char_12 in OVERWRITABLE_CHARS and home_char_12 in POSITIVE_IMPORT_CHARS:
                    logger.debug(f"    Importing positive {fk1_str}->{fk2_str}: '{home_char_12}' over existing '{current_char_12}' from {os.path.basename(home_tracker_path or 'N/A')}")
                    final_char_12 = home_char_12
                # Rule 1b: Import 'n' from home only over p/s/S
                elif current_char_12 in ('p', 's', 'S') and home_char_12 == 'n':
                    logger.debug(f"    Importing 'n' {fk1_str}->{fk2_str}: '{home_char_12}' over existing '{current_char_12}' from {os.path.basename(home_tracker_path or 'N/A')}")
                    final_char_12 = home_char_12
                # Rule 2: Explicitly set 'n' if current is 'p' AND relationship wasn't *found defined* in home
                elif current_char_12 == PLACEHOLDER_CHAR and not found_home_rel_12:
                    logger.info(f"  Auto-setting {fk1_str}->{fk2_str} to 'n' (no defined relationship found in home tracker).")
                    final_char_12 = 'n'
                # --- If none of the above, final_char_12 remains current_char_12 ---

                # --- Determine final value for 2 -> 1 ---
                # Rule 1: Import positive relation from home over overwritable chars
                if current_char_21 in OVERWRITABLE_CHARS and home_char_21 in POSITIVE_IMPORT_CHARS:
                    logger.debug(f"    Importing positive {fk2_str}->{fk1_str}: '{home_char_21}' over existing '{current_char_21}' from {os.path.basename(home_tracker_path or 'N/A')}")
                    final_char_21 = home_char_21
                 # Rule 1b: Import 'n' from home only over p/s/S
                elif current_char_21 in ('p', 's', 'S') and home_char_21 == 'n':
                    logger.debug(f"    Importing 'n' {fk2_str}->{fk1_str}: '{home_char_21}' over existing '{current_char_21}' from {os.path.basename(home_tracker_path or 'N/A')}")
                    final_char_21 = home_char_21
                # Rule 2: Explicitly set 'n' if current is 'p' AND relationship wasn't *found defined* in home
                elif current_char_21 == PLACEHOLDER_CHAR and not found_home_rel_21:
                    logger.info(f"  Auto-setting {fk2_str}->{fk1_str} to 'n' (no defined relationship found in home tracker).")
                    final_char_21 = 'n'
                # --- If none of the above, final_char_21 remains current_char_21 ---

                # --- Apply changes if the final determined character is different from the current one ---
                if temp_decomp_grid[fk1_str][fk2_idx] != final_char_12:
                    temp_decomp_grid[fk1_str][fk2_idx] = final_char_12
                    imported_rels_count += 1 # Count any cell change
                    changed_12 = True

                if temp_decomp_grid[fk2_str][fk1_idx] != final_char_21:
                    temp_decomp_grid[fk2_str][fk1_idx] = final_char_21
                    imported_rels_count += 1
                    changed_21 = True

                # Log once per pair if any change occurred
                if changed_12 or changed_21:
                     logger.info(f"  Updated relationship for ({fk1_str}, {fk2_str}) based on home tracker / auto-n rule. New: ('{final_char_12}', '{final_char_21}')")

        logger.info(f"Finished importing/resolving relationships. Updated cell count: {imported_rels_count}.")

    # --- Apply Suggestions (Includes Reciprocal/Mutual Logic & Modified Conflict Handling) ---
    suggestion_applied = False
    # Initialize variables to store details for the specific manual update message
    applied_manual_source = None
    applied_manual_targets = [] # Use a list to collect targets
    applied_manual_dep_type = None

    if final_suggestions_to_apply:
        logger.debug(f"Applying {sum(len(v) for v in final_suggestions_to_apply.values())} suggestions to grid for {output_file} (Force Apply: {force_apply_suggestions})")
        key_to_idx = final_key_to_idx

        # Iterate through suggestions and apply them, handling reciprocals on the fly
        # <<< Restore variable name consistency if needed (row_key is source_key here) >>>
        for source_key, deps in final_suggestions_to_apply.items():
            if source_key not in key_to_idx: continue
            current_decomp_row = temp_decomp_grid.get(source_key)
            if not current_decomp_row: continue
            row_idx = key_to_idx[source_key] # Use source_key for row index

            # <<< Restore variable name consistency if needed (col_key is target_key here) >>>
            for target_key, dep_char in deps:
                if target_key not in key_to_idx: continue
                if source_key == target_key: continue
                col_idx = key_to_idx[target_key] # Use target_key for column index
                existing_char_in_grid = current_decomp_row[col_idx]

                applied_this_iter = False
                final_char_to_apply = dep_char # Start with the suggested char
                upgrade_to_x = False # Flag to track if 'x' upgrade occurs

                # --- Determine if suggestion should be applied ---
                should_apply_suggestion = False
                if force_apply_suggestions:
                    # Apply if forcing, suggestion isn't placeholder, and it's different
                    if dep_char != PLACEHOLDER_CHAR and existing_char_in_grid != dep_char:
                        should_apply_suggestion = True
                        logger.debug(f"Force apply triggered for {row_key}->{col_key} ('{dep_char}') over ('{existing_char_in_grid}')")
                elif existing_char_in_grid == PLACEHOLDER_CHAR and dep_char != PLACEHOLDER_CHAR:
                     # Apply if grid is placeholder and suggestion isn't
                     should_apply_suggestion = True
                elif not force_apply_suggestions and existing_char_in_grid not in (PLACEHOLDER_CHAR, DIAGONAL_CHAR) and existing_char_in_grid != dep_char:
                    # This block now handles ONLY the non-forced conflict scenario
                    try:
                        existing_priority = get_priority(existing_char_in_grid)
                        suggestion_priority = get_priority(dep_char)
                        # Apply if suggestion is stronger AND existing is NOT 'n'
                        if existing_char_in_grid != 'n' and suggestion_priority > existing_priority:
                            logger.info(f"Suggestion Conflict RESOLVED in {os.path.basename(output_file)}: Applying '{dep_char}' (prio {suggestion_priority}) over '{existing_char_in_grid}' (prio {existing_priority}) for {source_key}->{target_key}.")
                            should_apply_suggestion = True # Set flag to apply suggestion
                        else: logger.debug(f"Suggestion Conflict Ignored: Grid '{existing_char_in_grid}' kept over sugg '{dep_char}' for {source_key}->{target_key}.")
                    except Exception as e: logger.error(f"Priority check error: {e}. Grid value kept.")

                # --- Apply suggestion if flag is set ---
                if should_apply_suggestion:
                    # Check for mutual '<' or '>' requiring 'x' upgrade FIRST
                    if dep_char in ('<', '>'):
                        reverse_decomp_row = temp_decomp_grid.get(target_key)
                        if reverse_decomp_row and row_idx < len(reverse_decomp_row):
                             char_in_reverse = reverse_decomp_row[row_idx]
                             # Check if the reverse direction ALSO has the SAME directional char
                             if char_in_reverse == dep_char:
                                 logger.debug(f"Mutual: Merging {target_key} -> {source_key} to 'x' due to matching '{dep_char}' dependencies.")
                                 logger.debug(f"Mutual: Merging {source_key} -> {target_key} to 'x' due to matching '{dep_char}' dependencies.")
                                 final_char_to_apply = 'x'
                                 # Update the reverse direction in the grid immediately
                                 reverse_decomp_row[row_idx] = 'x'
                                 suggestion_applied = True; upgrade_to_x = True

                    # Apply the final character (original suggestion or 'x')
                    if existing_char_in_grid != final_char_to_apply: # Check again in case 'x' upgrade happened
                        logger.debug(f"Applying to grid: {source_key} -> {target_key} = '{final_char_to_apply}' (Force: {force_apply_suggestions}, Sugg: '{dep_char}', Existed: '{existing_char_in_grid}')")
                        current_decomp_row[col_idx] = final_char_to_apply
                        suggestion_applied = True
                        applied_this_iter = True
                        logger.debug(f"Applied suggestion: {source_key} -> {target_key} ({final_char_to_apply}) in {output_file}")

                    # If NOT upgraded to 'x', check for simple reciprocal needed
                    if not upgrade_to_x:
                        reciprocal_char = None
                        if dep_char == '>': reciprocal_char = '<'
                        elif dep_char == '<': reciprocal_char = '>'

                        if reciprocal_char:
                            reverse_decomp_row = temp_decomp_grid.get(target_key) # Check reverse using target_key
                            if reverse_decomp_row and row_idx < len(reverse_decomp_row): # Use source's index (row_idx)
                                char_in_reverse = reverse_decomp_row[row_idx]
                                should_apply_reciprocal = False
                                if force_apply_suggestions:
                                     if char_in_reverse != 'x' and char_in_reverse != reciprocal_char: should_apply_reciprocal = True
                                else:
                                     if char_in_reverse == PLACEHOLDER_CHAR or get_priority(reciprocal_char) > get_priority(char_in_reverse): should_apply_reciprocal = True
                                if should_apply_reciprocal:
                                     logger.debug(f"Reciprocal Apply: Setting {target_key} -> {source_key}  ('{reciprocal_char}') (Force: {force_apply_suggestions}, Existed: '{char_in_reverse}')")
                                     reverse_decomp_row[row_idx] = reciprocal_char
                                     suggestion_applied = True

                            # Only warn if the suggestion is STRONGER (higher priority number)
                            # than the existing character, AND the existing character is NOT 'n'.
                            # 'n' represents a manual override that suggestions should never overwrite or warn about.
                # --- Handle Conflicts if suggestion NOT applied ---
                elif not force_apply_suggestions and existing_char_in_grid not in (PLACEHOLDER_CHAR, DIAGONAL_CHAR) and existing_char_in_grid != dep_char:
                    try:
                        existing_priority = get_priority(existing_char_in_grid)
                        suggestion_priority = get_priority(dep_char)

                        # Check if suggestion is STRONGER AND existing is NOT 'n'
                        # User confirmed 'n' will have priority 5, so this also correctly prevents 'n' override
                        if existing_char_in_grid != 'n' and suggestion_priority > existing_priority:
                            # <<< APPLY the suggestion instead of just warning >>>
                            logger.info(f"Suggestion Conflict RESOLVED in {os.path.basename(output_file)}: For {source_key}->{target_key}, "
                                           f"applying suggestion '{dep_char}' (prio {suggestion_priority}) over existing '{existing_char_in_grid}' (prio {existing_priority}).")
                            current_decomp_row[col_idx] = dep_char
                            suggestion_applied = True # Mark grid change
                            applied_this_iter = True # Indicate change happened here
                        # else:
                            # Suggestion is weaker or equal, or existing is 'n'. Keep existing.
                            # logger.debug(f"Suggestion Conflict Ignored: {row_key}->{col_key}, grid='{existing_char_in_grid}', sugg='{dep_char}'. Grid value kept.")

                    except KeyError as e:
                        # Handle case where a character might not be in the priority map
                        logger.error(f"Character priority lookup failed for '{str(e)}' during suggestion conflict check. Grid value kept.")
                    except Exception as e:
                        logger.error(f"Error during suggestion priority check: {e}. Grid value kept.")
                
                # <<< Store details if force applying and a change occurred >>>
                if force_apply_suggestions and applied_this_iter:
                    # Capture details for the specific commit message
                    if applied_manual_source is None: applied_manual_source = source_key
                    elif applied_manual_source != source_key: logger.warning("Multiple source keys detected during forced apply; message may simplify.")
                    applied_manual_targets.append(target_key) # Add target key
                    # Capture the type that was actually applied (could be 'x' after upgrade)
                    current_applied_type = final_char_to_apply
                    if applied_manual_dep_type is None: applied_manual_dep_type = current_applied_type
                    elif applied_manual_dep_type != current_applied_type: logger.warning("Multiple dependency types detected during forced apply; message may simplify.")

            # temp_decomp_grid[row_key] = current_decomp_row # Update the row in the temp grid

    # Import Established Relationships for Native-Foreign Pairs (Mini-Trackers Only)
    native_foreign_import_count = 0
    if tracker_type == "mini" and module_path: # Ensure we have module_path
        logger.debug(f"Mini Tracker ({module_key_string}): Importing established relationships for Native <-> Foreign pairs...")

        # Identify native and foreign keys based on parent path
        native_keys: Dict[str, KeyInfo] = {}
        foreign_keys: Dict[str, KeyInfo] = {}
        for key_str in final_sorted_keys_list:
            key_info = path_to_key_info.get(final_key_defs.get(key_str))
            if key_info:
                if key_info.parent_path == module_path or key_info.norm_path == module_path:
                    native_keys[key_str] = key_info
                else:
                    foreign_keys[key_str] = key_info

        native_key_list = list(native_keys.keys())
        foreign_key_list = list(foreign_keys.keys())

        if native_key_list and foreign_key_list:
            logger.debug(f"Checking {len(native_key_list)} native keys against {len(foreign_key_list)} foreign keys.")

            # Get doc directories for checking home tracker type
            abs_doc_roots_set = {normalize_path(os.path.join(project_root, p)) for p in config.get_doc_directories()}
            def is_path_in_doc_roots(item_path: str) -> bool:
                norm_item_path = normalize_path(item_path)
                return any(is_subpath(norm_item_path, doc_root) or norm_item_path == doc_root for doc_root in abs_doc_roots_set)

            # Iterate through each native key
            for native_key_str in native_key_list:
                native_key_info = native_keys[native_key_str]
                native_key_idx = final_key_to_idx[native_key_str] # Index in the CURRENT grid

                # Iterate through each foreign key
                for foreign_key_str in foreign_key_list:
                    foreign_key_info = foreign_keys[foreign_key_str]
                    foreign_key_idx = final_key_to_idx[foreign_key_str] # Index in the CURRENT grid

                    # Determine the home tracker of the FOREIGN key
                    home_tracker_path: Optional[str] = None
                    foreign_parent = foreign_key_info.parent_path
                    is_foreign_doc = is_path_in_doc_roots(foreign_key_info.norm_path)

                    if is_foreign_doc:
                        home_tracker_path = get_tracker_path(project_root, tracker_type="doc")
                    elif foreign_parent: # Foreign key is code, not doc
                        home_tracker_path = get_tracker_path(project_root, tracker_type="mini", module_path=foreign_parent)
                    # else: # Foreign key has no parent? Should not happen based on key generation.

                    if not home_tracker_path:
                        # logger.warning(f"Could not determine home tracker for foreign key {foreign_key_str}. Skipping import.")
                        continue

                    # Attempt to read relationship from home tracker
                    home_char_native_foreign = PLACEHOLDER_CHAR # native -> foreign
                    home_char_foreign_native = PLACEHOLDER_CHAR # foreign -> native

                    if os.path.exists(home_tracker_path):
                        home_data = read_tracker_file(home_tracker_path)
                        home_keys = home_data.get("keys", {})
                        home_grid = home_data.get("grid", {})

                        # Check if BOTH keys exist in the home tracker's definitions
                        if home_keys and home_grid and native_key_str in home_keys and foreign_key_str in home_keys:
                            home_keys_list = sort_key_strings_hierarchically(list(home_keys.keys()))
                            home_key_to_idx = {k: idx for idx, k in enumerate(home_keys_list)}
                            home_native_idx = home_key_to_idx.get(native_key_str)
                            home_foreign_idx = home_key_to_idx.get(foreign_key_str)

                            if home_native_idx is not None and home_foreign_idx is not None:
                                # Extract native -> foreign char safely
                                row_native_comp = home_grid.get(native_key_str)
                                if row_native_comp:
                                    try:
                                        row_native_decomp = decompress(row_native_comp)
                                        if len(row_native_decomp) == len(home_keys_list) and home_foreign_idx < len(row_native_decomp):
                                            home_char_native_foreign = row_native_decomp[home_foreign_idx]
                                    except Exception as e: logger.warning(f"  Error decompressing home row {native_key_str}: {e}")
                                # Extract foreign -> native char safely
                                row_foreign_comp = home_grid.get(foreign_key_str)
                                if row_foreign_comp:
                                     try:
                                        row_foreign_decomp = decompress(row_foreign_comp)
                                        if len(row_foreign_decomp) == len(home_keys_list) and home_native_idx < len(row_foreign_decomp):
                                            home_char_foreign_native = row_foreign_decomp[home_native_idx]
                                     except Exception as e: logger.warning(f"  Error decompressing home row {foreign_key_str}: {e}")
                        # else: logger.debug(f"    Keys {native_key_str} or {foreign_key_str} missing index in home tracker {os.path.basename(home_tracker_path)}.")
                    # else: logger.debug(f"    Keys {native_key_str} or {foreign_key_str} not found in home tracker {os.path.basename(home_tracker_path)} keys/grid.")

                    # --- Compare priorities and update the CURRENT mini-tracker's temp grid ---
                    # Get current characters from the mini-tracker's temp grid
                    current_char_native_foreign = temp_decomp_grid[native_key_str][foreign_key_idx]
                    current_char_foreign_native = temp_decomp_grid[foreign_key_str][native_key_idx]

                    # Update native -> foreign cell if home relation is stronger (higher priority)
                    # Skip if home relation is 'p'
                    if home_char_native_foreign != PLACEHOLDER_CHAR:
                        try:
                            home_priority = get_priority(home_char_native_foreign)
                            current_priority = get_priority(current_char_native_foreign)
                            # Apply if home is higher priority, OR if current is 'p'/'s'/'S' and home is 'n'
                            should_update = home_priority > current_priority
                            if not should_update and home_char_native_foreign == 'n' and current_char_native_foreign in ('p','s','S'):
                                should_update = True

                            if should_update:
                                logger.info(f"  Updating {native_key_str}->{foreign_key_str} from '{current_char_native_foreign}' to '{home_char_native_foreign}' based on {os.path.basename(home_tracker_path or 'N/A')}")
                                temp_decomp_grid[native_key_str][foreign_key_idx] = home_char_native_foreign
                                native_foreign_import_count += 1
                        except KeyError as e:
                            logger.warning(f"    Priority lookup failed for char '{str(e)}' when comparing {native_key_str}->{foreign_key_str}. Skipping update.")

                    # Update foreign -> native cell if home relation is stronger
                    if home_char_foreign_native != PLACEHOLDER_CHAR:
                         try:
                            home_priority = get_priority(home_char_foreign_native)
                            current_priority = get_priority(current_char_foreign_native)
                            # Apply if home is higher priority, OR if current is 'p'/'s'/'S' and home is 'n'
                            should_update = home_priority > current_priority
                            if not should_update and home_char_foreign_native == 'n' and current_char_foreign_native in ('p','s','S'):
                                should_update = True

                            if should_update:
                                logger.info(f"  Updating {foreign_key_str}->{native_key_str} from '{current_char_foreign_native}' to '{home_char_foreign_native}' based on {os.path.basename(home_tracker_path or 'N/A')}")
                                temp_decomp_grid[foreign_key_str][native_key_idx] = home_char_foreign_native
                                native_foreign_import_count += 1
                         except KeyError as e:
                             logger.warning(f"    Priority lookup failed for char '{str(e)}' when comparing {foreign_key_str}->{native_key_str}. Skipping update.")

            if native_foreign_import_count > 0:
                 logger.info(f"Finished importing established Native <-> Foreign relationships. Updated cell count: {native_foreign_import_count}.")
        else:
            logger.debug("No native/foreign key pairs found in this mini-tracker grid. Skipping import.")

    # <<< START NEW BLOCK: Final Grid Consolidation based on Global Aggregation >>>
    consolidation_changes = 0
    logger.info(f"Consolidating grid for '{os.path.basename(output_file)}' against global highest-priority relationships...")

    # --- Step 1: Get Globally Aggregated Relationships ---
    # This needs to run efficiently. Consider caching the result of aggregation.
    # For now, call the aggregation helper directly. Caching would require
    # a key based on the mtimes of ALL tracker files.
    all_tracker_paths = find_all_tracker_paths(config, project_root)
    aggregated_results = aggregate_all_dependencies(all_tracker_paths, path_to_key_info)
    # Convert to simple (src,tgt) -> char map for easier lookup
    global_authoritative_rels: Dict[Tuple[str, str], str] = {
        link: char for link, (char, origins) in aggregated_results.items()
    }
    logger.debug(f"Retrieved {len(global_authoritative_rels)} globally authoritative relationships for consolidation.")

    # --- Step 2: Iterate through the current temp grid and consolidate ---
    for row_key in final_sorted_keys_list:
        if row_key not in temp_decomp_grid: continue # Should not happen, but safety check
        current_row_list = temp_decomp_grid[row_key]

        for col_idx, current_char in enumerate(current_row_list):
            if col_idx >= len(final_sorted_keys_list): break # Safety break
            col_key = final_sorted_keys_list[col_idx]

            if row_key == col_key: continue # Skip diagonal

            # Get the globally authoritative relationship for this pair
            authoritative_char = global_authoritative_rels.get((row_key, col_key), PLACEHOLDER_CHAR)

            # Compare priorities and update if global view is stronger
            if authoritative_char != PLACEHOLDER_CHAR: # Only act if global view has a defined non-'p' relationship
                try:
                    authoritative_priority = get_priority(authoritative_char)
                    current_priority = get_priority(current_char)

                    # Update if authoritative is strictly higher priority
                    should_update = authoritative_priority > current_priority
                    # Also update if authoritative is 'n' and current is overwritable ('p','s','S')
                    if not should_update and authoritative_char == 'n' and current_char in ('p', 's', 'S'):
                        should_update = True

                    if should_update:
                        # logger.debug(f"  Consolidating {row_key}->{col_key}: '{current_char}' -> '{authoritative_char}' (Global Prio: {authoritative_priority}, Current Prio: {current_priority})")
                        current_row_list[col_idx] = authoritative_char # Update the list directly
                        consolidation_changes += 1

                except KeyError as e:
                    logger.warning(f"  Consolidation: Priority lookup failed for char '{str(e)}' comparing {row_key}->{col_key}. Skipping cell.")

    if consolidation_changes > 0:
        logger.info(f"Consolidation applied {consolidation_changes} updates based on global relationships.")
        # Mark grid as changed if consolidation occurred (affects timestamp)
        grid_structure_changed = True # Re-use this flag maybe? Or a new one? Let's reuse for now.
        # If reusing, ensure the timestamp logic below correctly picks the most recent change type.
        # It might be better to introduce `grid_content_changed_by_consolidation = True`
        # and adjust the timestamp logic block. Let's stick with grid_structure_changed for now.
    else:
         logger.debug("No consolidation changes needed based on global relationships.")
    # <<< END NEW BLOCK >>>


    # --- Update Grid Edit Timestamp ---
    # This logic needs to correctly account for consolidation changes.
    # If we reused grid_structure_changed, the existing logic might set the
    # "Grid structure updated" message, which isn't quite right.
    # Let's refine the timestamp logic slightly:
    final_last_grid_edit = current_last_grid_edit
    grid_content_changed = suggestion_applied or (consolidation_changes > 0)

    # 1. Check if specific manual dependencies were applied FIRST
    # Ensure suggestion_applied is True to confirm *some* change happened via suggestions
    # Use the captured details: applied_manual_source, applied_manual_targets, applied_manual_dep_type
    if force_apply_suggestions and suggestion_applied and applied_manual_source and applied_manual_targets and applied_manual_dep_type:
        # Use the captured details for the specific message
        sorted_targets = sort_key_strings_hierarchically(list(set(applied_manual_targets)))
        final_last_grid_edit = f"Manual dependency update {applied_manual_source} -> {sorted_targets} ({applied_manual_dep_type or '?'}) ({datetime.datetime.now().isoformat()})"
        logger.debug(f"Setting last_GRID_edit to detailed manual message: {final_last_grid_edit}")
    elif grid_content_changed:
        final_last_grid_edit = f"Grid content updated ({datetime.datetime.now().isoformat()})"
        logger.debug(f"Setting last_GRID_edit to generic content update message: {final_last_grid_edit}")
    # 2. Else if only the grid structure changed (keys added/removed, but no suggestions applied)
    elif grid_structure_changed:
        final_last_grid_edit = f"Grid structure updated ({datetime.datetime.now().isoformat()})"
        logger.debug(f"Setting last_GRID_edit to structure update message: {final_last_grid_edit}")
    # 3. Otherwise, it remains the current_last_grid_edit (no relevant grid/suggestion changes occurred)
    else:
         logger.debug(f"Keeping existing last_GRID_edit message: {final_last_grid_edit}")

    # --- Compress the final grid state
    final_grid = {key: compress("".join(row_list)) for key, row_list in temp_decomp_grid.items()}

    # --- Write updated content to file ---
    try:
        is_mini = tracker_type == "mini"; mini_tracker_start_index = -1; mini_tracker_end_index = -1; marker_start, marker_end = "", ""
        if is_mini and lines:
            mini_tracker_info = get_mini_tracker_data(); marker_start, marker_end = mini_tracker_info["markers"]
            try:
                mini_tracker_start_index = next(i for i, l in enumerate(lines) if l.strip() == marker_start)
                mini_tracker_end_index = next(i for i, l in enumerate(lines) if l.strip() == marker_end)
                if mini_tracker_start_index >= mini_tracker_end_index: raise ValueError("Start marker after end marker.")
            except (StopIteration, ValueError) as e: logger.warning(f"Mini markers invalid in {output_file}: {e}. Overwriting."); mini_tracker_start_index = -1

        with open(output_file, "w", encoding="utf-8", newline='\n') as f:
            # Preserve content before start marker
            if is_mini and mini_tracker_start_index != -1:
                for i in range(mini_tracker_start_index + 1): f.write(lines[i])
                if not lines[mini_tracker_start_index].endswith('\n'): f.write('\n')
                f.write("\n") # Add newline after start marker content
            _write_key_definitions(f, final_key_defs, final_sorted_keys_list) # Write DEFINITIONS using final set of keys
            f.write("\n"); f.write(f"last_KEY_edit: {final_last_key_edit}\n"); f.write(f"last_GRID_edit: {final_last_grid_edit}\n\n")
            _write_grid(f, final_sorted_keys_list, final_grid) # Write GRID using final set of keys
            if is_mini and mini_tracker_end_index != -1 and mini_tracker_start_index != -1: # Preserve content after
                 f.write("\n")
                 for i in range(mini_tracker_end_index, len(lines)): f.write(lines[i])
                 if not lines[-1].endswith('\n'): f.write('\n') # Ensure final newline if needed
            elif is_mini and mini_tracker_start_index == -1: # Write end marker if overwriting
                 f.write("\n" + marker_end + "\n")
        logger.info(f"Successfully updated tracker: {output_file}")
        # Invalidate caches
        invalidate_dependent_entries('tracker_data', f"tracker_data:{output_file}:.*")
        invalidate_dependent_entries('grid_decompress', '.*'); invalidate_dependent_entries('grid_validation', '.*'); invalidate_dependent_entries('grid_dependencies', '.*')
    except IOError as e: logger.error(f"I/O Error updating tracker file {output_file}: {e}", exc_info=True)
    except Exception as e: logger.exception(f"Unexpected error updating tracker file {output_file}: {e}")

# --- Export Tracker ---
def export_tracker(tracker_path: str, output_format: str = "json", output_path: Optional[str] = None) -> str:
    """
    Export a tracker file to various formats (json, csv, dot, md).

    Args:
        tracker_path: Path to the tracker file
        output_format: Format to export to ('md', 'json', 'csv', 'dot')
        output_path: Optional path to save the exported file
    Returns:
        Path to the exported file or error message string
    """
    tracker_path = normalize_path(tracker_path); check_file_modified(tracker_path) # Check cache validity
    logger.info(f"Attempting to export '{os.path.basename(tracker_path)}' to format '{output_format}'")
    tracker_data = read_tracker_file(tracker_path)
    if not tracker_data or not tracker_data.get("keys"): msg = f"Error: Cannot export empty/unreadable tracker: {tracker_path}"; logger.error(msg); return msg
    if output_path is None: base_name = os.path.splitext(tracker_path)[0]; output_path = normalize_path(f"{base_name}_export.{output_format}")
    else: output_path = normalize_path(output_path)
    try:
        dirname = os.path.dirname(output_path); os.makedirs(dirname, exist_ok=True)
        keys_map = tracker_data.get("keys", {}); grid = tracker_data.get("grid", {})
        sorted_keys_list = sort_key_strings_hierarchically(list(keys_map.keys()))
        if output_format == "md": shutil.copy2(tracker_path, output_path)
        elif output_format == "json":
            export_data = tracker_data.copy()
            with open(output_path, 'w', encoding='utf-8') as f: json.dump(export_data, f, indent=2, ensure_ascii=False)
        elif output_format == "csv":
             with open(output_path, 'w', encoding='utf-8', newline='') as f:
                import csv; writer = csv.writer(f); writer.writerow(["Source Key", "Source Path", "Target Key", "Target Path", "Dependency Type"])
                key_to_idx = {k: i for i, k in enumerate(sorted_keys_list)}
                for source_key in sorted_keys_list:
                    compressed_row = grid.get(source_key)
                    if compressed_row:
                        try:
                             decompressed_row = decompress(compressed_row)
                             if len(decompressed_row) == len(sorted_keys_list):
                                 for j, dep_type in enumerate(decompressed_row):
                                     if dep_type not in (EMPTY_CHAR, DIAGONAL_CHAR, PLACEHOLDER_CHAR):
                                         target_key = sorted_keys_list[j]
                                         writer.writerow([source_key, keys_map.get(source_key, ""), target_key, keys_map.get(target_key, ""), dep_type])
                             else: logger.warning(f"CSV Export: Row length mismatch for key '{source_key}'")
                        except Exception as e: logger.warning(f"CSV Export: Error processing row for '{source_key}': {e}")
        elif output_format == "dot":
             with open(output_path, 'w', encoding='utf-8') as f:
                f.write("digraph Dependencies {\n  rankdir=LR;\n"); f.write('  node [shape=box, style="filled", fillcolor="#EFEFEF", fontname="Arial"];\n'); f.write('  edge [fontsize=10, fontname="Arial"];\n\n')
                for key in sorted_keys_list: label_path = os.path.basename(keys_map.get(key, '')).replace('\\', '/').replace('"', '\\"'); label = f"{key}\\n{label_path}"; f.write(f'  "{key}" [label="{label}"];\n')
                f.write("\n")
                key_to_idx = {k: i for i, k in enumerate(sorted_keys_list)}
                for source_key in sorted_keys_list:
                     compressed_row = grid.get(source_key)
                     if compressed_row:
                        try:
                             decompressed_row = decompress(compressed_row)
                             if len(decompressed_row) == len(sorted_keys_list):
                                 for j, dep_type in enumerate(decompressed_row):
                                     if dep_type not in (EMPTY_CHAR, DIAGONAL_CHAR, PLACEHOLDER_CHAR):
                                         target_key = sorted_keys_list[j]; color = "black"; style = "solid"; arrowhead="normal"
                                         if dep_type == '>': color = "blue"
                                         elif dep_type == '<': color = "green"; arrowhead="oinv"
                                         elif dep_type == 'x': color = "red"; style="dashed"; arrowhead="odot"
                                         elif dep_type == 'd': color = "orange"
                                         elif dep_type == 's': color = "grey"; style="dotted"
                                         elif dep_type == 'S': color = "dimgrey"; style="bold"
                                         f.write(f'  "{source_key}" -> "{target_key}" [label="{dep_type}", color="{color}", style="{style}", arrowhead="{arrowhead}"];\n')
                             else: logger.warning(f"DOT Export: Row length mismatch for key '{source_key}'")
                        except Exception as e: logger.warning(f"DOT Export: Error processing row for '{source_key}': {e}")
                f.write("}\n")
        else: msg = f"Error: Unsupported export format '{output_format}'"; logger.error(msg); return msg
        logger.info(f"Successfully exported tracker to: {output_path}")
        return output_path
    except IOError as e: msg = f"Error exporting tracker: I/O Error - {str(e)}"; logger.error(msg, exc_info=True); return msg
    except ImportError as e: msg = f"Error exporting tracker: Missing library for format '{output_format}' - {str(e)}"; logger.error(msg); return msg
    except Exception as e: msg = f"Error exporting tracker: Unexpected error - {str(e)}"; logger.exception(msg); return msg

# --- remove_key_from_tracker (REFACTORED to use update_tracker) ---
def remove_key_from_tracker(output_file: str, key_to_remove: str):
    """
    Removes a key string and its row/column from a tracker by calling update_tracker
    with a modified global key map copy where the key's path is excluded.

    Args:
        output_file: Path to the tracker file.
        key_to_remove: The key string to remove from this tracker.

    Raises:
        FileNotFoundError: If the tracker file doesn't exist.
        ValueError: If the key to remove is not found locally in the tracker.
        IOError: If writing the updated file fails (via update_tracker).
        Exception: For other unexpected errors during processing or update_tracker call.
    """
    output_file = normalize_path(output_file)
    logger.info(f"Attempting removal of key '{key_to_remove}' from tracker '{output_file}' via update_tracker.")

    # 1. Validate File Existence and Read Local Keys
    if not os.path.exists(output_file):
        logger.error(f"Tracker file '{output_file}' not found for removal.")
        raise FileNotFoundError(f"Tracker file '{output_file}' not found.")

    # Read only keys needed for initial validation and path lookup
    # Use read_tracker_file which leverages caching
    tracker_data = read_tracker_file(output_file)
    if not tracker_data or not tracker_data.get("keys"):
        # This case might mean an empty or malformed tracker.
        # If the file exists but keys can't be read, maybe raise an error?
        logger.error(f"Could not read keys from tracker file: {output_file}")
        raise ValueError(f"Could not read keys from tracker file: {output_file}")

    local_keys = tracker_data["keys"]
    if key_to_remove not in local_keys:
        logger.warning(f"Key '{key_to_remove}' not found in the definitions of tracker '{output_file}'. No update needed.")
        # Changed from raising ValueError to returning gracefully, as the key isn't there.
        # Alternatively, could still raise ValueError if the command expects the key to exist.
        # Let's stick with raising ValueError for now to match previous behavior.
        raise ValueError(f"Key '{key_to_remove}' not found in tracker '{output_file}'.")

    # Get the path associated with the key *in this specific tracker*
    path_removed = local_keys.get(key_to_remove)
    if not path_removed:
        logger.error(f"Internal inconsistency: Key '{key_to_remove}' found in keys map but has no path.")
        raise ValueError(f"Could not determine path for key '{key_to_remove}' in {output_file}.")
    logger.info(f"Key '{key_to_remove}' corresponds to path '{path_removed}' in this tracker.")

    # --- Backup original file before calling update_tracker ---
    backup_tracker_file(output_file)

    # 2. Load Global Map
    # This function handles errors and exits if map not found
    global_path_to_key_info = load_global_key_map() # Assume this exists or script exits

    # 3. Create Modified Map Copy (Remove target path entry)
    modified_path_to_key_info = global_path_to_key_info.copy()
    if path_removed in modified_path_to_key_info:
        del modified_path_to_key_info[path_removed]
        logger.debug(f"Removed path '{path_removed}' from the in-memory global map copy for update_tracker.")
    else:
        logger.warning(f"Path '{path_removed}' (from key '{key_to_remove}' in {output_file}) not found as a key in the loaded global map. Proceeding, but this might indicate an inconsistency.")

    # 4. Prepare Arguments for update_tracker
    is_mini_tracker = output_file.endswith("_module.md")
    tracker_type = "mini" if is_mini_tracker else ("doc" if "doc_tracker.md" in output_file else "main")

    # Generate file_to_module map (use original map is fine)
    file_to_module_map = {
        info.norm_path: info.parent_path
        for info in global_path_to_key_info.values() # Use original is safe
        if not info.is_directory and info.parent_path
    }

    # 5. Call update_tracker
    try:
        logger.info(f"Calling update_tracker for {output_file} with key '{key_to_remove}' effectively excluded.")
        # We need to call the update_tracker function defined within this same file (tracker_io.py)
        # Ensure it's callable directly or imported appropriately if it were in a different module.
        update_tracker(
            output_file_suggestion=output_file,
            # Pass the MODIFIED map where the target key's path is absent
            path_to_key_info=modified_path_to_key_info,
            tracker_type=tracker_type,
            suggestions=None, # No suggestions being applied
            file_to_module=file_to_module_map,
            new_keys=None, # No new keys being introduced globally
            force_apply_suggestions=False # Not applying suggestions
        )
        logger.info(f"update_tracker completed successfully for removing key '{key_to_remove}' from '{output_file}'.")
        # Invalidation is handled within update_tracker
        # No explicit return value needed, exceptions signal failure.

    except Exception as e:
        logger.error(f"update_tracker failed during key removal for {output_file}: {e}", exc_info=True)
        # Re-raise the exception so the handler in dependency_processor can catch it
        # Potentially wrap in a more specific error type if desired.
        raise Exception(f"Failed to update tracker {output_file} during key removal: {e}") from e

# --- End of tracker_io.py ---