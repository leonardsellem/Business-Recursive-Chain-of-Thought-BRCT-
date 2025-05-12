# core/dependency_grid.py

"""
Core module for dependency grid operations.
Handles grid creation, compression, decompression, and dependency management with key-centric design.
"""

import os
import re
from typing import Dict, List, Tuple, Optional
from collections import defaultdict # Ensure defaultdict is imported if used (e.g., get_dependencies_from_grid)


# Import only from utils or sibling core modules if necessary
from cline_utils.dependency_system.utils.cache_manager import cached, invalidate_dependent_entries, clear_all_caches
from cline_utils.dependency_system.utils.config_manager import ConfigManager
# Import only validate_key if needed, sort_keys is removed
from .key_manager import sort_key_strings_hierarchically, validate_key

import logging
logger = logging.getLogger(__name__)

# Constants
DIAGONAL_CHAR = "o"
PLACEHOLDER_CHAR = "p"
EMPTY_CHAR = "."

# Compile regex pattern for RLE compression scheme (repeating characters, excluding 'o')
COMPRESSION_PATTERN = re.compile(r'([^o])\1{2,}')

#def _cache_key_for_grid(func_name: str, grid: Dict[str, str], *args) -> str:
#    """Generate a cache key for grid operations."""
#    from cline_utils.dependency_system.utils.path_utils import normalize_path
#
#    grid_str = ":".join(f"{k}={v}" for k, v in sorted(grid.items()))
#    args_str = ":".join(str(a) for a in args)
#    return f"{func_name}:{grid_str}:{args_str}"

def compress(s: str) -> str:
    """
    Compress a dependency string using Run-Length Encoding (RLE).
    Only compresses sequences of 3 or more repeating characters (excluding 'o').

    Args:
        s: String to compress (e.g., "nnnnnpppdd")
    Returns:
        Compressed string (e.g., "n5p3d2")
    """
    if not s or len(s) <= 3:
        return s
    return COMPRESSION_PATTERN.sub(lambda m: m.group(1) + str(len(m.group())), s)

@cached("grid_decompress", key_func=lambda s: f"decompress:{s}")
def decompress(s: str) -> str:
    """
    Decompress a Run-Length Encoded dependency string with caching.

    Args:
        s: Compressed string (e.g., "n5p3d2")
    Returns:
        Decompressed string (e.g., "nnnnnpppdd")
    """
    if not s or (len(s) <= 3 and not any(c.isdigit() for c in s)):
        return s

    result = []
    i = 0
    while i < len(s):
        if i + 1 < len(s) and s[i + 1].isdigit():
            char = s[i]; j = i + 1
            while j < len(s) and s[j].isdigit(): j += 1
            count = int(s[i + 1:j])
            result += char * count; i = j
        else: result += s[i]; i += 1
    return "".join(result)

# --- Grid Creation ---
@cached("initial_grids",
       key_func=lambda keys: f"initial_grid:{':'.join(sort_key_strings_hierarchically(keys))}")
def create_initial_grid(keys: List[str]) -> Dict[str, str]:
    """
    Create an initial dependency grid with placeholders and diagonal markers.

    Args:
        keys: List of valid keys to include in the grid
    Returns:
        Dictionary mapping keys to compressed dependency strings
    """
    if not keys or not all(isinstance(k, str) and validate_key(k) for k in keys):
        logger.error(f"Invalid keys provided for initial grid: {keys}")
        raise ValueError("All keys must be valid non-empty strings")
    sorted_keys = sort_key_strings_hierarchically(keys)
    grid = {}
    num_keys = len(sorted_keys)
    for i, row_key in enumerate(sorted_keys):
        row_list = [PLACEHOLDER_CHAR] * num_keys
        row_list[i] = DIAGONAL_CHAR
        grid[row_key] = compress("".join(row_list))
    return grid

# --- Character Access Helpers (No changes needed) ---
def _parse_count(s: str, start: int) -> Tuple[int, int]:
    """Helper function to parse the count from a string.
    Args:
        s: The string to parse
        start: The starting index for parsing
    Returns:
        Tuple containing:
        - The parsed count as an integer
        - The index after the count
    """
    j = start
    while j < len(s) and s[j].isdigit(): j += 1
    return int(s[start:j]), j

def get_char_at(s: str, index: int) -> str:
    """
    Get the character at a specific index in a decompressed string.

    Args:
        s: The compressed string
        index: The index in the decompressed string
    Returns:
        The character at the specified index
    Raises:
        IndexError: If the index is out of range
    """
    decompressed_index = 0
    i = 0
    while i < len(s):
        if i + 1 < len(s) and s[i + 1].isdigit():
            char = s[i]; count, i = _parse_count(s, i + 1)
            if decompressed_index + count > index: return char
            decompressed_index += count
        else:
            if decompressed_index == index: return s[i]
            decompressed_index += 1; i += 1
    raise IndexError("Index out of range")

