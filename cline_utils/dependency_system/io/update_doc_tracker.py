"""
IO module for doc tracker specific data.
"""
from typing import Dict, Callable
from cline_utils.dependency_system.utils.config_manager import ConfigManager
from cline_utils.dependency_system.utils.path_utils import is_subpath, normalize_path, join_paths
import os

def doc_file_inclusion_logic(project_root: str, key_map: Dict[str, str]) -> Dict[str, str]:
    """Logic for determining which files to include in doc tracker."""
    config_manager = ConfigManager()
    doc_directories = config_manager.get_doc_directories()
    filtered_keys = {}
    for key, path in key_map.items():
        for doc_dir in doc_directories:
            # Normalize paths for comparison
            norm_path = normalize_path(path)
            norm_doc_dir = normalize_path(os.path.join(project_root, doc_dir))
            if is_subpath(norm_path, norm_doc_dir):
                filtered_keys[key] = path
                break
    return filtered_keys

def get_doc_tracker_path(project_root: str) -> str:
    """Gets the path to the doc tracker file."""
    config_manager = ConfigManager()
    memory_dir = join_paths(project_root, config_manager.get_path("memory_dir"))
    return join_paths(memory_dir, "doc_tracker.md")

# Data structure for doc tracker
doc_tracker_data = {
    "file_inclusion": doc_file_inclusion_logic,
    "get_tracker_path": get_doc_tracker_path
}
