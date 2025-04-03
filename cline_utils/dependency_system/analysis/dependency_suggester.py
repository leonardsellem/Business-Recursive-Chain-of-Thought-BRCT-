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

def _identify_structural_dependencies(source_path: str, source_analysis: Dict[str, Any],
                                     key_map: Dict[str, str], project_root: str) -> List[Tuple[str, str]]:
    """
    Identifies dependencies based on AST analysis (calls, attribute access, inheritance).
    Returns list of tuples (dependency_key, dependency_character).
    """
    suggestions = []
    if not source_analysis: # Handle case where analysis might be None or empty
        return []

    imports_data = source_analysis.get("imports", []) # Raw import strings/modules
    calls = source_analysis.get("calls", [])
    attributes = source_analysis.get("attribute_accesses", [])
    inheritance = source_analysis.get("inheritance", [])
    source_dir = os.path.dirname(source_path)
    path_to_key = {v: k for k, v in key_map.items()} # For faster path lookup

    # --- Helper to build an import map using AST ---
    import_map_cache = {} # Cache import maps per source file
    def _build_import_map(current_source_path: str) -> Dict[str, str]:
        """ Parses a Python file and builds a map of imported names to their resolved module paths. """
        norm_source_path = normalize_path(current_source_path)
        if norm_source_path in import_map_cache:
            return import_map_cache[norm_source_path]

        local_import_map: Dict[str, str] = {} # name -> absolute_module_path
        try:
            with open(norm_source_path, 'r', encoding='utf-8') as f:
                content = f.read()
            tree = ast.parse(content, filename=norm_source_path)
            current_source_dir = os.path.dirname(norm_source_path)

            for node in ast.walk(tree):
                if isinstance(node, ast.Import):
                    for alias in node.names:
                        module_name = alias.name
                        imported_name = alias.asname or module_name # Use alias if present
                        # Resolve module_name to path(s)
                        possible_paths = _convert_python_import_to_paths(module_name, current_source_dir, project_root)
                        if possible_paths:
                             # Use the first resolved path (assuming it's the correct one)
                            local_import_map[imported_name] = normalize_path(possible_paths[0])

                elif isinstance(node, ast.ImportFrom):
                    module_name = node.module or "" # Can be None for relative imports like 'from . import foo'
                    level = node.level # For relative imports

                    # Construct the full base module name for resolution, handling relative imports
                    if level > 0:
                        # Relative import: Calculate base path based on level
                        # level=1: current_dir, level=2: parent, level=3: grandparent...
                        base_dir_for_relative = current_source_dir
                        for _ in range(level - 1):
                            base_dir_for_relative = os.path.dirname(base_dir_for_relative)

                        if module_name: # e.g., from ..utils import config
                            # Resolve module_name relative to the calculated base_dir_for_relative
                             full_module_name_for_path = module_name # Use the module name part directly for resolution
                        else: # e.g., from . import config -> module_name is None
                            full_module_name_for_path = "" # Base directory itself
                    else: # level == 0 (absolute import)
                        full_module_name_for_path = module_name

                    # Resolve the base module path using the context
                    # Pass the correct base directory for relative resolution if level > 0
                    resolve_from_dir = base_dir_for_relative if level > 0 else current_source_dir
                    possible_base_paths = _convert_python_import_to_paths(full_module_name_for_path, resolve_from_dir, project_root, is_from_import=True, relative_level=level)

                    if possible_base_paths:
                        resolved_base_path = normalize_path(possible_base_paths[0]) # Assume first is correct base module/package path

                        for alias in node.names:
                            original_name = alias.name
                            imported_name = alias.asname or original_name # Use alias if present

                            # Map the imported name (or alias) to the RESOLVED BASE MODULE PATH
                            local_import_map[imported_name] = resolved_base_path
                    # else: logger.warning(f"Could not resolve base path for ImportFrom: module='{module_name}', level={level} in {norm_source_path}")

        except Exception as e:
            logger.error(f"Error building import map for {norm_source_path}: {e}", exc_info=True)

        import_map_cache[norm_source_path] = local_import_map
        # logger.debug(f"Built import map for {norm_source_path}: {local_import_map}") # Optional: Debug logging
        return local_import_map

    # --- Build the import map for the current source file ---
    import_map = _build_import_map(source_path)

    # --- Updated helper to resolve potential source name to key using the import map ---
    resolved_cache = {} # Cache resolution results
    def _resolve_source_to_key(potential_source_name: Optional[str]) -> Optional[str]:
        """ Resolves a name (potentially dotted) to a module key using the pre-built import map. """
        if not potential_source_name:
            return None

        cache_key = (source_path, potential_source_name) # Cache per source file + name
        if cache_key in resolved_cache:
            return resolved_cache[cache_key]

        # Check the primary name part (e.g., 'os' in 'os.path.join', 'aliased_func' in 'aliased_func()')
        base_name = potential_source_name.split('.')[0]

        resolved_module_path = import_map.get(base_name)

        found_key = None
        if resolved_module_path:
            # Convert the resolved module path to its key
            found_key = path_to_key.get(resolved_module_path)
            # if not found_key:
            #      logger.debug(f"Resolved path '{resolved_module_path}' for '{base_name}' (from '{potential_source_name}' in {source_path}) not found in path_to_key map.")

        # Cache and return result (even if None)
        resolved_cache[cache_key] = found_key
        # logger.debug(f"Resolving '{potential_source_name}' in {source_path} -> base '{base_name}' -> path '{resolved_module_path}' -> key '{found_key}'") # Optional: Debug logging
        return found_key
    # --- End Updated Helper ---

    # Get source key once for logging
    source_key = get_key_from_path(source_path, key_map)

    # Process Calls
    for call in calls:
        # Resolve the object being called on (e.g., 'os' in 'os.path.join')
        target_key = _resolve_source_to_key(call.get("potential_source"))
        if target_key and target_key != source_key: # Avoid self-dependency via structure
            logger.debug(f"Suggesting {source_key} -> {target_key} (>) due to call: {call.get('target_name')}")
            suggestions.append((target_key, ">"))

    # Process Attribute Accesses
    for attr in attributes:
        # Resolve the object whose attribute is being accessed
        target_key = _resolve_source_to_key(attr.get("potential_source"))
        if target_key and target_key != source_key:
            logger.debug(f"Suggesting {source_key} -> {target_key} (>) due to attribute access: {attr.get('potential_source')}.{attr.get('target_name')}")
            suggestions.append((target_key, ">"))

    # Process Inheritance
    for inh in inheritance:
        # Resolve the module/file containing the base class
        target_key = _resolve_source_to_key(inh.get("potential_source"))
        if target_key and target_key != source_key:
            logger.debug(f"Suggesting {source_key} -> {target_key} (<) due to inheritance from: {inh.get('base_class_name')}")
            suggestions.append((target_key, "<")) # Inheritance implies Row depends on Column (<)

    return list(set(suggestions)) # Remove duplicates


