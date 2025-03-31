"""
Main entry point for the dependency tracking system.
Processes command-line arguments and delegates to appropriate handlers.
"""

import argparse
from collections import defaultdict
import logging
import os
import sys
import re # <<< ADDED IMPORT

from cline_utils.dependency_system.analysis.project_analyzer import analyze_project

from cline_utils.dependency_system.core.dependency_grid import compress, decompress, get_char_at, set_char_at, add_dependency_to_grid
from cline_utils.dependency_system.io.tracker_io import remove_file_from_tracker, merge_trackers, read_tracker_file, write_tracker_file, export_tracker
from cline_utils.dependency_system.utils.path_utils import get_project_root, normalize_path, KEY_PATTERN # <<< MODIFIED IMPORT
from cline_utils.dependency_system.utils.config_manager import ConfigManager
from cline_utils.dependency_system.utils.cache_manager import clear_all_caches, file_modified
from cline_utils.dependency_system.analysis.dependency_analyzer import analyze_file
from cline_utils.dependency_system.core.dependency_grid import get_dependencies_from_grid # Added
from cline_utils.dependency_system.core.key_manager import sort_keys # Added for consistent sorting
# from cline_utils.dependency_system.io.tracker_io import get_tracker_paths # Assuming this exists or similar logic needed
import glob # Added

# Configure logging (moved to main block)
# logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__) # Get logger for this module

def command_handler_analyze_file(args):
    """Handle the analyze-file command."""
    import json

    try:
        if not os.path.exists(args.file_path):
            print(f"Error: File not found: {args.file_path}")
            return 1

        results = analyze_file(args.file_path)

        if args.output:
            output_dir = os.path.dirname(args.output)
            if output_dir and not os.path.exists(output_dir):
                os.makedirs(output_dir, exist_ok=True)
            with open(args.output, 'w', encoding='utf-8') as f:
                json.dump(results, f, indent=2)
            print(f"Analysis results saved to {args.output}")
        else:
            print(json.dumps(results, indent=2))
        return 0
    except Exception as e:
        print(f"Error analyzing file: {str(e)}")
        return 1

def command_handler_analyze_project(args):
    """Handle the analyze-project command."""
    import json

    try:
        if not args.project_root:
             # If project_root is not provided, default to current directory
             args.project_root = "."
             logger.info(f"No project root provided, defaulting to current directory: {os.path.abspath(args.project_root)}")

        abs_project_root = normalize_path(os.path.abspath(args.project_root))

        if not os.path.exists(abs_project_root) or not os.path.isdir(abs_project_root):
            print(f"Error: Project directory not found or is not a directory: {abs_project_root}")
            return 1

        # Change CWD for the analysis if project_root is specified and different
        original_cwd = os.getcwd()
        if abs_project_root != normalize_path(original_cwd):
             logger.info(f"Changing working directory to: {abs_project_root}")
             os.chdir(abs_project_root)
             # Re-initialize ConfigManager relative to the new CWD
             ConfigManager.initialize(force=True)

        logger.debug(f"Analyzing project: {abs_project_root}, force_analysis={args.force_analysis}, force_embeddings={args.force_embeddings}")
        # Analyze project now implicitly uses the new CWD if changed
        results = analyze_project(force_analysis=args.force_analysis, force_embeddings=args.force_embeddings)

        logger.debug(f"All Suggestions before Tracker Update: {results.get('dependency_suggestion', {}).get('suggestions')}") # Log suggestions

        if args.output:
            output_path_abs = normalize_path(os.path.abspath(args.output))
            output_dir = os.path.dirname(output_path_abs)
            if output_dir: # Check if output_dir is not empty (can happen if output is just a filename)
                os.makedirs(output_dir, exist_ok=True)
            with open(output_path_abs, 'w', encoding='utf-8') as f:
                json.dump(results, f, indent=2)
            print(f"Analysis results saved to {output_path_abs}") # Use absolute path
        else:
            # Prevent printing potentially large JSON to stdout if no output file specified
            print("Analysis complete. Results not printed to console (use --output to save).") # Inform user
        return 0

    except Exception as e:
        logger.error(f"Error analyzing project: {str(e)}", exc_info=True)
        print(f"Error analyzing project: {str(e)}")
        return 1
    finally:
        # Change back to original CWD if it was changed
        if 'original_cwd' in locals() and normalize_path(os.getcwd()) != normalize_path(original_cwd):
             logger.info(f"Changing working directory back to: {original_cwd}")
             os.chdir(original_cwd)
             # Re-initialize ConfigManager back to original CWD
             ConfigManager.initialize(force=True)


