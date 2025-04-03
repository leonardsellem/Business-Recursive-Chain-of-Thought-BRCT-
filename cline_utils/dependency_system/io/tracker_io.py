# io/tracker_io.py

"""
IO module for tracker file operations.
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

# Import only from utils and core layers
from cline_utils.dependency_system.core.key_manager import get_key_from_path, sort_keys, validate_key
from cline_utils.dependency_system.utils.path_utils import get_project_root, is_subpath, normalize_path, join_paths
from cline_utils.dependency_system.utils.config_manager import ConfigManager
# Assuming these plugin-like structures exist and are correctly imported
# These imports provide the functions for tracker-specific logic (filtering, aggregation, path)
from cline_utils.dependency_system.io.update_doc_tracker import doc_tracker_data
from cline_utils.dependency_system.io.update_mini_tracker import get_mini_tracker_data
from cline_utils.dependency_system.io.update_main_tracker import main_tracker_data
from cline_utils.dependency_system.utils.cache_manager import cached, check_file_modified, invalidate_dependent_entries
from cline_utils.dependency_system.core.dependency_grid import compress, create_initial_grid, decompress, validate_grid, PLACEHOLDER_CHAR, EMPTY_CHAR, DIAGONAL_CHAR

import logging
logger = logging.getLogger(__name__)

# Caching for get_tracker_path (consider config mtime)
# @cached("tracker_paths",
#         key_func=lambda project_root, tracker_type="main", module_path=None:
#         f"tracker_path:{normalize_path(project_root)}:{tracker_type}:{normalize_path(module_path) if module_path else 'none'}:{(os.path.getmtime(ConfigManager().config_path) if os.path.exists(ConfigManager().config_path) else 0)}")
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

# Caching for read_tracker_file based on path and modification time.
# @cached("tracker_data",
#         key_func=lambda tracker_path:
#         f"tracker_data:{normalize_path(tracker_path)}:{(os.path.getmtime(tracker_path) if os.path.exists(tracker_path) else 0)}")
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
                        keys[k] = normalize_path(v.strip()) # Normalize and strip whitespace from path
                    else:
                        logger.warning(f"Skipping invalid key format in {tracker_path}: '{k}'")
                # else: logger.debug(f"Skipping malformed key definition line in {tracker_path}: '{line}'")


        # Parse grid using regex for robustness
        grid_section_match = re.search(r'---GRID_START---\n(.*?)\n---GRID_END---', content, re.DOTALL | re.IGNORECASE)
        if grid_section_match:
            grid_section_content = grid_section_match.group(1)
            lines = grid_section_content.strip().splitlines()
            # Skip header line (X ...) if present
            if lines and (lines[0].strip().upper().startswith("X ") or lines[0].strip() == "X"):
                lines = lines[1:]
            for line in lines:
                line = line.strip()
                match = re.match(r'^([a-zA-Z0-9]+)\s*=\s*(.*)$', line)
                if match:
                    k, v = match.groups()
                    if validate_key(k): # Also validate grid key format
                       # Only add grid rows for keys defined above? No, allow grid rows even if key def is missing (might be temporary state)
                       grid[k] = v.strip() # Store compressed string
                    else:
                         logger.warning(f"Grid row key '{k}' in {tracker_path} has invalid format. Skipping.")
                # else: logger.debug(f"Skipping malformed grid line in {tracker_path}: '{line}'")

        # Parse metadata using regex for robustness
        last_key_edit_match = re.search(r'^last_KEY_edit\s*:\s*(.*)$', content, re.MULTILINE | re.IGNORECASE)
        if last_key_edit_match:
            last_key_edit = last_key_edit_match.group(1).strip()

        last_grid_edit_match = re.search(r'^last_GRID_edit\s*:\s*(.*)$', content, re.MULTILINE | re.IGNORECASE)
        if last_grid_edit_match:
            last_grid_edit = last_grid_edit_match.group(1).strip()

        logger.debug(f"Read tracker '{os.path.basename(tracker_path)}': {len(keys)} keys, {len(grid)} grid rows")
        return {"keys": keys, "grid": grid, "last_key_edit": last_key_edit, "last_grid_edit": last_grid_edit}

    except Exception as e:
        logger.exception(f"Error reading tracker file {tracker_path}: {e}") # Use exception for stack trace
        return {"keys": {}, "grid": {}, "last_key_edit": "", "last_grid_edit": ""}


def write_tracker_file(tracker_path: str, keys: Dict[str, str], grid: Dict[str, str], last_key_edit: str, last_grid_edit: str = "") -> bool:
    """
    Write tracker data to a file in markdown format. Ensures directory exists.
    Performs validation before writing.

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
        if dirname:
            os.makedirs(dirname, exist_ok=True)

        # Sort keys for consistent output
        sorted_keys_list = sort_keys(list(keys.keys()))

        # --- Validate grid before writing ---
        if not validate_grid(grid, sorted_keys_list):
            logger.error(f"Aborting write to {tracker_path} due to grid validation failure. Check previous logs for details.")
            return False

        # Rebuild/Fix Grid to ensure consistency with sorted_keys_list
        final_grid = {}
        expected_len = len(sorted_keys_list)
        key_to_idx = {key: i for i, key in enumerate(sorted_keys_list)}

        for row_key in sorted_keys_list:
            compressed_row = grid.get(row_key)
            row_list = None

            if compressed_row is not None:
                try:
                    decompressed_row = decompress(compressed_row)
                    if len(decompressed_row) == expected_len:
                        row_list = list(decompressed_row) # Use existing if valid length
                    else:
                        logger.warning(f"Correcting grid row length for key '{row_key}' in {tracker_path} (expected {expected_len}, got {len(decompressed_row)}).")
                except Exception as decomp_err:
                     logger.warning(f"Error decompressing row for key '{row_key}' in {tracker_path}: {decomp_err}. Re-initializing.")

            if row_list is None: # Initialize if missing, invalid length, or decompression error
                row_list = [PLACEHOLDER_CHAR] * expected_len
                row_idx = key_to_idx.get(row_key)
                if row_idx is not None:
                    row_list[row_idx] = DIAGONAL_CHAR
                else: # Should not happen if row_key is from sorted_keys_list
                    logger.error(f"Key '{row_key}' not found in index map during grid rebuild!")

            final_grid[row_key] = compress("".join(row_list))


        # --- Write Content ---
        with open(tracker_path, 'w', encoding='utf-8', newline='\n') as f: # Use LF line endings
            # --- Write key definitions ---
            f.write("---KEY_DEFINITIONS_START---\n")
            f.write("Key Definitions:\n")
            for key in sorted_keys_list:
                f.write(f"{key}: {normalize_path(keys[key])}\n") # Ensure path uses forward slashes
            f.write("---KEY_DEFINITIONS_END---\n\n")

            # --- Write metadata ---
            f.write(f"last_KEY_edit: {last_key_edit}\n")
            f.write(f"last_GRID_edit: {last_grid_edit}\n\n")

            # --- Write grid ---
            f.write("---GRID_START---\n")
            if sorted_keys_list:
                f.write(f"X {' '.join(sorted_keys_list)}\n")
                for key in sorted_keys_list:
                    # Use the validated/rebuilt grid row
                    f.write(f"{key} = {final_grid.get(key, '')}\n") # Use final_grid
            else:
                f.write("X \n") # Empty header if no keys
            f.write("---GRID_END---\n")

        logger.info(f"Successfully wrote tracker file: {tracker_path} with {len(sorted_keys_list)} keys.")
        # Invalidate cache for this specific tracker file after writing
        invalidate_dependent_entries('tracker_data', f"tracker_data:{tracker_path}:.*")
        return True

    except IOError as e:
        logger.error(f"I/O Error writing tracker file {tracker_path}: {e}", exc_info=True)
        return False
    except Exception as e:
        logger.exception(f"Unexpected error writing tracker file {tracker_path}: {e}")
        return False