def set_char_at(s: str, index: int, new_char: str) -> str:
    """Set a character at a specific index and return the compressed string.
    Args:
        s: The compressed string
        index: The index in the decompressed string
        new_char: The new character to set
    Returns:
        The updated compressed string
    Raises:
        ValueError: If new_char is not a single character string
        IndexError: If the index is out of range
    """
    if not isinstance(new_char, str) or len(new_char) != 1:
        logger.error(f"Invalid new_char: {new_char}")
        raise ValueError("new_char must be a single character")
    decompressed = decompress(s)  # This will use the cached decompress
    if index >= len(decompressed): raise IndexError("Index out of range")
    decompressed = decompressed[:index] + new_char + decompressed[index + 1:]
    return compress(decompressed)

# --- Grid Validation ---
# <<< *** MODIFIED SORTING *** >>>
@cached("grid_validation", # Caching needs careful review if inputs change frequently or if side effects (logging) matter
       key_func=lambda grid, keys: f"validate_grid:{hash(str(sorted(grid.items())))}:{':'.join(sort_key_strings_hierarchically(keys))}") # Use hierarchical sort for keys part
def validate_grid(grid: Dict[str, str], sorted_keys_list: List[str]) -> bool:
    """
    Validate a dependency grid for consistency with keys.
    Uses standard sorting for key strings. Provides detailed logging.

    Args:
        grid: Dictionary mapping keys to compressed dependency strings
        sorted_keys_list: Pre-sorted list of keys expected in the grid.
    Returns:
        True if valid, False otherwise
    """
    if not isinstance(grid, dict): logger.error("Grid validation failed: 'grid' not a dict."); return False
    if not isinstance(sorted_keys_list, list): logger.error("Grid validation failed: 'sorted_keys_list' not a list."); return False

    # <<< *** REMOVE REDUNDANT SORT *** >>>
    # try:
    #     # Ensure we work with a sorted list internally using standard sort
    #     # sorted_keys_list = sorted(keys) # No! Assume input is sorted.
    #     pass # Keep the variable name consistent
    # except Exception as e:
    #     logger.error(f"Grid validation failed: Error processing keys - {e}"); return False

    num_keys = len(sorted_keys_list)
    if num_keys == 0 and not grid: return True # Empty grid and keys is valid
    if num_keys == 0 and grid: logger.error("Grid validation failed: Grid not empty but keys list is."); return False

    expected_keys_set = set(sorted_keys_list)
    actual_grid_keys_set = set(grid.keys())

    # 1. Check row keys match expected keys
    missing_rows = expected_keys_set - actual_grid_keys_set
    extra_rows = actual_grid_keys_set - expected_keys_set
    if missing_rows: logger.error(f"Grid validation failed: Missing rows for keys: {sorted(list(missing_rows))}"); return False
    if extra_rows: logger.error(f"Grid validation failed: Extra rows found for keys: {sorted(list(extra_rows))}"); return False

    # 2. Check row lengths and diagonal character
    for idx, key in enumerate(sorted_keys_list):
        compressed_row = grid.get(key)
        if compressed_row is None: logger.error(f"Grid validation failed: Row missing for key '{key}'."); return False # Should have been caught

        try: decompressed = decompress(compressed_row)
        except Exception as e: logger.error(f"Grid validation failed: Error decompressing row '{key}': {e}"); return False

        if len(decompressed) != num_keys: logger.error(f"Grid validation failed: Row '{key}' length incorrect (Exp:{num_keys}, Got:{len(decompressed)})."); return False

        # <<< *** Check character at the current index 'idx' *** >>>
        if decompressed[idx] != DIAGONAL_CHAR:
            logger.error(f"Grid validation failed: Row for key '{key}' has incorrect diagonal character at index {idx} (Expected: '{DIAGONAL_CHAR}', Got: '{decompressed[idx]}'). Row: '{decompressed}'")
            return False

    logger.debug("Grid validation successful.")
    return True

# --- Grid Modification (No changes needed) ---
def add_dependency_to_grid(grid: Dict[str, str], source_key: str, target_key: str,
                            keys: List[str], dep_type: str = ">") -> Dict[str, str]:
    """
    Add a dependency between two keys in the grid.

    Args:
        grid: Dictionary mapping keys to compressed dependency strings
        source_key: Source key (row)
        target_key: Target key (column)
        keys: List of keys for index mapping
        dep_type: Dependency type character

    Returns:
        Updated grid
    """
    if source_key not in keys or target_key not in keys:
        raise ValueError(f"Keys {source_key} or {target_key} not in keys list")

    source_idx = keys.index(source_key)
    target_idx = keys.index(target_key)
    if source_idx == target_idx:
        # Diagonal elements ('o') cannot be changed directly.
        # Grid validation ensures they are 'o'.
        # This prevents accidental overwrites and maintains grid integrity.
        raise ValueError(f"Cannot directly modify diagonal element for key '{source_key}'. Self-dependency must be 'o'.")

    # Create a copy of the grid to avoid modifying the original
    new_grid = grid.copy()
    row = decompress(new_grid.get(source_key, PLACEHOLDER_CHAR * len(keys)))
    new_row = row[:target_idx] + dep_type + row[target_idx + 1:]
    new_grid[source_key] = compress(new_row)
    # Invalidate cached decompress for the modified row
    invalidate_dependent_entries('grid_decompress', f"decompress:{new_grid.get(source_key)}")
    # Invalidate cached grid validation.  Use new_grid!
    #invalidate_dependent_entries('tracker', _cache_key_for_grid('validate_grid', new_grid, keys))
    return new_grid

