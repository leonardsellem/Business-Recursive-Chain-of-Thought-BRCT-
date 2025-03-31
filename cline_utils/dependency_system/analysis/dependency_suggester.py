# analysis/dependency_suggester.py

"""
Analysis module for dependency suggestion.
Suggests potential dependencies based on code analysis and embeddings.
Assigns specific characters based on the type of dependency found.
"""

from collections import defaultdict
import json
import re
import os
from typing import Dict, List, Tuple, Optional, Any
import importlib.util
import ast

# Import only from lower-level modules
from cline_utils.dependency_system.core.key_manager import get_key_from_path
from cline_utils.dependency_system.utils.path_utils import get_file_type, normalize_path, resolve_relative_path, is_subpath, get_project_root
from cline_utils.dependency_system.utils.config_manager import ConfigManager
from cline_utils.dependency_system.utils.cache_manager import cached, clear_all_caches
# NOTE: Avoid importing analyze_file here to prevent circular dependency if analyzer calls suggester
# from .dependency_analyzer import analyze_file, find_explicit_references

# Logger setup (assuming it's configured elsewhere)
import logging
logger = logging.getLogger(__name__)

# Character Definitions (from user feedback):
# <: Row depends on column.
# >: Column depends on row.
# x: Mutual dependency.
# d: Documentation dependency.
# o: Self dependency (diagonal only).
# n: Verified no dependency.
# p: Placeholder (unverified).
# s: Semantic dependency (weak .06-.07) - Adjusted based on .clinerules
# S: Semantic dependency (strong .07+) - Added based on .clinerules

# REMOVED: Hardcoded thresholds. Will read from ConfigManager.
# suggestion_threshold_s_weak = 0.6
# suggestion_threshold_S_strong = 0.7

def clear_caches():
    """Clear all internal caches."""
    clear_all_caches()

def load_metadata(metadata_path: str) -> Dict[str, Any]:
    """
    Load metadata file with caching.

    Args:
        metadata_path: Path to the metadata file
    Returns:
        Dictionary containing metadata or empty dict on failure
    """
    try:
        with open(metadata_path, 'r', encoding='utf-8') as f:
            metadata = json.load(f)
        return metadata
    except FileNotFoundError:
        logger.warning(f"Metadata file not found at {metadata_path}. Run generate-embeddings first.")
        return {}
    except json.JSONDecodeError as e:
        logger.error(f"Invalid JSON in metadata file {metadata_path}: {e}")
        return {}
    except Exception as e:
        logger.exception(f"Unexpected error reading metadata {metadata_path}: {e}")
        return {}

# Main dispatcher - now returns characters
def suggest_dependencies(file_path: str, key_map: Dict[str, str], project_root: str, file_analysis_results: Dict[str, Any], threshold: float = 0.7) -> List[Tuple[str, str]]:
    """
    Suggest dependencies for a file, assigning appropriate characters.

    Args:
        file_path: Path to the file to analyze
        key_map: Dictionary mapping keys to file paths
        project_root: Root directory of the project
        file_analysis_results: Pre-computed analysis results for files
        threshold: Confidence threshold for *semantic* suggestions (0.0 to 1.0)
    Returns:
        List of (dependency_key, dependency_character) tuples
    """
    if not os.path.exists(file_path):
        logger.warning(f"File not found: {file_path}")
        return []

    norm_path = normalize_path(file_path)
    file_ext = os.path.splitext(norm_path)[1].lower()

    # Pass file_analysis_results down
    if file_ext == '.py':
        return suggest_python_dependencies(norm_path, key_map, project_root, file_analysis_results, threshold)
    elif file_ext in ('.js', '.ts'):
        return suggest_javascript_dependencies(norm_path, key_map, project_root, file_analysis_results, threshold)
    elif file_ext in ('.md', '.rst'):
        # Assuming documentation relies on specific doc analysis and semantic
         # Need embeddings_dir and metadata_path if suggest_doc_dependencies is used
        config = ConfigManager()
        embeddings_dir_rel = config.get_path("embeddings_dir", "cline_utils/dependency_system/analysis/embeddings")
        embeddings_dir = normalize_path(os.path.join(project_root, embeddings_dir_rel))
        metadata_path = os.path.join(embeddings_dir, "metadata.json") # Assuming standard location
        return suggest_documentation_dependencies(norm_path, key_map, project_root, file_analysis_results, threshold, embeddings_dir, metadata_path)
    else:
        # Generic uses semantic only
        return suggest_generic_dependencies(norm_path, key_map, project_root, threshold)