def handle_compress(args: argparse.Namespace) -> int:
    """Handle the compress command."""
    try:
        result = compress(args.string)
        # Use print for direct command output, logger for internal info
        print(f"Compressed string: {result}")
        return 0
    except Exception as e:
        logger.error(f"Error compressing string: {str(e)}")
        print(f"Error: {str(e)}") # Also print error to console
        return 1

def handle_decompress(args: argparse.Namespace) -> int:
    """Handle the decompress command."""
    try:
        result = decompress(args.string)
        print(f"Decompressed string: {result}")
        return 0
    except Exception as e:
        logger.error(f"Error decompressing string: {str(e)}")
        print(f"Error: {str(e)}")
        return 1

def handle_get_char(args: argparse.Namespace) -> int:
    """Handle the get_char command."""
    try:
        result = get_char_at(args.string, args.index)
        print(f"Character at index {args.index}: {result}")
        return 0
    except IndexError:
        logger.error("Error: Index out of range")
        print("Error: Index out of range")
        return 1
    except Exception as e:
        logger.error(f"Error getting character: {str(e)}")
        print(f"Error: {str(e)}")
        return 1

def handle_set_char(args: argparse.Namespace) -> int:
    """Handle the set_char command."""
    try:
        tracker_data = read_tracker_file(args.tracker_file)
        if not tracker_data or not tracker_data.get("keys"):
             print(f"Error: Could not read tracker file or no keys found: {args.tracker_file}")
             return 1

        if args.key not in tracker_data["keys"]:
            print(f"Error: Key {args.key} not found in tracker {args.tracker_file}")
            return 1

        sorted_keys = list(tracker_data["keys"].keys()) # Get keys for index lookup
        if args.key not in sorted_keys: # Should not happen if check above passes, but good sanity check
             print(f"Internal Error: Key '{args.key}' found in map but not in list?")
             return 1

        row_str = tracker_data["grid"].get(args.key, "")
        if not row_str: # Handle case where grid row might be missing
            print(f"Warning: Grid row for key '{args.key}' not found. Initializing.")
            row_str = compress('p' * len(sorted_keys)) # Initialize with placeholders

        # Use set_char_at which handles decompression/recompression
        updated_compressed_row = set_char_at(row_str, args.index, args.char)

        tracker_data["grid"][args.key] = updated_compressed_row
        tracker_data["last_grid_edit"] = f"Set {args.key}[{args.index}] to {args.char}"
        success = write_tracker_file(args.tracker_file, tracker_data["keys"], tracker_data["grid"], tracker_data.get("last_key_edit", ""), tracker_data["last_grid_edit"])

        if success:
            print(f"Set character at index {args.index} to '{args.char}' for key {args.key} in {args.tracker_file}")
            # Invalidate relevant caches after modifying the tracker
            file_modified(tracker_data["keys"][args.key], ".") # Pass project root if needed, assuming current dir for now
            return 0
        else:
            print(f"Error: Failed to write updated tracker file: {args.tracker_file}")
            return 1

    except IndexError:
        print(f"Error: Index {args.index} is out of range for key {args.key}.")
        return 1
    except ValueError as e:
         print(f"Error: {e}") # e.g., invalid character or key issues
         return 1
    except Exception as e:
        logger.error(f"Error setting character: {str(e)}", exc_info=True)
        print(f"An unexpected error occurred: {str(e)}")
        return 1