def suggest_python_dependencies(file_path: str, key_map: Dict[str, str], project_root: str, file_analysis_results: Dict[str, Any], threshold: float) -> List[Tuple[str, str]]:
    """
    Suggest dependencies for a Python file using imports, structural analysis, and semantics.

    Args:
        file_path: Path to the Python file (normalized)
        key_map: Dictionary mapping keys to file paths
        project_root: Root directory of the project
        file_analysis_results: Pre-computed analysis results for files (expects normalized paths)
        threshold: Confidence threshold for *semantic* suggestions
    Returns:
        List of (dependency_key, character) tuples
    """
    # Ensure file_path key is normalized for lookup
    norm_file_path = normalize_path(file_path)
    analysis = file_analysis_results.get(norm_file_path)

    if analysis is None:
        logger.warning(f"No analysis results found for normalized path {norm_file_path}")
        return []
    if "error" in analysis or "skipped" in analysis:
        logger.info(f"Skipping dependency suggestion for {norm_file_path} due to analysis error/skip.")
        return []

    # 1. Explicit import dependency ('>')
    explicit_suggestions = []
    # Pass key_map down to the helper function
    explicit_deps_paths = _identify_python_dependencies(norm_file_path, analysis, file_analysis_results, project_root, key_map)
    for dep_path, dep_type in explicit_deps_paths: # dep_type should be '>'
        dep_key = get_key_from_path(dep_path, key_map) # dep_path is already normalized absolute
        if dep_key:
            source_key = get_key_from_path(norm_file_path, key_map)
            if source_key and dep_key != source_key: # Avoid self-imports
                logger.debug(f"Suggesting {source_key} -> {dep_key} ({dep_type}) due to explicit Python import.")
                explicit_suggestions.append((dep_key, dep_type))
        else:
            logger.debug(f"Could not find key for explicit python dependency path: {dep_path}")

    # 2. Structural dependency ('>' for calls/attributes, '<' for inheritance)
    structural_suggestions = _identify_structural_dependencies(norm_file_path, analysis, key_map, project_root)

    # 3. Semantic suggestions ('s' or 'S')
    semantic_suggestions = suggest_semantic_dependencies(norm_file_path, key_map, project_root)

    # 4. Combine: explicit/structural take precedence over semantic based on config priority
    all_suggestions = explicit_suggestions + structural_suggestions + semantic_suggestions
    return _combine_suggestions_with_char_priority(all_suggestions)

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
    norm_file_path = normalize_path(file_path) # Ensure normalization
    analysis = file_analysis_results.get(norm_file_path)
    if analysis is None:
        logger.warning(f"No analysis results found for {norm_file_path}")
        return []

    explicit_suggestions = []
    # Explicit import dependency ('>')
    # Pass key_map down to the helper function
    explicit_deps_paths = _identify_javascript_dependencies(norm_file_path, analysis, file_analysis_results, project_root, key_map)
    for dep_path, dep_type in explicit_deps_paths:
        dep_key = get_key_from_path(dep_path, key_map)
        if dep_key:
            source_key = get_key_from_path(norm_file_path, key_map)
            if source_key and dep_key != source_key: # Avoid self-imports
                logger.debug(f"Suggesting {source_key} -> {dep_key} ({dep_type}) due to JS/TS import.")
                explicit_suggestions.append((dep_key, dep_type))
        else:
            logger.debug(f"Could not find key for explicit js dependency path: {dep_path}")

    # Semantic suggestions ('s' or 'S')
    semantic_suggestions = suggest_semantic_dependencies(norm_file_path, key_map, project_root)

    # Combine explicit (>) and semantic (s/S)
    return _combine_suggestions_with_char_priority(explicit_suggestions + semantic_suggestions)

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
    norm_file_path = normalize_path(file_path) # Ensure normalization
    analysis = file_analysis_results.get(norm_file_path)
    if analysis is None:
        logger.warning(f"Analysis results are None for {norm_file_path}. Skipping suggestions.")
        return []
    if "error" in analysis:
        logger.warning(f"Analysis result contains error for {norm_file_path}: {analysis['error']}. Skipping suggestions.")
        return []

    explicit_suggestions = []
    # Explicit link dependency ('d')
    # Pass key_map down to the helper function
    explicit_deps_paths = _identify_markdown_dependencies(norm_file_path, analysis, file_analysis_results, project_root, key_map)
    for dep_path, dep_type in explicit_deps_paths: # dep_type should be 'd'
        dep_key = get_key_from_path(dep_path, key_map)
        if dep_key:
            source_key = get_key_from_path(norm_file_path, key_map)
            if source_key and dep_key != source_key: # Avoid self-links
                logger.debug(f"Suggesting {source_key} -> {dep_key} ({dep_type}) due to Markdown link.")
                explicit_suggestions.append((dep_key, dep_type))
        else:
            logger.debug(f"Could not find key for explicit MD dependency path: {dep_path}")

    # Semantic suggestions ('s' or 'S')
    semantic_suggestions = suggest_semantic_dependencies(norm_file_path, key_map, project_root)

    # Combine explicit ('d') and semantic ('s'/'S')
    return _combine_suggestions_with_char_priority(explicit_suggestions + semantic_suggestions)

