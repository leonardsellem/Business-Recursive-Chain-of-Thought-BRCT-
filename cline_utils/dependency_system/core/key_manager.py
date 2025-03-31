"""
Core module for key management.
Handles key generation, validation, and sorting.
"""

import glob
import os
import re
from typing import Dict, List, Tuple, Optional, Set
from collections import defaultdict

from cline_utils.dependency_system.utils.path_utils import get_project_root, normalize_path, HIERARCHICAL_KEY_PATTERN, KEY_PATTERN
from cline_utils.dependency_system.utils.config_manager import ConfigManager

import logging
logger = logging.getLogger(__name__)

# Constants
ASCII_A = 65  # ASCII value for 'A'

# Moved from dependency_analyzer to break circular dependency
def get_file_type_for_key(file_path: str) -> str:
    """
    Determines the file type based on its extension.
    Simplified version for key management purposes.
    
    Args:
        file_path: The path to the file.
    Returns:
        The file type as a string (e.g., "py", "js", "md", "generic").
    """
    _, ext = os.path.splitext(file_path)
    ext = ext.lower()
    
    if ext == ".py":
        return "py"
    elif ext in (".js", ".ts", ".jsx", ".tsx"):
        return "js"
    elif ext in (".md", ".rst"):
        return "md"
    elif ext in (".html", ".htm"):
        return "html"
    elif ext == ".css":
        return "css"
    else:
        return "generic"