def handle_remove_file(args: argparse.Namespace) -> int:
    """Handle the remove-file command."""
    try:
        remove_file_from_tracker(args.tracker_file, args.file)
        print(f"Removed file {args.file} from tracker {args.tracker_file}")
        # Invalidate relevant caches after removing a file
        # Assuming project root is needed for accurate invalidation
        config = ConfigManager()
        project_root = get_project_root()
        file_modified(args.file, project_root)
        return 0
    except FileNotFoundError as e:
        print(f"Error: {e}")
        return 1
    except ValueError as e:
        print(f"Error: {e}")
        return 1
    except Exception as e:
        logger.error(f"Failed to remove file: {str(e)}", exc_info=True)
        print(f"An unexpected error occurred: {str(e)}")
        return 1

def handle_add_dependency(args: argparse.Namespace) -> int:
    """Handle the add-dependency command."""
    try:
        tracker_data = read_tracker_file(args.tracker)
        if not tracker_data or not tracker_data.get("keys"):
            print(f"Error: Could not read tracker file or no keys found: {args.tracker}")
            return 1
 
        # --- Dependency Type Validation ---
        # Based on .clinerules Character_Definitions
        ALLOWED_DEP_TYPES = {'<', '>', 'x', 'd', 'o', 'n', 'p', 's', 'S'}
        if args.dep_type not in ALLOWED_DEP_TYPES:
            print(f"Error: Invalid dependency type '{args.dep_type}'. Allowed types are: {', '.join(sorted(list(ALLOWED_DEP_TYPES)))}")
            # Log the error as well
            logger.error(f"Invalid dependency type '{args.dep_type}' provided via add-dependency command.")
            return 1
        # --- End Validation ---

        keys = sort_keys(list(tracker_data["keys"].keys())) # Ensure keys are sorted using key_manager.sort_keys for consistent indexing
        if args.source_key not in keys or args.target_key not in keys:
            print(f"Error: Source '{args.source_key}' or target '{args.target_key}' not found in tracker")
            return 1

        new_grid = add_dependency_to_grid(tracker_data["grid"], args.source_key, args.target_key, keys, args.dep_type)

        tracker_data["grid"] = new_grid
        tracker_data["last_grid_edit"] = f"Add {args.source_key}->{args.target_key} ({args.dep_type})"
        success = write_tracker_file(args.tracker, tracker_data["keys"], tracker_data["grid"],
                                     tracker_data.get("last_key_edit", ""), tracker_data["last_grid_edit"])
        if success:
            print(f"Added dependency {args.source_key} -> {args.target_key} ({args.dep_type}) in {args.tracker}")
             # Invalidate cache if needed
            config = ConfigManager()
            project_root = get_project_root()
            file_modified(tracker_data["keys"][args.source_key], project_root) # Invalidate source file analysis/suggestion cache
            return 0
        else:
            print(f"Error: Failed to write updated tracker to {args.tracker}")
            return 1
    except ValueError as e:
         print(f"Error: {e}")
         return 1
    except Exception as e:
        logger.error(f"Error adding dependency: {str(e)}", exc_info=True)
        print(f"An unexpected error occurred: {str(e)}")
        return 1

def handle_merge_trackers(args: argparse.Namespace) -> int:
    """Handle the merge-trackers command."""
    try:
        primary_tracker_path = normalize_path(args.primary_tracker_path)
        secondary_tracker_path = normalize_path(args.secondary_tracker_path)
        output_path = normalize_path(args.output) if args.output else primary_tracker_path

        # Assuming project root is current dir if not specified elsewhere
        config = ConfigManager()
        project_root = get_project_root()

        merged_data = merge_trackers(primary_tracker_path, secondary_tracker_path, output_path)
         # Invalidate relevant caches after merging trackers
        file_modified("", project_root) # Broad invalidation needed after merge
        print(
            f"Merged trackers: {primary_tracker_path} and {secondary_tracker_path} into {output_path}. Total keys: {len(merged_data.get('keys', {}))}"
        )
        return 0
    except Exception as e:
        logger.exception(f"Failed to merge trackers: {e}")
        print(f"Error merging trackers: {e}")
        return 1

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
        if "Error:" in result: # Check if the return value indicates an error
            print(result) # Print the error message returned by export_tracker
            return 1
        print(f"Tracker exported successfully to {output_path}")
        return 0
    except Exception as e:
        logger.exception(f"Error exporting tracker: {e}")
        print(f"Error exporting tracker: {e}")
        return 1

