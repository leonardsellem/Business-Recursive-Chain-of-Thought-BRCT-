# --- START OF FILE tracker_io.py ---

"""
IO module for tracker file operations.
Handles reading, writing, merging and exporting tracker files.
"""

import datetime
import io
import json
import os
import re
import shutil
from typing import Dict, List, Tuple, Any, Optional, Set
from collections import defaultdict

# Import only from utils and core layers
# Corrected import based on previous files provided
from cline_utils.dependency_system.core.key_manager import get_key_from_path, sort_keys, validate_key
from cline_utils.dependency_system.utils.path_utils import get_project_root, is_subpath, normalize_path, join_paths
from cline_utils.dependency_system.utils.config_manager import ConfigManager
# Assuming these plugin-like structures exist and are correctly imported
from cline_utils.dependency_system.io.update_doc_tracker import doc_tracker_data
from cline_utils.dependency_system.io.update_mini_tracker import get_mini_tracker_data
from cline_utils.dependency_system.io.update_main_tracker import main_tracker_data
from cline_utils.dependency_system.utils.cache_manager import cached, check_file_modified, invalidate_dependent_entries # Removed tracker_modified as it's not defined in cache_manager provided
from cline_utils.dependency_system.core.dependency_grid import compress, create_initial_grid, decompress, validate_grid, PLACEHOLDER_CHAR, EMPTY_CHAR, DIAGONAL_CHAR # Added validate_grid import

import logging
logger = logging.getLogger(__name__)

# @cached("tracker_paths",
#         key_func=lambda project_root, tracker_type="main", module_path=None:
#         f"tracker_path:{normalize_path(project_root)}:{tracker_type}:{normalize_path(module_path) if module_path else 'none'}:{os.path.getmtime(ConfigManager().config_path) if os.path.exists(ConfigManager().config_path) else 'missing'}")
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

    if tracker_type == "main":
        # Delegate and normalize result
        return normalize_path(main_tracker_data["get_tracker_path"](project_root))
    elif tracker_type == "doc":
        # Delegate and normalize result
        return normalize_path(doc_tracker_data["get_tracker_path"](project_root))
    elif tracker_type == "mini":
        # Mini trackers are in module directories - keep existing logic
        if not module_path:
            raise ValueError("module_path must be provided for mini-trackers")
        # Ensure module_path itself is normalized before joining
        norm_module_path = normalize_path(module_path)
        module_name = os.path.basename(norm_module_path) # Use basename from normalized path
        # Use os.path.join and then normalize the final result
        raw_path = os.path.join(norm_module_path, f"{module_name}_module.md")
        return normalize_path(raw_path) # <<< FIX: Normalize the final path
    else:
        raise ValueError(f"Unknown tracker type: {tracker_type}")

# --- Caching for read_tracker_file ---
# The key needs to depend on the file modification time for the cache to be effective.
# @cached("tracker_data",
#         key_func=lambda tracker_path:
#         f"tracker_data:{normalize_path(tracker_path)}:{os.path.getmtime(tracker_path) if os.path.exists(tracker_path) else 'missing'}")
def read_tracker_file(tracker_path: str) -> Dict[str, Any]:
    """
    Read a tracker file and parse its contents. Caches based on path and mtime.
    Args:
        tracker_path: Path to the tracker file
    Returns:
        Dictionary with keys, grid, and metadata, or empty structure on failure.
    """
    tracker_path = normalize_path(tracker_path)
    if not os.path.exists(tracker_path):
        logger.debug(f"Tracker file not found: {tracker_path}. Returning empty structure.")
        return {"keys": {}, "grid": {}, "last_key_edit": "", "last_grid_edit": ""}

    try:
        with open(tracker_path, 'r', encoding='utf-8') as f:
            content = f.read()

        keys = {}
        grid = {}
        last_key_edit = ""
        last_grid_edit = ""

        # Parse key definitions using regex for robustness
        key_section_match = re.search(r'---KEY_DEFINITIONS_START---\n(.*?)\n---KEY_DEFINITIONS_END---', content, re.DOTALL | re.IGNORECASE)
        if key_section_match:
            key_section_content = key_section_match.group(1)
            for line in key_section_content.splitlines():
                line = line.strip()
                if not line or line.lower().startswith("key definitions:"):
                    continue
                # Match key: path format, allowing spaces around ':'
                match = re.match(r'^([a-zA-Z0-9]+)\s*:\s*(.*)$', line)
                if match:
                    k, v = match.groups()
                    if validate_key(k): # Ensure key format is valid before adding
                        keys[k] = normalize_path(v)
                    else:
                        logger.warning(f"Skipping invalid key format in {tracker_path}: '{k}'")
                else:
                     logger.debug(f"Skipping malformed key definition line in {tracker_path}: '{line}'")


        # Parse grid using regex for robustness
        grid_section_match = re.search(r'---GRID_START---\n(.*?)\n---GRID_END---', content, re.DOTALL | re.IGNORECASE)
        if grid_section_match:
            grid_section_content = grid_section_match.group(1)
            lines = grid_section_content.strip().splitlines()
            # Skip header line (X ...) if present
            if lines and lines[0].strip().upper().startswith("X "):
                lines = lines[1:]
            for line in lines:
                line = line.strip()
                # Match key = grid_string format, allowing spaces
                match = re.match(r'^([a-zA-Z0-9]+)\s*=\s*(.*)$', line)
                if match:
                    k, v = match.groups()
                    if k in keys: # Only add grid rows for keys defined above
                        grid[k] = v.strip() # Store compressed string
                    else:
                        logger.warning(f"Grid row key '{k}' in {tracker_path} not found in key definitions. Skipping.")
                else:
                     logger.debug(f"Skipping malformed grid line in {tracker_path}: '{line}'")

        # Parse metadata using regex for robustness
        last_key_edit_match = re.search(r'^last_KEY_edit\s*:\s*(.*)$', content, re.MULTILINE | re.IGNORECASE)
        if last_key_edit_match:
            last_key_edit = last_key_edit_match.group(1).strip()

        last_grid_edit_match = re.search(r'^last_GRID_edit\s*:\s*(.*)$', content, re.MULTILINE | re.IGNORECASE)
        if last_grid_edit_match:
            last_grid_edit = last_grid_edit_match.group(1).strip()

        logger.debug(f"Read tracker '{os.path.basename(tracker_path)}': {len(keys)} keys, {len(grid)} grid entries")
        return {"keys": keys, "grid": grid, "last_key_edit": last_key_edit, "last_grid_edit": last_grid_edit}

    except Exception as e:
        logger.exception(f"Error reading tracker file {tracker_path}: {e}") # Use exception for stack trace
        return {"keys": {}, "grid": {}, "last_key_edit": "", "last_grid_edit": ""}


