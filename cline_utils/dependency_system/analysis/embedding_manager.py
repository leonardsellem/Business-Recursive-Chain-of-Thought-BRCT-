"""
Module for managing embeddings generation and similarity calculations.
Handles embedding creation from project files and cosine similarity between embeddings.
"""
import sys
import torch
import os
import json
from typing import List, Dict, Optional, Tuple, Any
import numpy as np
import ast # <-- Import ast module

# Import only from lower-level modules
# Import get_project_root from path_utils
from cline_utils.dependency_system.utils.path_utils import is_subpath, normalize_path, is_valid_project_path, get_project_root
from cline_utils.dependency_system.utils.config_manager import ConfigManager
from cline_utils.dependency_system.utils.cache_manager import cached, invalidate_dependent_entries
from cline_utils.dependency_system.core.key_manager import generate_keys, validate_key
# from cline_utils.dependency_system.io.tracker_io import read_tracker_file, write_tracker_file # Not used directly here

import logging
logger = logging.getLogger(__name__)

# Default model configuration
DEFAULT_MODEL_NAME = "sentence-transformers/all-mpnet-base-v2"
MODEL_INSTANCE = None # Global variable to hold the loaded model
SELECTED_DEVICE = None # Global variable to hold the selected device

def _get_best_device() -> str:
    """Automatically determines the best available torch device."""
    # 1. Check CUDA
    if torch.cuda.is_available():
        logger.info("CUDA is available. Using CUDA.")
        return "cuda"
    # 2. Check MPS (Apple Silicon GPU) - Requires PyTorch 1.12+ and macOS 12.3+
    # Check if MPS is available and supported
    # Add platform check to avoid errors on non-macOS
    elif sys.platform == "darwin" and hasattr(torch.backends, "mps") and torch.backends.mps.is_available():
         # Check if MPS is built with PyTorch
        if torch.backends.mps.is_built():
             logger.info("Apple Silicon MPS is available. Using MPS.")
             return "mps"
        else:
            logger.warning("MPS available but not built with PyTorch installation. Falling back to CPU.")
            return "cpu"
    # 3. Default to CPU
    else:
        logger.info("CUDA and MPS not available. Using CPU.")
        return "cpu"

def _select_device() -> str:
    """Selects device based on config override or automatic detection."""
    global SELECTED_DEVICE
    if SELECTED_DEVICE is None:
        config_manager = ConfigManager()
        # Use .get() with default "auto" to handle missing key gracefully
        config_device = config_manager.config.get("compute", {}).get("embedding_device", "auto").lower()

        if config_device in ["cuda", "mps", "cpu"]:
            # Validate configured device choice
            if config_device == "cuda" and not torch.cuda.is_available():
                logger.warning(f"Config specified 'cuda', but CUDA is not available. Falling back to auto-detection.")
                SELECTED_DEVICE = _get_best_device()
            elif config_device == "mps" and not (sys.platform == "darwin" and hasattr(torch.backends, "mps") and torch.backends.mps.is_available() and torch.backends.mps.is_built()):
                 logger.warning(f"Config specified 'mps', but MPS is not available/built. Falling back to auto-detection.")
                 SELECTED_DEVICE = _get_best_device()
            else:
                logger.info(f"Using device specified in config: {config_device}")
                SELECTED_DEVICE = config_device
        elif config_device == "auto":
            logger.info("Device set to 'auto' in config, performing automatic detection.")
            SELECTED_DEVICE = _get_best_device()
        else:
            logger.warning(f"Invalid device '{config_device}' specified in config. Falling back to auto-detection.")
            SELECTED_DEVICE = _get_best_device()
    return SELECTED_DEVICE