def suggest_generic_dependencies(file_path: str, key_map: Dict[str, str], project_root: str, threshold: float) -> List[Tuple[str, str]]:
    """
    Suggest dependencies for a generic file (semantic 's'/'S' only).

    Args:
        file_path: Path to the file (normalized)
        key_map: Dictionary mapping keys to file paths
        project_root: Root directory of the project
        threshold: Confidence threshold for semantic suggestions (Note: threshold is currently read from config within suggest_semantic_dependencies)
    Returns:
        List of (dependency_key, character) tuples
    """
    norm_file_path = normalize_path(file_path) # Ensure normalization
    # Semantic suggestions ('s' or 'S')
    semantic_suggestions = suggest_semantic_dependencies(norm_file_path, key_map, project_root)

    # Only semantic suggestions remain for generic
    return _combine_suggestions_with_char_priority(semantic_suggestions)


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
    file_key = path_to_key.get(file_path) # file_path is already normalized here
    if not file_key:
        logger.debug(f"No key found for file: {file_path}")
        return []

    suggested_dependencies = []
    keys_to_compare = [k for k in key_map.keys() if k != file_key]

    # Get necessary context for calculate_similarity
    code_roots = config.get_code_root_directories()
    doc_roots = config.get_doc_directories()
    try:
        # Local import to avoid potential top-level circular dependency
        from .embedding_manager import calculate_similarity
    except ImportError:
        logger.error("Could not import calculate_similarity from embedding_manager. Semantic suggestions disabled.")
        return []


    source_path = key_map.get(file_key) # Get original path for checks if needed

    for other_key in keys_to_compare:
        target_path = key_map.get(other_key)

        # Ensure both source and target are files before calculating similarity
        if not source_path or not target_path or os.path.isdir(source_path) or os.path.isdir(target_path):
            continue

        try:
            confidence = calculate_similarity(file_key, other_key, embeddings_dir, key_map, project_root, code_roots, doc_roots)
        except Exception as e:
             logger.warning(f"Error calculating similarity between {file_key} and {other_key}: {e}")
             confidence = 0.0 # Assume no similarity on error

        # --- Read thresholds from config ---
        threshold_S_strong = config.get_threshold("code_similarity")
        threshold_s_weak = config.get_threshold("doc_similarity")

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

        if assigned_char:
            suggested_dependencies.append((other_key, assigned_char))

    return suggested_dependencies