def generate_keys(root_paths: List[str], excluded_dirs: Optional[Set[str]] = None,
                 excluded_extensions: Optional[Set[str]] = None,
                 precomputed_excluded_paths: Optional[Set[str]] = None) -> Tuple[Dict[str, str], List[str]]:
    """
    Generate hierarchical keys for files and directories.
    Args:
        root_paths: List of root directory paths to process
        excluded_dirs: Optional set of directory names to exclude
        excluded_extensions: Optional set of file extensions to exclude
        precomputed_excluded_paths: Optional set of pre-calculated absolute paths to exclude (handles wildcards).
    Returns:
        Tuple containing:
        - Dictionary mapping hierarchical keys to file/directory paths
        - List of newly assigned keys
        - Dictionary of initial dependency suggestions (directory <-> file)
    """
    # Handle single string input
    if isinstance(root_paths, str):
        root_paths = [root_paths]
    
    # Validate all root paths exist
    for root_path in root_paths:
        if not os.path.exists(root_path):
            raise FileNotFoundError(f"Root path '{root_path}' does not exist.")
    
    # Use a ConfigManager instance to ensure consistent defaults
    config_manager = ConfigManager()

    # Use sets for efficient membership testing, get defaults from config if None
    excluded_dirs_names = set(excluded_dirs) if excluded_dirs else config_manager.get_excluded_dirs()
    excluded_extensions = set(excluded_extensions) if excluded_extensions else config_manager.get_excluded_extensions()
    # Get absolute, normalized paths for excluded dirs for robust checking
    project_root = get_project_root()
    absolute_excluded_dirs = {normalize_path(os.path.join(project_root, d)) for d in excluded_dirs_names}

    # Determine the final exclusion set
    if precomputed_excluded_paths is not None:
        # Use precomputed list (already handles wildcards) and combine with simple dir exclusions
        exclusion_set_for_processing = precomputed_excluded_paths.union(absolute_excluded_dirs)
        logger.debug(f"Using precomputed excluded paths combined with excluded dirs. Total: {len(exclusion_set_for_processing)}")
    else:
        # Fallback: Calculate wildcard paths now if not precomputed
        logger.debug("Precomputed excluded paths not provided, calculating now...")
        calculated_excluded_paths_list = config_manager.get_excluded_paths() # Returns a list
        # Convert list to set before union
        exclusion_set_for_processing = set(calculated_excluded_paths_list).union(absolute_excluded_dirs)
        logger.debug(f"Calculated excluded paths combined with excluded dirs. Total: {len(exclusion_set_for_processing)}")

    dir_to_letter: Dict[str, str] = {}  # Tracks directory letters to avoid duplicates
    key_map: Dict[str, str] = {}  # Maps hierarchical keys to normalized paths
    new_keys: List[str] = []  # Tracks newly assigned keys

    # Pass the final exclusion_set_for_processing down
    def process_directory(dir_path: str, exclusion_set: Set[str], parent_key: str = None, tier: int = 1):
        """Recursively processes directories and files."""
        nonlocal dir_to_letter, key_map, new_keys

        norm_dir_path = normalize_path(dir_path) # Normalize once
        # 1. Skip excluded directories using the combined exclusion_set (handles prefixes and wildcards)
        # Check if the normalized directory path starts with any path in the exclusion set
        if any(norm_dir_path.startswith(ex_path) for ex_path in exclusion_set):
            logger.debug(f"Exclusion Check 1 (Combined Set): Skipping excluded dir path: '{norm_dir_path}'")
            return
        else:
            logger.debug(f"Exclusion Check 1 (Combined Set): Processing dir path: '{norm_dir_path}'")

        # Assign a letter to this directory if it's a top-level directory
        if parent_key is None:
            dir_name = os.path.basename(dir_path)
            dir_letter = chr(ASCII_A + len(dir_to_letter))
            norm_dir_path = normalize_path(dir_path)
            dir_to_letter[norm_dir_path] = dir_letter
            key = f"{tier}{dir_letter}"

            if key not in key_map:
                key_map[key] = norm_dir_path.replace("\\", "/")
                new_keys.append(key)  # Record new key
        else:
            key = parent_key  # Use the parent key for subdirectories/files

        try:
            items = sorted(os.listdir(dir_path))  # Get items only once
        except OSError as e:
            logger.error(f"Error accessing directory '{dir_path}': {e}")
            return

        file_count = 1
        subdir_count = 1

        for item_name in items:
            item_path = os.path.join(dir_path, item_name)
            norm_item_path = normalize_path(item_path).replace("\\", "/")

            # REMOVED Redundant Check: The startswith check using exclusion_set handles this now.
            # # 2. Check against excluded file patterns (wildcards)
            # abs_item_path = os.path.join(dir_path, item_name)
            # excluded_paths = ConfigManager().get_excluded_paths() # Get configured excluded paths - THIS WAS THE BOTTLENECK
            # if any(glob.has_magic(pattern) and glob.glob(pattern, root_dir=get_project_root(), recursive=True) and normalize_path(abs_item_path) in [normalize_path(fp) for fp in glob.glob(pattern, root_dir=get_project_root(), recursive=True)] or not glob.has_magic(pattern) and normalize_path(abs_item_path) == normalize_path(pattern) for pattern in excluded_paths):
            #     logger.debug(f"Exclusion Check 2 (Wildcard Patterns): Skipping item '{item_name}' in '{norm_dir_path}' due to pattern match.")
            #     continue

            # 3. Skip excluded item names within the current directory
            # Relies solely on the set derived from config or args.
            # Also explicitly skip '.gitkeep' which isn't typically configured.
            if item_name in excluded_dirs_names or item_name == ".gitkeep":
                logger.debug(f"Exclusion Check 3 (Item Name): Skipping item '{item_name}' in '{norm_dir_path}'")
                continue
            else:
                logger.debug(f"Exclusion Check 3 (Item Name): Processing item '{item_name}' in '{norm_dir_path}'")

            # 3. Skip mini-tracker files by naming convention
            if item_name.endswith("_module.md"):
                logger.debug(f"Exclusion Check 4 (Mini-Tracker Name): Skipping item '{item_name}' in '{norm_dir_path}'")
                continue
            else:
                 # Proceed to extension check only if not skipped by name
                logger.debug(f"Exclusion Check 4 (Mini-Tracker Name): Processing item '{item_name}' in '{norm_dir_path}'")

                # 4. Skip files with excluded extensions
                _, ext = os.path.splitext(item_name)
                if ext in excluded_extensions:
                    logger.debug(f"Exclusion Check 5 (Extension): Skipping item '{item_name}' with extension '{ext}' in '{norm_dir_path}'")
                    continue
                # Only process or log processing if not skipped by extension
                elif os.path.isfile(item_path):
                    logger.debug(f"Exclusion Check 5 (Extension): Processing file item '{item_name}' with extension '{ext}' in '{norm_dir_path}'")
                    file_key = f"{key}{file_count}" # Assign key only if it's a file to be processed
                    if file_key not in key_map:
                        key_map[file_key] = norm_item_path
                        new_keys.append(file_key)  # Record new key
                    file_count += 1
                elif os.path.isdir(item_path):
                    subdir_letter = chr(97 + subdir_count - 1)  # Start with 'a' (ASCII 97) # Moved up
                    subdir_key = f"{tier + 1}{key[1:]}{subdir_letter}" # subdir_letter now defined
                    if subdir_key not in key_map:
                        key_map[subdir_key] = norm_item_path
                        new_keys.append(subdir_key)  # Record new key
                    subdir_count += 1
                    # Pass the same combined exclusion_set in recursive call
                    process_directory(item_path, exclusion_set, subdir_key, tier + 1)

    for root_path in root_paths:
        # Pass the final exclusion_set_for_processing to initial call
        process_directory(root_path, exclusion_set_for_processing)

    # Generate initial suggestions after processing all directories
    from cline_utils.dependency_system.analysis.dependency_suggester import suggest_initial_dependencies
    initial_suggestions = suggest_initial_dependencies(key_map)

    return key_map, new_keys, initial_suggestions