def _load_model():
    """Loads the sentence transformer model if not already loaded, using the selected device."""
    global MODEL_INSTANCE
    if MODEL_INSTANCE is None:
        device = _select_device() # Determine the device to use
        try:
            from sentence_transformers import SentenceTransformer
            # Pass the selected device to the model constructor
            MODEL_INSTANCE = SentenceTransformer(DEFAULT_MODEL_NAME, device=device)
            logger.info(f"Loaded sentence transformer model: {DEFAULT_MODEL_NAME} on device: {device}")
        except ImportError as e:
            logger.error(f"Failed to import SentenceTransformer: {e}. Please install it (`pip install sentence-transformers`)")
            raise # Re-raise to indicate failure
        except Exception as e:
            # Catch potential errors during model loading with specific device
            logger.error(f"Failed to load model {DEFAULT_MODEL_NAME} on device {device}: {e}")
            raise # Re-raise to indicate failure
    return MODEL_INSTANCE

def _preprocess_content_for_embedding(file_path: str, content: str) -> str:
    """
    Preprocesses file content before embedding generation.
    Currently removes Python import lines.
    Future enhancements: Contextual weighting, comment/docstring handling.

    Args:
        file_path: The path to the file (used to determine file type).
        content: The original file content.

    Returns:
        The preprocessed content string.
    """
    # Simple check based on extension for now
    if file_path.lower().endswith(".py"):
        lines = content.splitlines()
        # 1. Remove import lines
        filtered_lines = [
            line for line in lines
            if not (line.strip().startswith("import ") or line.strip().startswith("from "))
        ]

        # 2. Extract and weight important definitions (AST)
        weighted_definitions = []
        try:
            tree = ast.parse(content)
            for node in ast.walk(tree):
                segment = None
                if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef)):
                    # Requires Python 3.8+ and source availability
                    segment = ast.get_source_segment(content, node)

                if segment:
                    # Append segment twice for weighting
                    weighted_definitions.append(segment)
                    weighted_definitions.append(segment)
        except SyntaxError:
            logger.warning(f"Syntax error in {file_path} during AST parsing for weighting. Proceeding without weighting.")
        except Exception as e:
            logger.error(f"Error during AST processing for weighting in {file_path}: {e}. Proceeding without weighting.")

        # 3. Combine filtered lines and weighted definitions
        final_content_list = filtered_lines + weighted_definitions
        return "\n".join(final_content_list)
    # TODO: Add preprocessing for other file types if needed (e.g., remove boilerplate HTML/JS?)
    return content # Return original content for non-Python files

