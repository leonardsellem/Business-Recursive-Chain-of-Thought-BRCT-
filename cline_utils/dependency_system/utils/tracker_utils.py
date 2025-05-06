# utils/tracker_utils.py

import os
import glob
import logging
import re
from typing import Any, Dict, Set, Tuple, List
from collections import defaultdict

from .cache_manager import cached
from .config_manager import ConfigManager
from .path_utils import normalize_path, get_project_root
from cline_utils.dependency_system.core.key_manager import KeyInfo, sort_key_strings_hierarchically, validate_key
from cline_utils.dependency_system.core.dependency_grid import decompress, DIAGONAL_CHAR, EMPTY_CHAR

logger = logging.getLogger(__name__)

@cached("tracker_data",
        key_func=lambda tracker_path:
        f"tracker_data:{normalize_path(tracker_path)}:{(os.path.getmtime(tracker_path) if os.path.exists(tracker_path) else 0)}")
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
        with open(tracker_path, 'r', encoding='utf-8') as f: content = f.read()
        keys = {}; grid = {}; last_key_edit = ""; last_grid_edit = ""
        key_section_match = re.search(r'---KEY_DEFINITIONS_START---\n(.*?)\n---KEY_DEFINITIONS_END---', content, re.DOTALL | re.IGNORECASE)
        if key_section_match:
            key_section_content = key_section_match.group(1)
            for line in key_section_content.splitlines():
                line = line.strip()
                if not line or line.lower().startswith("key definitions:"): continue
                match = re.match(r'^([a-zA-Z0-9]+)\s*:\s*(.*)$', line)
                if match:
                    k, v = match.groups()
                    if validate_key(k): keys[k] = normalize_path(v.strip())
                    else: logger.warning(f"Skipping invalid key format in {tracker_path}: '{k}'")

        grid_section_match = re.search(r'---GRID_START---\n(.*?)\n---GRID_END---', content, re.DOTALL | re.IGNORECASE)
        if grid_section_match:
            grid_section_content = grid_section_match.group(1)
            lines = grid_section_content.strip().splitlines()
            # Skip header line (X ...) if present
            if lines and (lines[0].strip().upper().startswith("X ") or lines[0].strip() == "X"): lines = lines[1:]
            for line in lines:
                line = line.strip()
                match = re.match(r'^([a-zA-Z0-9]+)\s*=\s*(.*)$', line)
                if match:
                    k, v = match.groups()
                    if validate_key(k): grid[k] = v.strip()
                    else: logger.warning(f"Grid row key '{k}' in {tracker_path} has invalid format. Skipping.")

        last_key_edit_match = re.search(r'^last_KEY_edit\s*:\s*(.*)$', content, re.MULTILINE | re.IGNORECASE)
        if last_key_edit_match: last_key_edit = last_key_edit_match.group(1).strip()
        last_grid_edit_match = re.search(r'^last_GRID_edit\s*:\s*(.*)$', content, re.MULTILINE | re.IGNORECASE)
        if last_grid_edit_match: last_grid_edit = last_grid_edit_match.group(1).strip()

        logger.debug(f"Read tracker '{os.path.basename(tracker_path)}': {len(keys)} keys, {len(grid)} grid rows")
        return {"keys": keys, "grid": grid, "last_key_edit": last_key_edit, "last_grid_edit": last_grid_edit}
    except Exception as e:
        logger.exception(f"Error reading tracker file {tracker_path}: {e}")
        return {"keys": {}, "grid": {}, "last_key_edit": "", "last_grid_edit": ""}