def validate_key(key: str) -> bool:
    """
    Validate if a key follows the hierarchical key format.
    Args:
        key: The hierarchical key to validate
        
    Returns:
        True if valid, False otherwise
    """
    # Basic pattern: starts with a number, followed by uppercase letter,
    # then optional lowercase letters and numbers
    return bool(re.match(HIERARCHICAL_KEY_PATTERN, key))

def get_path_from_key(key: str, key_map: Dict[str, str]) -> Optional[str]:
    """
    Get the file/directory path corresponding to a hierarchical key.
    Args:
        key: The hierarchical key
        key_map: Dictionary mapping keys to paths
        
    Returns:
        The file/directory path or None if key not found
    """
    return key_map.get(key)

def get_key_from_path(path: str, key_map: Dict[str, str]) -> Optional[str]:
    """
    Get the hierarchical key corresponding to a file/directory path.
    Args:
        path: The file/directory path
        key_map: Dictionary mapping keys to paths
        
    Returns:
        The hierarchical key or None if path not found
    """
    norm_path = normalize_path(path).replace("\\", "/")
    for k, v in key_map.items():
        if v == norm_path:
            return k
    return None

def sort_keys(keys: List[str]) -> List[str]:
    """
    Sort hierarchical keys in a natural order.
    Args:
        keys: List of hierarchical keys to sort
    Returns:
        Sorted list of keys
    """
    def sort_key(key):
        parts = re.findall(KEY_PATTERN, key)
        return [int(p) if p.isdigit() else p for p in parts]
    
    return sorted(keys, key=sort_key)

def regenerate_keys(root_paths: List[str], excluded_dirs: Set[str] = None,
                 excluded_extensions: Set[str] = None) -> Tuple[Dict[str, str], List[str]]:
    """
    Regenerates keys for the given root paths. This function is explicitly added
    to allow for dynamic key updates. It simply calls `generate_keys` with the same
    arguments.
    Args:
        root_paths: List of root directory paths to process
        excluded_dirs: Optional set of directory names to exclude
        excluded_extensions: Optional set of file extensions to exclude

    Returns:
        Tuple containing:
        - Dictionary mapping hierarchical keys to file/directory paths
        - List of newly assigned keys
        - Dictionary of initial dependency suggestions (directory <-> file) # Note: initial suggestions are now empty due to previous change
    """
    # Note: This regenerate function doesn't handle the new precomputed_excluded_paths parameter.
    # If regeneration is needed with precomputed paths, this function would need updating or
    # the caller should use generate_keys directly.
    return generate_keys(root_paths, excluded_dirs, excluded_extensions)

# EoF