def handle_update_config(args: argparse.Namespace) -> int:
    """Handle the update-config command."""
    config_manager = ConfigManager()
    try:
        # Assume value is string, let ConfigManager handle type conversion if needed
        success = config_manager.update_config_setting(args.key, args.value)
        if success:
            print(f"Updated configuration setting: {args.key} = {args.value}")
            return 0
        else:
            print(f"Error: Failed to update configuration setting (key '{args.key}' might be invalid or value incorrect type).")
            return 1
    except Exception as e:
        logger.exception(f"Error updating configuration setting: {e}")
        print(f"Error updating config: {e}")
        return 1

def handle_reset_config(args: argparse.Namespace) -> int:
    """Handle the reset-config command."""
    config_manager = ConfigManager()
    try:
        success = config_manager.reset_to_defaults()
        if success:
            print("Configuration reset to default values.")
            return 0
        else:
            print("Error: Failed to reset configuration to default values.")
            return 1
    except Exception as e:
        logger.exception(f"Error resetting configuration: {e}")
        print(f"Error resetting config: {e}")
        return 1

def handle_show_dependencies(args: argparse.Namespace) -> int:
    """Handle the show-dependencies command."""
    target_key = args.key
    logger.info(f"Showing dependencies for key: {target_key}")

    config = ConfigManager()
    project_root = get_project_root() # Assuming this helper gets the correct root

    # --- Gather all tracker paths ---
    all_tracker_paths = set()
    memory_dir_rel = config.get_path('memory_dir') # Get memory_dir from config
    if not memory_dir_rel:
        logger.error("Memory directory path ('memory_dir') not configured in .clinerules.config.json")
        print("Error: Memory directory path ('memory_dir') not configured. Check .clinerules.config.json and debug.txt.")
        return 1 # Early exit if config is missing
    memory_dir_abs = normalize_path(os.path.join(project_root, memory_dir_rel))

    # 1. Construct main and doc tracker paths dynamically
    main_tracker_abs = normalize_path(os.path.join(memory_dir_abs, 'module_relationship_tracker.md'))
    doc_tracker_abs = normalize_path(os.path.join(memory_dir_abs, 'doc_tracker.md'))

    if os.path.exists(main_tracker_abs):
        all_tracker_paths.add(main_tracker_abs)
    else:
        logger.warning(f"Main tracker path not found: {main_tracker_abs}")
    if os.path.exists(doc_tracker_abs):
        all_tracker_paths.add(doc_tracker_abs)
    else:
        logger.warning(f"Doc tracker path not found: {doc_tracker_abs}")

    # 2. Find mini-trackers (*_module.md) in code roots
    # get_code_root_directories already returns normalized paths relative to project_root
    code_roots_rel = config.get_code_root_directories()
    for code_root_rel in code_roots_rel:
        code_root_abs = normalize_path(os.path.join(project_root, code_root_rel))
        # Search for module files directly within the code root and subdirectories
        # Using recursive glob pattern '**/*_module.md'
        mini_tracker_pattern = os.path.join(code_root_abs, '**', '*_module.md')
        found_mini_trackers = glob.glob(mini_tracker_pattern, recursive=True)
        for mt_path in found_mini_trackers:
             mt_path_abs = normalize_path(mt_path)
             if os.path.exists(mt_path_abs):
                 all_tracker_paths.add(mt_path_abs)
             else: # Should not happen with glob, but good practice
                 logger.warning(f"Glob found mini-tracker but it doesn't exist? {mt_path_abs}")


    if not all_tracker_paths:
        print("Error: No tracker files found based on configuration.")
        return 1

    logger.debug(f"Found tracker files to search: {all_tracker_paths}")

    # --- Aggregate dependencies ---
    outgoing_deps = set() # Using set to store (key, path) tuples for auto-deduplication
    incoming_deps = set()
    key_found_in_any_tracker = False
    master_key_map = {} # Aggregate all key definitions found across trackers
    all_dependencies_by_type = defaultdict(set) # Store sets of (key, path) tuples

    # First pass: Aggregate all key definitions
    for tracker_path in all_tracker_paths:
        try:
            logger.debug(f"Reading tracker for key map: {tracker_path}")
            tracker_data = read_tracker_file(tracker_path)
            if tracker_data and tracker_data.get("keys"):
                master_key_map.update(tracker_data["keys"]) # Add/overwrite keys
        except Exception as e:
            logger.error(f"Failed to read tracker {tracker_path} for key map: {e}", exc_info=True)
            # Continue processing other trackers

    if not master_key_map:
        print("Error: No valid key definitions found in any tracker file.")
        return 1

    # Second pass: Find dependencies using the master map for path lookups
    for tracker_path in all_tracker_paths:
        try:
            logger.debug(f"Reading tracker for dependencies: {tracker_path}")
            tracker_data = read_tracker_file(tracker_path)
            if not tracker_data or not tracker_data.get("keys") or not tracker_data.get("grid"):
                logger.warning(f"Skipping tracker with missing keys or grid: {tracker_path}")
                continue

            key_map = tracker_data["keys"]
            grid = tracker_data["grid"]
            # Use canonical sort order for keys *within this specific tracker*
            sorted_keys_local = sort_keys(list(key_map.keys()))

            if target_key in key_map:
                key_found_in_any_tracker = True
                logger.debug(f"Key '{target_key}' found in {tracker_path}, analyzing grid.")
                try:
                    # Call the refactored get_dependencies_from_grid
                    # Pass the grid, target key, and the canonically sorted keys for THIS tracker
                    deps_from_this_grid = get_dependencies_from_grid(grid, target_key, sorted_keys_local)

                    # Merge results into the main dictionary, using the master_key_map for paths
                    for dep_type, key_list in deps_from_this_grid.items():
                        for dep_key in key_list:
                            dep_path = master_key_map.get(dep_key, "PATH_NOT_FOUND") # Lookup path in aggregated map
                            all_dependencies_by_type[dep_type].add((dep_key, dep_path))

                except ValueError as e:
                    logger.error(f"Error processing dependencies for {target_key} in {tracker_path}: {e}")
                except Exception as e:
                    logger.error(f"Unexpected error processing dependencies for {target_key} in {tracker_path}: {e}", exc_info=True)

        except Exception as e:
            logger.error(f"Failed to read or process tracker {tracker_path} during dependency aggregation: {e}", exc_info=True)
            print(f"Warning: Error processing {tracker_path}. See debug.txt for details.")

    # --- Print results ---
    if not key_found_in_any_tracker:
         print(f"Error: Key '{target_key}' not found in any processed tracker file.")
         return 1

    target_path_str = f" ({master_key_map.get(target_key, 'Path definition not found')})"
    print(f"\n--- Dependencies for Key: {target_key}{target_path_str} ---")

    # Helper function to generate the actual sort key for hierarchical comparison
    def _hierarchical_sort_key_func(key_str: str):
        """Mimics the core logic of key_manager.sort_keys for a single key."""
        if not key_str: return [] # Handle empty strings if they somehow occur
        # Use the imported KEY_PATTERN
        parts = re.findall(KEY_PATTERN, key_str)
        # Convert numeric parts to integers for proper sorting
        return [int(p) if p.isdigit() else p for p in parts]

    # Define output sections and corresponding characters
    # Using definitions from .clinerules
    output_sections = [
        ("Mutual ('x')", 'x'),
        ("Documentation ('d')", 'd'),
        ("Semantic (Strong) ('S')", 'S'),
        ("Semantic (Weak) ('s')", 's'),
        ("Depends On ('<')", '<'),      # Target depends ON listed key
        ("Depended On By ('>')", '>'), # Listed key depends ON target
        ("Placeholders ('p')", 'p')
    ]

    for section_title, dep_char in output_sections:
        print(f"\n{section_title}:")
        dep_set = all_dependencies_by_type.get(dep_char)
        if dep_set:
            # Sort for consistent output using the helper function
            # Apply the sort key function to the actual key (item[0])
            sorted_deps = sorted(list(dep_set), key=lambda item: _hierarchical_sort_key_func(item[0]))
            for dep_key, dep_path in sorted_deps:
                logger.debug(f"Printing dependency: {(dep_key, dep_path)}") # <<< ADD DEBUG LOGGING
                print(f"  - {dep_key}: {dep_path}")
        else:
            print("  None")

    print("\n------------------------------------------")

    return 0


