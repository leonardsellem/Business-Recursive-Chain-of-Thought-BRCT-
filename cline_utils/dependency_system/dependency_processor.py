# dependency_processor.py

"""
Main entry point for the dependency tracking system.
Processes command-line arguments and delegates to appropriate handlers.
"""

import argparse
from collections import defaultdict
import json
import logging
import os
import sys
import re
import glob
from typing import Dict, List, Tuple, Any, Optional, Set

# --- Core Imports ---
from cline_utils.dependency_system.core.dependency_grid import (
    PLACEHOLDER_CHAR, compress, decompress, get_char_at, set_char_at,
    add_dependency_to_grid, get_dependencies_from_grid
)
from cline_utils.dependency_system.core.key_manager import (
    KeyInfo, KeyGenerationError, validate_key, sort_key_strings_hierarchically,
    load_global_key_map
)

# --- IO Imports ---
from cline_utils.dependency_system.io.tracker_io import (
    remove_key_from_tracker, merge_trackers, write_tracker_file,
    export_tracker, update_tracker
)

# --- Analysis Imports ---
from cline_utils.dependency_system.analysis.project_analyzer import analyze_project
from cline_utils.dependency_system.analysis.dependency_analyzer import analyze_file

# --- Utility Imports ---
from cline_utils.dependency_system.utils.path_utils import (
    get_project_root, normalize_path
)
from cline_utils.dependency_system.utils.config_manager import ConfigManager
from cline_utils.dependency_system.utils.cache_manager import (
    clear_all_caches, file_modified, invalidate_dependent_entries
)
# <<< MODIFIED IMPORT: Import from tracker_utils >>>
from cline_utils.dependency_system.utils.tracker_utils import (
    read_tracker_file, find_all_tracker_paths, aggregate_all_dependencies
)


# Configure logging
logger = logging.getLogger(__name__)

# --- Constants ---
KEY_DEFINITIONS_START_MARKER = "---KEY_DEFINITIONS_START---"
KEY_DEFINITIONS_END_MARKER = "---KEY_DEFINITIONS_END---"

# --- Helper Functions ---

def _load_global_map_or_exit() -> Dict[str, KeyInfo]:
    """Loads the global key map, exiting if it fails."""
    logger.info("Loading global key map...")
    path_to_key_info = load_global_key_map()
    if path_to_key_info is None:
        print("Error: Global key map not found or failed to load.", file=sys.stderr)
        print("Please run 'analyze-project' first to generate the key map.", file=sys.stderr)
        logger.critical("Global key map missing or invalid. Exiting.")
        sys.exit(1)
    logger.info("Global key map loaded successfully.")
    return path_to_key_info

def is_parent_child(key1_str: str, key2_str: str, global_map: Dict[str, KeyInfo]) -> bool:
    """Checks if two keys represent a direct parent-child directory relationship."""
    info1 = next((info for path, info in global_map.items() if info.key_string == key1_str), None)
    info2 = next((info for path, info in global_map.items() if info.key_string == key2_str), None)

    if not info1 or not info2:
        logger.debug(f"is_parent_child: Could not find KeyInfo for '{key1_str if not info1 else ''}' or '{key2_str if not info2 else ''}'. Returning False.")
        return False # Cannot determine relationship if info is missing

    # Ensure paths are normalized (they should be from KeyInfo, but double-check)
    path1 = normalize_path(info1.norm_path)
    path2 = normalize_path(info2.norm_path)
    parent1 = normalize_path(info1.parent_path) if info1.parent_path else None
    parent2 = normalize_path(info2.parent_path) if info2.parent_path else None

    # Check both directions: info1 is parent of info2 OR info2 is parent of info1
    is_parent1 = parent2 == path1
    is_parent2 = parent1 == path2

    logger.debug(f"is_parent_child check: {key1_str}({path1}) vs {key2_str}({path2}). Is Parent1: {is_parent1}, Is Parent2: {is_parent2}")
    return is_parent1 or is_parent2

# --- Command Handlers ---

def command_handler_analyze_file(args):
    """Handle the analyze-file command."""
    import json
    try:
        if not os.path.exists(args.file_path): print(f"Error: File not found: {args.file_path}"); return 1
        results = analyze_file(args.file_path)
        if args.output:
            output_dir = os.path.dirname(args.output); os.makedirs(output_dir, exist_ok=True) if output_dir else None
            with open(args.output, 'w', encoding='utf-8') as f: json.dump(results, f, indent=2)
            print(f"Analysis results saved to {args.output}")
        else: print(json.dumps(results, indent=2))
        return 0
    except Exception as e: print(f"Error analyzing file: {str(e)}"); return 1

def command_handler_analyze_project(args):
    """Handle the analyze-project command."""
    import json
    try:
        if not args.project_root: args.project_root = "."; logger.info(f"Defaulting project root to CWD: {os.path.abspath(args.project_root)}")
        abs_project_root = normalize_path(os.path.abspath(args.project_root))
        if not os.path.isdir(abs_project_root): print(f"Error: Project directory not found: {abs_project_root}"); return 1
        original_cwd = os.getcwd()
        if abs_project_root != normalize_path(original_cwd):
             logger.info(f"Changing CWD to: {abs_project_root}"); os.chdir(abs_project_root)
             # ConfigManager.initialize(force=True) # Re-init if CWD matters for config finding

        logger.debug(f"Analyzing project: {abs_project_root}, force_analysis={args.force_analysis}, force_embeddings={args.force_embeddings}")
        results = analyze_project(force_analysis=args.force_analysis, force_embeddings=args.force_embeddings)
        logger.debug(f"All Suggestions before Tracker Update: {results.get('dependency_suggestion', {}).get('suggestions')}")

        if args.output:
            output_path_abs = normalize_path(os.path.abspath(args.output))
            output_dir = os.path.dirname(output_path_abs); os.makedirs(output_dir, exist_ok=True) if output_dir else None
            with open(output_path_abs, 'w', encoding='utf-8') as f: json.dump(results, f, indent=2)
            print(f"Analysis results saved to {output_path_abs}")
        else: print("Analysis complete. Results not printed (use --output to save).")
        return 0
    except Exception as e:
        logger.error(f"Error analyzing project: {str(e)}", exc_info=True); print(f"Error analyzing project: {str(e)}"); return 1
    finally:
        if 'original_cwd' in locals() and normalize_path(os.getcwd()) != normalize_path(original_cwd):
             logger.info(f"Changing CWD back to: {original_cwd}"); os.chdir(original_cwd)
             # ConfigManager.initialize(force=True) # Re-init if needed