#@cached("embeddings_generation",
#        key_func=lambda project_paths, force=False:
#        f"generate_embeddings:{':'.join(normalize_path(p) for p in project_paths)}:{force}:"
#        f"{os.path.getmtime(ConfigManager().config_path)}")
def generate_embeddings(project_paths: List[str], global_key_map: Dict[str, str], force: bool = False) -> bool: # Added global_key_map, changed return type
    """
    Generate embeddings for all files in the specified project paths. Iterates through each path.

    Args:
        project_paths: List of project directory paths (relative to project root)
        global_key_map: The single, consistent key map for the entire project.
        force: If True, regenerate embeddings even if they exist
    Returns:
        success: bool indicating overall success.
    """
    if not project_paths:
        logger.error("No project paths provided for embedding generation.")
        return False, {}

    # Ensure model is loaded
    try:
        model = _load_model()
    except Exception:
        return False, {} # Loading failed

    config_manager = ConfigManager()
    # Use get_project_root from path_utils, not config_manager
    project_root = get_project_root()
    embeddings_dir = config_manager.get_path("embeddings_dir", "cline_utils/dependency_system/analysis/embeddings") # Get path from config

    # Ensure embeddings_dir is absolute or relative to project root
    if not os.path.isabs(embeddings_dir):
        embeddings_dir = os.path.join(project_root, embeddings_dir)

    os.makedirs(embeddings_dir, exist_ok=True) # Ensure base embeddings dir exists

    # Removed: all_generated_keys = {} - Use passed-in global_key_map
    overall_success = True

    for relative_path in project_paths:
        # Validate and normalize the individual project path relative to project_root
        current_project_path = normalize_path(os.path.join(project_root, relative_path))
        if not is_valid_project_path(current_project_path):
             logger.error(f"Invalid project path skipped: {current_project_path}")
             overall_success = False
             continue

        project_name = os.path.basename(current_project_path) # Use the name of the actual dir being processed
        project_embeddings_dir = normalize_path(os.path.join(embeddings_dir, project_name))
        metadata_file = normalize_path(os.path.join(project_embeddings_dir, "metadata.json"))
        os.makedirs(project_embeddings_dir, exist_ok=True)
        logger.info(f"Processing embeddings for: {project_name} in {project_embeddings_dir}")

        existing_metadata = {}
        if not force and os.path.exists(metadata_file):
            try:
                with open(metadata_file, 'r', encoding='utf-8') as f:
                    existing_metadata = json.load(f)
                if existing_metadata.get("version") != "1.0":
                    logger.warning(f"Incompatible metadata version in {metadata_file} for {project_name}. Regenerating.")
                    existing_metadata = {}
            except (json.JSONDecodeError, KeyError, FileNotFoundError) as e:
                logger.warning(f"Corrupted or missing metadata file {metadata_file} for {project_name}: {e}. Regenerating.")
                existing_metadata = {}

        # Filter the global_key_map to get keys relevant to the current path
        keys_for_current_path = {
            k: p for k, p in global_key_map.items()
            if is_subpath(normalize_path(p), current_project_path)
        }

        if not keys_for_current_path:
            logger.warning(f"No keys from global map found within path: {current_project_path}")
            continue # Move to the next project path

        file_contents = {}
        for key, file_path in keys_for_current_path.items(): # Use filtered map
            # Ensure file_path is absolute for reading
            abs_file_path = normalize_path(file_path) # Keys should already store absolute paths from generate_keys
            # Explicitly skip directories first
            if os.path.isdir(abs_file_path):
                logger.debug(f"Skipping directory: {abs_file_path}")
                continue

            # Check if it exists and is a file
            if not os.path.isfile(abs_file_path):
                 if not os.path.exists(abs_file_path):
                      logger.warning(f"File path from key_map does not exist or is not a file: {abs_file_path} for key {key}. Skipping.")
                 else: # Exists but is not a file (and not a directory based on above check) - e.g. broken symlink?
                      logger.warning(f"Path exists but is not a file: {abs_file_path} for key {key}. Skipping.")
                 continue # Skip non-files

            # Proceed only if it's confirmed to be a file
            try:
                # Check if file is potentially binary before reading all content
                is_binary = False
                with open(abs_file_path, 'rb') as f_check:
                    chunk = f_check.read(1024)
                    if b'\0' in chunk: # Simple check for null bytes
                        is_binary = True

                if is_binary:
                    logger.debug(f"Skipping likely binary file: {abs_file_path}")
                    continue

                with open(abs_file_path, 'r', encoding='utf-8') as f:
                    file_contents[key] = f.read()
            except UnicodeDecodeError:
                 logger.debug(f"Skipping non-UTF8 file: {abs_file_path}")
            except Exception as e:
                logger.warning(f"Failed to read {abs_file_path}: {e}")

        # Generate or load embeddings for the current project path
        current_embeddings = {}
        for key, file_path in keys_for_current_path.items(): # Use filtered map
            abs_file_path = normalize_path(file_path) # Use absolute path
            logger.debug(f"--- Processing embedding for key: {key}, path: {abs_file_path}") # DEBUG Line
            if not os.path.exists(abs_file_path):
                logger.debug(f"Skipping key {key} as file path {abs_file_path} does not exist.")
                continue

            # --- ADDED: Check if file is valid based on config exclusions ---
            if not _is_valid_file(abs_file_path):
                logger.debug(f"Skipping excluded or invalid file based on config: {abs_file_path}")
                continue
            # --- END ADDED ---

            # Check if embedding exists and is up-to-date
            should_generate = True
            if key in existing_metadata.get("keys", {}) and not force:
                # <<< Ensure path in metadata is normalized for comparison if needed, but focus on mtime first >>>
                # metadata_path_norm = normalize_path(existing_metadata["keys"][key].get("path", ""))

                # Path for the actual .npy file (using mirrored structure)
                try:
                    relative_file_path_for_npy = os.path.relpath(abs_file_path, project_root)
                    mirrored_npy_path = normalize_path(os.path.join(embeddings_dir, relative_file_path_for_npy) + ".npy")
                except ValueError:
                    logger.warning(f"Could not determine relative path for {abs_file_path} relative to {project_root}. Cannot check existing NPY.")
                    mirrored_npy_path = None # Indicate path couldn't be determined

                if mirrored_npy_path and os.path.exists(mirrored_npy_path): # Check if NPY file exists
                    try:
                        current_mtime = os.path.getmtime(abs_file_path)
                        metadata_mtime = existing_metadata["keys"][key].get("mtime")

                        # <<< ADD DEBUG LOGGING >>>
                        logger.debug(f"Checking mtime for {key} ({os.path.basename(abs_file_path)}):")
                        logger.debug(f"  Current file mtime: {current_mtime}")
                        logger.debug(f"  Metadata mtime:     {metadata_mtime}")

                        if metadata_mtime is not None and current_mtime == metadata_mtime:
                            # Try loading only if mtime matches and file exists
                            # No need to load here, just decide whether to generate
                            logger.debug(f"  MTime match. Skipping generation for {key}.")
                            should_generate = False # Don't generate if mtime matches
                        elif metadata_mtime is None:
                            logger.debug(f"  Metadata mtime missing. Will regenerate embedding for {key}.")
                        else:
                            logger.debug(f"  MTime mismatch ({current_mtime} != {metadata_mtime}). Will regenerate embedding for {key}.")
                         # <<< END DEBUG LOGGING >>>

                    except FileNotFoundError:
                         # This might happen if the source file was deleted between key generation and here
                         logger.warning(f"Source file {abs_file_path} not found when checking mtime. Skipping embedding generation.")
                         should_generate = False # Can't generate if source is gone
                    except Exception as e:
                        logger.warning(f"Failed to check mtime/metadata for {key} ({abs_file_path}): {e}. Will regenerate.")
                        should_generate = True # Regenerate on error
                else:
                     logger.debug(f"Embedding file not found at expected path {mirrored_npy_path} for key {key}. Will generate.")
                     should_generate = True
            elif force:
                 logger.info(f"Force flag set. Will regenerate embedding for key {key}.")
                 should_generate = True
            else: # Not in metadata keys OR force=False (first run or new file)
                 logger.debug(f"Key {key} not in existing metadata or metadata missing/corrupt. Will generate embedding.")
                 should_generate = True


            # Generate new or updated embedding if needed
            if should_generate:
                original_content = file_contents.get(key, "")
                # Preprocess content before encoding
                processed_content = _preprocess_content_for_embedding(abs_file_path, original_content)

                if processed_content.strip(): # Check if content remains after preprocessing
                    try:
                        logger.debug(f"Encoding preprocessed content for key: {key}...")
                        embedding = model.encode(processed_content, show_progress_bar=False, convert_to_numpy=True)
                        current_embeddings[key] = embedding
                        logger.debug(f"Encoding successful for key: {key}.")

                        # --- NEW: Save using mirrored directory structure ---
                        try:
                            # Get relative path from project root
                            relative_file_path = os.path.relpath(abs_file_path, project_root)
                            # Construct mirrored path under embeddings_dir (base embeddings dir)
                            mirrored_path_base = os.path.join(embeddings_dir, relative_file_path)
                            mirrored_dir = os.path.dirname(mirrored_path_base)
                            # Ensure the mirrored directory exists
                            os.makedirs(mirrored_dir, exist_ok=True)
                            # Final save path with .npy extension
                            save_path = mirrored_path_base + ".npy"
                            save_path = normalize_path(save_path) # Normalize the final path

                            logger.debug(f"Saving embedding for key: {key} to {save_path}...")
                            np.save(save_path, embedding)
                            logger.info(f"Generated and saved embedding for {key} to {save_path}")
                        except Exception as e:
                             logger.error(f"Failed create directory or save embedding for {key} ({abs_file_path}) at {save_path}: {e}")
                             overall_success = False # Mark failure if saving fails

                    except Exception as e: # Catch errors during encoding itself
                        logger.error(f"Failed to generate embedding for {key} ({abs_file_path}): {e}")
                        overall_success = False
                        # Continue to next file even if one fails
                else:
                    logger.debug(f"Skipping empty file content for key {key} ({abs_file_path})")


        # Save metadata for this specific project path
        valid_keys_in_metadata = {}
        for k, v_path in keys_for_current_path.items(): # Use filtered map
            # Only include keys for which we successfully generated OR loaded (based on should_generate=False)
            # We need to know which ones were skipped due to mtime match
            # Let's refine this: check if the key *exists* in the final set of embeddings for this run
            # OR if it was skipped because it was up-to-date

            # Check if the file corresponding to the key still exists before getting mtime
            abs_v_path = normalize_path(v_path) # Ensure absolute and normalized
            if not os.path.exists(abs_v_path):
                 logger.warning(f"File {abs_v_path} for key {k} no longer exists. Skipping metadata entry.")
                 continue

            # Check if we have an embedding (newly generated OR previously existing and loaded/checked)
            # A key should be in metadata if its source file exists and either:
            # 1. An embedding was successfully generated for it in this run (it's in current_embeddings)
            # 2. An existing embedding was found and deemed up-to-date (should_generate was False for this key)
            # Let's track the 'up-to-date' status per key during the loop.

            # --- Modification needed: Track which keys were skipped due to mtime ---
            # Add a set outside the inner loop: keys_skipped_mtime = set()
            # Inside the mtime check, if should_generate becomes False, add key to keys_skipped_mtime

            # --- Then, when creating valid_keys_in_metadata ---
            # if k in current_embeddings or k in keys_skipped_mtime: # Check if generated OR skipped(up-to-date)
            # ^^^ This requires adding the tracking set. Let's simplify for now:
            # If the key is in the original map for this project path AND the file exists:
            if k in keys_for_current_path: # Use filtered map
                 try:
                    # <<< Ensure path saved is normalized >>>
                    valid_keys_in_metadata[k] = {
                        "path": normalize_path(v_path), # Save normalized path
                        "mtime": os.path.getmtime(abs_v_path) # Use the absolute path here
                    }
                 except FileNotFoundError:
                     logger.warning(f"File {abs_v_path} for key {k} disappeared before metadata save. Skipping.")
                 except Exception as e:
                     logger.error(f"Error getting mtime for {abs_v_path} (key {k}): {e}. Skipping metadata entry.")

        if not valid_keys_in_metadata:
             logger.warning(f"No valid files processed for {project_name}. Skipping metadata save.")
        else:
            metadata = {
                "version": "1.0",
                "model": DEFAULT_MODEL_NAME,
                # Save only the valid keys determined above
                "keys": valid_keys_in_metadata
            }
            try:
                with open(metadata_file, 'w', encoding='utf-8') as f:
                    json.dump(metadata, f, indent=2)
                logger.info(f"Saved metadata for {project_name} to {metadata_file}")
            except Exception as e:
                logger.error(f"Failed to write metadata file {metadata_file}: {e}")
                overall_success = False

    # --- End of loop through project_paths ---

    if overall_success:
        logger.info(f"Completed embedding generation for paths: {project_paths}")
    else:
        logger.warning(f"Embedding generation completed with errors for paths: {project_paths}")

    return overall_success # Return only boolean status