# --- Helper Functions ---

def _combine_suggestions_with_char_priority(suggestions: List[Tuple[str, str]]) -> List[Tuple[str, str]]:
    """
    Combine suggestions for the same target key, prioritizing based on character type.
    Priority order (highest first): '<', '>', 'x', 'd', 'S', 's', 'p'
    Handles merging '<' and '>' into 'x'.
    """
    combined: Dict[str, str] = {}
    config = ConfigManager()
    get_priority = config.get_char_priority

    for key, char in suggestions:
        if not key: continue # Skip if target key is somehow invalid

        current_char = combined.get(key)
        current_priority = get_priority(current_char) if current_char else -1
        new_priority = get_priority(char)

        if new_priority > current_priority:
            # New char has higher priority, overwrite
            logger.debug(f"Combining suggestions for target {key}: Choosing '{char}' (prio {new_priority}) over '{current_char}' (prio {current_priority}).")
            combined[key] = char
        elif new_priority == current_priority and char != current_char and current_char is not None:
            # Equal priority, but different characters
            if {char, current_char} == {'<', '>'}:
                # Specific rule: < and > merge to x
                if combined.get(key) != 'x': # Avoid redundant logs/updates
                    logger.debug(f"Combining suggestions for target {key}: Conflict between '<' and '>'. Setting to 'x'.")
                    combined[key] = 'x'
            else:
                # Keep the existing character for other equal priority conflicts (arbitrary, but consistent)
                logger.debug(f"Combining suggestions for target {key}: Equal priority conflict between '{char}' and '{current_char}'. Keeping existing '{current_char}'.")
        # else: Lower priority or same character, do nothing

    # Return as list of tuples
    return list(combined.items())


# --- Dependency Identification Helpers (Ensure they return Tuple[str, str]) ---

# Deprecated - Logic moved into language-specific suggest_* functions.
# def _identify_dependencies(source_path: str, source_analysis: Dict[str, Any],
#                           file_analyses: Dict[str, Dict[str, Any]],
#                           project_root: str) -> List[Tuple[str, str]]: ...