def handle_compress(args: argparse.Namespace) -> int:
    """Handle the compress command."""
    try: result = compress(args.string); print(f"Compressed string: {result}"); return 0
    except Exception as e: logger.error(f"Error compressing: {e}"); print(f"Error: {e}"); return 1

def handle_decompress(args: argparse.Namespace) -> int:
    """Handle the decompress command."""
    try: result = decompress(args.string); print(f"Decompressed string: {result}"); return 0
    except Exception as e: logger.error(f"Error decompressing: {e}"); print(f"Error: {e}"); return 1

def handle_get_char(args: argparse.Namespace) -> int:
    """Handle the get_char command."""
    try: result = get_char_at(args.string, args.index); print(f"Character at index {args.index}: {result}"); return 0
    except IndexError: logger.error("Index out of range"); print("Error: Index out of range"); return 1
    except Exception as e: logger.error(f"Error get_char: {e}"); print(f"Error: {e}"); return 1

def handle_set_char(args: argparse.Namespace) -> int:
    """Handle the set_char command."""
    try:
        tracker_data = read_tracker_file(args.tracker_file)
        if not tracker_data or not tracker_data.get("keys"): print(f"Error: Could not read tracker: {args.tracker_file}"); return 1
        if args.key not in tracker_data["keys"]: print(f"Error: Key {args.key} not found"); return 1
        sorted_keys = sort_key_strings_hierarchically(list(tracker_data["keys"].keys())) # Use hierarchical sort
        # Check index validity against sorted list length
        if not (0 <= args.index < len(sorted_keys)): print(f"Error: Index {args.index} out of range for {len(sorted_keys)} keys."); return 1
        # Check char validity (optional, could rely on set_char_at)
        # if len(args.char) != 1: print("Error: Character must be a single character."); return 1

        row_str = tracker_data["grid"].get(args.key, "")
        if not row_str: logger.warning(f"Row for key '{args.key}' missing. Initializing."); row_str = compress('p' * len(sorted_keys))

        updated_compressed_row = set_char_at(row_str, args.index, args.char)
        tracker_data["grid"][args.key] = updated_compressed_row
        tracker_data["last_grid_edit"] = f"Set {args.key}[{args.index}] to {args.char}"
        success = write_tracker_file(args.tracker_file, tracker_data["keys"], tracker_data["grid"], tracker_data.get("last_key_edit", ""), tracker_data["last_grid_edit"])
        if success: print(f"Set char at index {args.index} to '{args.char}' for key {args.key} in {args.tracker_file}"); return 0
        else: print(f"Error: Failed write to {args.tracker_file}"); return 1
    except IndexError: print(f"Error: Index {args.index} out of range."); return 1
    except ValueError as e: print(f"Error: {e}"); return 1
    except Exception as e: logger.error(f"Error set_char: {e}", exc_info=True); print(f"Error: {e}"); return 1

def handle_remove_key(args: argparse.Namespace) -> int:
    """Handle the remove-key command."""
    try:
        # Call the updated tracker_io function
        remove_key_from_tracker(args.tracker_file, args.key)
        print(f"Removed key '{args.key}' from tracker '{args.tracker_file}'")
        # Invalidate cache for the modified tracker
        invalidate_dependent_entries('tracker_data', f"tracker_data:{normalize_path(args.tracker_file)}:.*")
        # Broader invalidation might be needed if other caches depend on grid structure
        invalidate_dependent_entries('grid_decompress', '.*'); invalidate_dependent_entries('grid_validation', '.*'); invalidate_dependent_entries('grid_dependencies', '.*')
        return 0
    except FileNotFoundError as e: print(f"Error: {e}"); return 1
    except ValueError as e: print(f"Error: {e}"); return 1 # e.g., key not found in tracker
    except Exception as e:
        logger.error(f"Failed to remove key: {str(e)}", exc_info=True); print(f"Error: {e}"); return 1