def write_tracker_file(tracker_path: str, keys: Dict[str, str], grid: Dict[str, str], last_key_edit: str, last_grid_edit: str = "") -> bool:
    """
    Write tracker data to a file in markdown format. Ensures directory exists.

    Args:
        tracker_path: Path to the tracker file
        keys: Dictionary of keys to paths (will be sorted before writing)
        grid: Dictionary of grid rows (compressed strings)
        last_key_edit: Last key edit identifier
        last_grid_edit: Last grid edit identifier
    Returns:
        True if successful, False otherwise
    """
    tracker_path = normalize_path(tracker_path)
    try:
        # Create directory if it doesn't exist
        dirname = os.path.dirname(tracker_path)
        if dirname: # Avoid trying to create "" if path is just a filename
            os.makedirs(dirname, exist_ok=True)

        # Sort keys for consistent output
        sorted_keys_list = sort_keys(list(keys.keys()))
 
        # --- Validate grid before writing ---
        if not validate_grid(grid, sorted_keys_list): # Use the sorted list for validation
            logger.error(f"Aborting write to {tracker_path} due to grid validation failure. Check previous logs for details.")
            return False
        # --- End Validation ---

        with open(tracker_path, 'w', encoding='utf-8') as f:
            # --- Write key definitions ---
            f.write("---KEY_DEFINITIONS_START---\n")
            f.write("Key Definitions:\n")
            for key in sorted_keys_list:
                # Ensure path uses forward slashes for consistency
                f.write(f"{key}: {normalize_path(keys[key])}\n")
            f.write("---KEY_DEFINITIONS_END---\n\n") # Add newline for separation

            # --- Write metadata ---
            f.write(f"last_KEY_edit: {last_key_edit}\n")
            f.write(f"last_GRID_edit: {last_grid_edit}\n\n") # Add newline for separation

            # --- Write grid ---
            f.write("---GRID_START---\n")
            if sorted_keys_list: # Only write grid if there are keys
                f.write(f"X {' '.join(sorted_keys_list)}\n")
                # Ensure grid dimensions match sorted_keys_list
                expected_len = len(sorted_keys_list)
                for key in sorted_keys_list:
                    grid_row = grid.get(key)
                    # If row missing or wrong length, create/fix it
                    if grid_row is None:
                        # Create initial row if missing
                        row_list = [PLACEHOLDER_CHAR] * expected_len
                        try:
                            idx = sorted_keys_list.index(key)
                            row_list[idx] = DIAGONAL_CHAR
                        except ValueError: # Should not happen if key is from sorted_keys_list
                            pass
                        grid_row = compress("".join(row_list))
                        logger.warning(f"Missing grid row for key '{key}' in {tracker_path}. Initializing.")
                    else:
                        # Validate length and fix if necessary
                        decompressed_row = decompress(grid_row)
                        if len(decompressed_row) != expected_len:
                            logger.warning(f"Incorrect grid row length for key '{key}' in {tracker_path} (expected {expected_len}, got {len(decompressed_row)}). Re-initializing.")
                            row_list = [PLACEHOLDER_CHAR] * expected_len
                            try:
                                idx = sorted_keys_list.index(key)
                                row_list[idx] = DIAGONAL_CHAR
                            except ValueError:
                                pass
                            grid_row = compress("".join(row_list))

                    f.write(f"{key} = {grid_row}\n")
            else:
                f.write("X \n") # Write empty header if no keys
            f.write("---GRID_END---\n")

        logger.info(f"Wrote tracker file: {tracker_path}")
        # Invalidate cache for this specific tracker file after writing
        invalidate_dependent_entries('tracker_data', f"tracker_data:{tracker_path}:.*")
        return True
    except IOError as e:
        logger.error(f"I/O Error writing tracker file {tracker_path}: {e}")
        return False
    except Exception as e:
        logger.exception(f"Unexpected error writing tracker file {tracker_path}: {e}")
        return False


def backup_tracker_file(tracker_path: str) -> str:
    """
    Create a backup of a tracker file.

    Args:
        tracker_path: Path to the tracker file
    Returns:
        Path to the backup file or empty string on failure
    """
    tracker_path = normalize_path(tracker_path)
    if not os.path.exists(tracker_path):
        logger.warning(f"Tracker file not found for backup: {tracker_path}")
        return ""

    try:
        config = ConfigManager()
        # Get backup dir relative to project root, then make absolute
        project_root = get_project_root()
        backup_dir_rel = config.get_path("backups_dir", "cline_docs/backups") # Get from config
        backup_dir_abs = normalize_path(os.path.join(project_root, backup_dir_rel))

        os.makedirs(backup_dir_abs, exist_ok=True)

        # Create backup filename with timestamp
        timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S_%f") # Added microseconds
        base_name = os.path.basename(tracker_path)
        backup_filename = f"{base_name}.{timestamp}.bak"
        backup_path = os.path.join(backup_dir_abs, backup_filename)

        # Copy the file
        shutil.copy2(tracker_path, backup_path)
        logger.info(f"Backed up tracker '{base_name}' to: {backup_path}")

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
                        except ValueError:
                            logger.warning(f"Could not parse timestamp for backup file: {filename}")
                    else:
                        logger.debug(f"Backup file name format mismatch, skipping cleanup consideration: {filename}")


            # Sort by timestamp, newest first
            backup_files.sort(key=lambda x: x[0], reverse=True)

            # Keep only the 2 most recent backups
            if len(backup_files) > 2:
                files_to_delete = backup_files[2:]
                logger.info(f"Found {len(backup_files)} backups for '{base_name}'. Cleaning up {len(files_to_delete)} older backups.")
                for _, file_path_to_delete in files_to_delete:
                    try:
                        os.remove(file_path_to_delete)
                        logger.debug(f"Deleted old backup: {file_path_to_delete}")
                    except OSError as delete_error:
                        logger.error(f"Error deleting old backup file {file_path_to_delete}: {delete_error}")
        except Exception as cleanup_error:
            logger.error(f"Error during backup cleanup for {base_name}: {cleanup_error}")
        # --- End Cleanup ---

        return backup_path
    except Exception as e:
        logger.error(f"Error backing up tracker file {tracker_path}: {e}")
        return ""