def _identify_python_dependencies(source_path: str, source_analysis: Dict[str, Any],
                                 file_analysis_results: Dict[str, Dict[str, Any]], # Expects absolute paths as keys
                                 project_root: str,
                                 key_map: Dict[str, str]) -> List[Tuple[str, str]]: # <<< Added key_map
    """
    Identifies Python import dependencies. Returns (abs_path, '>').
    Uses 'imports' list from analysis results.
    """
    dependencies = []
    imports = source_analysis.get("imports", [])
    source_dir = os.path.dirname(source_path)
    norm_file_analysis_keys = {normalize_path(k) for k in file_analysis_results.keys()} # Use a set for faster lookup

    for import_name_or_path in imports:
         possible_paths_abs = _convert_python_import_to_paths(import_name_or_path, source_dir, project_root)

         found = False
         for path_abs in possible_paths_abs:
             norm_path_abs = normalize_path(path_abs)
             if norm_path_abs in norm_file_analysis_keys:
                 dependencies.append((norm_path_abs, ">"))
                 found = True
                 break
         # if not found: logger.debug(f"Could not resolve Python import '{import_name_or_path}' in {source_path} to a tracked file.")
    return list(set(dependencies))


def _convert_python_import_to_paths(import_name: str, source_dir: str, project_root: str, is_from_import: bool = False, relative_level: int = 0) -> List[str]:
    """
    Converts a Python import statement/module name to potential absolute file paths.
    Handles relative imports based on level.
    """
    potential_paths_abs = []
    normalized_project_root = normalize_path(project_root)
    normalized_source_dir = normalize_path(source_dir)

    # --- Handle Relative Imports ---
    if relative_level > 0:
        relative_module_part = import_name # Assume import_name is the module part after dots
        level = relative_level
        current_dir = normalized_source_dir
        for _ in range(level - 1):
            parent_dir = os.path.dirname(current_dir)
            if not parent_dir or parent_dir == current_dir or not parent_dir.startswith(normalized_project_root):
                 current_dir = None
                 break
            current_dir = parent_dir

        if current_dir:
            if relative_module_part:
                module_path_part = relative_module_part.replace('.', os.sep)
                base_path = normalize_path(os.path.join(current_dir, module_path_part))
                potential_paths_abs.append(f"{base_path}.py")
                potential_paths_abs.append(normalize_path(os.path.join(base_path, "__init__.py")))
            else:
                 potential_paths_abs.append(normalize_path(os.path.join(current_dir, "__init__.py")))

    # --- Handle Absolute Imports ---
    elif relative_level == 0 and import_name and not import_name.startswith('.'):
        module_path_part = import_name.replace('.', os.sep)
        # Check relative to project root(s) - consider multiple source roots if necessary?
        # For now, assume single project_root acts as the main source root.
        # TODO: Potentially check against all configured code_roots?
        base_path_in_proj = normalize_path(os.path.join(normalized_project_root, module_path_part))
        potential_paths_abs.append(f"{base_path_in_proj}.py")
        potential_paths_abs.append(normalize_path(os.path.join(base_path_in_proj, "__init__.py")))

        # Consider site-packages (filtered later)
        try:
             spec = importlib.util.find_spec(import_name)
             if spec and spec.origin and spec.origin not in ('namespace', 'built-in', None):
                  origin_path = normalize_path(spec.origin)
                  # If it's a package (__init__.py), keep it. If it's a module (.py), keep it.
                  if origin_path.endswith("__init__.py") or origin_path.endswith(".py"):
                       potential_paths_abs.append(origin_path)
                  # If the origin points to a directory (e.g., namespace package), we might need __init__.py
                  elif os.path.isdir(origin_path):
                       potential_paths_abs.append(normalize_path(os.path.join(origin_path, "__init__.py")))
        except (ImportError, ValueError, ModuleNotFoundError, AttributeError):
             # Module not found externally or other import issue, rely on project paths
             pass

    # --- Filter based on project boundaries ---
    final_paths = []
    for p_abs in potential_paths_abs:
        # Check if the potential path exists and is inside the project root
        # We also want to include paths that might be external dependencies if they were resolved
        # But the dependency check later should only link project files.
        # Let's filter to only include paths within the project root for internal dependency tracking.
        if p_abs.startswith(normalized_project_root): # and os.path.exists(p_abs): # Check existence? Might be slow.
            final_paths.append(p_abs)

    # logger.debug(f"Converted import '{import_name}' (level {relative_level}) in '{source_dir}' to potential paths: {final_paths}")
    return final_paths