def handle_add_dependency(args: argparse.Namespace) -> int:
    """Handle the add-dependency command. Allows adding foreign keys to mini-trackers."""
    tracker_path = normalize_path(args.tracker)
    is_mini_tracker = tracker_path.endswith("_module.md")
    source_key = args.source_key
    target_keys = args.target_key # This is a list
    dep_type = args.dep_type
    # Dependency type validation
    ALLOWED_DEP_TYPES = {'<', '>', 'x', 'd', 'o', 'n', 'p', 's', 'S'}

    logger.info(f"Attempting to add dependency: {source_key} -> {target_keys} ({dep_type}) in tracker {tracker_path}")

    # --- Basic Validation ---
    if dep_type not in ALLOWED_DEP_TYPES:
        print(f"Error: Invalid dep type '{dep_type}'. Allowed: {', '.join(sorted(list(ALLOWED_DEP_TYPES)))}")
        return 1

    # --- Load Local Tracker Data ---
    tracker_data = read_tracker_file(tracker_path)
    if not tracker_data or not tracker_data.get("keys"):
        print(f"Error: Could not read tracker or no keys found: {tracker_path}")
        # If it's a mini-tracker that doesn't exist yet, update_tracker might handle creation
        if not is_mini_tracker:
            return 1
        else:
            logger.warning(f"Mini-tracker {tracker_path} not found or invalid, proceeding to update_tracker for potential creation.")
            # Allow proceeding, update_tracker handles creation
            local_keys = {}
            local_grid = {}
            local_sorted_keys = []
    else:
        local_keys = tracker_data.get("keys", {}) # key_string -> path_string map
        local_grid = tracker_data.get("grid", {})
        local_sorted_keys = sort_key_strings_hierarchically(list(local_keys.keys()))


    # --- Validate Source Key Locally (if tracker exists) ---
    if local_keys and source_key not in local_keys:
        print(f"Error: Source key '{source_key}' not found in tracker '{tracker_path}'.")
        return 1

    # --- Process Target Keys ---
    internal_changes = [] # List of (target_key, dep_type) for local targets
    foreign_adds = []     # List of (target_key, dep_type) for valid foreign targets (mini-trackers only)
    global_map_loaded = False
    global_path_to_key_info = None

    for target_key in target_keys:
        if target_key == source_key:
             logger.warning(f"Skipping self-dependency: {source_key} -> {target_key}")
             continue

        if target_key in local_keys:
            # Target exists locally, treat as internal change
            internal_changes.append((target_key, dep_type))
            logger.debug(f"Target '{target_key}' found locally. Queued for internal update.")
        elif is_mini_tracker:
            # Target missing locally, BUT it's a mini-tracker - check globally
            logger.debug(f"Target '{target_key}' not found locally in mini-tracker. Checking globally...")
            if not global_map_loaded:
                # <<< USE UTILITY >>>
                global_path_to_key_info = _load_global_map_or_exit()
                global_map_loaded = True # Mark as loaded

            # Check existence using the loaded map
            target_exists_globally = any(info.key_string == target_key for info in global_path_to_key_info.values())
            if target_exists_globally:
                foreign_adds.append((target_key, dep_type))
                logger.info(f"Target '{target_key}' is valid globally. Queued for foreign key addition.")
            else:
                print(f"Error: Target key '{target_key}' not found locally or globally. Cannot add dependency.")
                # Decide if we should stop entirely or just skip this target
                return 1 # Stop on first invalid target key
        else:
            # Target missing locally and it's NOT a mini-tracker - standard error
            print(f"Error: Target key '{target_key}' not found in tracker '{tracker_path}'.")
            return 1 # Stop on first invalid target key

    # --- Combine all changes ---
    all_targets_for_source = internal_changes + foreign_adds
    if not all_targets_for_source:
        print("No valid dependencies specified or identified."); return 0

    # --- Prepare data for update_tracker ---
    suggestions_for_update = {source_key: all_targets_for_source}
    force_apply = True # Always force apply from add-dependency

    # Load global map if not already loaded (needed for file_to_module)
    if not global_map_loaded:
        global_path_to_key_info = _load_global_map_or_exit()

    # Generate file_to_module map (needed by update_tracker even if no foreign keys added this time)
    file_to_module_map = {info.norm_path: info.parent_path for info in global_path_to_key_info.values() if not info.is_directory and info.parent_path}

    # --- Call update_tracker for ALL cases (mini, main, doc) ---
    # Let update_tracker handle type determination, reading, writing, content preservation
    try:
        logger.info(f"Calling update_tracker for {tracker_path} (Force Apply: {force_apply})")
        update_tracker(
            output_file_suggestion=tracker_path, # Pass path for context/determination
            path_to_key_info=global_path_to_key_info,
            tracker_type="mini" if is_mini_tracker else ("doc" if "doc_tracker.md" in tracker_path else "main"),
            suggestions=suggestions_for_update,
            file_to_module=file_to_module_map,
            new_keys=None, # add-dependency doesn't introduce globally new keys
            force_apply_suggestions=force_apply
        )
        print(f"Successfully updated tracker {tracker_path} with dependencies.")
        return 0
    except Exception as e:
        logger.error(f"Error calling update_tracker for {tracker_path}: {e}", exc_info=True)
        print(f"Error updating tracker {tracker_path}: {e}")
        return 1

def handle_merge_trackers(args: argparse.Namespace) -> int:
    """Handle the merge-trackers command."""
    try:
        primary_tracker_path = normalize_path(args.primary_tracker_path); secondary_tracker_path = normalize_path(args.secondary_tracker_path)
        output_path = normalize_path(args.output) if args.output else primary_tracker_path
        merged_data = merge_trackers(primary_tracker_path, secondary_tracker_path, output_path)
        if merged_data: print(f"Merged trackers into {output_path}. Total keys: {len(merged_data.get('keys', {}))}"); return 0
        else: print("Error merging trackers."); return 1
    except Exception as e: logger.exception(f"Failed merge: {e}"); print(f"Error: {e}"); return 1

def handle_clear_caches(args: argparse.Namespace) -> int:
    """Handle the clear-caches command."""
    try:
        clear_all_caches()
        print("All caches cleared.")
        return 0
    except Exception as e:
        logger.exception(f"Error clearing caches: {e}")
        print(f"Error clearing caches: {e}")
        return 1

def handle_export_tracker(args: argparse.Namespace) -> int:
    """Handle the export-tracker command."""
    try:
        output_path = args.output or os.path.splitext(args.tracker_file)[0] + '.' + args.format
        result = export_tracker(args.tracker_file, args.format, output_path)
        if isinstance(result, str) and result.startswith("Error:"): # Check if export returned an error string
            print(result); return 1
        print(f"Tracker exported to {output_path}"); return 0
    except Exception as e: logger.exception(f"Error export_tracker: {e}"); print(f"Error: {e}"); return 1

def handle_update_config(args: argparse.Namespace) -> int:
    """Handle the update-config command."""
    config_manager = ConfigManager()
    try:
        # Attempt to parse value as JSON (allows lists/dicts), fall back to string
        try: value = json.loads(args.value)
        except json.JSONDecodeError: value = args.value
        success = config_manager.update_config_setting(args.key, value)
        if success: print(f"Updated config: {args.key} = {value}"); return 0
        else: print(f"Error: Failed update config (key '{args.key}' invalid?)."); return 1
    except Exception as e: logger.exception(f"Error update_config: {e}"); print(f"Error: {e}"); return 1