# --- Helper function for merge ---
def _merge_grids(primary_grid: Dict[str, str], secondary_grid: Dict[str, str],
                 primary_keys_list: List[str], secondary_keys_list: List[str],
                 merged_keys_list: List[str]) -> Dict[str, str]:
    """Merges two decompressed grids based on the merged key list."""
    merged_decompressed_grid = {}
    merged_size = len(merged_keys_list)
    key_to_merged_idx = {key: i for i, key in enumerate(merged_keys_list)}

    # Initialize merged grid with placeholders and diagonal
    for i, row_key in enumerate(merged_keys_list):
        row = [PLACEHOLDER_CHAR] * merged_size
        row[i] = DIAGONAL_CHAR
        merged_decompressed_grid[row_key] = row

    # Fill from secondary grid first
    if secondary_grid:
        key_to_secondary_idx = {key: i for i, key in enumerate(secondary_keys_list)}
        for sec_row_key, sec_row_list in secondary_grid.items():
            if sec_row_key in key_to_merged_idx:
                merged_row_idx = key_to_merged_idx[sec_row_key]
                for sec_col_idx, value in enumerate(sec_row_list):
                    sec_col_key = secondary_keys_list[sec_col_idx]
                    if sec_col_key in key_to_merged_idx:
                         merged_col_idx = key_to_merged_idx[sec_col_key]
                         # Only fill if it's not the diagonal and value is meaningful
                         if merged_row_idx != merged_col_idx and value != PLACEHOLDER_CHAR:
                              merged_decompressed_grid[sec_row_key][merged_col_idx] = value

    # Fill/Overwrite from primary grid
    if primary_grid:
        key_to_primary_idx = {key: i for i, key in enumerate(primary_keys_list)}
        for pri_row_key, pri_row_list in primary_grid.items():
            if pri_row_key in key_to_merged_idx:
                merged_row_idx = key_to_merged_idx[pri_row_key]
                for pri_col_idx, value in enumerate(pri_row_list):
                    pri_col_key = primary_keys_list[pri_col_idx]
                    if pri_col_key in key_to_merged_idx:
                        merged_col_idx = key_to_merged_idx[pri_col_key]
                        # Overwrite anything except diagonal
                        if merged_row_idx != merged_col_idx:
                            merged_decompressed_grid[pri_row_key][merged_col_idx] = value

    # Compress the final merged grid
    compressed_grid = {key: compress("".join(row_list)) for key, row_list in merged_decompressed_grid.items()}
    return compressed_grid

# --- Merge Trackers ---
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

    # Backup before potentially overwriting
    if output_path == primary_tracker_path:
        backup_tracker_file(primary_tracker_path)
    elif output_path == secondary_tracker_path:
         backup_tracker_file(secondary_tracker_path)


    # Read both trackers (using cached read)
    primary_data = read_tracker_file(primary_tracker_path)
    secondary_data = read_tracker_file(secondary_tracker_path)

    # Handle cases where one or both trackers are empty/missing
    if not primary_data or not primary_data.get("keys"):
        if not secondary_data or not secondary_data.get("keys"):
             logger.warning("Both trackers are empty or missing. Cannot merge.")
             return None
        logger.info(f"Primary tracker {os.path.basename(primary_tracker_path)} empty/missing. Using secondary tracker.")
        merged_data = secondary_data
    elif not secondary_data or not secondary_data.get("keys"):
        logger.info(f"Secondary tracker {os.path.basename(secondary_tracker_path)} empty/missing. Using primary tracker.")
        merged_data = primary_data
    else:
        # --- Perform the merge ---
        logger.info(f"Merging '{os.path.basename(primary_tracker_path)}' and '{os.path.basename(secondary_tracker_path)}'")

        # Merge keys (primary takes precedence for path if key exists in both)
        merged_keys_map = {**secondary_data["keys"], **primary_data["keys"]}
        merged_keys_list = sort_keys(list(merged_keys_map.keys()))

        # Decompress grids for merging
        primary_grid_decomp = {k: list(decompress(v)) for k, v in primary_data["grid"].items() if k in primary_data["keys"]}
        secondary_grid_decomp = {k: list(decompress(v)) for k, v in secondary_data["grid"].items() if k in secondary_data["keys"]}

        # Merge the decompressed grids
        merged_compressed_grid = _merge_grids(
            primary_grid_decomp, secondary_grid_decomp,
            sort_keys(list(primary_data["keys"].keys())), # Pass sorted lists
            sort_keys(list(secondary_data["keys"].keys())),
            merged_keys_list
        )

        # Merge metadata (simple precedence for now)
        merged_last_key_edit = primary_data["last_key_edit"] or secondary_data["last_key_edit"]
        merged_last_grid_edit = primary_data["last_grid_edit"] or secondary_data["last_grid_edit"]

        merged_data = {
            "keys": merged_keys_map,
            "grid": merged_compressed_grid,
            "last_key_edit": merged_last_key_edit,
            "last_grid_edit": merged_last_grid_edit,
        }

    # Write the merged tracker
    if write_tracker_file(output_path, merged_data["keys"], merged_data["grid"], merged_data["last_key_edit"], merged_data["last_grid_edit"]):
        logger.info(f"Successfully merged trackers into: {output_path}")
        # Invalidate caches related to the output file
        invalidate_dependent_entries('tracker_data', f"tracker_data:{output_path}:.*")
        # Invalidate grid-related caches as structure might have changed
        invalidate_dependent_entries('grid_decompress', '.*')
        invalidate_dependent_entries('grid_validation', '.*')
        invalidate_dependent_entries('grid_dependencies', '.*')
        return merged_data
    else:
        logger.error(f"Failed to write merged tracker to: {output_path}")
        return None

# --- Helper functions for update_tracker (moved from original implementation) ---

def _read_existing_keys(lines: List[str]) -> Dict[str, str]:
    """Reads existing key definitions from lines."""
    key_map = {}
    in_section = False
    key_def_start_pattern = re.compile(r'^---KEY_DEFINITIONS_START---$', re.IGNORECASE)
    key_def_end_pattern = re.compile(r'^---KEY_DEFINITIONS_END---$', re.IGNORECASE)

    for line in lines:
        if key_def_end_pattern.match(line):
            break
        if in_section:
            line = line.strip()
            if not line or line.lower().startswith("key definitions:"):
                continue
            match = re.match(r'^([a-zA-Z0-9]+)\s*:\s*(.*)$', line)
            if match:
                k, v = match.groups()
                if validate_key(k):
                    key_map[k] = normalize_path(v) # Store normalized path
            # else: logger.debug(f"Skipping malformed key line in _read_existing_keys: '{line}'")
        elif key_def_start_pattern.match(line):
            in_section = True
    return key_map

def _read_existing_grid(lines: List[str]) -> Dict[str, str]:
    """Reads the existing compressed grid data from lines."""
    grid_map = {}
    in_section = False
    grid_start_pattern = re.compile(r'^---GRID_START---$', re.IGNORECASE)
    grid_end_pattern = re.compile(r'^---GRID_END---$', re.IGNORECASE)

    for line in lines:
        if grid_end_pattern.match(line):
            break
        if in_section:
            line = line.strip()
            if line.upper().startswith("X "):
                continue # Skip header
            match = re.match(r'^([a-zA-Z0-9]+)\s*=\s*(.*)$', line)
            if match:
                k, v = match.groups()
                grid_map[k] = v.strip() # Store compressed string
            # else: logger.debug(f"Skipping malformed grid line in _read_existing_grid: '{line}'")
        elif grid_start_pattern.match(line):
            in_section = True
    return grid_map