# --- Tracker Type Specific Suggestion Logic (Adapted for character assignment) ---

# Note: suggest_main_dependencies logic seems different, more about aggregating module level.
# The current project_analyzer calls suggest_dependencies per file, so we focus on file-level suggestions first.
# If module-level aggregation is needed later, project_analyzer might handle it.

def suggest_python_dependencies(file_path: str, key_map: Dict[str, str], project_root: str, file_analysis_results: Dict[str, Any], threshold: float) -> List[Tuple[str, str]]:
    """
    Suggest dependencies for a Python file, assigning characters.

    Args:
        file_path: Path to the Python file (normalized)
        key_map: Dictionary mapping keys to file paths
        project_root: Root directory of the project
        file_analysis_results: Pre-computed analysis results for files
        threshold: Confidence threshold for *semantic* suggestions
    Returns:
        List of (dependency_key, character) tuples
    """
    analysis = file_analysis_results.get(file_path)
    if analysis is None:
        logger.warning(f"No analysis results found for {file_path}")
        return []

    explicit_suggestions = []
    # Explicit import dependency ('<', '>') - original logic used '>'
    explicit_deps_paths = _identify_python_dependencies(file_path, analysis, file_analysis_results, project_root)
    for dep_path, dep_type in explicit_deps_paths: # dep_type is likely '>' from _identify_python_dependencies
        dep_key = get_key_from_path(dep_path, key_map)
        if dep_key:
            logger.debug(f"Suggesting {get_key_from_path(file_path, key_map)} -> {dep_key} ({dep_type}) due to Python import.")
            explicit_suggestions.append((dep_key, dep_type)) # Use the type from identification
        else:
            logger.debug(f"Could not find key for explicit python dependency path: {dep_path}")

    # Semantic suggestions ('s' or 'S')
    semantic_suggestions = suggest_semantic_dependencies(file_path, key_map, project_root)

    # REMOVED: Directory dependencies ('x') - Added from original logic
    # directory_suggestions = suggest_directory_dependencies(file_path, key_map)
 
    # Combine: explicit takes precedence over semantic
    return _combine_suggestions_with_char_priority(explicit_suggestions + semantic_suggestions) # Removed directory_suggestions

def suggest_javascript_dependencies(file_path: str, key_map: Dict[str, str], project_root: str, file_analysis_results: Dict[str, Any], threshold: float) -> List[Tuple[str, str]]:
    """
    Suggest dependencies for a JavaScript/TypeScript file, assigning characters.

    Args:
        file_path: Path to the JS/TS file (normalized)
        key_map: Dictionary mapping keys to file paths
        project_root: Root directory of the project
        file_analysis_results: Pre-computed analysis results for files
        threshold: Confidence threshold for *semantic* suggestions
    Returns:
        List of (dependency_key, character) tuples
    """
    analysis = file_analysis_results.get(file_path)
    if analysis is None:
        logger.warning(f"No analysis results found for {file_path}")
        return []

    explicit_suggestions = []
    # Explicit import dependency ('>')
    explicit_deps_paths = _identify_javascript_dependencies(file_path, analysis, file_analysis_results, project_root)
    for dep_path, dep_type in explicit_deps_paths:
        dep_key = get_key_from_path(dep_path, key_map)
        if dep_key:
            logger.debug(f"Suggesting {get_key_from_path(file_path, key_map)} -> {dep_key} ({dep_type}) due to JS/TS import.")
            explicit_suggestions.append((dep_key, dep_type))
        else:
            logger.debug(f"Could not find key for explicit js dependency path: {dep_path}")

    # Semantic suggestions ('s' or 'S')
    semantic_suggestions = suggest_semantic_dependencies(file_path, key_map, project_root)

    # REMOVED: Directory dependencies ('x')
    # directory_suggestions = suggest_directory_dependencies(file_path, key_map)
 
    return _combine_suggestions_with_char_priority(explicit_suggestions + semantic_suggestions) # Removed directory_suggestions