def main():
    """Parse arguments and dispatch to handlers."""
    parser = argparse.ArgumentParser(description="Dependency tracking system CLI")
    subparsers = parser.add_subparsers(dest="command", help="Available commands", required=True) # Make command required

    # --- Analysis Commands ---
    analyze_file_parser = subparsers.add_parser("analyze-file", help="Analyze a single file for dependencies")
    analyze_file_parser.add_argument("file_path", help="Path to the file to analyze")
    analyze_file_parser.add_argument("--output", help="Path to save the analysis results (JSON)")
    analyze_file_parser.set_defaults(func=command_handler_analyze_file)

    analyze_project_parser = subparsers.add_parser("analyze-project", help="Analyze a project, generate embeddings, suggest dependencies, and update trackers")
    analyze_project_parser.add_argument("project_root", nargs='?', default='.', help="Path to the project directory (default: current directory)")
    # analyze_project_parser.add_argument("--tracker-file", help="Path to the main tracker file (deprecated, determined by config)")
    analyze_project_parser.add_argument("--output", help="Path to save the overall analysis results (JSON)")
    analyze_project_parser.add_argument("--force-embeddings", action="store_true", help="Force regeneration of embeddings")
    analyze_project_parser.add_argument("--force-analysis", action="store_true", help="Force re-analysis and bypass cache")
    analyze_project_parser.set_defaults(func=command_handler_analyze_project)

    # --- Grid Manipulation Commands ---
    compress_parser = subparsers.add_parser("compress", help="Compress a dependency grid string using RLE")
    compress_parser.add_argument("string", help="String to compress")
    compress_parser.set_defaults(func=handle_compress)

    decompress_parser = subparsers.add_parser("decompress", help="Decompress an RLE dependency grid string")
    decompress_parser.add_argument("string", help="Compressed string to decompress")
    decompress_parser.set_defaults(func=handle_decompress)

    get_char_parser = subparsers.add_parser("get_char", help="Get character at a logical index in a compressed string")
    get_char_parser.add_argument("string", help="Compressed string")
    get_char_parser.add_argument("index", type=int, help="Logical index (0-based)")
    get_char_parser.set_defaults(func=handle_get_char)

    set_char_parser = subparsers.add_parser("set_char", help="Set character at a logical index in a tracker file")
    set_char_parser.add_argument("tracker_file", help="Path to the tracker file (.md)")
    set_char_parser.add_argument("key", type=str, help="Row key to update")
    set_char_parser.add_argument("index", type=int, help="Logical index (0-based) of the character to change")
    set_char_parser.add_argument("char", type=str, help="New dependency character (e.g., '>', '<', 'x', 'n', 'd', 's', 'p')")
    set_char_parser.set_defaults(func=handle_set_char)

    add_dep_parser = subparsers.add_parser("add-dependency", help="Add a dependency relationship between two keys in a tracker")
    add_dep_parser.add_argument("--tracker", required=True, type=str, help="Path to the tracker file (.md)")
    add_dep_parser.add_argument("--source-key", required=True, type=str, help="Source key (row)")
    add_dep_parser.add_argument("--target-key", required=True, type=str, help="Target key (column)")
    add_dep_parser.add_argument("--dep-type", type=str, default=">", help="Dependency type character (e.g., '>', '<', 'x', 'n', 'd', 's')")
    add_dep_parser.set_defaults(func=handle_add_dependency)

    # --- Tracker File Management ---
    remove_file_parser = subparsers.add_parser("remove-file", help="Remove a file and its corresponding key/row/column from a tracker")
    remove_file_parser.add_argument("tracker_file", help="Path to the tracker file (.md)")
    remove_file_parser.add_argument("file", type=str, help="Absolute or relative path of the file to remove")
    remove_file_parser.set_defaults(func=handle_remove_file)

    merge_parser = subparsers.add_parser("merge-trackers", help="Merge two tracker files (primary takes precedence)")
    merge_parser.add_argument("primary_tracker_path", help="Path to the primary tracker file")
    merge_parser.add_argument("secondary_tracker_path", help="Path to the secondary tracker file")
    merge_parser.add_argument("--output", "-o", help="Output path for merged tracker (defaults to overwriting primary tracker)")
    # merge_parser.add_argument("--tracker-type", default="main", choices=["main", "doc", "mini"], help="Tracker type (influences merge logic if specialized)") # Keep simple for now
    merge_parser.set_defaults(func=handle_merge_trackers)

    export_parser = subparsers.add_parser("export-tracker", help="Export tracker data to JSON, CSV, or DOT format")
    export_parser.add_argument("tracker_file", help="Path to the tracker file (.md)")
    export_parser.add_argument("--format", choices=["json", "csv", "dot"], default="json", help="Export format")
    export_parser.add_argument("--output", "-o", help="Output file path (defaults to tracker path with new extension)")
    export_parser.set_defaults(func=handle_export_tracker)

    # --- Utility Commands ---
    clear_caches_parser = subparsers.add_parser("clear-caches", help="Clear all internal caches used by the system")
    clear_caches_parser.set_defaults(func=handle_clear_caches)

    reset_config_parser = subparsers.add_parser("reset-config", help="Reset configuration to default values")
    reset_config_parser.set_defaults(func=handle_reset_config)

    update_config_parser = subparsers.add_parser("update-config", help="Update a specific configuration setting")
    update_config_parser.add_argument("key", help="Configuration key path (e.g., 'paths.doc_dir', 'thresholds.code_similarity')")
    update_config_parser.add_argument("value", help="New value for the configuration key (will be parsed appropriately)")
    update_config_parser.set_defaults(func=handle_update_config)

    show_deps_parser = subparsers.add_parser("show-dependencies", help="Show aggregated dependencies for a key across all trackers")
    show_deps_parser.add_argument("--key", required=True, type=str, help="Key to show dependencies for")
    show_deps_parser.set_defaults(func=handle_show_dependencies)


    args = parser.parse_args()

    # Execute the function associated with the chosen command
    if hasattr(args, 'func'):
        # Add project_root to args if not present but needed by handler (like remove-file)
        if 'project_root' not in args and args.command in ['remove-file', 'merge-trackers', 'set_char']:
             # Infer project root - assumes script is run from project root or handler can find it
             args.project_root = ConfigManager().get_project_root() # Get root from config

        return args.func(args)
    else:
        # This should not happen if subparsers are required=True
        parser.print_help()
        return 1 # Indicate error if no command was provided (though argparse should handle this)