def find_all_tracker_paths(config: ConfigManager, project_root: str) -> Set[str]:
    """Finds all main, doc, and mini tracker files in the project."""
    all_tracker_paths = set()
    memory_dir_rel = config.get_path('memory_dir')
    if not memory_dir_rel:
        logger.warning("memory_dir not configured. Cannot find main/doc trackers.")
        memory_dir_abs = None
    else:
        memory_dir_abs = normalize_path(os.path.join(project_root, memory_dir_rel))
        logger.debug(f"Path Components: project_root='{project_root}', memory_dir_rel='{memory_dir_rel}', calculated memory_dir_abs='{memory_dir_abs}'")

        # Main Tracker
        main_tracker_abs = config.get_path("main_tracker_filename", os.path.join(memory_dir_abs, "module_relationship_tracker.md"))
        logger.debug(f"Using main_tracker_abs from config (or default): '{main_tracker_abs}'")
        if os.path.exists(main_tracker_abs): all_tracker_paths.add(main_tracker_abs)
        else: logger.debug(f"Main tracker not found at: {main_tracker_abs}")

        # Doc Tracker
        doc_tracker_abs = config.get_path("doc_tracker_filename", os.path.join(memory_dir_abs, "doc_tracker.md"))
        logger.debug(f"Using doc_tracker_abs from config (or default): '{doc_tracker_abs}'")
        if os.path.exists(doc_tracker_abs): all_tracker_paths.add(doc_tracker_abs)
        else: logger.debug(f"Doc tracker not found at: {doc_tracker_abs}")

    # Mini Trackers
    code_roots_rel = config.get_code_root_directories()
    if not code_roots_rel:
         logger.warning("No code_root_directories configured. Cannot find mini trackers.")
    else:
        for code_root_rel in code_roots_rel:
            code_root_abs = normalize_path(os.path.join(project_root, code_root_rel))
            mini_tracker_pattern = os.path.join(code_root_abs, '**', '*_module.md')
            try:
                found_mini_trackers = glob.glob(mini_tracker_pattern, recursive=True)
                normalized_mini_paths = {normalize_path(mt_path) for mt_path in found_mini_trackers}
                all_tracker_paths.update(normalized_mini_paths)
                logger.debug(f"Found {len(normalized_mini_paths)} mini trackers under '{code_root_rel}'.")
            except Exception as e:
                 logger.error(f"Error during glob search for mini trackers under '{code_root_abs}': {e}")

    logger.info(f"Found {len(all_tracker_paths)} total tracker files.")
    return all_tracker_paths

def aggregate_all_dependencies(
    tracker_paths: Set[str],
    global_key_map: Dict[str, KeyInfo] # Pass the loaded map
) -> Dict[Tuple[str, str], Tuple[str, Set[str]]]:
    """
    Reads all specified tracker files and aggregates dependencies.

    Args:
        tracker_paths: A set of normalized paths to the tracker files.
        global_key_map: The loaded global path -> KeyInfo map.

    Returns:
        A dictionary where:
            Key: Tuple (source_key_str, target_key_str) representing a directed link.
            Value: Tuple (highest_priority_dep_char, Set[origin_tracker_path_str])
                   for that directed link across all trackers.
                   Origin set contains paths of trackers where this link (with this char or lower priority) was found.
    """
    aggregated_links: Dict[Tuple[str, str], Tuple[str, Set[str]]] = {}
    config = ConfigManager() # Needed for priority
    get_priority = config.get_char_priority

    logger.info(f"Aggregating dependencies from {len(tracker_paths)} trackers...")

    for tracker_path in tracker_paths:
        logger.debug(f"Processing tracker for aggregation: {os.path.basename(tracker_path)}")
        tracker_data = read_tracker_file(tracker_path) # Uses cache
        if not tracker_data or not tracker_data.get("keys") or not tracker_data.get("grid"):
            logger.debug(f"Skipping empty or invalid tracker: {os.path.basename(tracker_path)}")
            continue

        local_keys_map = tracker_data["keys"]
        grid = tracker_data["grid"]
        # Use hierarchical sort for reliable indexing
        sorted_keys_local = sort_key_strings_hierarchically(list(local_keys_map.keys()))
        key_to_idx_local = {k: i for i, k in enumerate(sorted_keys_local)} # Not strictly needed for this simplified extraction

        # Extract raw links directly from grid data
        for row_key in sorted_keys_local:
            compressed_row = grid.get(row_key)
            if not compressed_row: continue
            try:
                decompressed_row = decompress(compressed_row)
                if len(decompressed_row) != len(sorted_keys_local): continue # Skip malformed rows

                for col_idx, dep_char in enumerate(decompressed_row):
                    col_key = sorted_keys_local[col_idx]
                    # Skip diagonal, no-dependency, empty
                    if row_key == col_key or dep_char in (DIAGONAL_CHAR, '-', 'X'): continue

                    # --- Priority Resolution and Origin Tracking ---
                    current_link = (row_key, col_key)
                    existing_char, existing_origins = aggregated_links.get(current_link, (None, set()))

                    try:
                        current_priority = get_priority(dep_char)
                        existing_priority = get_priority(existing_char) if existing_char else -1 # Assign lowest priority if non-existent
                    except KeyError as e:
                         logger.warning(f"Invalid dependency character '{str(e)}' found in {tracker_path} for {row_key}->{col_key}. Skipping.")
                         continue

                    if current_priority > existing_priority:
                        # New char has higher priority, replace char and reset origins
                        aggregated_links[current_link] = (dep_char, {tracker_path})
                    elif current_priority == existing_priority:
                        # Same priority, add tracker to origins
                        existing_origins.add(tracker_path)
                        aggregated_links[current_link] = (dep_char, existing_origins)
                    # else: Lower priority, do nothing

            except Exception as e:
                logger.warning(f"Aggregation: Error processing row '{row_key}' in {os.path.basename(tracker_path)}: {e}")

    logger.info(f"Aggregation complete. Found {len(aggregated_links)} unique directed links.")
    return aggregated_links