# @cached("embedding_similarity",
#        key_func=lambda key1, key2, embeddings_dir:
#        f"similarity:{key1}:{key2}:{normalize_path(embeddings_dir)}:"
#        f"{os.path.getmtime(os.path.join(embeddings_dir, 'subdir', f'{key1}.npy')) if os.path.exists(os.path.join(embeddings_dir, 'subdir', f'{key1}.npy')) else 'missing'}:" # Adjusted for subdirs
#        f"{os.path.getmtime(os.path.join(embeddings_dir, 'subdir', f'{key2}.npy')) if os.path.exists(os.path.join(embeddings_dir, 'subdir', f'{key2}.npy')) else 'missing'}") # Adjusted for subdirs
def calculate_similarity(key1: str, key2: str, embeddings_dir: str, key_map: Dict[str, str], project_root: str, code_roots: List[str], doc_roots: List[str]) -> float:
    """
    Calculate cosine similarity between embeddings of two keys.

    Args:
        key1: First key
        key2: Second key
        embeddings_dir: Base directory containing embedding project subdirectories
        key_map: Dictionary mapping keys to file paths
        project_root: Root directory of the project
        code_roots: List of code root directories (relative to project_root)
        doc_roots: List of documentation root directories (relative to project_root)

    Returns:
        Cosine similarity score (0.0 to 1.0), or 0.0 on failure
    """
    # Validate key format first
    if not (validate_key(key1) and validate_key(key2)):
        logger.warning(f"Invalid key format for similarity calculation: {key1}, {key2}")
        return 0.0

    # Ensure keys exist in the current key_map before proceeding
    if key1 not in key_map or key2 not in key_map:
        logger.warning(f"Key(s) not found in key_map for similarity calculation: {key1 if key1 not in key_map else ''}{' and ' if key1 not in key_map and key2 not in key_map else ''}{key2 if key2 not in key_map else ''}")
        return 0.0

    if key1 == key2:
        return 1.0

    # Ensure embeddings_dir is absolute
    if not os.path.isabs(embeddings_dir):
        embeddings_dir = normalize_path(os.path.join(project_root, embeddings_dir))

    def get_embedding_path(key: str) -> Optional[str]:
        """Helper to find the correct .npy file path using the mirrored directory structure."""
        # Get the absolute path associated with the key
        abs_file_path = key_map.get(key)
        if not abs_file_path:
            logger.warning(f"Could not find file path for key {key} in key_map.")
            return None
        norm_abs_file_path = normalize_path(abs_file_path)
        norm_project_root = normalize_path(project_root)

        # Ensure the file path is actually within the project root
        if not norm_abs_file_path.startswith(norm_project_root):
             logger.warning(f"File path {norm_abs_file_path} for key {key} is outside project root {norm_project_root}.")
             return None

        try:
            # Calculate the relative path from the project root
            relative_file_path = os.path.relpath(norm_abs_file_path, norm_project_root)
        except ValueError as e:
            logger.error(f"Error calculating relative path for {norm_abs_file_path} from {norm_project_root}: {e}")
            return None

        # Construct the expected path in the mirrored structure under embeddings_dir
        # embeddings_dir is already absolute
        expected_npy_path = normalize_path(os.path.join(embeddings_dir, relative_file_path) + ".npy")
        # logger.debug(f"Constructed mirrored embedding path for key {key}: {expected_npy_path}")

        # Return the expected path (existence check happens later in calculate_similarity)
        return expected_npy_path

    file1_path = get_embedding_path(key1)
    file2_path = get_embedding_path(key2)

    if not file1_path or not file2_path or not (os.path.exists(file1_path) and os.path.exists(file2_path)):
        missing = []
        if not file1_path or not os.path.exists(file1_path): missing.append(file1_path or f"{key1}.npy (path unknown)")
        if not file2_path or not os.path.exists(file2_path): missing.append(file2_path or f"{key2}.npy (path unknown)")
        # Use relative paths in debug message if possible
        relative_missing = [os.path.relpath(m, embeddings_dir) if m and os.path.isabs(m) and embeddings_dir in m else m for m in missing]
        logger.debug(f"Embedding files missing/path error during similarity calculation: {', '.join(relative_missing)}")
        return 0.0

    try:
        emb1 = np.load(file1_path)
        emb2 = np.load(file2_path)
        # Ensure embeddings are 1D arrays before dot product
        if emb1.ndim > 1: emb1 = emb1.flatten()
        if emb2.ndim > 1: emb2 = emb2.flatten()
        # Check for zero vectors
        norm1 = np.linalg.norm(emb1)
        norm2 = np.linalg.norm(emb2)
        if norm1 == 0 or norm2 == 0:
            logger.debug(f"Zero vector encountered for key(s) {key1 if norm1 == 0 else ''}{' and ' if norm1 == 0 and norm2 == 0 else ''}{key2 if norm2 == 0 else ''}. Similarity is 0.")
            return 0.0
        similarity = float(np.dot(emb1, emb2) / (norm1 * norm2))
        return max(0.0, min(1.0, similarity))  # Clamp to [0, 1]
    except Exception as e:
        logger.exception(f"Failed to calculate similarity for {key1} ({file1_path}) and {key2} ({file2_path}): {e}") # Use logger.exception
        return 0.0