def _identify_javascript_dependencies(source_path: str, source_analysis: Dict[str, Any],
                                    file_analyses: Dict[str, Dict[str, Any]], # Expects absolute paths as keys
                                    project_root: str,
                                    key_map: Dict[str, str]) -> List[Tuple[str, str]]: # <<< Added key_map
    """
    Identifies JS/TS import dependencies. Returns (abs_path, '>').
    Uses 'imports' list from analysis results.
    """
    dependencies = []
    imports = source_analysis.get("imports", []) # Should be list of strings like './utils', '../components/button'
    source_dir = os.path.dirname(source_path)
    js_extensions = ['.js', '.jsx', '.ts', '.tsx', '.mjs', '.cjs']
    norm_file_analysis_keys = {normalize_path(k) for k in file_analyses.keys()} # Use set

    for import_path_str in imports:
        # Basic check for relative/absolute paths within the project context
        # Skips external package imports (e.g., 'react', 'lodash') and URLs
        if not import_path_str or \
           not (import_path_str.startswith('.') or import_path_str.startswith('/')) or \
           import_path_str.startswith('http:') or import_path_str.startswith('https:'):
            # Could add more sophisticated checks for aliased paths (e.g., '@/') later if needed
            continue

        try:
            # Resolve the base path relative to the source file
            # Use the utility function `resolve_relative_path` (ensure it handles '/' prefix correctly relative to project root if needed)
            # For now, assume '/' is not used for project-root relative imports here.
            resolved_base = normalize_path(os.path.join(source_dir, import_path_str))

            possible_targets = []
            # 1. Check if the resolved path directly matches a file (including extension)
            # (Handled by checking variations below)

            # 2. Check variations: direct file match, adding extensions, index file in dir
            # If import has extension already:
            has_extension = any(import_path_str.lower().endswith(ext) for ext in js_extensions)
            if has_extension:
                possible_targets.append(resolved_base)
            else:
                 # Try adding extensions to the resolved base
                for ext in js_extensions:
                     possible_targets.append(f"{resolved_base}{ext}")
                 # Try index file within the directory pointed to by resolved_base
                for ext in js_extensions:
                     possible_targets.append(normalize_path(os.path.join(resolved_base, f"index{ext}")))

            # Check if any possible target exists in our tracked files
            found = False
            for target_path_abs in possible_targets:
                norm_target_path = normalize_path(target_path_abs)
                if norm_target_path in norm_file_analysis_keys:
                    dependencies.append((norm_target_path, ">")) # Assign '>'
                    found = True
                    break # Found the dependency
            # if not found: logger.debug(f"Could not resolve JS/TS import '{import_path_str}' in {source_path} to a tracked file. Tried: {possible_targets}")

        except Exception as e:
            logger.error(f"Error resolving JS import '{import_path_str}' in {source_path}: {e}")

    return list(set(dependencies))


def _identify_markdown_dependencies(source_path: str, source_analysis: Dict[str, Any],
                                  file_analyses: Dict[str, Dict[str, Any]], # Expects absolute paths as keys
                                  project_root: str,
                                  key_map: Dict[str, str]) -> List[Tuple[str, str]]: # <<< Added key_map
    """
    Identifies Markdown link dependencies. Returns (abs_path, 'd').
    Uses 'links' list from analysis results.
    """
    dependencies = []
    links = source_analysis.get("links", []) # Should be list of dicts like {"url": "...", "text": "..."}
    source_dir = os.path.dirname(source_path)
    norm_file_analysis_keys = {normalize_path(k) for k in file_analyses.keys()} # Use set

    for link in links:
        url = link.get("url", "")
        # Skip empty URLs, internal page anchors, and absolute web URLs
        if not url or url.startswith('#') or \
           ('://' in url) or (url.startswith('//')) or \
           (url.startswith('mailto:')) or (url.startswith('tel:')):
            continue

        try:
            # Resolve relative to source directory
            # Handle potential URL fragments and query parameters
            url_cleaned = url.split('#')[0].split('?')[0]
            if not url_cleaned: # If URL was just an anchor or query
                continue

            # Use os.path.join and normalize for robust path resolution
            resolved_path_abs = normalize_path(os.path.join(source_dir, url_cleaned))

            # Check if the resolved path (or variations like adding .md) exists in tracked files
            possible_targets = [resolved_path_abs]
            # If no extension, try adding common doc extensions
            if not os.path.splitext(resolved_path_abs)[1]:
                possible_targets.append(resolved_path_abs + ".md")
                possible_targets.append(resolved_path_abs + ".rst")
                # Also check for index file in directory
                possible_targets.append(normalize_path(os.path.join(resolved_path_abs, "index.md")))
                possible_targets.append(normalize_path(os.path.join(resolved_path_abs, "README.md")))


            found = False
            for target_path in possible_targets:
                 norm_target_path = normalize_path(target_path)
                 if norm_target_path in norm_file_analysis_keys:
                     # Check if the target is actually a file (links shouldn't point to directories conceptually here)
                     # We rely on file_analyses keys representing actual files tracked.
                     dependencies.append((norm_target_path, "d")) # Assign 'd'
                     found = True
                     break # Found the target
            # if not found: logger.debug(f"Could not resolve MD link '{url}' in {source_path} to a tracked file. Tried: {possible_targets}")

        except Exception as e:
             logger.error(f"Error resolving MD link '{url}' in {source_path}: {e}")

    return list(set(dependencies))