def backup_tracker_file(tracker_path: str) -> str:
    """
    Create a backup of a tracker file, keeping the 2 most recent backups.

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
        backup_dir_rel = config.get_path("backups_dir", "cline_docs/backups") # Default backup dir
        backup_dir_abs = normalize_path(os.path.join(project_root, backup_dir_rel))

        os.makedirs(backup_dir_abs, exist_ok=True)

        # Create backup filename with timestamp
        timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S_%f") # Added microseconds
        base_name = os.path.basename(tracker_path)
        backup_filename = f"{base_name}.{timestamp}.bak"
        backup_path = os.path.join(backup_dir_abs, backup_filename)

        shutil.copy2(tracker_path, backup_path) # copy2 preserves metadata
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
                    # else: logger.debug(f"Backup filename format mismatch: {filename}")


            # Sort by timestamp, newest first
            backup_files.sort(key=lambda x: x[0], reverse=True)

            if len(backup_files) > 2:
                files_to_delete = backup_files[2:]
                logger.debug(f"Cleaning up {len(files_to_delete)} older backups for '{base_name}'.")
                for _, file_path_to_delete in files_to_delete:
                    try:
                        os.remove(file_path_to_delete)
                        # logger.debug(f"Deleted old backup: {file_path_to_delete}")
                    except OSError as delete_error:
                        logger.error(f"Error deleting old backup {file_path_to_delete}: {delete_error}")
        except Exception as cleanup_error:
            logger.error(f"Error during backup cleanup for {base_name}: {cleanup_error}")
        # --- End Cleanup ---

        return backup_path
    except Exception as e:
        logger.error(f"Error backing up tracker file {tracker_path}: {e}", exc_info=True)
        return ""

# --- Helper function for merge ---
def _merge_grids(primary_grid: Dict[str, str], secondary_grid: Dict[str, str],
                 primary_keys_list: List[str], secondary_keys_list: List[str],
                 merged_keys_list: List[str]) -> Dict[str, str]:
    """Merges two decompressed grids based on the merged key list. Primary overwrites secondary."""
    merged_decompressed_grid = {}
    merged_size = len(merged_keys_list)
    key_to_merged_idx = {key: i for i, key in enumerate(merged_keys_list)}

    # Initialize merged grid with placeholders and diagonal
    for i, row_key in enumerate(merged_keys_list):
        row = [PLACEHOLDER_CHAR] * merged_size
        row[i] = DIAGONAL_CHAR
        merged_decompressed_grid[row_key] = row

    config = ConfigManager() # For priorities during merge
    get_priority = config.get_char_priority

    # Decompress input grids (handle potential errors)
    def safe_decompress(grid_data, keys_list):
        decomp_grid = {}
        key_to_idx = {k: i for i, k in enumerate(keys_list)}
        expected_len = len(keys_list)
        for key, compressed in grid_data.items():
            if key not in key_to_idx: continue # Skip rows not in key list
            try:
                decomp = list(decompress(compressed))
                if len(decomp) == expected_len:
                    decomp_grid[key] = decomp
                else:
                    logger.warning(f"Merge Prep: Incorrect length for key '{key}' (expected {expected_len}, got {len(decomp)}). Skipping row.")
            except Exception as e:
                logger.warning(f"Merge Prep: Failed to decompress row for key '{key}': {e}. Skipping row.")
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
                 if pri_col_idx < len(primary_decomp[row_key]):
                      primary_val = primary_decomp[row_key][pri_col_idx]

            secondary_val = None
            if row_key in secondary_decomp and col_key in key_to_secondary_idx:
                 sec_col_idx = key_to_secondary_idx[col_key]
                 if sec_col_idx < len(secondary_decomp[row_key]):
                      secondary_val = secondary_decomp[row_key][sec_col_idx]

            # Determine final value (primary takes precedence over secondary, ignore placeholders)
            final_val = PLACEHOLDER_CHAR
            if primary_val is not None and primary_val != PLACEHOLDER_CHAR:
                final_val = primary_val
            elif secondary_val is not None and secondary_val != PLACEHOLDER_CHAR:
                final_val = secondary_val

            merged_decompressed_grid[row_key][merged_col_idx] = final_val

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

    logger.info(f"Attempting to merge '{os.path.basename(primary_tracker_path)}' (primary) and '{os.path.basename(secondary_tracker_path)}' into '{os.path.basename(output_path)}'")

    # Backup before potentially overwriting
    backup_made = False
    if output_path == primary_tracker_path and os.path.exists(primary_tracker_path):
        backup_tracker_file(primary_tracker_path); backup_made = True
    elif output_path == secondary_tracker_path and os.path.exists(secondary_tracker_path):
         backup_tracker_file(secondary_tracker_path); backup_made = True
    if backup_made: logger.info(f"Backed up target file before merge: {os.path.basename(output_path)}")

    # Read both trackers (using cached read)
    primary_data = read_tracker_file(primary_tracker_path)
    secondary_data = read_tracker_file(secondary_tracker_path)

    # Check if data is valid
    primary_keys = primary_data.get("keys", {})
    secondary_keys = secondary_data.get("keys", {})

    if not primary_keys and not secondary_keys:
         logger.warning("Both trackers are empty or unreadable. Cannot merge.")
         return None
    elif not primary_keys:
        logger.info(f"Primary tracker {os.path.basename(primary_tracker_path)} empty/unreadable. Using secondary tracker.")
        merged_data = secondary_data
    elif not secondary_keys:
        logger.info(f"Secondary tracker {os.path.basename(secondary_tracker_path)} empty/unreadable. Using primary tracker.")
        merged_data = primary_data
    else:
        # --- Perform the merge ---
        logger.debug(f"Merging {len(primary_keys)} primary keys and {len(secondary_keys)} secondary keys.")

        # Merge keys (primary takes precedence for path if key exists in both)
        merged_keys_map = {**secondary_keys, **primary_keys}
        merged_keys_list = sort_keys(list(merged_keys_map.keys()))

        # Merge the grids (handles decompression inside)
        merged_compressed_grid = _merge_grids(
            primary_data.get("grid", {}), secondary_data.get("grid", {}),
            sort_keys(list(primary_keys.keys())),
            sort_keys(list(secondary_keys.keys())),
            merged_keys_list
        )

        # Merge metadata (simple precedence for now, consider timestamp comparison?)
        merged_last_key_edit = primary_data.get("last_key_edit", "") or secondary_data.get("last_key_edit", "")
        merged_last_grid_edit = primary_data.get("last_grid_edit", "") or secondary_data.get("last_grid_edit", "")
        # Use a timestamp for the merge event itself?
        merged_last_grid_edit = f"Merged from {os.path.basename(primary_tracker_path)} and {os.path.basename(secondary_tracker_path)} on {datetime.datetime.now().isoformat()}"

        merged_data = {
            "keys": merged_keys_map,
            "grid": merged_compressed_grid,
            "last_key_edit": merged_last_key_edit,
            "last_grid_edit": merged_last_grid_edit,
        }

    # Write the merged tracker
    if write_tracker_file(output_path, merged_data["keys"], merged_data["grid"], merged_data["last_key_edit"], merged_data["last_grid_edit"]):
        logger.info(f"Successfully merged trackers into: {output_path}")
        # Invalidate caches related to the output file AND potentially source files if output overwrites
        invalidate_dependent_entries('tracker_data', f"tracker_data:{output_path}:.*")
        if output_path == primary_tracker_path:
             invalidate_dependent_entries('tracker_data', f"tracker_data:{primary_tracker_path}:.*")
        if output_path == secondary_tracker_path:
             invalidate_dependent_entries('tracker_data', f"tracker_data:{secondary_tracker_path}:.*")
        # Invalidate grid-related caches
        invalidate_dependent_entries('grid_decompress', '.*')
        invalidate_dependent_entries('grid_validation', '.*')
        invalidate_dependent_entries('grid_dependencies', '.*')
        return merged_data
    else:
        logger.error(f"Failed to write merged tracker to: {output_path}")
        return None

# --- Helper functions for update_tracker ---

def _read_existing_keys(lines: List[str]) -> Dict[str, str]:
    """Reads existing key definitions from lines."""
    key_map = {}
    in_section = False
    key_def_start_pattern = re.compile(r'^---KEY_DEFINITIONS_START---$', re.IGNORECASE)
    key_def_end_pattern = re.compile(r'^---KEY_DEFINITIONS_END---$', re.IGNORECASE)

    for line in lines:
        if key_def_end_pattern.match(line.strip()): # Check stripped line for end marker
            break # Stop processing after end marker
        if in_section:
            line_content = line.strip()
            if not line_content or line_content.lower().startswith("key definitions:"):
                continue
            match = re.match(r'^([a-zA-Z0-9]+)\s*:\s*(.*)$', line_content)
            if match:
                k, v = match.groups()
                if validate_key(k):
                    key_map[k] = normalize_path(v.strip())
            # else: logger.debug(f"Skipping malformed key line in _read_existing_keys: '{line_content}'")
        elif key_def_start_pattern.match(line.strip()): # Check stripped line for start marker
            in_section = True
    return key_map

def _read_existing_grid(lines: List[str]) -> Dict[str, str]:
    """Reads the existing compressed grid data from lines."""
    grid_map = {}
    in_section = False
    grid_start_pattern = re.compile(r'^---GRID_START---$', re.IGNORECASE)
    grid_end_pattern = re.compile(r'^---GRID_END---$', re.IGNORECASE)

    for line in lines:
        if grid_end_pattern.match(line.strip()): # Check stripped line
            break
        if in_section:
            line_content = line.strip()
            if line_content.upper().startswith("X ") or line_content == "X":
                continue # Skip header
            match = re.match(r'^([a-zA-Z0-9]+)\s*=\s*(.*)$', line_content)
            if match:
                k, v = match.groups()
                if validate_key(k): # Validate key before adding
                   grid_map[k] = v.strip()
            # else: logger.debug(f"Skipping malformed grid line in _read_existing_grid: '{line_content}'")
        elif grid_start_pattern.match(line.strip()): # Check stripped line
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
    """Writes the grid section to the provided file object, ensuring correctness."""
    file_obj.write("---GRID_START---\n")
    if not sorted_keys_list:
        file_obj.write("X \n") # Empty header
    else:
        file_obj.write(f"X {' '.join(sorted_keys_list)}\n")
        expected_len = len(sorted_keys_list)
        key_to_idx = {key: i for i, key in enumerate(sorted_keys_list)}

        for row_key in sorted_keys_list:
            compressed_row = grid.get(row_key)
            final_compressed_row = None

            if compressed_row is not None:
                try:
                    decompressed = decompress(compressed_row)
                    if len(decompressed) == expected_len:
                        final_compressed_row = compressed_row # Use existing if valid
                    else:
                        logger.warning(f"Correcting grid row length for key '{row_key}' before write (expected {expected_len}, got {len(decompressed)}).")
                except Exception:
                     logger.warning(f"Error decompressing row for key '{row_key}' before write. Re-initializing.")

            if final_compressed_row is None: # Initialize if missing or invalid
                 row_list = [PLACEHOLDER_CHAR] * expected_len
                 row_idx = key_to_idx.get(row_key)
                 if row_idx is not None: row_list[row_idx] = DIAGONAL_CHAR
                 final_compressed_row = compress("".join(row_list))

            file_obj.write(f"{row_key} = {final_compressed_row}\n")
    file_obj.write("---GRID_END---\n")


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

def create_mini_tracker(module_path: str,
                        global_key_map: Dict[str, str], # Full key map
                        relevant_keys_for_grid: List[str], # Keys needed in grid (internal + external deps)
                        new_keys_for_this_tracker: Optional[List[str]] = None): # Filtered new keys
    """Creates a new mini-tracker file with the template."""
    mini_tracker_info = get_mini_tracker_data()
    template = mini_tracker_info["template"]
    marker_start, marker_end = mini_tracker_info["markers"]
    norm_module_path = normalize_path(module_path)
    module_name = os.path.basename(norm_module_path)
    output_file = get_mini_tracker_path(norm_module_path) # Use helper

    # Definitions should only include keys relevant to the grid
    keys_to_write_defs = {k: global_key_map.get(k, "PATH_NOT_FOUND_IN_GLOBAL_MAP")
                          for k in relevant_keys_for_grid if k in global_key_map}

    # Ensure module's own key is included if it exists
    module_key = get_key_from_path(norm_module_path, global_key_map)
    if module_key and module_key not in relevant_keys_for_grid:
        relevant_keys_for_grid.append(module_key)
        if module_key not in keys_to_write_defs:
             keys_to_write_defs[module_key] = global_key_map.get(module_key)

    # Grid dimensions are based on relevant_keys_for_grid
    sorted_relevant_keys_list = sort_keys(relevant_keys_for_grid)

    try:
        dirname = os.path.dirname(output_file)
        if dirname: os.makedirs(dirname, exist_ok=True)

        with open(output_file, "w", encoding="utf-8", newline='\n') as f:
            # Write the main template part (may include start marker)
            # Format with module_name if placeholder exists
            try:
                 f.write(template.format(module_name=module_name))
            except KeyError: # Handle case where template doesn't use {module_name}
                 f.write(template)

            # Check if start marker was already in template
            if marker_start not in template:
                 f.write("\n" + marker_start + "\n") # Add start marker if needed
            f.write("\n") # Ensure newline after start marker section

            # --- Write the tracker data section ---
            _write_key_definitions(f, keys_to_write_defs)
            f.write("\n") # Separator

            last_key_edit_msg = f"Assigned keys: {', '.join(new_keys_for_this_tracker)}" if new_keys_for_this_tracker else (f"Initial key: {module_key}" if module_key else "Initial creation")
            f.write(f"last_KEY_edit: {last_key_edit_msg}\n")
            f.write(f"last_GRID_edit: Initial creation\n\n") # Separator

            # Write the grid using the relevant keys and an initial empty grid
            initial_grid = create_initial_grid(sorted_relevant_keys_list)
            _write_grid(f, sorted_relevant_keys_list, initial_grid)
            f.write("\n") # Add newline before end marker

            # Ensure end marker is present
            if marker_end not in template:
                 f.write(marker_end + "\n")

        logger.info(f"Created new mini tracker: {output_file}")
        return True # Indicate success

    except IOError as e:
         logger.error(f"I/O Error creating mini tracker {output_file}: {e}", exc_info=True)
         return False
    except Exception as e:
         logger.exception(f"Unexpected error creating mini tracker {output_file}: {e}")
         return False

# --- update_tracker (Main dispatcher) ---
def update_tracker(output_file_suggestion: str, # Path suggestion (may be ignored for mini/main)
                   key_map: Dict[str, str], # GLOBAL key map
                   tracker_type: str = "main",
                   suggestions: Optional[Dict[str, List[Tuple[str, str]]]] = None, # Used by mini/doc. Main gets from aggregation.
                   file_to_module: Optional[Dict[str, str]] = None, # Needed by mini and main aggregation
                   new_keys: Optional[List[str]] = None): # GLOBAL list of new keys
    """
    Updates or creates a tracker file based on type. Invalidates cache on changes.
    Calls tracker-specific logic for filtering, aggregation (main), and path determination.
    """
    project_root = get_project_root()
    config = ConfigManager()
    get_priority = config.get_char_priority

    output_file = "" # Final path will be determined based on type
    filtered_keys = {} # Keys relevant for DEFINITIONS in this tracker
    relevant_keys_for_grid = [] # Keys relevant for GRID rows/columns in this tracker
    final_suggestions_to_apply = defaultdict(list) # Suggestions filtered/aggregated for THIS tracker
    module_path = "" # Keep track of module path for mini-trackers

    # --- Determine Type-Specific Settings ---
    if tracker_type == "main":
        output_file = main_tracker_data["get_tracker_path"](project_root)
        filtered_keys = main_tracker_data["key_filter"](project_root, key_map)
        relevant_keys_for_grid = list(filtered_keys.keys())
        logger.info(f"Main tracker update for {len(relevant_keys_for_grid)} modules.")
        # Call aggregation function - THIS IS THE SOURCE OF SUGGESTIONS FOR MAIN
        logger.debug("Performing main tracker aggregation...")
        try:
            # Aggregation reads mini-trackers and performs hierarchical rollup
            aggregated_result = main_tracker_data["dependency_aggregation"](
                project_root, key_map, filtered_keys, file_to_module
            )
            # Convert result to defaultdict format
            for src, targets in aggregated_result.items():
                 final_suggestions_to_apply[src].extend(targets)
            logger.info(f"Main tracker aggregation complete. Found {sum(len(v) for v in final_suggestions_to_apply.values())} aggregated dependencies.")
        except Exception as agg_err:
            logger.error(f"Main tracker aggregation failed: {agg_err}", exc_info=True)
            # Continue with empty suggestions if aggregation fails

    elif tracker_type == "doc":
        output_file = doc_tracker_data["get_tracker_path"](project_root)
        filtered_keys = doc_tracker_data["file_inclusion"](project_root, key_map)
        # Grid includes only files from the filtered keys
        relevant_keys_for_grid = [k for k, p in filtered_keys.items() if os.path.isfile(normalize_path(p))]
        logger.info(f"Doc tracker update for {len(relevant_keys_for_grid)} files.")
        # Use passed-in suggestions, filtering happens during grid update below
        if suggestions:
             for src, targets in suggestions.items():
                  final_suggestions_to_apply[src].extend(targets)

    elif tracker_type == "mini":
        if not file_to_module:
            logger.error("file_to_module mapping is required for mini-tracker updates.")
            return
        if not key_map:
            logger.warning("Global key_map is empty, cannot determine mini-tracker path/content.")
            return

        # Derive module_path from the initial suggestion (e.g., parent dir of a file)
        # Or more reliably, derive from the FIRST key in suggestions IF available
        # Let's rely on project_analyzer passing the correct module context via output_file_suggestion
        potential_module_path = os.path.dirname(normalize_path(output_file_suggestion))
        module_key = get_key_from_path(potential_module_path, key_map)

        if not module_key or potential_module_path not in key_map.values():
             logger.error(f"Cannot determine valid module path/key from suggestion: {output_file_suggestion}")
             return

        module_path = potential_module_path
        output_file = get_mini_tracker_path(module_path) # Get definitive path

        # Filter keys internal to this module
        internal_keys = {k: v for k, v in key_map.items() if is_subpath(normalize_path(v), module_path)}
        internal_keys_set = set(internal_keys.keys())
        filtered_keys = internal_keys # Definitions only include internal keys

        # Determine relevant keys for the grid (internal + external dependencies touched by internal files)
        relevant_keys_set = internal_keys_set.copy()

        config = ConfigManager()
        project_root_for_exclude = get_project_root() # Get project root for absolute paths
        # Get ALL excluded paths (dirs, specific files, AND patterns)
        excluded_dirs_abs = {normalize_path(os.path.join(project_root_for_exclude, p)) for p in config.get_excluded_dirs()}
        # get_excluded_paths now includes pattern results
        excluded_files_abs = set(config.get_excluded_paths()) # This returns absolute paths
        all_excluded_abs = excluded_dirs_abs.union(excluded_files_abs)

        if suggestions:
            for src_key, deps in suggestions.items():
                 source_is_internal = src_key in internal_keys_set
                 if source_is_internal:
                      src_path = key_map.get(src_key)
                      if src_path and src_path in all_excluded_abs:
                           continue # Skip suggestions FROM excluded files
                      relevant_keys_set.add(src_key) # Add internal source

                      for target_key, dep_char in deps:
                           if dep_char != PLACEHOLDER_CHAR and dep_char != DIAGONAL_CHAR and target_key in key_map:
                                tgt_path = key_map.get(target_key)
                                if not tgt_path or tgt_path in all_excluded_abs:
                                     continue # Skip suggestions TO excluded files
                                relevant_keys_set.add(target_key) # Add target if dependency exists and not excluded

        # Also consider incoming dependencies to internal files
        all_target_keys_in_suggestions = {tgt for deps in suggestions.values() for tgt, _ in deps}
        for target_key in all_target_keys_in_suggestions:
             if target_key in internal_keys_set:
                 # --- ADD Check: Ensure target (internal) is not excluded ---
                 tgt_path = key_map.get(target_key)
                 if tgt_path and tgt_path in all_excluded_abs:
                      continue # Skip incoming deps TO excluded internal files

                 # Find sources pointing to this non-excluded internal target
                 for src_key, deps in suggestions.items():
                     if any(t == target_key and c != PLACEHOLDER_CHAR and c != DIAGONAL_CHAR for t, c in deps):
                         if src_key in key_map: # Ensure source exists
                             # --- ADD Check: Ensure source is not excluded ---
                             src_path = key_map.get(src_key)
                             if not src_path or src_path in all_excluded_abs:
                                 continue # Skip incoming deps FROM excluded files
                             relevant_keys_set.add(src_key) # Add non-excluded source

        # --- FINAL FILTERING: Remove any keys corresponding to excluded paths ---
        final_relevant_keys_list = []
        for k in sort_keys(list(relevant_keys_set)):
            path = key_map.get(k)
            if path and path not in all_excluded_abs:
                 final_relevant_keys_list.append(k)
            # else: logger.debug(f"Filtering excluded key '{k}' from mini-tracker grid {os.path.basename(output_file)}")

        relevant_keys_for_grid = final_relevant_keys_list # Use the final filtered list

        logger.info(f"Mini tracker update for module {module_key} ({os.path.basename(module_path)}). Grid keys: {len(relevant_keys_for_grid)}.")

        # Use passed-in suggestions, filtering happens during grid update below
        if suggestions:
             for src, targets in suggestions.items():
                  final_suggestions_to_apply[src].extend(targets)
    else:
        raise ValueError(f"Unknown tracker type: {tracker_type}")

    # --- Common Logic: Read Existing / Create New ---
    check_file_modified(output_file) # Check cache validity

    # Determine relevant new keys for THIS tracker's definitions/grid
    keys_in_final_grid_set = set(relevant_keys_for_grid)
    relevant_new_keys_list = []
    if new_keys:
        relevant_new_keys_list = sort_keys([k for k in new_keys if k in keys_in_final_grid_set])

    existing_key_defs = {}
    existing_grid = {}
    current_last_key_edit = ""
    current_last_grid_edit = ""
    lines = []
    tracker_exists = os.path.exists(output_file)

    if tracker_exists:
        try:
            with open(output_file, "r", encoding="utf-8") as f:
                lines = f.readlines()
            existing_key_defs = _read_existing_keys(lines)
            existing_grid = _read_existing_grid(lines) # Returns compressed grid strings
            last_key_edit_line = next((line for line in lines if line.strip().lower().startswith("last_key_edit")), None)
            last_grid_edit_line = next((line for line in lines if line.strip().lower().startswith("last_grid_edit")), None)
            current_last_key_edit = last_key_edit_line.split(":", 1)[1].strip() if last_key_edit_line else "Unknown"
            current_last_grid_edit = last_grid_edit_line.split(":", 1)[1].strip() if last_grid_edit_line else "Unknown"
        except Exception as e:
            logger.error(f"Failed to read existing tracker {output_file}: {e}. Proceeding cautiously.", exc_info=True)
            # Reset state if read fails badly
            existing_key_defs = {}; existing_grid = {}; current_last_key_edit = ""; current_last_grid_edit = ""; lines = []
            tracker_exists = False # Treat as non-existent if read failed

    # Create tracker if it doesn't exist
    if not tracker_exists:
        logger.info(f"Tracker file not found: {output_file}. Creating new file.")
        created_ok = False
        if tracker_type == "mini":
            # Pass GLOBAL key_map, relevant keys for grid, and filtered new keys
            created_ok = create_mini_tracker(module_path, key_map, relevant_keys_for_grid, relevant_new_keys_list)
        else: # Create main or doc tracker
            keys_to_write_defs = {k: key_map[k] for k in relevant_keys_for_grid if k in key_map}
            sorted_keys_list = sort_keys(relevant_keys_for_grid)
            last_key_edit_msg = f"Assigned keys: {', '.join(relevant_new_keys_list)}" if relevant_new_keys_list else (f"Initial keys: {len(sorted_keys_list)}" if sorted_keys_list else "Initial creation")
            initial_grid = create_initial_grid(sorted_keys_list)
            created_ok = write_tracker_file(output_file, keys_to_write_defs, initial_grid, last_key_edit_msg, "Initial creation")

        if not created_ok:
             logger.error(f"Failed to create new tracker {output_file}. Aborting update.")
             return # Stop if creation failed

        # Re-read the newly created file to proceed with applying suggestions
        try:
            with open(output_file, "r", encoding="utf-8") as f:
                lines = f.readlines()
            existing_key_defs = _read_existing_keys(lines)
            existing_grid = _read_existing_grid(lines)
            current_last_key_edit = f"Assigned keys: {', '.join(relevant_new_keys_list)}" if relevant_new_keys_list else "Initial creation"
            current_last_grid_edit = "Initial creation"
        except Exception as e:
             logger.error(f"Failed to read newly created tracker {output_file}: {e}. Aborting update.", exc_info=True)
             return

    # --- Update Existing Tracker ---
    logger.debug(f"Updating tracker: {output_file}")
    if tracker_exists: # Only backup if it existed before this function call
        backup_tracker_file(output_file)

    # --- Key Definition Update ---
    # Final definitions should match the keys relevant to this tracker's grid
    final_key_defs = {k: key_map[k] for k in relevant_keys_for_grid if k in key_map}
    final_sorted_keys_list = sort_keys(list(final_key_defs.keys())) # Keys for the final grid

    # --- Determine Key Changes for Metadata ---
    existing_keys_in_file_set = set(existing_key_defs.keys())
    keys_in_final_grid_set = set(final_sorted_keys_list) # Use the final grid keys for comparison
    added_keys_to_this_tracker = keys_in_final_grid_set - existing_keys_in_file_set
    removed_keys_from_this_tracker = existing_keys_in_file_set - keys_in_final_grid_set

    final_last_key_edit = current_last_key_edit # Default to existing
    if relevant_new_keys_list: # Highest precedence: newly assigned keys relevant here
         final_last_key_edit = f"Assigned keys: {', '.join(relevant_new_keys_list)}"
    elif added_keys_to_this_tracker or removed_keys_from_this_tracker: # If keys changed in this tracker's scope
         change_parts = []
         if added_keys_to_this_tracker: change_parts.append(f"Added {len(added_keys_to_this_tracker)} keys")
         if removed_keys_from_this_tracker: change_parts.append(f"Removed {len(removed_keys_from_this_tracker)} keys")
         final_last_key_edit = f"Keys updated: {'; '.join(change_parts)}"

    # --- Grid Structure Update ---
    final_grid = {} # Rebuild the grid based on final_sorted_keys_list
    grid_structure_changed = bool(added_keys_to_this_tracker or removed_keys_from_this_tracker)
    final_last_grid_edit = current_last_grid_edit # Default

    if grid_structure_changed:
        final_last_grid_edit = f"Grid structure updated ({datetime.datetime.now().isoformat()})"
        logger.debug(f"Rebuilding grid structure for {output_file}. Added: {len(added_keys_to_this_tracker)}, Removed: {len(removed_keys_from_this_tracker)}")

    temp_decomp_grid = {}
    old_keys_list = sort_keys(list(existing_key_defs.keys())) # Use keys from the read file
    old_key_to_idx = {k: i for i, k in enumerate(old_keys_list)}
    final_key_to_idx = {k: i for i, k in enumerate(final_sorted_keys_list)}

    # Initialize new grid structure
    for row_key in final_sorted_keys_list:
        row_list = [PLACEHOLDER_CHAR] * len(final_sorted_keys_list)
        row_idx = final_key_to_idx.get(row_key)
        if row_idx is not None: row_list[row_idx] = DIAGONAL_CHAR
        temp_decomp_grid[row_key] = row_list

    # Copy old values where keys still exist
    for old_row_key, compressed_row in existing_grid.items():
        if old_row_key in final_key_to_idx: # If the row key is kept
            try:
                decomp_row = list(decompress(compressed_row))
                # Ensure decompressed row has expected length based on *old* keys
                if len(decomp_row) == len(old_keys_list):
                    for old_col_idx, value in enumerate(decomp_row):
                         # Prevent IndexError if old_keys_list is unexpectedly short
                         if old_col_idx < len(old_keys_list):
                             old_col_key = old_keys_list[old_col_idx]
                             if old_col_key in final_key_to_idx: # If the col key is also kept
                                 new_col_idx = final_key_to_idx[old_col_key]
                                 new_row_idx = final_key_to_idx[old_row_key] # Get index for the row key in the new grid

                                 # Copy the old value, unless it's the diagonal cell in the *new* grid
                                 if new_row_idx != new_col_idx:
                                     temp_decomp_grid[old_row_key][new_col_idx] = value
                                 # else: Diagonal was already set during init, don't overwrite with old value
                         # else: logger.warning(f"old_col_idx {old_col_idx} out of bounds for old_keys_list (len {len(old_keys_list)})")
                else:
                     logger.warning(f"Grid Rebuild: Row length mismatch for '{old_row_key}' in {output_file}. Skipping values.")
            except Exception as e:
                 logger.warning(f"Grid Rebuild: Error processing row '{old_row_key}' in {output_file}: {e}. Skipping values.")

    # --- Apply Suggestions to Decompressed Grid ---
    suggestion_applied = False
    if final_suggestions_to_apply:
        logger.debug(f"Applying {sum(len(v) for v in final_suggestions_to_apply.values())} suggestions to grid for {output_file}")
        for row_key, deps in final_suggestions_to_apply.items():
            if row_key not in final_key_to_idx: continue # Skip suggestions for rows not in the final grid
            current_decomp_row = temp_decomp_grid.get(row_key)
            if not current_decomp_row: continue

            for col_key, dep_char in deps:
                if col_key not in final_key_to_idx: continue # Skip suggestions for columns not in final grid
                if row_key == col_key: continue # Never overwrite diagonal

                col_idx = final_key_to_idx[col_key]
                existing_char = current_decomp_row[col_idx]

                # Apply suggestion only if current char is placeholder
                if existing_char == PLACEHOLDER_CHAR and dep_char != PLACEHOLDER_CHAR:
                    current_decomp_row[col_idx] = dep_char
                    if not suggestion_applied: # Update message only on first application
                        final_last_grid_edit = f"Applied suggestions ({datetime.datetime.now().isoformat()})"
                    suggestion_applied = True
                    # logger.debug(f"Applied suggestion: {row_key} -> {col_key} ({dep_char}) in {output_file}")

                # Log conflict if suggestion differs from a non-placeholder, non-diagonal char
                elif existing_char != PLACEHOLDER_CHAR and existing_char != DIAGONAL_CHAR and existing_char != dep_char:
                    warning_msg = (f"Suggestion Conflict in {os.path.basename(output_file)}: "
                                   f"For {row_key}->{col_key}, grid has '{existing_char}', suggestion is '{dep_char}'. "
                                   f"Grid value kept. Manual review recommended.")
                    logger.warning(warning_msg)
                    print(f"WARNING: {warning_msg}")
            # Update the map with the modified row
            temp_decomp_grid[row_key] = current_decomp_row

    # Compress the final grid state
    final_grid = {key: compress("".join(row_list)) for key, row_list in temp_decomp_grid.items()}

    # --- Write updated content to file ---
    try:
        # Handle mini-tracker content preservation
        mini_tracker_start_index = -1
        mini_tracker_end_index = -1
        marker_start, marker_end = "", ""
        is_mini = tracker_type == "mini"

        if is_mini and lines: # Only check markers if it's a mini tracker and we read lines
            mini_tracker_info = get_mini_tracker_data()
            marker_start, marker_end = mini_tracker_info["markers"]
            try:
                mini_tracker_start_index = next(i for i, line in enumerate(lines) if line.strip() == marker_start)
                mini_tracker_end_index = next(i for i, line in enumerate(lines) if line.strip() == marker_end)
                if mini_tracker_start_index >= mini_tracker_end_index:
                     raise ValueError("Start marker found after or at the same line as end marker.")
            except (StopIteration, ValueError) as e:
                logger.warning(f"Mini-tracker start/end markers not found or invalid in {output_file}: {e}. Overwriting entire file.")
                mini_tracker_start_index = -1 # Signal to overwrite all

        with open(output_file, "w", encoding="utf-8", newline='\n') as f:
            # Preserve content before start marker (if mini and markers found)
            if is_mini and mini_tracker_start_index != -1:
                for i in range(mini_tracker_start_index + 1): # Include the start marker line
                    f.write(lines[i])
                # Ensure newline after marker line if missing
                if not lines[mini_tracker_start_index].endswith('\n'): f.write('\n')
            # Add newline separator if we wrote 'before' content or if not mini
            if is_mini and mini_tracker_start_index != -1:
                f.write("\n") # Only add newline after preserved mini header

            # Write the updated tracker data section
            _write_key_definitions(f, final_key_defs)
            f.write("\n")
            f.write(f"last_KEY_edit: {final_last_key_edit}\n")
            f.write(f"last_GRID_edit: {final_last_grid_edit}\n\n")
            _write_grid(f, final_sorted_keys_list, final_grid)

            # Preserve content after end marker (if mini and markers found)
            if is_mini and mini_tracker_end_index != -1 and mini_tracker_start_index != -1:
                 f.write("\n") # Ensure newline before end marker section
                 for i in range(mini_tracker_end_index, len(lines)): # Start writing from end marker line
                     f.write(lines[i])
            # If overwriting a mini-tracker (markers missing), add end marker
            elif is_mini and mini_tracker_start_index == -1:
                 f.write("\n" + marker_end + "\n")

        logger.info(f"Successfully updated tracker: {output_file}")
        # Invalidate cache for this specific tracker file
        invalidate_dependent_entries('tracker_data', f"tracker_data:{output_file}:.*")
        # Invalidate grid caches
        invalidate_dependent_entries('grid_decompress', '.*')
        invalidate_dependent_entries('grid_validation', '.*')
        invalidate_dependent_entries('grid_dependencies', '.*')

    except IOError as e:
        logger.error(f"I/O Error updating tracker file {output_file}: {e}", exc_info=True)
    except Exception as e:
        logger.exception(f"Unexpected error updating tracker file {output_file}: {e}")


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
    tracker_path = normalize_path(tracker_path)
    check_file_modified(tracker_path) # Check cache validity

    logger.info(f"Attempting to export '{os.path.basename(tracker_path)}' to format '{output_format}'")

    tracker_data = read_tracker_file(tracker_path)
    if not tracker_data or not tracker_data.get("keys"):
        msg = f"Error: Cannot export empty or unreadable tracker: {tracker_path}"
        logger.error(msg)
        return msg

    # Determine output path
    if output_path is None:
        base_name = os.path.splitext(tracker_path)[0]
        output_path = normalize_path(f"{base_name}_export.{output_format}")
    else:
        output_path = normalize_path(output_path)

    try:
        dirname = os.path.dirname(output_path)
        if dirname: os.makedirs(dirname, exist_ok=True)

        keys_map = tracker_data.get("keys", {})
        grid = tracker_data.get("grid", {})
        sorted_keys_list = sort_keys(list(keys_map.keys()))

        if output_format == "md":
            shutil.copy2(tracker_path, output_path)
        elif output_format == "json":
            export_data = tracker_data.copy()
            # Optionally add decompressed grid for convenience?
            # export_data['grid_decompressed'] = {k: decompress(v) for k, v in grid.items() if k in keys_map}
            with open(output_path, 'w', encoding='utf-8') as f:
                json.dump(export_data, f, indent=2, ensure_ascii=False)
        elif output_format == "csv":
             with open(output_path, 'w', encoding='utf-8', newline='') as f:
                import csv
                writer = csv.writer(f)
                writer.writerow(["Source Key", "Source Path", "Target Key", "Target Path", "Dependency Type"])
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
                                         writer.writerow([
                                             source_key, keys_map.get(source_key, ""),
                                             target_key, keys_map.get(target_key, ""),
                                             dep_type
                                         ])
                             else: logger.warning(f"CSV Export: Row length mismatch for key '{source_key}'")
                        except Exception as e: logger.warning(f"CSV Export: Error processing row for '{source_key}': {e}")
        elif output_format == "dot":
             with open(output_path, 'w', encoding='utf-8') as f:
                f.write("digraph Dependencies {\n")
                f.write("  rankdir=LR;\n")
                f.write('  node [shape=box, style="filled", fillcolor="#EFEFEF", fontname="Arial"];\n') # Specify font
                f.write('  edge [fontsize=10, fontname="Arial"];\n\n')

                # Define nodes
                for key in sorted_keys_list:
                    # Escape backslashes and double quotes in label
                    label_path = os.path.basename(keys_map.get(key, '')).replace('\\', '/').replace('"', '\\"')
                    label = f"{key}\\n{label_path}"
                    f.write(f'  "{key}" [label="{label}"];\n')
                f.write("\n")

                # Define edges
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
                                         # Basic styling
                                         color = "black"; style = "solid"; arrowhead="normal"
                                         if dep_type == '>': color = "blue"
                                         elif dep_type == '<': color = "green"; arrowhead="oinv" # Reversed arrow
                                         elif dep_type == 'x': color = "red"; style="dashed"; arrowhead="odot" # Mutual
                                         elif dep_type == 'd': color = "orange"
                                         elif dep_type == 's': color = "grey"; style="dotted"
                                         elif dep_type == 'S': color = "dimgrey"; style="bold"
                                         f.write(f'  "{source_key}" -> "{target_key}" [label="{dep_type}", color="{color}", style="{style}", arrowhead="{arrowhead}"];\n')
                             else: logger.warning(f"DOT Export: Row length mismatch for key '{source_key}'")
                        except Exception as e: logger.warning(f"DOT Export: Error processing row for '{source_key}': {e}")
                f.write("}\n")
        else:
            msg = f"Error: Unsupported export format '{output_format}'"
            logger.error(msg)
            return msg

        logger.info(f"Successfully exported tracker to: {output_path}")
        return output_path

    except IOError as e:
        msg = f"Error exporting tracker: I/O Error - {str(e)}"
        logger.error(msg, exc_info=True)
        return msg
    except ImportError as e:
        msg = f"Error exporting tracker: Missing library for format '{output_format}' - {str(e)}"
        logger.error(msg)
        return msg
    except Exception as e:
        msg = f"Error exporting tracker: Unexpected error - {str(e)}"
        logger.exception(msg)
        return msg


# --- Remove File from Tracker ---
def remove_file_from_tracker(output_file: str, file_to_remove: str):
    """Removes a file's key and row/column from the tracker. Invalidates relevant caches."""
    output_file = normalize_path(output_file)
    file_to_remove_norm = normalize_path(file_to_remove)

    if not os.path.exists(output_file):
        logger.error(f"Tracker file '{output_file}' not found for removal.")
        raise FileNotFoundError(f"Tracker file '{output_file}' not found.")

    logger.info(f"Attempting to remove file '{file_to_remove_norm}' from tracker '{output_file}'")
    backup_tracker_file(output_file)

    lines = []
    try:
        with open(output_file, "r", encoding="utf-8") as f:
            lines = f.readlines()
    except Exception as e:
         logger.error(f"Failed to read tracker file {output_file} for removal: {e}", exc_info=True)
         raise IOError(f"Failed to read tracker file {output_file}: {e}") from e

    # Read existing data
    existing_key_defs = _read_existing_keys(lines)
    existing_grid = _read_existing_grid(lines)
    last_key_edit_line = next((line for line in lines if line.strip().lower().startswith("last_key_edit")), None)
    last_grid_edit_line = next((line for line in lines if line.strip().lower().startswith("last_grid_edit")), None)
    # current_last_key_edit = last_key_edit_line.split(":", 1)[1].strip() if last_key_edit_line else ""
    # current_last_grid_edit = last_grid_edit_line.split(":", 1)[1].strip() if last_grid_edit_line else ""

    # Find the key to remove
    key_to_remove = None
    for k, v in existing_key_defs.items():
        if v == file_to_remove_norm:
            key_to_remove = k
            break

    if key_to_remove is None:
        logger.warning(f"File '{file_to_remove_norm}' not found in tracker '{output_file}'. No changes made.")
        # Optionally raise error: raise ValueError(...)
        return # Exit gracefully if not found

    logger.info(f"Found key '{key_to_remove}' for file '{file_to_remove_norm}'. Proceeding with removal.")

    # --- Prepare updated data ---
    final_key_defs = {k: v for k, v in existing_key_defs.items() if k != key_to_remove}
    final_sorted_keys_list = sort_keys(list(final_key_defs.keys()))

    final_last_key_edit = f"Removed key: {key_to_remove} ({os.path.basename(file_to_remove_norm)})"
    final_last_grid_edit = f"Grid adjusted for removal of key: {key_to_remove}"

    # Rebuild grid without the removed key/row/column
    final_grid = {}
    old_keys_list = sort_keys(list(existing_key_defs.keys()))
    try:
        idx_to_remove = old_keys_list.index(key_to_remove)
    except ValueError:
        logger.error(f"Key '{key_to_remove}' not found in old sorted list during removal grid update. Using filtered grid.")
        # Fallback: Just remove the row from the existing grid
        final_grid = {k:v for k,v in existing_grid.items() if k != key_to_remove}
        # This fallback doesn't remove the column, which is inconsistent. Better to rebuild if possible.
    else:
        for old_row_key, compressed_row in existing_grid.items():
             if old_row_key != key_to_remove: # Keep rows not being removed
                 try:
                     decomp_row = list(decompress(compressed_row))
                     if len(decomp_row) == len(old_keys_list):
                          # Remove the character at the removed key's index
                          new_decomp_row_list = decomp_row[:idx_to_remove] + decomp_row[idx_to_remove+1:]
                          final_grid[old_row_key] = compress("".join(new_decomp_row_list))
                     else:
                          logger.warning(f"Removal: Row length mismatch for key '{old_row_key}'. Re-initializing row for new size.")
                          row_list = [PLACEHOLDER_CHAR] * len(final_sorted_keys_list)
                          if old_row_key in final_sorted_keys_list: row_list[final_sorted_keys_list.index(old_row_key)] = DIAGONAL_CHAR
                          final_grid[old_row_key] = compress("".join(row_list))
                 except Exception as e:
                      logger.warning(f"Removal: Error decompressing row for key '{old_row_key}': {e}. Re-initializing row.")
                      row_list = [PLACEHOLDER_CHAR] * len(final_sorted_keys_list)
                      if old_row_key in final_sorted_keys_list: row_list[final_sorted_keys_list.index(old_row_key)] = DIAGONAL_CHAR
                      final_grid[old_row_key] = compress("".join(row_list))

    # --- Write updated file ---
    # Re-use the generic write_tracker_file function which handles validation and mini-tracker markers are NOT relevant here (only key/grid/metadata are changed)
    if write_tracker_file(output_file, final_key_defs, final_grid, final_last_key_edit, final_last_grid_edit):
         logger.info(f"Successfully removed key '{key_to_remove}' and file '{file_to_remove_norm}' from tracker '{output_file}'")
         # Invalidate caches (already handled by write_tracker_file)
    else:
         logger.error(f"Failed to write updated tracker file after removal: {output_file}")
         # Consider restoring backup? Or raise error? For now, just log the failure.
         raise IOError(f"Failed to write updated tracker file {output_file} after removal.")


# --- End of tracker_io.py ---