# @cached("file_validation",
#        key_func=lambda file_path: f"is_valid_file:{normalize_path(file_path)}:{os.path.getmtime(ConfigManager().config_path)}")
def _is_valid_file(file_path: str) -> bool:
    """
    Check if a file is valid for embedding generation.

    Args:
        file_path: Normalized path to the file
    Returns:
        True if the file should be processed, False otherwise
    """
    config = ConfigManager()
    # Ensure paths are fetched correctly using project_root if needed
    # Use get_project_root from path_utils
    project_root = get_project_root()
    # Corrected: Use specific getter methods or .config property
    exclude_dirs_raw = config.get_excluded_dirs()
    exclude_dirs = [normalize_path(os.path.join(project_root, d)) for d in exclude_dirs_raw] # Normalize exclusion paths
    exclude_exts = config.get_excluded_extensions()
    exclude_files_raw = config.config.get("exclude_files", []) # Access underlying dict for non-standard keys
    exclude_files = [normalize_path(os.path.join(project_root, f)) for f in exclude_files_raw] # Normalize exclusion files

    norm_file_path = normalize_path(file_path) # Normalize the file path being checked
    logger.debug(f"_is_valid_file: Checking path: {norm_file_path}") # DEBUG
    logger.debug(f"_is_valid_file: Excluded Dirs (absolute): {exclude_dirs}") # DEBUG
    logger.debug(f"_is_valid_file: Excluded Exts: {exclude_exts}") # DEBUG
    logger.debug(f"_is_valid_file: Excluded Files (absolute): {exclude_files}") # DEBUG

    # Check against normalized exclude_files list
    if norm_file_path in exclude_files:
         logger.debug(f"_is_valid_file: Path excluded by exclude_files list.") # DEBUG
         return False

    file_name = os.path.basename(norm_file_path)
    if file_name.startswith('.'):
        return False

    # Check against normalized exclude_dirs list
    is_excluded_by_dir = any(norm_file_path.startswith(ex_dir) for ex_dir in exclude_dirs) # DEBUG
    if is_excluded_by_dir: # DEBUG
        logger.debug(f"_is_valid_file: Path excluded by exclude_dirs list.") # DEBUG
        return False

    ext = os.path.splitext(norm_file_path)[1].lower()
    if ext in exclude_exts:
        logger.debug(f"_is_valid_file: Path excluded by exclude_exts list (ext: {ext}).") # DEBUG
        return False

    # Check file size and existence last
    try:
        return os.path.isfile(norm_file_path) and os.path.getsize(norm_file_path) < 10 * 1024 * 1024  # 10MB limit
    except OSError:
        return False # File might not exist or be accessible

def register_parser(subparsers):
    """Register command-line interface commands."""
    parser = subparsers.add_parser("generate-embeddings", help="Generate embeddings for project files")
    parser.add_argument("project_paths", nargs="+", help="Paths to project directories (relative to project root)")
    # Output dir is now determined by config, removing CLI arg
    # parser.add_argument("--output-dir", default=".", help="Directory to store embeddings")
    parser.add_argument("--force", action="store_true", help="Force regeneration of embeddings")
    parser.set_defaults(func=command_handler)

def command_handler(args):
    """Handle the generate-embeddings command."""
    # Output dir is now handled internally via config
    success, key_map = generate_embeddings(args.project_paths, args.force)
    if success:
        config_manager = ConfigManager()
        embeddings_dir = config_manager.get_path("embeddings_dir", "cline_utils/dependency_system/analysis/embeddings")
        print(f"Successfully generated/updated embeddings for {len(key_map)} relevant files in subdirs under {embeddings_dir}")
        return 0
    else:
        print("Error: Failed to generate embeddings. Check logs for details.")
        return 1

# EoF