def handle_reset_config(args: argparse.Namespace) -> int:
    """Handle the reset-config command."""
    config_manager = ConfigManager()
    try:
        success = config_manager.reset_to_defaults()
        if success: print("Config reset to defaults."); return 0
        else: print("Error: Failed reset config."); return 1
    except Exception as e: logger.exception(f"Error reset_config: {e}"); print(f"Error: {e}"); return 1

def handle_show_dependencies(args: argparse.Namespace) -> int:
    """Handle the show-dependencies command using the contextual key system."""
    target_key_str = args.key
    logger.info(f"Showing dependencies for key string: {target_key_str}")
    path_to_key_info = _load_global_map_or_exit()
   
    config = ConfigManager()
    project_root = get_project_root()
    matching_infos = [info for info in path_to_key_info.values() if info.key_string == target_key_str]
    if not matching_infos:
        print(f"Error: Key string '{target_key_str}' not found in the project.")
        return 1
    target_info: KeyInfo
    if len(matching_infos) > 1:
        print(f"Warning: Key string '{target_key_str}' is ambiguous and matches multiple paths:")
        for i, info in enumerate(matching_infos):
            print(f"  [{i+1}] {info.norm_path}")
        target_info = matching_infos[0] # Use the first match
        print(f"Using the first match: {target_info.norm_path}")
    else:
        target_info = matching_infos[0]
    target_norm_path = target_info.norm_path
    print(f"\n--- Dependencies for Key: {target_key_str} (Path: {target_norm_path}) ---")

    # --- Use Utility Functions ---
    all_tracker_paths = find_all_tracker_paths(config, project_root)
    if not all_tracker_paths: print("Warning: No tracker files found.")
    aggregated_links_with_origins = aggregate_all_dependencies(all_tracker_paths, path_to_key_info)

    # --- Process Aggregated Results for Display ---
    all_dependencies_by_type = defaultdict(set) # Store sets of (dep_key_string, dep_path_string) tuples
    origin_tracker_map_display = defaultdict(lambda: defaultdict(set)) # For p/s/S origins

    logger.debug(f"Filtering aggregated links for target key display: {target_key_str}")
    for (source, target), (dep_char, origins) in aggregated_links_with_origins.items():
        dep_key_str = None
        display_char = dep_char # Character used to categorize for display
        if source == target_key_str:
            dep_key_str = target # Target is the dependency shown
        elif target == target_key_str:
            dep_key_str = source # Source is the dependency shown
            # Adjust display category based on relationship direction relative to target
            if dep_char == '>': display_char = '<' # Target depends on Source (show Source in Depends On)
            elif dep_char == '<': display_char = '>' # Source depends on Target (show Source in Depended On By)
            # 'x', 'd', 's', 'S' remain the same category regardless of direction
            else: display_char = dep_char

        if dep_key_str:
            # Find path for the dependency key
            dep_info = next((info for info in path_to_key_info.values() if info.key_string == dep_key_str), None)
            dep_path_str = dep_info.norm_path if dep_info else "PATH_NOT_FOUND_GLOBALLY"

            # Add to the correct category for display
            all_dependencies_by_type[display_char].add((dep_key_str, dep_path_str))

            # Track origins specifically for p/s/S if needed for display
            if display_char in ('p', 's', 'S'):
                origin_tracker_map_display[display_char][dep_key_str].update(origins)

    # --- Print results ---
    output_sections = [
        ("Mutual ('x')", 'x'), ("Documentation ('d')", 'd'), ("Semantic (Strong) ('S')", 'S'),
        ("Semantic (Weak) ('s')", 's'), ("Depends On ('<')", '<'), ("Depended On By ('>')", '>'),
        ("Placeholders ('p')", 'p')
    ]
    for section_title, dep_char in output_sections:
        print(f"\n{section_title}:")
        dep_set = all_dependencies_by_type.get(dep_char)
        if dep_set:
            # Define helper for hierarchical sorting
            def _hierarchical_sort_key_func(key_str: str):
                KEY_PATTERN = r'\d+|\D+' # Pattern from key_manager
                if not key_str or not isinstance(key_str, str): return []
                parts = re.findall(KEY_PATTERN, key_str)
                try:
                    return [(int(p) if p.isdigit() else p) for p in parts]
                except (ValueError, TypeError): # Fallback
                    logger.warning(f"Could not convert parts for sorting display key '{key_str}'")
                    return parts

            sorted_deps = sorted(list(dep_set), key=lambda item: _hierarchical_sort_key_func(item[0]))
            for dep_key, dep_path in sorted_deps:
                # Check for and add origin info for p/s/S
                origin_info = ""
                if dep_char in ('p', 's', 'S'):
                    origins = origin_tracker_map_display.get(dep_char, {}).get(dep_key, set())
                    if origins:
                        # Format origin filenames nicely
                        origin_filenames = sorted([os.path.basename(p) for p in origins])
                        origin_info = f" (In: {', '.join(origin_filenames)})"
                # Print with optional origin info
                print(f"  - {dep_key}: {dep_path}{origin_info}")
        else: print("  None")
    print("\n------------------------------------------")
    return 0