def _identify_html_dependencies(source_path: str, source_analysis: Dict[str, Any],
                              file_analyses: Dict[str, Dict[str, Any]], # Expects absolute paths as keys
                              project_root: str,
                              key_map: Dict[str, str]) -> List[Tuple[str, str]]: # <<< Added key_map
    """
    Identifies HTML dependencies (links, scripts, styles). Returns various chars.
    Uses 'links', 'scripts', 'stylesheets', 'images' from analysis results.
    """
    dependencies = []
    links = source_analysis.get("links", []) # e.g., [{"href": "...", "rel": "..."}]
    scripts = source_analysis.get("scripts", []) # e.g., [{"src": "..."}]
    stylesheets = source_analysis.get("stylesheets", []) # e.g., [{"href": "..."}]
    images = source_analysis.get("images", []) # e.g., [{"src": "..."}]
    source_dir = os.path.dirname(source_path)
    norm_file_analysis_keys = {normalize_path(k) for k in file_analyses.keys()} # Use set

    urls_to_check = []
    # Extract URLs, noting the type of resource if possible
    for link in links: urls_to_check.append((link.get("href"), "link"))
    for script in scripts: urls_to_check.append((script.get("src"), "script"))
    for style in stylesheets: urls_to_check.append((style.get("href"), "style"))
    for img in images: urls_to_check.append((img.get("src"), "image"))


    for url, resource_type in urls_to_check:
        # Skip empty, anchors, web URLs etc.
        if not url or url.startswith('#') or \
           ('://' in url) or (url.startswith('//')) or \
           (url.startswith('mailto:')) or (url.startswith('tel:')) or \
           url.startswith('data:'):
             continue

        try:
            url_cleaned = url.split('#')[0].split('?')[0]
            if not url_cleaned: continue

            resolved_path_abs = normalize_path(os.path.join(source_dir, url_cleaned))
            norm_resolved_path = normalize_path(resolved_path_abs) # Use normalized version for checks

            # Check if the resolved path exists directly in tracked files
            if norm_resolved_path in norm_file_analysis_keys:
                 dep_type = ">"; reason = f"HTML {resource_type} resource"
                 target_ext = os.path.splitext(norm_resolved_path)[1].lower()

                 if resource_type == "style" or target_ext == '.css':
                     dep_type = 'd'; reason = "HTML stylesheet link"
                 elif resource_type == "script" or target_ext in ['.js', '.ts', '.mjs']:
                     dep_type = '>'; reason = "HTML script link"
                 elif resource_type == "link" and target_ext in ['.html', '.htm']:
                     dep_type = 'd'; reason = "HTML link to another HTML doc"
                 elif resource_type == "link" and target_ext in ['.md', '.rst']:
                      dep_type = 'd'; reason = "HTML link to documentation"
                 # Add more specific types if needed (e.g., for images)

                 src_key = get_key_from_path(source_path, key_map) # Use global key_map here
                 tgt_key = get_key_from_path(norm_resolved_path, key_map)
                 if src_key and tgt_key and src_key != tgt_key: # Avoid self-ref
                    logger.debug(f"Suggesting {src_key} -> {tgt_key} ({dep_type}) due to {reason} ('{url}').")
                    dependencies.append((norm_resolved_path, dep_type))
                 else:
                    logger.warning(f"Could not map keys for HTML dependency: {source_path} -> {norm_resolved_path}")
            # else: logger.debug(f"Could not resolve HTML resource '{url}' in {source_path} to a tracked file. Tried: {norm_resolved_path}")

        except Exception as e:
             logger.error(f"Error resolving HTML resource '{url}' in {source_path}: {e}")

    return list(set(dependencies))