def _write_key_definitions(file_obj: io.TextIOBase, key_map: Dict[str, str]):
    """Writes the key definitions section to the file object."""
    file_obj.write("---KEY_DEFINITIONS_START---\n")
    file_obj.write("Key Definitions:\n")
    # Explicitly sort keys using the canonical sort_keys function first
    sorted_keys_list = sort_keys(list(key_map.keys()))
    for k in sorted_keys_list:
        v = key_map[k] # Get value from the original map
        file_obj.write(f"{k}: {normalize_path(v)}\n") # Write normalized path
    file_obj.write("---KEY_DEFINITIONS_END---\n")

def _write_grid(file_obj: io.TextIOBase, sorted_keys_list: List[str], grid: Dict[str, str]):
    """Writes the grid section to the provided file object."""
    file_obj.write("---GRID_START---\n")
    if not sorted_keys_list:
        file_obj.write("X \n") # Empty header
    else:
        file_obj.write(f"X {' '.join(sorted_keys_list)}\n")
        expected_len = len(sorted_keys_list)
        for row_key in sorted_keys_list:
            compressed_row = grid.get(row_key)
            # Validate or initialize the row
            if compressed_row is None:
                 row_list = [PLACEHOLDER_CHAR] * expected_len
                 if row_key in sorted_keys_list: row_list[sorted_keys_list.index(row_key)] = DIAGONAL_CHAR
                 compressed_row = compress("".join(row_list))
            else:
                 # Optional: Add validation here if needed, similar to write_tracker_file
                 pass
            file_obj.write(f"{row_key} = {compressed_row}\n")
    file_obj.write("---GRID_END---\n")

# --- Mini Tracker Specific Functions ---

def get_mini_tracker_path(module_path: str) -> str:
    """Gets the path to the mini tracker file. Ensures normalization."""
    # Re-implemented based on get_tracker_path logic
    norm_module_path = normalize_path(module_path)
    module_name = os.path.basename(norm_module_path)
    raw_path = os.path.join(norm_module_path, f"{module_name}_module.md")
    return normalize_path(raw_path)

def create_mini_tracker(module_path: str,
                        global_key_map: Dict[str, str],
                        filtered_keys_internal: Dict[str, str], # Renamed for clarity
                        relevant_keys_for_grid: List[str],
                        new_keys_for_this_tracker: Optional[List[str]] = None): # Use filtered new keys
    """Creates a new mini-tracker file with the template."""
    mini_tracker_info = get_mini_tracker_data()
    template = mini_tracker_info["template"]
    marker_start, marker_end = mini_tracker_info["markers"] # Get both markers
    module_name = os.path.basename(normalize_path(module_path))
    output_file = get_mini_tracker_path(module_path) # Use normalized path

    # Use relevant_keys_for_grid and the GLOBAL map to get paths for ALL keys in the grid definitions
    keys_to_write_defs = {k: global_key_map.get(k, "PATH_NOT_FOUND_IN_GLOBAL_MAP") for k in relevant_keys_for_grid}

    # Ensure module's own key is always included
    module_key = get_key_from_path(module_path, global_key_map)
    if module_key and module_key not in relevant_keys_for_grid:
        relevant_keys_for_grid.append(module_key)

    # Grid dimensions are based on relevant_keys_for_grid
    sorted_relevant_keys_list = sort_keys(relevant_keys_for_grid)

    try:
        dirname = os.path.dirname(output_file)
        if dirname: os.makedirs(dirname, exist_ok=True)

        with open(output_file, "w", encoding="utf-8") as f:
            # Write the main template part (ends right after start marker)
            f.write(template.format(module_name=module_name))
            f.write("\n") # Add a newline after the start marker line from template

            # --- Write the tracker data section ---
            _write_key_definitions(f, keys_to_write_defs)
            f.write("\n") # Separator

            # Use filtered new keys for the message
            last_key_edit_msg = f"Assigned keys: {', '.join(new_keys_for_this_tracker)}" if new_keys_for_this_tracker else (sorted_relevant_keys_list[-1] if sorted_relevant_keys_list else "Initial creation")
            f.write(f"last_KEY_edit: {last_key_edit_msg}\n")
            f.write(f"last_GRID_edit: Initial creation\n\n") # Separator

            # Write the grid using the full list of relevant keys and an empty grid initially
            _write_grid(f, sorted_relevant_keys_list, {})
            f.write("\n") # Add newline before end marker

            # --- FIX: Explicitly write the end marker ---
            f.write(marker_end + "\n")
            # --- END FIX ---

        logger.info(f"Created new mini tracker: {output_file}")

    except IOError as e:
         logger.error(f"I/O Error creating mini tracker {output_file}: {e}")
    except Exception as e:
         logger.exception(f"Unexpected error creating mini tracker {output_file}: {e}")