def remove_dependency_from_grid(grid: Dict[str, str], source_key: str, target_key: str,
                                keys: List[str]) -> Dict[str, str]:
    """
    Remove a dependency between two keys in the grid.

    Args:
        grid: Dictionary mapping keys to compressed dependency strings
        source_key: Source key (row)
        target_key: Target key (column)
        keys: List of keys for index mapping

    Returns:
        Updated grid
    """
    if source_key not in keys or target_key not in keys: raise ValueError(f"Keys {source_key} or {target_key} not in keys list")
    source_idx = keys.index(source_key); target_idx = keys.index(target_key)
    if source_idx == target_idx: return grid
    new_grid = grid.copy()
    row = decompress(new_grid.get(source_key, PLACEHOLDER_CHAR * len(keys)))  # Uses cached decompress
    new_row = row[:target_idx] + EMPTY_CHAR + row[target_idx + 1:]
    new_grid[source_key] = compress(new_row)
    invalidate_dependent_entries('grid_decompress', f"decompress:{new_grid[source_key]}")
    invalidate_dependent_entries('grid_validation', f"validate_grid:{hash(str(sorted(new_grid.items())))}:{':'.join(keys)}")
    return new_grid

# --- Dependency Retrieval ---
@cached("grid_dependencies",
        key_func=lambda grid, key, keys: f"grid_deps:{hash(str(sorted(grid.items())))}:{key}:{':'.join(sort_key_strings_hierarchically(keys))}") # Use hierarchical sort for keys part
def get_dependencies_from_grid(grid: Dict[str, str], key: str, keys: List[str]) -> Dict[str, List[str]]:
    """
    Get dependencies for a specific key, categorized by relationship type.

    Args:
        grid: Dictionary mapping keys to compressed dependency strings
        key: Key to get dependencies for
        keys: List of keys for index mapping (MUST be in canonical sort order)

    Returns:
        Dictionary mapping dependency characters ('<', '>', 'x', 'd', 's', 'S', 'p')
        to lists of related keys.
    """
    if key not in keys:
        raise ValueError(f"Key {key} not in keys list")
    results = defaultdict(set); key_idx = keys.index(key)
    defined_dep_chars = {'<', '>', 'x', 'd', 's', 'S'} # Characters indicating a defined relationship
    for i, other_key in enumerate(keys):
        if key == other_key: continue
        char_outgoing = EMPTY_CHAR; row_key_compressed = grid.get(key)
        if row_key_compressed:
            try: char_outgoing = get_char_at(row_key_compressed, i)
            except IndexError: pass # Ignore if index out of bounds for this row
        # Categorize based on characters (prioritize defined relationships over placeholders)
        # Note: Symmetric checks ('x', 'd', 's', 'S') list the other key if *either* direction shows the char.
        # Directional checks ('>', '<') only consider the specific direction.
        # Placeholders ('p') are only listed if neither direction has a defined relationship.
        if char_outgoing == 'x':
            results['x'].add(other_key)
        elif char_outgoing == 'd':
             results['d'].add(other_key)
        elif char_outgoing == 'S':
             results['S'].add(other_key)
        elif char_outgoing == 's':
             results['s'].add(other_key)
        # Directional check AFTER symmetric checks
        elif char_outgoing == '>':
             results['>'].add(other_key)
        elif char_outgoing == '<':
             results['<'].add(other_key)             
        # Placeholder check LAST - only if no defined relationship exists in EITHER direction
        elif char_outgoing not in defined_dep_chars:
             if char_outgoing == 'p':
                 results['p'].add(other_key)
    # Convert sets to lists for the final output
    return {k: list(v) for k, v in results.items()}

# --- Grid Formatting (No changes needed) ---
def format_grid_for_display(grid: Dict[str, str], keys: List[str]) -> str:
    """
    Format a grid for display.

    Args:
        grid: Dictionary mapping keys to compressed dependency strings
        keys: List of keys in the grid

    Returns:
        Formatted string representation of the grid
    """
    result = ["X " + " ".join(keys)]
    for key in keys:
        result.append(f"{key} = {grid.get(key, compress(PLACEHOLDER_CHAR * len(keys)))}")
    return "\n".join(result)

def clear_cache():
    """Clear all function caches via cache_manager."""
    clear_all_caches()

# EoF