def suggest_documentation_dependencies(file_path: str, key_map: Dict[str, str], project_root: str, file_analysis_results: Dict[str, Any], threshold: float, embeddings_dir: str, metadata_path: str) -> List[Tuple[str, str]]:
    """
    Suggest dependencies for a documentation file, assigning characters.

    Args:
        file_path: Path to the documentation file (normalized)
        key_map: Dictionary mapping keys to file paths
        project_root: Root directory of the project
        file_analysis_results: Pre-computed analysis results for files
        threshold: Confidence threshold for *semantic* suggestions
        embeddings_dir: Path to embeddings directory
        metadata_path: Path to metadata file
    Returns:
        List of (dependency_key, character) tuples
    """
    analysis = file_analysis_results.get(file_path)
    if analysis is None:
        logger.warning(f"Analysis results are None for {file_path}. Skipping suggestions.")
        return []
    if "error" in analysis:
        logger.warning(f"Analysis result contains error for {file_path}: {analysis['error']}. Skipping suggestions.")
        return []

    explicit_suggestions = []
    # Explicit link dependency ('d')
    explicit_deps_paths = _identify_markdown_dependencies(file_path, analysis, file_analysis_results, project_root)
    for dep_path, dep_type in explicit_deps_paths: # dep_type should be 'd'
        dep_key = get_key_from_path(dep_path, key_map)
        if dep_key:
            logger.debug(f"Suggesting {get_key_from_path(file_path, key_map)} -> {dep_key} ({dep_type}) due to Markdown link.")
            explicit_suggestions.append((dep_key, dep_type))
        else:
            logger.debug(f"Could not find key for explicit MD dependency path: {dep_path}")

    # Semantic suggestions ('s' or 'S')
    # Note: Previous logic incorrectly used 'x' for docs; now uses standard 's'/'S' based on thresholds.
    semantic_suggestions = suggest_semantic_dependencies(file_path, key_map, project_root)

    # REMOVED: Directory dependencies ('x')
    # directory_suggestions = suggest_directory_dependencies(file_path, key_map)
 
    # Combine explicit ('d') and semantic ('x') - Note: Semantic still uses 'x' for docs based on previous logic
    return _combine_suggestions_with_char_priority(explicit_suggestions + semantic_suggestions) # Removed directory_suggestions

def suggest_generic_dependencies(file_path: str, key_map: Dict[str, str], project_root: str, threshold: float) -> List[Tuple[str, str]]:
    """
    Suggest dependencies for a generic file (semantic 's' and directory 'x' only).

    Args:
        file_path: Path to the file (normalized)
        key_map: Dictionary mapping keys to file paths
        project_root: Root directory of the project
        threshold: Confidence threshold for semantic suggestions
    Returns:
        List of (dependency_key, character) tuples
    """
    # Semantic suggestions ('s' or 'S')
    semantic_suggestions = suggest_semantic_dependencies(file_path, key_map, project_root)
    # REMOVED: Directory dependencies ('x')
    # directory_suggestions = suggest_directory_dependencies(file_path, key_map)

    # Only semantic suggestions remain for generic
    return _combine_suggestions_with_char_priority(semantic_suggestions) # Removed directory_suggestions
 
# REMOVED FUNCTION: suggest_directory_dependencies
# def suggest_directory_dependencies(file_path: str, key_map: Dict[str, str]) -> List[Tuple[str, str]]:
#     """Suggests mutual 'x' dependency between a file and its parent directory."""
        # The reverse (parent -> file) will be handled when the parent is processed or aggregated
# REMOVED FUNCTION BODY
#     suggestions = []
#     path_to_key = {v: k for k, v in key_map.items()}
#     file_key = path_to_key.get(normalize_path(file_path))
#     if not file_key:
#         return []
#
#     parent_dir = os.path.dirname(normalize_path(file_path))
#     parent_key = path_to_key.get(parent_dir)
#
#     if parent_key and parent_key != file_key:
#         logger.debug(f"Suggesting {file_key} <-> {parent_key} (x) due to directory structure.")
#         suggestions.append((parent_key, "x"))
#         # The reverse (parent -> file) will be handled when the parent is processed or aggregated
#
#     return suggestions