# --- Modify update_tracker (specifically the file writing part near the end) ---
def update_tracker(output_file: str, # Note: output_file might be recalculated inside for mini-trackers
                   key_map: Dict[str, str], # This is the GLOBAL key map
                   tracker_type: str = "main", # Changed default to main for clarity
                   suggestions: Optional[Dict[str, List[Tuple[str, str]]]] = None,
                   file_to_module: Optional[Dict[str, str]] = None,
                   new_keys: Optional[List[str]] = None): # This is the GLOBAL list of new keys
    """
    Updates or creates a tracker file. Invalidates cache on changes.
    Acts as a dispatcher, calling the appropriate logic based on tracker_type.

    Args:
        output_file: Initial path suggestion (may be ignored for mini-trackers)
        key_map: GLOBAL dictionary mapping keys to file paths
        tracker_type: Type of tracker ("main", "doc", or "mini")
        suggestions: Optional GLOBAL dependency suggestions to update the grid
        file_to_module: Optional mapping of files to module paths (required for mini-trackers)
        new_keys: Optional GLOBAL list of newly assigned keys for last_KEY_edit
    """
    project_root = get_project_root() # Needed for determining paths

    # --- Determine Correct Output File and Filter Keys/Suggestions ---
    filtered_keys = {} # Keys relevant just for definitions in this tracker
    relevant_keys = [] # Keys relevant for grid rows/columns in this tracker
    filtered_suggestions = suggestions if suggestions is not None else {} # Suggestions relevant to this tracker

    if tracker_type == "main":
        output_file = main_tracker_data["get_tracker_path"](project_root)
        filtered_keys = main_tracker_data["key_filter"](project_root, key_map)
        relevant_keys = list(filtered_keys.keys()) # For main, relevant keys are the filtered keys
        # Aggregate suggestions if provided
        filtered_suggestions = main_tracker_data["dependency_aggregation"](project_root, key_map, suggestions, filtered_keys, file_to_module)

    elif tracker_type == "doc":
        output_file = doc_tracker_data["get_tracker_path"](project_root)
        filtered_keys = doc_tracker_data["file_inclusion"](project_root, key_map)
        # For doc, relevant keys are the filtered keys, BUT EXCLUDE DIRECTORIES
        relevant_keys = [k for k, p in filtered_keys.items() if os.path.isfile(p)]
        # Doc tracker uses global suggestions, but only for rows/cols matching filtered_keys
        # No specific aggregation needed here, filtering happens during grid update

    elif tracker_type == "mini":
        if not file_to_module:
            logger.error("file_to_module mapping is required for mini-tracker updates.")
            return # Cannot proceed without mapping
        if not key_map:
            logger.warning("Global key_map is empty, cannot determine mini-tracker path.")
            return # Cannot proceed

        # Determine module_path based on the *intended* content (use file_to_module)
        # Find *a* key that belongs to the module this tracker represents.
        # This assumes `update_tracker` is called in a context where it knows which module it's for.
        # The original call in project_analyzer iterates through module dirs. Let's assume `output_file`
        # passed initially IS the correct mini-tracker path or derivable from it.
        # We'll derive module_path from the initially passed output_file suggestion.
        potential_module_path = os.path.dirname(normalize_path(output_file)) # Assume tracker is inside module dir

        # Re-verify using file_to_module if possible, but rely on path structure primarily
        # This part is tricky if update_tracker is called generically. Let's stick to deriving from output_file path.
        if not os.path.exists(potential_module_path):
             logger.error(f"Cannot determine module path from suggested output_file: {output_file}")
             return

        module_path = potential_module_path
        output_file = get_mini_tracker_path(module_path) # Get definitive, normalized path

        # Filter keys internal to this module
        filtered_keys = {k: v for k, v in key_map.items() if is_subpath(normalize_path(v), module_path)}
        internal_keys_set = set(filtered_keys.keys())

        # Determine relevant keys (internal + external dependencies)
        relevant_keys_set = internal_keys_set.copy()
        positive_dep_chars = {'<', '>', 'x', 'd', 's'}
        if suggestions:
            for src_key, deps in suggestions.items():
                 # If source is internal OR target is internal, the dependency is relevant
                 source_is_internal = src_key in internal_keys_set
                 for target_key, dep_char in deps:
                     target_is_internal = target_key in internal_keys_set
                     # Include if:
                     # 1. Source is internal and dependency is positive
                     # 2. Target is internal and dependency is positive (shows incoming)
                     if dep_char in positive_dep_chars and (source_is_internal or target_is_internal):
                          relevant_keys_set.add(src_key) # Ensure source is included
                          # Only add if it's a file path
                          if target_key in key_map and os.path.isfile(key_map[target_key]):
                               relevant_keys_set.add(target_key) # Ensure target is included if it's a file
                          if src_key in key_map and os.path.isfile(key_map[src_key]):
                               relevant_keys_set.add(src_key) # Ensure source is included if it's a file

        # Filter out any remaining directories from the final list for mini-tracker grid
        relevant_keys = sort_keys([k for k in relevant_keys_set if k in key_map and os.path.isfile(key_map[k])])
        # For mini-trackers, suggestions don't need aggregation, just filtering during grid update

    else:
        raise ValueError(f"Unknown tracker type: {tracker_type}")

    # --- Check modification time AFTER determining the correct output_file ---
    check_file_modified(output_file) # Check cache validity

    # --- Determine relevant new keys for THIS tracker ---
    keys_for_this_tracker = set(relevant_keys) # Use relevant keys for the check
    relevant_new_keys = []
    if new_keys:
        relevant_new_keys = sort_keys([k for k in new_keys if k in keys_for_this_tracker])

    # --- Create tracker if it doesn't exist ---
    if not os.path.exists(output_file):
        logger.info(f"Tracker file not found: {output_file}. Creating new file.")
        if tracker_type == "mini":
            # Pass GLOBAL key_map, internal keys (filtered_keys), relevant keys for grid, and filtered new keys
            create_mini_tracker(module_path, key_map, filtered_keys, relevant_keys, relevant_new_keys)
        else:
            # Create main or doc tracker
            keys_to_write_defs = {k: key_map[k] for k in relevant_keys if k in key_map} # Definitions use relevant keys
            sorted_keys_list = sort_keys(relevant_keys)
            last_key_edit_msg = f"Assigned keys: {', '.join(relevant_new_keys)}" if relevant_new_keys else (sorted_keys_list[-1] if sorted_keys_list else "Initial creation")
            initial_grid = create_initial_grid(sorted_keys_list) # Generate initial placeholder grid
            logger.debug(f"Generated initial grid with {len(initial_grid)} rows for new tracker {output_file}.") # Added log message
            # Write using the generic write function
            write_tracker_file(output_file, keys_to_write_defs, initial_grid, last_key_edit_msg, "Initial creation")
        # REMOVED: No further update needed after creation in this call
        # REMOVED: return # <<< REMOVE THIS RETURN to allow suggestions to be applied to newly created files

    # --- Update existing tracker (or newly created one) --- # <<< MODIFIED COMMENT
    logger.info(f"Updating existing tracker: {output_file}")
    backup_tracker_file(output_file) # Backup before modifying

    lines = []
    try:
        with open(output_file, "r", encoding="utf-8") as f:
            lines = f.readlines()
    except Exception as e:
        logger.error(f"Failed to read existing tracker {output_file}: {e}")
        return # Cannot update if read fails

    # Read existing data from the lines
    existing_key_defs = _read_existing_keys(lines)
    existing_grid = _read_existing_grid(lines) # Returns compressed grid strings
    last_key_edit_line = next((line for line in lines if line.strip().lower().startswith("last_key_edit")), None)
    last_grid_edit_line = next((line for line in lines if line.strip().lower().startswith("last_grid_edit")), None)

    current_last_key_edit = last_key_edit_line.split(":", 1)[1].strip() if last_key_edit_line else ""
    current_last_grid_edit = last_grid_edit_line.split(":", 1)[1].strip() if last_grid_edit_line else ""

    # --- Determine changes and update metadata ---
    existing_keys_in_file_set = set(existing_key_defs.keys())
    # keys_for_this_tracker is already calculated based on tracker_type
    added_keys_to_this_tracker = keys_for_this_tracker - existing_keys_in_file_set
    removed_keys_from_this_tracker = existing_keys_in_file_set - keys_for_this_tracker

    # Update last_KEY_edit based on changes TO THIS TRACKER
    final_last_key_edit = current_last_key_edit # Default to existing
    if relevant_new_keys: # If global new keys intersect with this tracker's keys
         final_last_key_edit = f"Assigned keys: {', '.join(relevant_new_keys)}"
    elif added_keys_to_this_tracker: # Or if keys were added specifically to this tracker
         final_last_key_edit = f"Assigned keys: {', '.join(sort_keys(list(added_keys_to_this_tracker)))}"
    elif removed_keys_from_this_tracker: # Or if keys were removed
         final_last_key_edit = f"Removed keys: {', '.join(sort_keys(list(removed_keys_from_this_tracker)))}"

    # --- Prepare final key definitions and grid keys ---
    # Definitions should include all relevant keys for the grid
    final_key_defs = {k: key_map[k] for k in relevant_keys if k in key_map}
    final_sorted_keys_list = sort_keys(list(final_key_defs.keys())) # Use the keys actually being defined

    # --- Update Grid ---
    final_grid = existing_grid.copy() # Start with existing compressed grid
    final_last_grid_edit = current_last_grid_edit # Default

    # Adjust grid for added/removed keys
    if added_keys_to_this_tracker or removed_keys_from_this_tracker:
        final_last_grid_edit = f"Grid adjusted for key changes: Added {len(added_keys_to_this_tracker)}, Removed {len(removed_keys_from_this_tracker)}"
        # Rebuild the grid structure based on final_sorted_keys_list
        temp_decomp_grid = {}
        old_keys_list = sort_keys(list(existing_keys_in_file_set))
        old_key_to_idx = {k: i for i, k in enumerate(old_keys_list)}

        # Initialize new grid structure
        for i, row_key in enumerate(final_sorted_keys_list):
            row = [PLACEHOLDER_CHAR] * len(final_sorted_keys_list)
            row[i] = DIAGONAL_CHAR
            temp_decomp_grid[row_key] = row

        # Copy old values where keys match
        for old_row_key, compressed_row in existing_grid.items():
            if old_row_key in final_key_defs: # If the row key still exists
                decomp_row = list(decompress(compressed_row))
                for old_col_idx, value in enumerate(decomp_row):
                    if old_col_idx < len(old_keys_list): # Boundary check
                         old_col_key = old_keys_list[old_col_idx]
                         if old_col_key in final_key_defs: # If the col key still exists
                              # Find new index for the column key
                              new_col_idx = final_sorted_keys_list.index(old_col_key)
                              # Copy value if not placeholder/diagonal
                              if value != PLACEHOLDER_CHAR and temp_decomp_grid[old_row_key][new_col_idx] == PLACEHOLDER_CHAR:
                                   temp_decomp_grid[old_row_key][new_col_idx] = value

        # Compress the rebuilt grid
        final_grid = {key: compress("".join(row_list)) for key, row_list in temp_decomp_grid.items()}


    # Apply suggestions AFTER grid structure is finalized
    if filtered_suggestions: # Use the filtered/aggregated suggestions
        suggestion_applied = False
        # Use a temporary decompressed grid based on the potentially rebuilt final_grid
        temp_decomp_grid_for_sugg = {k: list(decompress(v)) for k, v in final_grid.items()}

        for row_key, deps in filtered_suggestions.items():
            if row_key not in final_sorted_keys_list:
                continue # Skip suggestions for rows not in the final grid

            current_decomp_row = temp_decomp_grid_for_sugg.get(row_key)
            if not current_decomp_row: continue # Should not happen if grid was built correctly

            for col_key, dep_char in deps:
                if col_key not in final_sorted_keys_list:
                    continue # Skip suggestions for columns not in the final grid

                try:
                    col_idx = final_sorted_keys_list.index(col_key)
                    # Apply the suggestion passed from project_analyzer (priority already handled)
                    # Check if the character is actually changing to avoid unnecessary grid edit message update
                    existing_char = current_decomp_row[col_idx]
                    # --- Apply suggestion ONLY if current char is a placeholder ---
                    if existing_char == PLACEHOLDER_CHAR and existing_char != dep_char:
                        # Ensure we don't overwrite the diagonal 'o'
                        if row_key != col_key:
                             current_decomp_row[col_idx] = dep_char
                             suggestion_applied = True
                             # Update last edit message only if a suggestion was actually applied (placeholder -> suggestion)
                             final_last_grid_edit = f"Applied suggestion: {row_key} -> {col_key} ({dep_char})"
                        # else: logger.debug(f"Skipping suggestion {row_key}->{col_key}; Attempted to overwrite diagonal.") # Optional debug
                    # else: logger.debug(f"Suggestion {row_key}->{col_key} ({dep_char}) matches existing character. No change.")

                    # --- ADD WARNING for mismatch on non-placeholder ---
                    elif existing_char != PLACEHOLDER_CHAR and existing_char != dep_char:
                        # Log a warning if the suggestion differs from a non-placeholder character
                        warning_msg = f"Suggestion Conflict in {os.path.basename(output_file)}: For {row_key}->{col_key}, grid has '{existing_char}', suggestion is '{dep_char}'. Manual review recommended."
                        logger.warning(warning_msg)
                        # <<< ADDED: Print warning directly to terminal >>>
                        print(f"WARNING: {warning_msg}")
                    # else: # Existing char is not placeholder and matches suggestion, or suggestion is invalid - no action/log needed
                    #    logger.debug(f"Suggestion {row_key}->{col_key} ({dep_char}) matches existing character '{existing_char}' or not applied. No change.")
                except (ValueError, IndexError) as e:
                     logger.error(f"Error applying suggestion {row_key}->{col_key} in {output_file}: {e}")

            # Update the temporary grid map after processing all suggestions for the row
            temp_decomp_grid_for_sugg[row_key] = current_decomp_row

        # Re-compress the grid if suggestions were applied
        if suggestion_applied:
            final_grid = {key: compress("".join(row_list)) for key, row_list in temp_decomp_grid_for_sugg.items()}


    # --- Write updated content to file ---
    try:
        # Find markers for mini-tracker preservation
        mini_tracker_start_index = -1
        mini_tracker_end_index = -1
        marker_start, marker_end = "", "" # Initialize
        if tracker_type == "mini":
            mini_tracker_info = get_mini_tracker_data()
            marker_start, marker_end = mini_tracker_info["markers"]
            try:
                # Find line indices containing the markers
                # Ensure we match the whole marker line to avoid partial matches
                mini_tracker_start_index = next(i for i, line in enumerate(lines) if line.strip() == marker_start)
                mini_tracker_end_index = next(i for i, line in enumerate(lines) if line.strip() == marker_end)
                if mini_tracker_start_index >= mini_tracker_end_index:
                     raise ValueError("Start marker found after or at the same line as end marker.") # Sanity check
            except (StopIteration, ValueError) as e:
                logger.warning(f"Mini-tracker start/end markers not found or invalid in {output_file}: {e}. Overwriting entire file.")
                mini_tracker_start_index = -1 # Signal to overwrite all
                mini_tracker_end_index = -1

        with open(output_file, "w", encoding="utf-8") as f:
            # --- Preserve content before start marker (if found) ---
            if tracker_type == "mini" and mini_tracker_start_index != -1:
                # Write lines strictly *before* the start marker line
                for i in range(mini_tracker_start_index):
                    f.write(lines[i])
                # Write the start marker line itself
                f.write(lines[mini_tracker_start_index])
                # Add a newline if the marker line didn't have one (it should)
                if not lines[mini_tracker_start_index].endswith('\n'):
                     f.write('\n')

            # --- Write the updated tracker data ---
            # Add spacing if we wrote the 'before' content or if it's not a mini-tracker
            if (tracker_type == "mini" and mini_tracker_start_index != -1) or tracker_type != "mini":
                 f.write("\n") # Add a separating newline

            _write_key_definitions(f, final_key_defs)
            f.write("\n")
            f.write(f"last_KEY_edit: {final_last_key_edit}\n")
            f.write(f"last_GRID_edit: {final_last_grid_edit}\n\n")
            _write_grid(f, final_sorted_keys_list, final_grid)
            # No newline here, let the 'after' section handle spacing if needed

            # --- Preserve content after end marker (if found) ---
            if tracker_type == "mini" and mini_tracker_end_index != -1 and mini_tracker_start_index != -1:
                 # Add newline before the end marker line
                 f.write("\n")
                 # Start writing *from* the end marker line itself
                 for i in range(mini_tracker_end_index, len(lines)):
                    f.write(lines[i])
            # --- If overwriting a mini-tracker because markers were missing, add markers ---
            elif tracker_type == "mini" and mini_tracker_start_index == -1:
                 # We just wrote the data. Need to add *both* markers if overwriting.
                 # The template should have been added manually if needed.
                 # This case is less ideal, better to fix the creation.
                 # For now, just ensure the end marker is present.
                 f.write("\n" + marker_end + "\n")


        logger.info(f"Successfully updated tracker: {output_file}")
        # Invalidate cache for this specific tracker file after writing
        invalidate_dependent_entries('tracker_data', f"tracker_data:{output_file}:.*")
        # Invalidate grid caches as content has changed
        invalidate_dependent_entries('grid_decompress', '.*')
        invalidate_dependent_entries('grid_validation', '.*')
        invalidate_dependent_entries('grid_dependencies', '.*')

    except IOError as e:
        logger.error(f"I/O Error updating tracker file {output_file}: {e}")
    except Exception as e:
        logger.exception(f"Unexpected error updating tracker file {output_file}: {e}")