if __name__ == "__main__":
    # --- Setup Logging ---
    log_formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
    root_logger = logging.getLogger() # Get the root logger
    root_logger.setLevel(logging.DEBUG) # Capture all levels

    # File Handler (DEBUG level)
    # Ensure logs directory exists or handle appropriately
    log_file_path = 'debug.txt'
    try:
        file_handler = logging.FileHandler(log_file_path, mode='w') # Overwrite each run
        file_handler.setLevel(logging.DEBUG)
        file_handler.setFormatter(log_formatter)
        root_logger.addHandler(file_handler)
    except Exception as e:
        print(f"Error setting up file logger for {log_file_path}: {e}", file=sys.stderr)

    # Suggestions File Handler (DEBUG level)
    suggestions_log_path = 'suggestions.log'
    try:
        suggestion_handler = logging.FileHandler(suggestions_log_path, mode='w') # Overwrite each run
        suggestion_handler.setLevel(logging.DEBUG)
        suggestion_handler.setFormatter(log_formatter)
        # Add filter to only capture logs from specific modules
        class SuggestionLogFilter(logging.Filter):
            def filter(self, record):
                return record.name.startswith('cline_utils.dependency_system.analysis.project_analyzer') or \
                       record.name.startswith('cline_utils.dependency_system.analysis.dependency_suggester')
        suggestion_handler.addFilter(SuggestionLogFilter())
        root_logger.addHandler(suggestion_handler)
    except Exception as e:
        print(f"Error setting up suggestions file logger for {suggestions_log_path}: {e}", file=sys.stderr)

    # Console Handler (INFO level)
    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setLevel(logging.INFO) # Only show INFO and above on console
    console_handler.setFormatter(log_formatter)
    root_logger.addHandler(console_handler)

    # --- Run Main ---
    exit_code = main()
    sys.exit(exit_code)