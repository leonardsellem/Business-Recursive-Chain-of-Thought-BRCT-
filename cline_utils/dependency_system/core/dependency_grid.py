"""
Core module for dependency grid operations.
Handles grid creation, compression, decompression, and dependency management with key-centric design.
"""

import os
import re
from typing import Dict, List, Tuple, Optional

# Import only from utils
from cline_utils.dependency_system.utils.cache_manager import cached, invalidate_dependent_entries, clear_all_caches
from cline_utils.dependency_system.utils.config_manager import ConfigManager
from .key_manager import validate_key

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

#@cached("grid_decompress", key_func=lambda s: f"decompress:{s}")
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
            char = s[i]
            j = i + 1
            while j < len(s) and s[j].isdigit():
                j += 1
            count = int(s[i + 1:j])
            result += char * count
            i = j
        else:
            result += s[i]
            i += 1
    dependencies = [f"decompress:{s}"]
    return "".join(result)

# @cached("initial_grids",
#        key_func=lambda keys: f"initial_grid:{':'.join(keys)}")
def create_initial_grid(keys: List[str]) -> Dict[str, str]:
    """
    Create an initial dependency grid with placeholders and diagonal markers.

    Args:
        keys: List of valid keys to include in the grid
    Returns:
        Dictionary mapping keys to compressed dependency strings
    """
    if not keys or not all(isinstance(k, str) and validate_key(k) for k in keys):
        logger.error(f"Invalid keys provided: {keys}")
        raise ValueError("All keys must be valid non-empty strings")

    grid = {}
    for row_key in keys:
        diagonal_index = keys.index(row_key)
        if diagonal_index == 0:
            row = DIAGONAL_CHAR + PLACEHOLDER_CHAR * (len(keys) - 1)
        elif diagonal_index == len(keys) - 1:
            row = PLACEHOLDER_CHAR * (len(keys) - 1) + DIAGONAL_CHAR
        else:
            row = (PLACEHOLDER_CHAR * diagonal_index + DIAGONAL_CHAR +
                   PLACEHOLDER_CHAR * (len(keys) - diagonal_index - 1))
        grid[row_key] = compress(row)
    return grid

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
    while j < len(s) and s[j].isdigit():
        j += 1
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
            char = s[i]
            count, i = _parse_count(s, i + 1)
            if decompressed_index + count > index:
                return char
            decompressed_index += count
        else:
            if decompressed_index == index:
                return s[i]
            decompressed_index += 1
            i += 1
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
    if index >= len(decompressed):
        raise IndexError("Index out of range")

    decompressed = decompressed[:index] + new_char + decompressed[index + 1:]
    return compress(decompressed)

#@cached("grid_validation",
# Add near top of dependency_grid.py if not already present
# import logging # Assume logger is already initialized
from .key_manager import sort_keys # Ensure this import is present

# Ensure logger is initialized in the module
# logger = logging.getLogger(__name__) # Should already exist

#@cached("grid_validation", # Caching needs careful review if inputs change frequently or if side effects (logging) matter
#        key_func=lambda grid, keys: f"validate_grid:{hash(str(sorted(grid.items())))}:{':'.join(keys)}")
def validate_grid(grid: Dict[str, str], keys: List[str]) -> bool:
    """
    Validate a dependency grid for consistency with keys. Ensures keys are sorted
    using key_manager.sort_keys for diagonal check and provides detailed logging.
    Args:
        grid: Dictionary mapping keys to compressed dependency strings
        keys: List of keys expected in the grid (will be sorted internally)
    Returns:
        True if valid, False otherwise
    """
    if not isinstance(grid, dict):
        logger.error("Grid validation failed: 'grid' argument is not a dictionary.")
        return False
    if not isinstance(keys, list):
        logger.error("Grid validation failed: 'keys' argument is not a list.")
        return False

    try:
        # Ensure we work with a sorted list internally for index consistency
        sorted_keys_list = sort_keys(keys)
    except Exception as e:
        logger.error(f"Grid validation failed: Error sorting keys - {e}")
        return False

    num_keys = len(sorted_keys_list)

    # 1. Check if all expected keys are present as rows in the grid
    expected_keys_set = set(sorted_keys_list)
    actual_grid_keys_set = set(grid.keys())

    missing_rows = expected_keys_set - actual_grid_keys_set
    if missing_rows:
        logger.error(f"Grid validation failed: Missing grid rows for keys: {sorted(list(missing_rows))}")
        return False

    expected_length = len(keys)
    for key in keys:
        decompressed = decompress(grid.get(key, ''))  # This will use the cached decompress
        if len(decompressed) != expected_length:
            return False
        if decompressed[keys.index(key)] != DIAGONAL_CHAR:
            return False

    logger.debug("Grid validation successful.")
    return True

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
        return grid

    # Create a copy of the grid to avoid modifying the original
    new_grid = grid.copy()
    row = decompress(new_grid.get(source_key, PLACEHOLDER_CHAR * len(keys)))  # Uses cached decompress
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
    if source_key not in keys or target_key not in keys:
        raise ValueError(f"Keys {source_key} or {target_key} not in keys list")

    source_idx = keys.index(source_key)
    target_idx = keys.index(target_key)
    if source_idx == target_idx:
        return grid

    new_grid = grid.copy()
    row = decompress(new_grid.get(source_key, PLACEHOLDER_CHAR * len(keys)))  # Uses cached decompress
    new_row = row[:target_idx] + EMPTY_CHAR + row[target_idx + 1:]
    new_grid[source_key] = compress(new_row)

    invalidate_dependent_entries('grid_decompress', f"decompress:{new_grid[source_key]}")
    invalidate_dependent_entries('grid_validation', f"validate_grid:{hash(str(sorted(new_grid.items())))}:{':'.join(keys)}")
    return new_grid

from collections import defaultdict # <<< ADD IMPORT

# Remove caching for now as the return type and logic are changing significantly
# @cached("grid_dependencies", ...)
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

    results = defaultdict(set)
    key_idx = keys.index(key)
    defined_dep_chars = {'<', '>', 'x', 'd', 's', 'S'} # Characters indicating a defined relationship

    for i, other_key in enumerate(keys):
        if key == other_key:
            continue # Skip self

        # Determine the relationship character in both directions
        char_outgoing = EMPTY_CHAR # Default if row missing
        row_key_compressed = grid.get(key)
        if row_key_compressed:
            try:
                char_outgoing = get_char_at(row_key_compressed, i)
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