# --- Semantic Suggestion (Uses 's'/'S' thresholds) ---

def suggest_semantic_dependencies(file_path: str, key_map: Dict[str, str], project_root: str) -> List[Tuple[str, str]]:
    """
    Suggest dependencies based on semantic similarity, assigning 's' or 'S' based on thresholds.

    Args:
        file_path: Path to the file (normalized)
        key_map: Dictionary mapping keys to file paths
        project_root: Root directory of the project
    Returns:
        List of (dependency_key, character) tuples ('s' or 'S') passing the respective thresholds.
    """
    config = ConfigManager()
    embeddings_dir_rel = config.get_path("embeddings_dir", "cline_utils/dependency_system/analysis/embeddings")
    embeddings_dir = normalize_path(os.path.join(project_root, embeddings_dir_rel))

    if not os.path.exists(embeddings_dir):
        logger.warning(f"Embeddings directory not found at {embeddings_dir}. Cannot perform semantic analysis. Please run embedding generation.")
        return []

    path_to_key = {normalize_path(path): key for key, path in key_map.items()}
    file_key = path_to_key.get(file_path)
    if not file_key:
        logger.debug(f"No key found for file: {file_path}")
        return []

    suggested_dependencies = []
    keys_to_compare = [k for k in key_map.keys() if k != file_key]

    # Get necessary context for calculate_similarity
    code_roots = config.get_code_root_directories()
    doc_roots = config.get_doc_directories()
    from .embedding_manager import calculate_similarity # Local import

    source_path = key_map.get(file_key)

    for other_key in keys_to_compare:
        target_path = key_map.get(other_key)

        if not source_path or not target_path or os.path.isdir(source_path) or os.path.isdir(target_path):
            continue

        confidence = calculate_similarity(file_key, other_key, embeddings_dir, key_map, project_root, code_roots, doc_roots)

        # --- Read thresholds from config ---
        # Use .get_threshold() which handles defaults if key is missing
        threshold_S_strong = config.get_threshold("code_similarity") # 'S' uses code_similarity (Default is 0.7 in config_manager)
        threshold_s_weak = config.get_threshold("doc_similarity")   # 's' uses doc_similarity (Default is 0.65 in config_manager)

        # --- Log raw confidence BEFORE thresholding ---
        logger.debug(f"Raw confidence {file_key} -> {other_key}: {confidence:.4f}") # Log raw score

        # Determine character based on config thresholds
        assigned_char = None
        if confidence >= threshold_S_strong:
            assigned_char = 'S'
            logger.debug(f"Suggesting {file_key} -> {other_key} ('S') due to strong semantic similarity (confidence: {confidence:.4f} >= {threshold_S_strong:.2f}).")
        elif confidence >= threshold_s_weak:
            assigned_char = 's'
            logger.debug(f"Suggesting {file_key} -> {other_key} ('s') due to weak semantic similarity (confidence: {confidence:.4f} >= {threshold_s_weak:.2f}).")
        # else: # Confidence below weak threshold, no suggestion generated
            # logger.debug(f"Confidence {confidence:.4f} for {file_key} -> {other_key} below weak threshold {threshold_s_weak:.2f}. No suggestion.")

        if assigned_char:
            suggested_dependencies.append((other_key, assigned_char))

    return suggested_dependencies

# --- Helper Functions ---

def _combine_suggestions_with_char_priority(suggestions: List[Tuple[str, str]]) -> List[Tuple[str, str]]:
    """
    Combine suggestions, prioritizing explicit and strong semantic characters.
    Priority: explicit ('>', '<', 'd', 'x'), strong semantic ('S') > weak semantic ('s')
    """
    combined: Dict[str, str] = {}
    # Define priority: Higher number = higher priority
    priority = {'<': 3, '>': 3, 'x': 3, 'd': 3, 'S': 3, 's': 2, '-': 1}

    for key, char in suggestions:
        if key:
            current_char = combined.get(key)
            current_priority = priority.get(current_char, 0)
            new_priority = priority.get(char, 0)

            if new_priority > current_priority:
                logger.debug(f"Combining suggestions for target {key}: Choosing '{char}' (prio {new_priority}) over '{current_char}' (prio {current_priority}).")
                combined[key] = char
            elif new_priority == current_priority and char != current_char:
                 # Handle conflict, e.g., log warning, maybe default to 'x'?
                 # For now, let's keep the first one encountered or make it 'x' if priorities are equal but chars differ
                 logger.debug(f"Combining suggestions for target {key}: Conflict between '{char}' and '{current_char}' (both prio {new_priority}). Setting to 'x'.")
                 if current_char != 'x': # Avoid logging if it's already 'x'
                     combined[key] = 'x' # Indicate potential mutual or conflicting signals
            # else: logger.debug(f"Combining suggestions for target {key}: Keeping '{current_char}' (prio {current_priority}) over '{char}' (prio {new_priority}).") # Optional: Log kept suggestions


    # Return as list of tuples, potentially sorted if needed, but order doesn't matter for grid update
    return list(combined.items())