# --- Export Tracker ---
def export_tracker(tracker_path: str, output_format: str = "json", output_path: Optional[str] = None) -> str:
    """
    Export a tracker file to various formats.

    Args:
        tracker_path: Path to the tracker file
        output_format: Format to export to ('md', 'json', 'csv', 'dot')
        output_path: Optional path to save the exported file
    Returns:
        Path to the exported file or error message string
    """
    tracker_path = normalize_path(tracker_path)
    check_file_modified(tracker_path) # Check cache validity

    # Read the tracker (using cached read)
    tracker_data = read_tracker_file(tracker_path)
    if not tracker_data or not tracker_data.get("keys"):
        logger.error(f"Cannot export empty or unreadable tracker: {tracker_path}")
        return f"Error: Empty tracker or tracker not found at {tracker_path}"

    # Determine output path if not provided
    if output_path is None:
        base_name = os.path.splitext(tracker_path)[0]
        output_path = normalize_path(f"{base_name}_export.{output_format}")
    else:
        output_path = normalize_path(output_path)

    try:
        dirname = os.path.dirname(output_path)
        if dirname: os.makedirs(dirname, exist_ok=True)

        if output_format == "md":
            shutil.copy2(tracker_path, output_path)
        elif output_format == "json":
            # Include all read data in JSON export
            export_data = tracker_data.copy()
            # Optionally add decompressed grid for convenience?
            # export_data['grid_decompressed'] = {k: decompress(v) for k, v in tracker_data.get("grid", {}).items()}
            with open(output_path, 'w', encoding='utf-8') as f:
                json.dump(export_data, f, indent=2, ensure_ascii=False)
        elif output_format == "csv":
            grid = tracker_data.get("grid", {})
            keys_map = tracker_data.get("keys", {})
            sorted_keys_list = sort_keys(list(keys_map.keys()))
            with open(output_path, 'w', encoding='utf-8', newline='') as f:
                import csv
                writer = csv.writer(f)
                writer.writerow(["Source Key", "Source Path", "Target Key", "Target Path", "Dependency Type"])
                for i, source_key in enumerate(sorted_keys_list):
                    compressed_row = grid.get(source_key)
                    if compressed_row:
                        decompressed_row = decompress(compressed_row)
                        if len(decompressed_row) == len(sorted_keys_list):
                            for j, dep_type in enumerate(decompressed_row):
                                if dep_type not in (EMPTY_CHAR, DIAGONAL_CHAR, PLACEHOLDER_CHAR):
                                    target_key = sorted_keys_list[j]
                                    writer.writerow([
                                        source_key, keys_map.get(source_key, ""),
                                        target_key, keys_map.get(target_key, ""),
                                        dep_type
                                    ])
                        else:
                             logger.warning(f"CSV Export: Row length mismatch for key '{source_key}' in {tracker_path}")

        elif output_format == "dot":
            grid = tracker_data.get("grid", {})
            keys_map = tracker_data.get("keys", {})
            sorted_keys_list = sort_keys(list(keys_map.keys()))
            with open(output_path, 'w', encoding='utf-8') as f:
                f.write("digraph Dependencies {\n")
                f.write("  rankdir=LR; // Left-to-right layout\n")
                f.write('  node [shape=box, style="filled", fillcolor="#EFEFEF"];\n')
                f.write('  edge [fontsize=10];\n\n')

                # Define nodes
                for key in sorted_keys_list:
                    label = f"{key}\\n{os.path.basename(keys_map.get(key, ''))}"
                    f.write(f'  "{key}" [label="{label}"];\n')
                f.write("\n")

                # Define edges
                for i, source_key in enumerate(sorted_keys_list):
                     compressed_row = grid.get(source_key)
                     if compressed_row:
                         decompressed_row = decompress(compressed_row)
                         if len(decompressed_row) == len(sorted_keys_list):
                             for j, dep_type in enumerate(decompressed_row):
                                 if dep_type not in (EMPTY_CHAR, DIAGONAL_CHAR, PLACEHOLDER_CHAR):
                                     target_key = sorted_keys_list[j]
                                     # Add styling based on type?
                                     color = "black"
                                     style = "solid"
                                     if dep_type == '>': color = "blue"
                                     elif dep_type == '<': color = "green"
                                     elif dep_type == 'x': color = "red"; style="dashed"
                                     elif dep_type == 'd': color = "orange"
                                     elif dep_type == 's': color = "grey"; style="dotted"
                                     f.write(f'  "{source_key}" -> "{target_key}" [label="{dep_type}", color="{color}", style="{style}"];\n')
                         else:
                              logger.warning(f"DOT Export: Row length mismatch for key '{source_key}' in {tracker_path}")

                f.write("}\n")
        else:
            logger.error(f"Unsupported export format: '{output_format}'")
            return f"Error: Unsupported output format '{output_format}'"

        logger.info(f"Exported tracker '{os.path.basename(tracker_path)}' to: {output_path}")
        return output_path
    except IOError as e:
        logger.error(f"I/O Error exporting tracker: {e}")
        return f"Error exporting tracker: {str(e)}"
    except Exception as e:
        logger.exception(f"Unexpected error exporting tracker: {e}")
        return f"Error exporting tracker: {str(e)}"