def _identify_css_dependencies(source_path: str, source_analysis: Dict[str, Any],
                             file_analyses: Dict[str, Dict[str, Any]], # Expects absolute paths as keys
                             project_root: str,
                             key_map: Dict[str, str]) -> List[Tuple[str, str]]: # <<< Added key_map
    """
    Identifies CSS @import dependencies. Returns (abs_path, '>').
    Uses 'imports' list from analysis results.
    """
    dependencies = []
    imports = source_analysis.get("imports", []) # Should be list of dicts e.g. {"url": "sheet.css"}
    source_dir = os.path.dirname(source_path)
    norm_file_analysis_keys = {normalize_path(k) for k in file_analyses.keys()} # Use set

    for import_item in imports:
        url = import_item.get("url", "")
         # Skip empty, web URLs etc.
        if not url or url.startswith('#') or \
           ('://' in url) or (url.startswith('//')) or url.startswith('data:'):
             continue

        try:
            url_cleaned = url.split('#')[0].split('?')[0]
            if not url_cleaned: continue

            resolved_path_abs = normalize_path(os.path.join(source_dir, url_cleaned))
            norm_resolved_path = normalize_path(resolved_path_abs)

            # Check if the resolved path exists directly in tracked files
            if norm_resolved_path in norm_file_analysis_keys:
                 src_key = get_key_from_path(source_path, key_map) # Use global key_map
                 tgt_key = get_key_from_path(norm_resolved_path, key_map)
                 if src_key and tgt_key and src_key != tgt_key: # Avoid self-ref
                     logger.debug(f"Suggesting {src_key} -> {tgt_key} (>) due to CSS @import ('{url}').")
                     dependencies.append((norm_resolved_path, ">")) # Assign '>'
                 else:
                    logger.warning(f"Could not map keys for CSS dependency: {source_path} -> {norm_resolved_path}")
            # else: logger.debug(f"Could not resolve CSS import '{url}' in {source_path} to a tracked file. Tried: {norm_resolved_path}")

        except Exception as e:
             logger.error(f"Error resolving CSS import '{url}' in {source_path}: {e}")

    return list(set(dependencies))

# --- Other Helpers ---

def extract_function_calls(source_content: str, source_type: str) -> List[str]:
    """Extracts function calls from source code. (Mainly for potential future use)"""
    function_calls = []
    if source_type == "py":
        try:
            tree = ast.parse(source_content)
            for node in ast.walk(tree):
                if isinstance(node, ast.Call):
                    func = node.func
                    call_name = None
                    # Extract names from simple calls (name()) and attribute calls (obj.name())
                    if isinstance(func, ast.Name):
                         call_name = func.id
                    elif isinstance(func, ast.Attribute):
                         # Could try to resolve func.value here to get the object type if needed
                         call_name = func.attr # Just get the attribute name being called
                    # Add more complex cases like calls on subscript results etc. if needed
                    if call_name:
                        function_calls.append(call_name)
        except SyntaxError:
            logger.warning("Syntax error extracting Python function calls")
    elif source_type == "js":
        # Regex-based extraction for JS (can be less precise than AST)
        # Matches function calls like func(), obj.func(), possibly new Class()
        # Avoids matching keywords like if(), for(), while() etc.
        func_call_pattern = re.compile(r'(?:[a-zA-Z0-9_$]\s*\.\s*)?([a-zA-Z_$][\w$]*)\s*\(')
        matches = func_call_pattern.findall(source_content)
        # Common JS keywords that look like function calls but aren't (or aren't relevant here)
        keywords = {'if', 'for', 'while', 'switch', 'catch', 'function', 'return', 'typeof', 'instanceof', 'delete', 'void', 'super', 'this'}
        # Also filter constructor calls starting with uppercase? Might be too restrictive.
        function_calls = [match for match in matches if match not in keywords]

    return list(set(function_calls))


def suggest_initial_dependencies(key_map: Dict[str, str]) -> Dict[str, List[Tuple[str, str]]]:
    """DEPRECATED: Suggest initial dependencies. Grid initialization handles placeholders."""
    logger.warning("suggest_initial_dependencies is deprecated. Grid initialization handles this.")
    return defaultdict(list)

# End of file