def handle_show_keys(args: argparse.Namespace) -> int:
    """
    Handle the show-keys command.
    Displays key definitions from the specified tracker file.
    Additionally, checks if the corresponding row in the grid contains
    any 'p', 's', or 'S' characters (indicating unverified placeholders
    or suggestions) and notes which were found.
    """
    tracker_path = normalize_path(args.tracker)
    logger.info(f"Attempting to show keys and check status (p, s, S) from tracker: {tracker_path}")

    if not os.path.exists(tracker_path):
        print(f"Error: Tracker file not found: {tracker_path}", file=sys.stderr)
        logger.error(f"Tracker file not found: {tracker_path}")
        return 1

    try:
        tracker_data = read_tracker_file(tracker_path) # Use cached read
        if not tracker_data:
            print(f"Error: Could not read or parse tracker file: {tracker_path}", file=sys.stderr)
            return 1

        keys_map = tracker_data.get("keys")
        grid_map = tracker_data.get("grid")

        if not keys_map:
            print(f"Error: No keys found in tracker file: {tracker_path}", file=sys.stderr)
            logger.error(f"No key definitions found in {tracker_path}")
            # Allow proceeding if grid is missing, but warn
            if not grid_map:
                logger.warning(f"Grid data also missing in {tracker_path}")
            return 1 # Considered an error state if keys are missing

        # Sort keys hierarchically for consistent output
        sorted_keys = sort_key_strings_hierarchically(list(keys_map.keys()))
        print(f"--- Keys Defined in {os.path.basename(tracker_path)} ---") # Header for clarity

        for key_string in sorted_keys:
            file_path = keys_map.get(key_string, "PATH_UNKNOWN")
            check_indicator = "" # Renamed for clarity
            # Check the grid for 'p', 's', or 'S' *only if* the grid exists
            if grid_map:
                compressed_row = grid_map.get(key_string, "")
                if compressed_row: # Check if the row string exists and is not empty
                    found_chars = []
                    # Check for each character efficiently using 'in'. This is safe
                    # as 'p', 's', 'S' won't appear in RLE counts (which are digits).
                    if 'p' in compressed_row: found_chars.append('p')
                    if 's' in compressed_row: found_chars.append('s')
                    if 'S' in compressed_row: found_chars.append('S')
                    if found_chars:
                        # Sort for consistent output order (e.g., p, s, S)
                        sorted_chars = sorted(found_chars)
                        chars_str = ", ".join(sorted_chars)
                        check_indicator = f" (checks needed: {chars_str})" # Updated indicator format
                else:
                    # Indicate if a key exists but has no corresponding grid row yet
                    check_indicator = " (grid row missing)"
                    logger.warning(f"Key '{key_string}' found in definitions but missing from grid in {tracker_path}")
            else: # Grid is missing entirely
                check_indicator = " (grid missing)"
            # Print the key, path, and the indicator (if any checks are needed or row is missing)
            print(f"{key_string}: {file_path}{check_indicator}")
        print("--- End of Key Definitions ---")
        try:
            with open(tracker_path, 'r', encoding='utf-8') as f_check:
                content = f_check.read()
                if KEY_DEFINITIONS_START_MARKER not in content:
                     logger.warning(f"Start marker '{KEY_DEFINITIONS_START_MARKER}' not found in {tracker_path}")
                if KEY_DEFINITIONS_END_MARKER not in content:
                     logger.warning(f"End marker '{KEY_DEFINITIONS_END_MARKER}' not found in {tracker_path}")
        except Exception:
             logger.warning(f"Could not perform marker check on {tracker_path}")
        return 0
    except IOError as e:
        print(f"Error reading tracker file {tracker_path}: {e}", file=sys.stderr)
        logger.error(f"IOError reading {tracker_path}: {e}", exc_info=True)
        return 1
    except Exception as e:
        print(f"An unexpected error occurred while processing {tracker_path}: {e}", file=sys.stderr)
        logger.error(f"Unexpected error processing {tracker_path}: {e}", exc_info=True)
        return 1