# --- Remove File from Tracker ---
def remove_file_from_tracker(output_file: str, file_to_remove: str):
    """Removes a file's key and row/column from the tracker. Invalidates relevant caches."""
    output_file = normalize_path(output_file)
    file_to_remove_norm = normalize_path(file_to_remove)

    if not os.path.exists(output_file):
        raise FileNotFoundError(f"Tracker file '{output_file}' not found.")

    logger.info(f"Attempting to remove file '{file_to_remove_norm}' from tracker '{output_file}'")
    backup_tracker_file(output_file) # Backup before removal

    lines = []
    try:
        with open(output_file, "r", encoding="utf-8") as f:
            lines = f.readlines()
    except Exception as e:
         raise IOError(f"Failed to read tracker file {output_file}: {e}") from e

    # Read existing data
    existing_key_defs = _read_existing_keys(lines)
    existing_grid = _read_existing_grid(lines) # Compressed grid
    last_key_edit_line = next((line for line in lines if line.strip().lower().startswith("last_key_edit")), None)
    last_grid_edit_line = next((line for line in lines if line.strip().lower().startswith("last_grid_edit")), None)
    current_last_key_edit = last_key_edit_line.split(":", 1)[1].strip() if last_key_edit_line else ""
    current_last_grid_edit = last_grid_edit_line.split(":", 1)[1].strip() if last_grid_edit_line else ""

    # Find the key to remove
    key_to_remove = None
    for k, v in existing_key_defs.items():
        if v == file_to_remove_norm:
            key_to_remove = k
            break

    if key_to_remove is None:
        logger.warning(f"File '{file_to_remove_norm}' not found in tracker '{output_file}'. No changes made.")
        # raise ValueError(f"File '{file_to_remove_norm}' not found in tracker.") # Optionally raise error
        return # Or just return gracefully

    logger.info(f"Found key '{key_to_remove}' for file '{file_to_remove_norm}'. Proceeding with removal.")

    # --- Prepare updated data ---
    # Remove key from definitions
    final_key_defs = {k: v for k, v in existing_key_defs.items() if k != key_to_remove}
    final_sorted_keys_list = sort_keys(list(final_key_defs.keys()))

    # Update metadata
    final_last_key_edit = f"Removed key: {key_to_remove}"
    final_last_grid_edit = f"Grid adjusted for removal of key: {key_to_remove}"

    # Rebuild grid without the removed key/row/column
    final_grid = {}
    old_keys_list = sort_keys(list(existing_key_defs.keys()))
    try:
        idx_to_remove = old_keys_list.index(key_to_remove)
    except ValueError:
        logger.error(f"Key '{key_to_remove}' was in definitions but not in sorted list? Skipping grid update.")
        # Fallback: Use the grid as is, but this is inconsistent
        final_grid = {k:v for k,v in existing_grid.items() if k != key_to_remove}
    else:
        for old_row_key, compressed_row in existing_grid.items():
             if old_row_key != key_to_remove: # Keep rows not being removed
                 decomp_row = list(decompress(compressed_row))
                 # Ensure row length matches old keys list before removing index
                 if len(decomp_row) == len(old_keys_list):
                      # Remove the character at the removed key's index
                      new_decomp_row_list = decomp_row[:idx_to_remove] + decomp_row[idx_to_remove+1:]
                      final_grid[old_row_key] = compress("".join(new_decomp_row_list))
                 else:
                     logger.warning(f"Row length mismatch for key '{old_row_key}' during removal. Re-initializing row.")
                     # Re-initialize row for the new size
                     row_list = [PLACEHOLDER_CHAR] * len(final_sorted_keys_list)
                     if old_row_key in final_sorted_keys_list: row_list[final_sorted_keys_list.index(old_row_key)] = DIAGONAL_CHAR
                     final_grid[old_row_key] = compress("".join(row_list))


    # --- Write updated file ---
    try:
        # Find markers for mini-tracker preservation (same logic as update_tracker)
        tracker_type = "unknown" # Determine type based on path? Or assume generic write?
        if "_module.md" in os.path.basename(output_file): tracker_type = "mini"
        # Add checks for main/doc paths if needed

        mini_tracker_start_index = -1
        mini_tracker_end_index = -1
        if tracker_type == "mini":
            mini_tracker_info = get_mini_tracker_data()
            marker_start, marker_end = mini_tracker_info["markers"]
            try:
                mini_tracker_start_index = next(i for i, line in enumerate(lines) if marker_start in line)
                mini_tracker_end_index = next(i for i, line in enumerate(lines) if marker_end in line)
            except StopIteration:
                logger.warning(f"Mini-tracker markers not found in {output_file} during removal. Overwriting entire file.")
                mini_tracker_start_index = -1

        with open(output_file, "w", encoding="utf-8") as f:
            # Preserve content before start marker (if found)
            if tracker_type == "mini" and mini_tracker_start_index != -1:
                for i in range(mini_tracker_start_index + 1):
                    f.write(lines[i])
                f.write("\n")

            # Write the updated tracker data
            _write_key_definitions(f, final_key_defs)
            f.write("\n")
            f.write(f"last_KEY_edit: {final_last_key_edit}\n")
            f.write(f"last_GRID_edit: {final_last_grid_edit}\n\n")
            _write_grid(f, final_sorted_keys_list, final_grid)
            f.write("\n")

            # Preserve content after end marker (if found)
            if tracker_type == "mini" and mini_tracker_end_index != -1 and mini_tracker_start_index != -1:
                for i in range(mini_tracker_end_index, len(lines)):
                    f.write(lines[i])
            elif tracker_type == "mini" and mini_tracker_start_index == -1:
                 f.write(get_mini_tracker_data()["markers"][1] + "\n") # Add end marker if overwriting

        logger.info(f"Successfully removed key '{key_to_remove}' and file '{file_to_remove_norm}' from tracker '{output_file}'")

        # Invalidate caches
        invalidate_dependent_entries('tracker_data', f"tracker_data:{output_file}:.*")
        invalidate_dependent_entries('grid_decompress', '.*')
        invalidate_dependent_entries('grid_validation', '.*')
        invalidate_dependent_entries('grid_dependencies', '.*')
        # Call tracker_modified if it exists and is needed
        # tracker_modified(file_to_remove_norm, os.path.dirname(output_file))

    except IOError as e:
        logger.error(f"I/O Error writing updated tracker file {output_file} after removal: {e}")
        raise # Re-raise error after logging
    except Exception as e:
        logger.exception(f"Unexpected error writing updated tracker file {output_file} after removal: {e}")
        raise # Re-raise error after logging


# EoF