# --- Dependency Identification Helpers (Mostly unchanged, ensure they return Tuple[str, str]) ---

def _identify_dependencies(source_path: str, source_analysis: Dict[str, Any],
                          file_analyses: Dict[str, Dict[str, Any]],
                          project_root: str) -> List[Tuple[str, str]]:
    """
    Identifies dependencies from a source file to other files in the project.
    Returns list of tuples (absolute_dependent_file_path, dependency_type_char).
    """
    dependencies = []
    file_type = source_analysis.get("file_type", "generic")

    abs_source_path = normalize_path(source_path)
    abs_project_root = normalize_path(project_root)
    abs_file_analyses = {normalize_path(k): v for k, v in file_analyses.items()}

    # Call language-specific identification functions which should return chars
    if file_type == "py":
        dependencies.extend(_identify_python_dependencies(abs_source_path, source_analysis, abs_file_analyses, abs_project_root))
    elif file_type == "js":
        dependencies.extend(_identify_javascript_dependencies(abs_source_path, source_analysis, abs_file_analyses, abs_project_root))
    elif file_type == "md":
        dependencies.extend(_identify_markdown_dependencies(abs_source_path, source_analysis, abs_file_analyses, abs_project_root))
    elif file_type == "html":
        dependencies.extend(_identify_html_dependencies(abs_source_path, source_analysis, abs_file_analyses, abs_project_root))
    elif file_type == "css":
        dependencies.extend(_identify_css_dependencies(abs_source_path, source_analysis, abs_file_analyses, abs_project_root))

    # Directory containment check ('x') - Simplified from original
    # This is now handled by suggest_directory_dependencies called separately

    return list(set(dependencies))


def _identify_python_dependencies(source_path: str, source_analysis: Dict[str, Any],
                                 file_analysis_results: Dict[str, Dict[str, Any]], # Expects absolute paths as keys
                                 project_root: str) -> List[Tuple[str, str]]:
    """
    Identifies Python import dependencies. Returns (abs_path, '>').
    """
    dependencies = []
    imports = source_analysis.get("imports", [])
    source_dir = os.path.dirname(source_path)

    for import_name in imports:
        possible_paths_abs = _convert_python_import_to_paths(import_name, source_dir, project_root)
        found = False
        for path_abs in possible_paths_abs:
            if path_abs in file_analysis_results:
                dependencies.append((path_abs, ">"))  # Assign '>' for explicit import
                found = True
                break
        # if not found: logger.debug(...) # Optional logging
    return dependencies