def handle_visualize_dependencies(args: argparse.Namespace) -> int:
    """Handles the visualize-dependencies command."""
    target_key_str = args.key
    output_format = args.format.lower()
    output_path_arg = args.output

    logger.info(f"Generating dependency visualization. Focus Key: {target_key_str or 'None'}, Format: {output_format}")
    if output_format != "mermaid": print(f"Error: Only 'mermaid' format supported."); return 1

    global_path_to_key_info = _load_global_map_or_exit()
    config = ConfigManager()
    project_root = get_project_root()
    all_tracker_paths = find_all_tracker_paths(config, project_root)
    if not all_tracker_paths: print("Warning: No tracker files found.")
    aggregated_links_with_origins = aggregate_all_dependencies(all_tracker_paths, global_path_to_key_info)
    # Ignore origins for visualization, just need consolidated directed links
    consolidated_directed_links: Dict[Tuple[str, str], str] = {
        link: char for link, (char, origins) in aggregated_links_with_origins.items()
    }

    # --- Prepare Edges for Drawing (Handle Mutual vs. One-Way) ---
    final_edges_to_draw_step1 = []
    processed_pairs_final = set()
    sorted_consolidated_items = sorted(consolidated_directed_links.items()) # Sort for determinism
    temp_mutual_edges = []
    temp_directional_map = {} # Store forward links temporarily

    # First pass: identify mutual/reciprocal links and store others
    for (source, target), forward_char in sorted_consolidated_items:
        pair = tuple(sorted((source, target)))
        reverse_char = consolidated_directed_links.get((target, source))
        if forward_char == 'x' or reverse_char == 'x':
            if pair not in processed_pairs_final:
                temp_mutual_edges.append((source, target, 'x')); processed_pairs_final.add(pair)
        elif (forward_char == '>' and reverse_char == '<'):
             if pair not in processed_pairs_final:
                 temp_mutual_edges.append((source, target, '>')); processed_pairs_final.add(pair) # Store as Source depends on Target
        elif (forward_char == '<' and reverse_char == '>'):
             if pair not in processed_pairs_final:
                 temp_mutual_edges.append((target, source, '>')); processed_pairs_final.add(pair) # Store as Target depends on Source
        else:
            # Store non-mutual, non-reciprocal links for second pass
            temp_directional_map[(source, target)] = forward_char

    # Combine mutual/resolved links
    final_edges_to_draw_step1.extend(temp_mutual_edges)
    # Add remaining directional links if their pair wasn't processed
    for (source, target), char in temp_directional_map.items():
         pair = tuple(sorted((source, target)))
         if pair not in processed_pairs_final:
              final_edges_to_draw_step1.append((source, target, char)); processed_pairs_final.add(pair)
    logger.info(f"Prepared {len(final_edges_to_draw_step1)} intermediate edges for drawing.")

    # --- Filter by --key ---
    relevant_keys = set()
    if target_key_str:
        target_info = next((info for info in global_path_to_key_info.values() if info.key_string == target_key_str), None)
        if not target_info: print(f"Error: Focus key '{target_key_str}' not found."); return 1
        print(f"Filtering visualization to focus on key: {target_key_str}")
        edges_for_key = []; relevant_keys = {target_key_str}
        for k1, k2, char in final_edges_to_draw_step1:
            if k1 == target_key_str or k2 == target_key_str:
                edges_for_key.append((k1, k2, char)); relevant_keys.add(k1); relevant_keys.add(k2)
        final_edges_to_draw_step2 = edges_for_key
        logger.info(f"Filtered to {len(final_edges_to_draw_step2)} edges and {len(relevant_keys)} keys.")
    else:
        final_edges_to_draw_step2 = final_edges_to_draw_step1
        relevant_keys = {k for edge in final_edges_to_draw_step2 for k in edge[:2]}
        logger.info(f"Including all {len(relevant_keys)} keys involved in dependencies.")

    # --- Filter Edges (Structural x, File/Dir Types, Placeholders 'p') ---
    final_edges_to_draw = []
    structural_removed = 0; type_mismatch_removed = 0; placeholder_removed = 0
    key_string_to_info_map = {info.key_string: info for info in global_path_to_key_info.values()} # Cache lookup

    for k1, k2, char in final_edges_to_draw_step2:
        # Skip placeholders
        if char == 'p': placeholder_removed += 1; continue
        # Skip structural 'x'
        if char == 'x' and is_parent_child(k1, k2, global_path_to_key_info): structural_removed += 1; continue
        # Skip file-dir/dir-file mismatches
        info1 = key_string_to_info_map.get(k1); info2 = key_string_to_info_map.get(k2)
        if not info1 or not info2: continue # Skip if key info is missing
        if info1.is_directory != info2.is_directory: type_mismatch_removed += 1; continue
        final_edges_to_draw.append((k1, k2, char))
    logger.info(f"Edges removed: Structural 'x'({structural_removed}), Type Mismatch({type_mismatch_removed}), Placeholders({placeholder_removed})")
    logger.info(f"Final count of edges to draw: {len(final_edges_to_draw)}")

    # --- Recalculate relevant keys, Build Hierarchy Map ---
    final_relevant_keys = {k for edge in final_edges_to_draw for k in edge[:2]}
    if not final_relevant_keys: print("No relevant nodes or dependencies found to visualize."); return 0
    logger.info(f"Final count of nodes to draw: {len(final_relevant_keys)}")

    parent_to_children: Dict[Optional[str], List[KeyInfo]] = defaultdict(list)
    processed_nodes_for_hierarchy = set()
    key_string_to_info_map = {info.key_string: info for info in global_path_to_key_info.values()}
    queue = list(final_relevant_keys); visited_for_hierarchy = set(final_relevant_keys)
    # BFS/DFS to find all necessary parent nodes for hierarchy structure
    while queue:
        key_str = queue.pop(0); info = key_string_to_info_map.get(key_str)
        if not info: continue
        processed_nodes_for_hierarchy.add(key_str)
        parent_path = normalize_path(info.parent_path) if info.parent_path else None
        parent_to_children[parent_path].append(info)
        if parent_path:
            parent_info = global_path_to_key_info.get(parent_path)
            if parent_info and parent_info.key_string not in visited_for_hierarchy:
                visited_for_hierarchy.add(parent_info.key_string); queue.append(parent_info.key_string)
    # Ensure all keys needed for subgraphs and nodes are included
    all_keys_for_node_defs = final_relevant_keys.union(
        {parent_info.key_string for path, children in parent_to_children.items() if path
         for parent_info in [global_path_to_key_info.get(path)] if parent_info}
    )
    logger.debug(f"Total nodes required for definition (incl. parents): {len(all_keys_for_node_defs)}")

    # --- Generate Mermaid String ---
    mermaid_string = "flowchart TB\n\n"
    defined_nodes = set()

    # Recursive function to generate nodes and subgraphs
    def generate_mermaid_nodes_recursive(parent_norm_path: Optional[str], nodes_in_scope: Set[str]):
        nonlocal mermaid_string, defined_nodes
        # Sort children based on their key string using hierarchical sort
        children_infos = parent_to_children.get(parent_norm_path, [])
        children = sorted(children_infos, key=lambda i: sort_key_strings_hierarchically([i.key_string])[0])
        parent_info = global_path_to_key_info.get(parent_norm_path) if parent_norm_path else None

        # Determine indentation based on path depth (simple approximation)
        indent = "  " * (parent_norm_path.count('/') if parent_norm_path else 0)
        subgraph_declared = False
        if parent_info:
             # Only declare subgraph if it or its children are needed
             parent_key_str = parent_info.key_string
             if parent_key_str in nodes_in_scope or any(child.key_string in nodes_in_scope for child in children):
                 parent_basename = os.path.basename(parent_info.norm_path)
                 mermaid_string += f'{indent}subgraph {parent_key_str} ["{parent_basename}"]\n'
                 # Optional: Set direction within subgraph
                 # mermaid_string += f'{indent}  direction LR\n'
                 subgraph_declared = True
                 # Define the subgraph node itself if it's relevant (e.g., has edges)
                 # It might be better to define all nodes at the top level first?
                 # For now, define within subgraph context.
                 if parent_key_str not in defined_nodes and parent_key_str in nodes_in_scope:
                     # Define the directory node itself if needed
                     # node_label = f'{parent_key_str}<br>{parent_basename}'
                     # mermaid_string += f'{indent}  {parent_key_str}(("{node_label}"))\n' # Example: circle for dir
                     # defined_nodes.add(parent_key_str)
                     pass # Let recursion handle sub-subgraphs first

        # Process Children
        for child_info in children:
            child_key = child_info.key_string
            # Skip if node isn't relevant for the final viz OR already defined
            if child_key not in nodes_in_scope or child_key in defined_nodes: continue
            child_path = child_info.norm_path
            child_basename = os.path.basename(child_path)
            if child_info.is_directory:
                # Recurse for subdirectories BEFORE defining the current dir node
                generate_mermaid_nodes_recursive(child_path, nodes_in_scope)
            else:
                # Define file node
                node_label = f'{child_key}<br>{child_basename}'
                # Use default rectangle shape for files
                mermaid_string += f'{indent}  {child_key}["{node_label}"]\n'
                defined_nodes.add(child_key)
        # End Subgraph
        if subgraph_declared:
             mermaid_string += f'{indent}end\n'
    # Initial call for root nodes (parent_path is None)
    generate_mermaid_nodes_recursive(None, all_keys_for_node_defs)

    # --- Add Dependencies (Consolidated and Sorted) ---
    mermaid_string += "\n// --- Dependencies ---\n"
    dep_char_to_label = {
        '<': "relies on", '>': "required by", 'x': "mutual reliance",
        'd': "docs", 's': "semantic (weak)", 'S': "semantic (strong)",
    }
    # Group edges by (source, label, arrow_type)
    grouped_edges: Dict[Tuple[str, str, str], List[str]] = defaultdict(list)
    arrow_map = {'x': '<-->', 's': '-.->', 'S': '==>'} # Map special chars to arrows

    for k1, k2, dep_char in final_edges_to_draw:
        # Ensure both nodes were needed (redundant check, but safe)
        if k1 not in all_keys_for_node_defs or k2 not in all_keys_for_node_defs: continue
        label = dep_char_to_label.get(dep_char, dep_char)
        # Determine arrow type based on final resolved character
        arrow = arrow_map.get(dep_char, '-->') # Default arrow
        group_key = (k1, label, arrow)
        grouped_edges[group_key].append(k2)
    # Get unique source keys first
    list_of_unique_sources = list({k[0] for k in grouped_edges.keys()})
    # Sort the list using the hierarchical sort function
    sorted_unique_sources = sort_key_strings_hierarchically(list_of_unique_sources)
    # Iterate through sorted sources, then grouped edges for that source
    for source_key in sorted_unique_sources: # Use the correctly sorted list
        # Find all groups starting with this source key
        source_groups = [(key, targets) for key, targets in grouped_edges.items() if key[0] == source_key]
        # Sort groups by label for consistent output order within a source
        source_groups.sort(key=lambda item: item[0][1])
        for (src, label, arrow), targets in source_groups:
            # Sort targets hierarchically
            sorted_targets = sort_key_strings_hierarchically(targets)
            targets_str = " & ".join(sorted_targets)
            mermaid_string += f'  {src} {arrow}|"{label}"| {targets_str}\n'

    # --- Determine Output Path & Write File ---
    output_path = output_path_arg
    if not output_path:
        if target_key_str:
            output_path = f"{target_key_str}_dependencies.{output_format}"
        else:
            output_path = f"project_dependencies.{output_format}"
    output_path = normalize_path(output_path)

    try:
        output_dir = os.path.dirname(output_path)
        if output_dir: os.makedirs(output_dir, exist_ok=True)
        with open(output_path, 'w', encoding='utf-8') as f:
            f.write(mermaid_string)
        logger.info(f"Successfully generated Mermaid visualization: {output_path}")
        print(f"\nDependency visualization saved to: {output_path}")
        print("You can view this file using Mermaid Live Editor (mermaid.live) or compatible Markdown viewers.")
        return 0
    except IOError as e:
        logger.error(f"Failed to write visualization file {output_path}: {e}", exc_info=True)
        print(f"Error: Could not write output file: {e}")
        return 1
    except Exception as e:
        logger.exception(f"An unexpected error occurred during visualization generation: {e}")
        print(f"Error: An unexpected error occurred: {e}")
        return 1

