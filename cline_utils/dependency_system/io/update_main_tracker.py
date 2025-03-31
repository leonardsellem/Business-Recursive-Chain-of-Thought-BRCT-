"""
IO module for main tracker specific data.
"""
from typing import Dict, List, Optional, Set, Tuple
from cline_utils.dependency_system.core.key_manager import get_key_from_path
from cline_utils.dependency_system.utils.config_manager import ConfigManager
from cline_utils.dependency_system.utils.path_utils import is_subpath, normalize_path, join_paths
import os

def main_key_filter(project_root: str, key_map: Dict[str, str]) -> Dict[str, str]:
    """Logic for determining which keys to include in the main tracker."""
    """Logic for determining which keys to include in the main tracker (module relationships)."""
    config_manager: ConfigManager = ConfigManager()
    root_directories_rel: List[str] = config_manager.get_code_root_directories()
    filtered_keys: Dict[str, str] = {}
    abs_code_roots: Set[str] = {normalize_path(os.path.join(project_root, p)) for p in root_directories_rel}

    for key, path in key_map.items():
        norm_path: str = normalize_path(path)
        # Check if the path is a directory
        if os.path.isdir(norm_path):
            # Check if the directory is within any of the code roots
            if any(is_subpath(norm_path, root_dir) for root_dir in abs_code_roots):
                filtered_keys[key] = path

    return filtered_keys

def aggregate_dependencies(project_root: str, key_map: Dict[str,str], suggestions: Dict[str, List[Tuple[str, str]]], filtered_keys: Dict[str, str], file_to_module: Optional[Dict[str, str]] = None) -> Dict[str, List[Tuple[str, str]]]:
    """
    Aggregates file-level dependencies to folder-level dependencies for the main tracker.
    """
    aggregated_dependencies: Dict[str, List[Tuple[str, str]]] = {}

    for source_key, source_path in filtered_keys.items():
        aggregated_dependencies[source_key] = []
        # Iterate through all files in the key_map
        for file_key, file_path in key_map.items():
            # Check if the file is within the current source folder
            if is_subpath(normalize_path(file_path), normalize_path(source_path)):
                # If the file has dependencies recorded
                if file_key in suggestions:
                    # Iterate through the file's dependencies
                    for target_key, dep_type in suggestions[file_key]:
                        # Check if file_to_module is available and use it
                        if file_to_module:
                            target_module = file_to_module.get(key_map[target_key])
                            if target_module:
                                target_folder_key = get_key_from_path(target_module, key_map)
                                if target_folder_key and target_folder_key != source_key:
                                    aggregated_dependencies[source_key].append((target_folder_key, dep_type))

                        else:
                            # Iterate through the filtered keys (folders) to find the target folder
                            for folder_key, folder_path in filtered_keys.items():
                                # Check if the target file is within the current folder and it is not the source folder
                                if is_subpath(normalize_path(key_map[target_key]), normalize_path(folder_path)) and folder_key != source_key:
                                    # Add the folder-to-folder dependency
                                    aggregated_dependencies[source_key].append((folder_key, dep_type))
    return aggregated_dependencies

def get_main_tracker_path(project_root: str) -> str:
    """Gets the path to the main tracker file."""
    config_manager = ConfigManager()
    memory_dir = join_paths(project_root, config_manager.get_path("memory_dir"))
    return join_paths(memory_dir, "module_relationship_tracker.md")

# Data structure for main tracker
main_tracker_data = {
    "key_filter": main_key_filter,
    "dependency_aggregation": aggregate_dependencies,
    "get_tracker_path": get_main_tracker_path
}