def _convert_python_import_to_paths(import_name: str, source_dir: str, project_root: str) -> List[str]:
    """
    Converts a Python import statement to potential absolute file paths. (Unchanged)
    """
    potential_paths_abs = []
    normalized_project_root = normalize_path(project_root)

    # --- Handle Relative Imports ---
    if import_name.startswith('.'):
        level = 0
        while level < len(import_name) and import_name[level] == '.': level += 1
        relative_module_part = import_name[level:] if level < len(import_name) else ""
        current_dir = source_dir
        for _ in range(level - 1):
            parent_dir = os.path.dirname(current_dir)
            if not parent_dir or parent_dir == current_dir or not parent_dir.startswith(normalized_project_root):
                 current_dir = None; break
            current_dir = parent_dir
        if current_dir:
            if relative_module_part:
                module_path_part = relative_module_part.replace('.', os.sep)
                potential_paths_abs.append(normalize_path(os.path.join(current_dir, f"{module_path_part}.py")))
                potential_paths_abs.append(normalize_path(os.path.join(current_dir, module_path_part, "__init__.py")))
            else:
                 potential_paths_abs.append(normalize_path(os.path.join(current_dir, "__init__.py")))
    # --- Handle Absolute Imports ---
    else:
        module_path_part = import_name.replace('.', os.sep)
        potential_paths_abs.append(normalize_path(os.path.join(normalized_project_root, f"{module_path_part}.py")))
        potential_paths_abs.append(normalize_path(os.path.join(normalized_project_root, module_path_part, "__init__.py")))

    # --- Filter based on project boundaries and external checks ---
    final_paths = []
    try:
        spec = importlib.util.find_spec(import_name)
        if spec and spec.origin and not normalize_path(spec.origin).startswith(normalized_project_root):
            return []
    except (ImportError, AttributeError, ValueError, ModuleNotFoundError):
        pass
    for p_abs in potential_paths_abs:
        if p_abs.startswith(normalized_project_root):
            final_paths.append(p_abs)
    return final_paths

def _identify_javascript_dependencies(source_path: str, source_analysis: Dict[str, Any],
                                    file_analyses: Dict[str, Dict[str, Any]],
                                    project_root: str) -> List[Tuple[str, str]]:
    """
    Identifies JS/TS import dependencies. Returns (abs_path, '>').
    """
    dependencies = []
    imports = source_analysis.get("imports", [])
    source_dir = os.path.dirname(source_path)
    js_extensions = ['.js', '.jsx', '.ts', '.tsx', '.mjs', '.cjs']

    for import_name in imports:
        if not (import_name.startswith('.') or import_name.startswith('/')) or \
           import_name.startswith('http:') or import_name.startswith('https:'):
            continue
        resolved_base_path = normalize_path(resolve_relative_path(source_dir, import_name, project_root))
        possible_targets = []
        if any(resolved_base_path.lower().endswith(ext) for ext in js_extensions):
            possible_targets.append(resolved_base_path)
        else:
            for ext in js_extensions: possible_targets.append(f"{resolved_base_path}{ext}")
            for ext in js_extensions: possible_targets.append(normalize_path(os.path.join(resolved_base_path, f"index{ext}")))
        found = False
        for possible_path_abs in possible_targets:
            if possible_path_abs in file_analyses:
                dependencies.append((possible_path_abs, ">")) # Assign '>'
                found = True; break
        # if not found: logger.debug(...)
    return dependencies

def _identify_markdown_dependencies(source_path: str, source_analysis: Dict[str, Any],
                                  file_analyses: Dict[str, Dict[str, Any]],
                                  project_root: str) -> List[Tuple[str, str]]:
    """
    Identifies Markdown link dependencies. Returns (abs_path, 'd').
    """
    dependencies = []
    links = source_analysis.get("links", [])
    source_dir = os.path.dirname(source_path)

    for link in links:
        url = link.get("url", "")
        if url.startswith('#') or ':' in url.split('/')[0] and ':\\' not in url.split('/')[0]:
            continue
        resolved_path_abs = normalize_path(resolve_relative_path(source_dir, url, project_root))
        cleaned_path_abs = resolved_path_abs.split('#')[0].split('?')[0]
        if cleaned_path_abs in file_analyses:
            dependencies.append((cleaned_path_abs, "d")) # Assign 'd'
    return dependencies