def main():
    """Parse arguments and dispatch to handlers."""
    parser = argparse.ArgumentParser(description="Dependency tracking system CLI")
    subparsers = parser.add_subparsers(dest="command", help="Available commands", required=True)

    # --- Analysis Commands ---
    analyze_file_parser = subparsers.add_parser("analyze-file", help="Analyze a single file")
    analyze_file_parser.add_argument("file_path", help="Path to the file")
    analyze_file_parser.add_argument("--output", help="Save results to JSON file")
    analyze_file_parser.set_defaults(func=command_handler_analyze_file)

    analyze_project_parser = subparsers.add_parser("analyze-project", help="Analyze project, generate keys/embeddings, update trackers")
    analyze_project_parser.add_argument("project_root", nargs='?', default='.', help="Project directory path (default: CWD)")
    analyze_project_parser.add_argument("--output", help="Save analysis summary to JSON file")
    analyze_project_parser.add_argument("--force-embeddings", action="store_true", help="Force regeneration of embeddings")
    analyze_project_parser.add_argument("--force-analysis", action="store_true", help="Force re-analysis and bypass cache")
    analyze_project_parser.set_defaults(func=command_handler_analyze_project)

    # --- Grid Manipulation Commands ---
    compress_parser = subparsers.add_parser("compress", help="Compress RLE string")
    compress_parser.add_argument("string", help="String to compress")
    compress_parser.set_defaults(func=handle_compress)

    decompress_parser = subparsers.add_parser("decompress", help="Decompress RLE string")
    decompress_parser.add_argument("string", help="String to decompress")
    decompress_parser.set_defaults(func=handle_decompress)

    get_char_parser = subparsers.add_parser("get_char", help="Get char at logical index in compressed string")
    get_char_parser.add_argument("string", help="Compressed string")
    get_char_parser.add_argument("index", type=int, help="Logical index")
    get_char_parser.set_defaults(func=handle_get_char)

    set_char_parser = subparsers.add_parser("set_char", help="Set char at logical index in a tracker file")
    set_char_parser.add_argument("tracker_file", help="Path to tracker file")
    set_char_parser.add_argument("key", type=str, help="Row key")
    set_char_parser.add_argument("index", type=int, help="Logical index")
    set_char_parser.add_argument("char", type=str, help="New character")
    set_char_parser.set_defaults(func=handle_set_char)

    add_dep_parser = subparsers.add_parser("add-dependency", help="Add dependency between keys")
    add_dep_parser.add_argument("--tracker", required=True, help="Path to tracker file")
    add_dep_parser.add_argument("--source-key", required=True, help="Source key")
    add_dep_parser.add_argument("--target-key", required=True, nargs='+', help="One or more target keys (space-separated)")
    add_dep_parser.add_argument("--dep-type", default=">", help="Dependency type (e.g., '>', '<', 'x')")
    add_dep_parser.set_defaults(func=handle_add_dependency)

    # --- Tracker File Management ---
    remove_key_parser = subparsers.add_parser("remove-key", help="Remove a key and its row/column from a specific tracker")
    remove_key_parser.add_argument("tracker_file", help="Path to the tracker file (.md)")
    remove_key_parser.add_argument("key", type=str, help="The key string to remove from this tracker")
    remove_key_parser.set_defaults(func=handle_remove_key)

    merge_parser = subparsers.add_parser("merge-trackers", help="Merge two tracker files")
    merge_parser.add_argument("primary_tracker_path", help="Primary tracker")
    merge_parser.add_argument("secondary_tracker_path", help="Secondary tracker")
    merge_parser.add_argument("--output", "-o", help="Output path (defaults to primary)")
    merge_parser.set_defaults(func=handle_merge_trackers)

    export_parser = subparsers.add_parser("export-tracker", help="Export tracker data")
    export_parser.add_argument("tracker_file", help="Path to tracker file")
    export_parser.add_argument("--format", choices=["json", "csv", "dot"], default="json", help="Export format")
    export_parser.add_argument("--output", "-o", help="Output file path")
    export_parser.set_defaults(func=handle_export_tracker)

    # --- Utility Commands ---
    clear_caches_parser = subparsers.add_parser("clear-caches", help="Clear all internal caches")
    clear_caches_parser.set_defaults(func=handle_clear_caches)

    reset_config_parser = subparsers.add_parser("reset-config", help="Reset config to defaults")
    reset_config_parser.set_defaults(func=handle_reset_config)

    update_config_parser = subparsers.add_parser("update-config", help="Update a config setting")
    update_config_parser.add_argument("key", help="Config key path (e.g., 'paths.doc_dir')")
    update_config_parser.add_argument("value", help="New value (JSON parse attempted)")
    update_config_parser.set_defaults(func=handle_update_config)

    show_deps_parser = subparsers.add_parser("show-dependencies", help="Show aggregated dependencies for a key")
    show_deps_parser.add_argument("--key", required=True, help="Key string to show dependencies for")
    show_deps_parser.set_defaults(func=handle_show_dependencies)

    # --- Show Keys Command ---
    show_keys_parser = subparsers.add_parser("show-keys", help="Show keys from tracker, indicating if checks needed (p, s, S)")
    show_keys_parser.add_argument("--tracker", required=True, help="Path to the tracker file (.md)")
    show_keys_parser.set_defaults(func=handle_show_keys)

    visualize_parser = subparsers.add_parser("visualize-dependencies", help="Generate a visualization of dependencies")
    visualize_parser.add_argument("--key", help="Optional: Key string to focus the visualization on (shows only direct connections)")
    visualize_parser.add_argument("--format", choices=["mermaid"], default="mermaid", help="Output format (only mermaid currently)")
    visualize_parser.add_argument("--output", "-o", help="Output file path (default: project_dependencies.mermaid or KEY_dependencies.mermaid)")
    visualize_parser.set_defaults(func=handle_visualize_dependencies)

    args = parser.parse_args()

    # --- Setup Logging ---
    log_formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
    root_logger = logging.getLogger(); root_logger.setLevel(logging.DEBUG)
    log_file_path = 'debug.txt'; suggestions_log_path = 'suggestions.log'
    try: # File Handler
        file_handler = logging.FileHandler(log_file_path, mode='w'); file_handler.setLevel(logging.DEBUG); file_handler.setFormatter(log_formatter); root_logger.addHandler(file_handler)
    except Exception as e: print(f"Error setting up file logger {log_file_path}: {e}", file=sys.stderr)
    try: # Suggestions Handler
        suggestion_handler = logging.FileHandler(suggestions_log_path, mode='w'); suggestion_handler.setLevel(logging.DEBUG); suggestion_handler.setFormatter(log_formatter)
        class SuggestionLogFilter(logging.Filter):
            def filter(self, record): return record.name.startswith('cline_utils.dependency_system.analysis') # Broaden slightly
        suggestion_handler.addFilter(SuggestionLogFilter()); root_logger.addHandler(suggestion_handler)
    except Exception as e: print(f"Error setting up suggestions logger {suggestions_log_path}: {e}", file=sys.stderr)
    # Console Handler
    console_handler = logging.StreamHandler(sys.stdout); console_handler.setLevel(logging.INFO); console_handler.setFormatter(log_formatter); root_logger.addHandler(console_handler)

    # Execute command
    if hasattr(args, 'func'):
        exit_code = args.func(args)
        sys.exit(exit_code)
    else:
        parser.print_help()
        sys.exit(1)

if __name__ == "__main__":
    main() # Call main function if script is executed
