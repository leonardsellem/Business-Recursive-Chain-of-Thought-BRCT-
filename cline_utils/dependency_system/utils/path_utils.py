"""
Core module for path utilities.
Handles path normalization, validation, and comparison.
"""

import os
import re
from typing import List, Optional, Set, Union, Tuple

HIERARCHICAL_KEY_PATTERN = r'^\d+[A-Z][a-z0-9]*$'
KEY_PATTERN = r'\d+|\D+'

def normalize_path(path: str) -> str:
    """
    Normalize a file path for consistent comparison.

    Args:
        path: Path to normalize

    Returns:
        Normalized path
    """
    from cline_utils.dependency_system.utils.cache_manager import cached

    # @cached("path_normalization",
    #        key_func=lambda p: f"normalize:{p if p else 'empty'}")
    def _normalize_path(p: str) -> str:
        if not p:
            return ""
        if not os.path.isabs(p):
            p = os.path.abspath(p)
        normalized = os.path.normpath(p).replace("\\", "/") # Normalize and replace backslashes with forward slashes
        if os.name == 'nt':
            normalized = normalized.lower()
        return normalized

    return _normalize_path(path)

def get_file_type(file_path: str) -> str:
    """
    Determines the file type based on its extension.

    Args:
        file_path: The path to the file.

    Returns:
        The file type as a string (e.g., "py", "js", "md", "generic").
    """
    from cline_utils.dependency_system.utils.cache_manager import cached

    # @cached("file_types",
    #        key_func=lambda fp: f"file_type:{normalize_path(fp)}")
    def _get_file_type(fp: str) -> str:
        _, ext = os.path.splitext(fp)
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

    return _get_file_type(file_path)

def resolve_relative_path(source_dir: str, relative_path: str, default_extension: str = '.js') -> str:
    """
    Resolve a relative import path to an absolute path based on the source directory.

    Args:
        source_dir: The directory of the source file (e.g., 'h:/path/to/project').
        relative_path: The relative import path (e.g., './module3' or '../utils/helper').
        default_extension: The file extension to append if none is present (default is '.js').

    Returns:
        The resolved absolute path (e.g., 'h:/path/to/project/module3.js').
    """
    # Combine the source directory and relative path, then normalize it
    resolved = os.path.normpath(os.path.join(source_dir, relative_path))

    # Append the default extension if no extension is present
    if not os.path.splitext(resolved)[1]:
        resolved += default_extension

    return resolved

def get_relative_path(path: str, base_path: str) -> str:
    """
    Get a path relative to a base path.

    Args:
        path: Path to convert
        base_path: Base path to make relative to

    Returns:
        Relative path
    """
    norm_path = normalize_path(path)
    norm_base = normalize_path(base_path)

    try:
        return os.path.relpath(norm_path, norm_base)
    except ValueError:
        # If paths are on different drives (Windows), return the normalized path
        return norm_path

def get_project_root() -> str:
    """
    Find the project root directory.

    Returns:
        Path to the project root directory
    """
    from cline_utils.dependency_system.utils.cache_manager import cached

    # @cached("project_root",
    #         key_func=lambda: f"project_root:{os.getcwd()}:{os.path.getmtime(os.getcwd())}")
    def _get_project_root() -> str:
        current_dir = os.path.abspath(os.getcwd())
        root_indicators = ['.git', '.clinerules', 'pyproject.toml', 'setup.py', 'package.json', 'Cargo.toml', 'CMakeLists.txt']
        while current_dir != os.path.dirname(current_dir):
            for indicator in root_indicators:
                if os.path.exists(os.path.join(current_dir, indicator)):
                    return current_dir
            current_dir = os.path.dirname(current_dir)
        return os.path.abspath(os.getcwd())

    return _get_project_root()

def join_paths(base_path: str, *paths: str) -> str:
    """
    Join paths and normalize the result.

    Args:
        base_path: Base path
        *paths: Additional path components

    Returns:
        Joined and normalized path
    """
    return normalize_path(os.path.join(base_path, *paths))

def is_path_excluded(path: str, excluded_paths: List[str]) -> bool:
    """
    Check if a path should be excluded based on a list of exclusion patterns.

    Args:
        path: Path to check
        excluded_paths: List of exclusion patterns

    Returns:
        True if the path should be excluded, False otherwise
    """
    if not excluded_paths:
        return False

    norm_path = normalize_path(path)
    for excluded in excluded_paths:
        # Handle glob patterns
        if '*' in excluded:
            pattern = excluded.replace('*', '.*')
            if re.search(pattern, norm_path):
                return True
        elif norm_path.startswith(normalize_path(excluded)) or norm_path == normalize_path(excluded):
            return True
    return False

def is_subpath(path: str, parent_path: str) -> bool:
    """
    Check if a path is a subpath of another path.

    Args:
        path: Path to check
        parent_path: Potential parent path

    Returns:
        True if path is a subpath of parent_path, False otherwise
    """
    norm_path = normalize_path(path)
    norm_parent = normalize_path(parent_path)

    # Check if the normalized path starts with the normalized parent path
    # and ensure it's a proper subpath (not just a string prefix)
    if norm_path.startswith(norm_parent):
        # If the parent path doesn't end with a separator, ensure the next character is a separator
        # After normalization, always use '/' as separator for comparison
        if not norm_parent.endswith('/'):
            # Ensure the next character in norm_path is a separator or it's the end of the string
            return len(norm_path) == len(norm_parent) or norm_path[len(norm_parent):].startswith('/')
        return True # If parent ends with '/', startswith is sufficient
    return False

def get_common_path(paths: List[str]) -> str:
    """
    Find the common path prefix for a list of paths.

    Args:
        paths: List of paths

    Returns:
        Common path prefix
    """
    if not paths:
        return ""

    # Normalize all paths
    norm_paths = [normalize_path(p) for p in paths]

    # Use os.path.commonpath
    try:
        return os.path.commonpath(norm_paths)
    except ValueError:
        # If paths are on different drives (Windows), return empty string
        return ""

def is_valid_project_path(path: str) -> bool:
    """
    Check if a path is within the project root directory.

    Args:
        path: Path to check

    Returns:
        True if the path is within the project root, False otherwise
    """
    from cline_utils.dependency_system.utils.cache_manager import cached

    # @cached("valid_project_paths",
    #        key_func=lambda p: f"valid_project_path:{normalize_path(p)}:{os.path.getmtime(get_project_root())}")
    def _is_valid_project_path(p: str) -> bool:
        project_root = get_project_root()
        return is_subpath(p, project_root)

    return _is_valid_project_path(path)