def _identify_html_dependencies(source_path: str, source_analysis: Dict[str, Any],
                              file_analyses: Dict[str, Dict[str, Any]],
                              project_root: str) -> List[Tuple[str, str]]:
    """
    Identifies HTML dependencies (links, scripts, styles). Returns various chars.
    """
    dependencies = []
    links = source_analysis.get("links", [])
    scripts = source_analysis.get("scripts", [])
    stylesheets = source_analysis.get("stylesheets", [])
    images = source_analysis.get("images", [])
    source_dir = os.path.dirname(source_path)

    urls_to_check = [link.get("url") for link in links] + \
                    [script.get("src") for script in scripts] + \
                    [style.get("href") for style in stylesheets] + \
                    [img.get("src") for img in images]

    for url in urls_to_check:
        if not url or url.startswith('#') or ':' in url.split('/')[0] and ':\\' not in url.split('/')[0]:
             continue
        resolved_path_abs = normalize_path(resolve_relative_path(source_dir, url, project_root))
        cleaned_path_abs = resolved_path_abs.split('#')[0].split('?')[0]

        if cleaned_path_abs in file_analyses:
             dep_type = ">" # Default reason
             reason = "HTML resource link"
             target_ext = os.path.splitext(cleaned_path_abs)[1].lower()
             if target_ext in ['.css']:
                 dep_type = 'd'; reason = "HTML stylesheet link"
             elif target_ext in ['.js', '.ts', '.mjs']:
                 dep_type = '>'; reason = "HTML script link"
             elif target_ext in ['.html']:
                 dep_type = 'd'; reason = "HTML link to another HTML doc" # Changed 'x' to 'd'
             # Images/other resources could be '>' or another char if needed
             logger.debug(f"Suggesting {get_key_from_path(source_path, file_analyses)} -> {get_key_from_path(cleaned_path_abs, file_analyses)} ({dep_type}) due to {reason}.")
             dependencies.append((cleaned_path_abs, dep_type))
    return dependencies

def _identify_css_dependencies(source_path: str, source_analysis: Dict[str, Any],
                             file_analyses: Dict[str, Dict[str, Any]],
                             project_root: str) -> List[Tuple[str, str]]:
    """
    Identifies CSS @import dependencies. Returns (abs_path, '>').
    """
    dependencies = []
    imports = source_analysis.get("imports", [])
    source_dir = os.path.dirname(source_path)

    for import_item in imports:
        url = import_item.get("url", "")
        if not url or ':' in url.split('/')[0] and ':\\' not in url.split('/')[0]:
             continue
        resolved_path_abs = normalize_path(resolve_relative_path(source_dir, url, project_root))
        cleaned_path_abs = resolved_path_abs.split('#')[0].split('?')[0]
        if cleaned_path_abs in file_analyses:
            dep_key = get_key_from_path(cleaned_path_abs, file_analyses)
            if dep_key:
                 logger.debug(f"Suggesting {get_key_from_path(source_path, file_analyses)} -> {dep_key} (>) due to CSS @import.")
                 dependencies.append((cleaned_path_abs, ">")) # Assign '>'
    return dependencies

# --- Other Helpers (Unchanged) ---

def extract_function_calls(source_content: str, source_type: str) -> List[str]:
    """Extracts function calls from source code."""
    # ... (implementation unchanged) ...
    function_calls = []

    if source_type == "py":
        try:
            tree = ast.parse(source_content)
            for node in ast.walk(tree):
                if isinstance(node, ast.Call):
                    func = node.func
                    call_name = None
                    if isinstance(func, ast.Name): call_name = func.id
                    elif isinstance(func, ast.Attribute): call_name = func.attr
                    if call_name: function_calls.append(call_name)
        except SyntaxError:
            logger.warning("Syntax error when extracting Python function calls")
    elif source_type == "js":
        func_call_pattern = re.compile(r'(?:\.\s*)?([a-zA-Z_$][\w$]*)\s*\(')
        matches = func_call_pattern.findall(source_content)
        keywords = {'if', 'for', 'while', 'switch', 'catch', 'function', 'return', 'typeof', 'new', 'delete', 'void'}
        function_calls = [match for match in matches if match not in keywords]
    return list(set(function_calls))


def suggest_initial_dependencies(key_map: Dict[str, str]) -> Dict[str, List[Tuple[str, str]]]:
    """Suggest initial 'x' dependencies between files and their parent directories."""
    # ... (implementation unchanged) ...
    suggestions: Dict[str, List[Tuple[str, str]]] = defaultdict(list)
    path_to_key = {v: k for k, v in key_map.items()}
    for key, path in key_map.items():
        parent_dir = os.path.dirname(path)
        parent_key = path_to_key.get(parent_dir)
        # Removed initial 'x' suggestion for parent-child directory relationships as per activeContext.md Next Step 1
        # if parent_key and parent_key != key:
        #     suggestions[key].append((parent_key, "x"))
        #     suggestions[parent_key].append((key, "x"))
    return suggestions

# End of file