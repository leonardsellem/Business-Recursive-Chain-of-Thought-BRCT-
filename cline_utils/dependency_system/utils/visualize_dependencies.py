# cline_utils/dependency_system/utils/visualize_dependencies.py

"""
Handles the generation of Mermaid syntax for visualizing project dependencies.
"""

import os
import logging
import re
from collections import defaultdict
from typing import List, Optional, Dict, Tuple, Set

# Assuming these are the correct relative import paths based on the new file location
from ..core.key_manager import KeyInfo, sort_key_strings_hierarchically # Assuming global_path_to_key_info_type is Dict[str, KeyInfo]
from ..core.dependency_grid import DIAGONAL_CHAR # For skipping self-loops if necessary
from ..io import tracker_io # For aggregate_all_dependencies
from ..utils.path_utils import normalize_path # For path normalization
from ..utils.config_manager import ConfigManager # To get priorities etc.

logger = logging.getLogger(__name__)

# Helper function to determine if a key represents a direct parent of another
# This is specific to how keys and paths are structured in your system.
def _is_direct_parent_child_key_relationship(
    key1_str: str,
    key2_str: str,
    global_path_to_key_info_map: Dict[str, KeyInfo]
) -> bool:
    """
    Checks if one key's path is the direct parent_path of the other key's path.
    """
    key1_info = next((info for info in global_path_to_key_info_map.values() if info.key_string == key1_str), None)
    key2_info = next((info for info in global_path_to_key_info_map.values() if info.key_string == key2_str), None)

    if not key1_info or not key2_info:
        return False

    # Check if key1's path is the parent of key2's path
    if key2_info.parent_path and normalize_path(key1_info.norm_path) == normalize_path(key2_info.parent_path):
        return True
    # Check if key2's path is the parent of key1's path
    if key1_info.parent_path and normalize_path(key2_info.norm_path) == normalize_path(key1_info.parent_path):
        return True
    return False


def generate_mermaid_diagram(
    focus_keys_list: List[str],
    global_path_to_key_info_map: Dict[str, KeyInfo],
    all_tracker_paths_list: List[str],
    config_manager_instance: ConfigManager
) -> Optional[str]:
    """
    Core logic to generate a Mermaid string for given focus keys or overall project.

    Args:
        focus_keys_list: List of key strings to focus on. If empty, attempts to visualize all.
        global_path_to_key_info_map: Maps normalized paths to KeyInfo objects.
        all_tracker_paths_list: List of paths to all tracker files.
        config_manager_instance: Instance of ConfigManager.

    Returns:
        The Mermaid diagram string or None on critical failure.
        Returns a simple "no data" Mermaid string if no relevant items are found.
    """
    logger.info(f"Generating Mermaid diagram. Focus Keys: {focus_keys_list or 'Project Overview'}")

    # 1. Aggregate all dependencies
    #    This function now directly returns Dict[Tuple[str, str], Tuple[str, Set[str]]]
    #    where key is (source_key_str, target_key_str) and value is (dep_char, {origin_trackers})
    aggregated_links_with_origins = tracker_io.aggregate_all_dependencies(
        all_tracker_paths_list,
        global_path_to_key_info_map
    )
    # For visualization, we primarily care about the consolidated link type after priority.
    # The aggregate_all_dependencies already resolves priorities.
    consolidated_directed_links: Dict[Tuple[str, str], str] = {
        link: char_and_origins[0] # Get the highest priority char
        for link, char_and_origins in aggregated_links_with_origins.items()
    }
    logger.debug(f"Aggregated {len(consolidated_directed_links)} consolidated directed links.")

    # --- Determine Scope Based on Focus Keys ---
    keys_in_module_scope = set() # Keys belonging to the focused module (if module view)
    is_module_view = False
    focus_keys_valid = set() # Keep track of valid focus keys provided by user

    if len(focus_keys_list) == 1:
        focus_key_str = focus_keys_list[0]
        focus_info = next((info for info in global_path_to_key_info_map.values() if info.key_string == focus_key_str), None)
        if focus_info and focus_info.is_directory:
            # --- MODULE VIEW LOGIC ---
            is_module_view = True
            module_path_prefix = focus_info.norm_path + "/" # Ensure trailing slash for prefix matching
            logger.info(f"Detected module view focus: {focus_key_str} ({focus_info.norm_path}). Finding descendants...")
            keys_in_module_scope.add(focus_key_str) # Include the module key itself
            for key_info in global_path_to_key_info_map.values():
                # Check path prefix for descendants, handle case where module IS the root path itself
                if key_info.norm_path == focus_info.norm_path or \
                   key_info.norm_path.startswith(module_path_prefix):
                    keys_in_module_scope.add(key_info.key_string)
            logger.info(f"Module view scope: {len(keys_in_module_scope)} keys including descendants.")
            focus_keys_valid.add(focus_key_str) # The module key is the valid focus
        elif focus_info:
             # Single non-directory focus key
             focus_keys_valid.add(focus_key_str)
        else:
             logger.warning(f"Focus key '{focus_key_str}' not found. Proceeding with overview.")
             focus_keys_list = [] # Reset focus list

    elif len(focus_keys_list) > 0 : # Multiple focus keys
         # Standard multi-focus logic: identify valid keys
         for fk_str in focus_keys_list:
             fk_info = next((info for info in global_path_to_key_info_map.values() if info.key_string == fk_str), None)
             if fk_info: focus_keys_valid.add(fk_str)
             else: logger.warning(f"Multi-focus key '{fk_str}' not found. Ignoring.")
         if not focus_keys_valid:
              logger.error("No valid focus keys provided for multi-focus view.")
              return "flowchart TB\n\n// Error: No valid focus keys found."

    # --- End Scope Determination ---


    # 2. Prepare Edges for Drawing (Consolidate 'x', '<'/'>') - Filter 'n' already done
    intermediate_edges = []
    processed_pairs_for_intermediate = set()
    # Create a map of links that are not 'n' for easier lookup
    non_n_links = {
        (s, t): char for (s, t), char in consolidated_directed_links.items() if char != 'n'
    }

    sorted_non_n_links = sorted(non_n_links.items())

    for (source, target), forward_char in sorted_non_n_links:
        pair_tuple = tuple(sorted((source, target)))
        if pair_tuple in processed_pairs_for_intermediate:
            continue

        reverse_char = non_n_links.get((target, source)) # Only look up non-'n' reverse links

        # Consolidate 'x' or reciprocal '<'/' >'
        if forward_char == 'x' or reverse_char == 'x':
            intermediate_edges.append((source, target, 'x'))
        elif forward_char == '<' and reverse_char == '>':
            intermediate_edges.append((source, target, '<'))
        elif forward_char == '>' and reverse_char == '<':
            intermediate_edges.append((target, source, '<')) # Store as target --> source
        else:
            # If it's a single directional link (reverse_char is None or doesn't form a pair)
            intermediate_edges.append((source, target, forward_char))
            # If reverse_char exists and is different (and not part of a pair), it will be added when its turn comes
        
        processed_pairs_for_intermediate.add(pair_tuple) # Mark pair as processed to handle both directions

    logger.debug(f"Prepared {len(intermediate_edges)} non-'n' intermediate edges for drawing after consolidation.")

    # 3. Filter Edges based on Scope (Module View vs. Standard Focus View vs. Overview)
    edges_within_scope = []
    relevant_keys_for_nodes = set() # Keys that will actually appear in the diagram

    if is_module_view:
        # --- Module View Edge Filter (Option C: Internal + Interface) ---
        relevant_keys_for_nodes.update(keys_in_module_scope) # Start with all keys within module
        for k1, k2, char_val in intermediate_edges:
            k1_is_internal = k1 in keys_in_module_scope
            k2_is_internal = k2 in keys_in_module_scope

            # Keep edge if BOTH are internal (A) OR exactly ONE is internal (B)
            if (k1_is_internal and k2_is_internal) or \
               (k1_is_internal and not k2_is_internal) or \
               (not k1_is_internal and k2_is_internal):
                edges_within_scope.append((k1, k2, char_val))
                # Add both endpoints to ensure nodes outside module are also drawn if linked
                relevant_keys_for_nodes.add(k1)
                relevant_keys_for_nodes.add(k2)
        logger.debug(f"Module View (Internal+Interface): Filtered to {len(edges_within_scope)} edges.")

    elif focus_keys_valid: # Standard Focus View (single file or multiple keys)
        # --- Standard Focus Edge Filter ---
        relevant_keys_for_nodes.update(focus_keys_valid) # Start with focus keys
        for k1, k2, char_val in intermediate_edges:
            # Keep edge if AT LEAST ONE endpoint is a focus key
            if k1 in focus_keys_valid or k2 in focus_keys_valid:
                edges_within_scope.append((k1, k2, char_val))
                relevant_keys_for_nodes.add(k1) # Add both neighbors
                relevant_keys_for_nodes.add(k2)
        logger.debug(f"Standard Focus View: Filtered to {len(edges_within_scope)} edges connected to focus keys.")

    else: # Overview (no focus keys)
        # --- Overview Edge Filter ---
        edges_within_scope = intermediate_edges # Keep all non-'n' consolidated edges
        relevant_keys_for_nodes = {k for edge in edges_within_scope for k in edge[:2]}
        logger.debug(f"Overview View: Including all {len(edges_within_scope)} consolidated edges.")


    # 4. Final Edge Filtering (Structural 'x', File/Dir Mismatches, Placeholders 'p')
    # Apply these filters to the `edges_within_scope`
    final_edges_to_draw = []
    structural_x_removed = 0; type_mismatch_removed = 0; placeholder_p_removed = 0
    key_string_to_info_lookup = {info.key_string: info for info in global_path_to_key_info_map.values()}

    for k1, k2, char_val in edges_within_scope: # Filter the scoped edges
        # Note: 'p' filtering might be redundant if aggregate_all_dependencies handles it, but safe to keep.
        # 'n' filtering was done earlier.
        if char_val == 'p': placeholder_p_removed += 1; continue

        info1 = key_string_to_info_lookup.get(k1)
        info2 = key_string_to_info_lookup.get(k2)

        if not info1 or not info2: # Should not happen if keys are from global_path_to_key_info_map
            logger.warning(f"Missing KeyInfo for '{k1 if not info1 else k2}' during edge filtering. Skipping edge.")
            continue
        
        # Filter structural 'x' between a direct parent and child
        if char_val == 'x' and _is_direct_parent_child_key_relationship(k1, k2, global_path_to_key_info_map):
            structural_x_removed += 1
            continue
        
        # Filter file-directory mismatches (unless it's a 'd' documentation link)
        # This assumes 'd' links can legitimately cross file/dir types.
        if char_val != 'd' and info1.is_directory != info2.is_directory:
            type_mismatch_removed += 1
            continue
            
        final_edges_to_draw.append((k1, k2, char_val))

    logger.debug(f"Edges removed after final filtering: Structural 'x'({structural_x_removed}), Type Mismatch({type_mismatch_removed}), Placeholders 'p'({placeholder_p_removed})")
    logger.info(f"Final count of edges to draw: {len(final_edges_to_draw)}")


    # 5. Recalculate relevant nodes based on FINAL edges, Build Hierarchy Map
    # Use nodes from the final drawable edges. Also ensure original focus keys included.
    final_relevant_keys_for_nodes = {k for edge_tuple in final_edges_to_draw for k in edge_tuple[:2]}
    if focus_keys_valid: # Add back original valid focus keys in case they have no drawable edges
         final_relevant_keys_for_nodes.update(focus_keys_valid)

    if not final_relevant_keys_for_nodes:
        logger.info("No relevant nodes or dependencies remain after filtering to visualize.")
        return "flowchart TB\n\n// No relevant data to visualize after filtering."
    logger.info(f"Final count of distinct nodes to draw: {len(final_relevant_keys_for_nodes)}")

    # Build hierarchy map (parent_to_children_map and all_keys_for_hierarchy_construction)
    # This logic should remain largely the same, ensuring all parents of
    # final_relevant_keys_for_nodes are included in all_keys_for_hierarchy_construction.
    parent_to_children_map: Dict[Optional[str], List[KeyInfo]] = defaultdict(list)
    all_keys_for_hierarchy_construction = set(final_relevant_keys_for_nodes)
    queue_for_parents = list(final_relevant_keys_for_nodes)
    visited_for_parents = set(final_relevant_keys_for_nodes)
    while queue_for_parents:
        key_str = queue_for_parents.pop(0)
        info = key_string_to_info_lookup.get(key_str)
        if not info: continue
        parent_norm_path = info.parent_path
        parent_to_children_map[parent_norm_path].append(info)
        if parent_norm_path:
            parent_key_info = global_path_to_key_info_map.get(parent_norm_path)
            if parent_key_info and parent_key_info.key_string not in visited_for_parents:
                 all_keys_for_hierarchy_construction.add(parent_key_info.key_string)
                 visited_for_parents.add(parent_key_info.key_string)
                 queue_for_parents.append(parent_key_info.key_string)
    logger.debug(f"Total nodes involved in hierarchy (incl. parents): {len(all_keys_for_hierarchy_construction)}")

    # 6. Generate Mermaid String (Nodes and Subgraphs)
    # The recursive function _generate_mermaid_nodes_recursive_internal
    # should now work correctly as it relies on all_keys_for_hierarchy_construction
    # to decide which directories become subgraphs.
    mermaid_string_parts = ["flowchart TB"]
    defined_mermaid_nodes = set() # Tracks keys for which a node box has been explicitly defined

    def _generate_mermaid_nodes_recursive_internal(
        current_parent_key_info: Optional[KeyInfo], # Pass KeyInfo of the parent, or None for root
        depth_indent_str: str
    ):
        nonlocal mermaid_string_parts, defined_mermaid_nodes # Allow modification

        current_parent_norm_path = current_parent_key_info.norm_path if current_parent_key_info else None
        children_key_infos_list = parent_to_children_map.get(current_parent_norm_path, [])
        
        # Sort children by their key string for consistent output
        sorted_children_key_infos = sorted(
            children_key_infos_list,
            key=lambda ki: sort_key_strings_hierarchically([ki.key_string])[0]
        )

        for child_ki in sorted_children_key_infos:
            child_key_str = child_ki.key_string
            child_norm_path_val = child_ki.norm_path # Path of the child itself

            # --- Subgraph Declaration for Directories ---
            if child_ki.is_directory:
                # Draw as subgraph if it's part of the necessary hierarchy structure
                if child_key_str in all_keys_for_hierarchy_construction:
                    dir_basename = os.path.basename(child_norm_path_val)
                    safe_subgraph_id = re.sub(r'[^a-zA-Z0-9_]', '_', child_key_str)
                    mermaid_string_parts.append(f'{depth_indent_str}subgraph {safe_subgraph_id} ["{child_key_str}<br>{dir_basename}"]')
                    _generate_mermaid_nodes_recursive_internal(child_ki, depth_indent_str + "  ")
                    mermaid_string_parts.append(f'{depth_indent_str}end')

            # --- Node Definition for Files (or relevant Dirs not drawn as subgraphs - less likely now) ---
            if child_key_str in final_relevant_keys_for_nodes and child_key_str not in defined_mermaid_nodes:
                 # Only define FILES explicitly here. Directories needed for structure are handled by subgraph.
                 # If a directory IS in final_relevant_keys_for_nodes but has NO relevant children/parents making it
                 # part of all_keys_for_hierarchy_construction (unlikely), it might be missed. Add fallback.
                if not child_ki.is_directory:
                    item_basename = os.path.basename(child_norm_path_val)
                    # Indentation should place it within the parent subgraph's context
                    mermaid_string_parts.append(f'{depth_indent_str}{"  " if current_parent_key_info else ""}  {child_key_str}["{child_key_str}<br>{item_basename}"]')
                    defined_mermaid_nodes.add(child_key_str)

    # Initial call
    _generate_mermaid_nodes_recursive_internal(None, "")

    # Fallback definition loop (mostly for files missed or truly rootless nodes)
    for key_str_fallback in final_relevant_keys_for_nodes:
        if key_str_fallback not in defined_mermaid_nodes:
            info_fallback = key_string_to_info_lookup.get(key_str_fallback)
            if info_fallback and not info_fallback.is_directory: # Primarily for files
                basename_fallback = os.path.basename(info_fallback.norm_path)
                mermaid_string_parts.append(f'  {key_str_fallback}["{key_str_fallback}<br>{basename_fallback}"]')
                defined_mermaid_nodes.add(key_str_fallback)


    # 7. Add Dependencies (Edges)
    mermaid_string_parts.append("\n  %% -- Dependencies --")
    dep_char_to_style = {
        '<': ('-->', "relies on"),    # k1 relies on k2  (k1 --> k2)
        '>': ('-->', "required by"),  # k1 is required by k2 (k2 --> k1) - need to flip k1,k2 for drawing
        'x': ('<-->', "mutual"),
        'd': ('-.->', "docs"),
        's': ('-.->', "semantic (weak)"), # Example, might need different arrow
        'S': ('==>', "semantic (strong)"),# Example, might need different arrow
    }

    # Sort edges for deterministic output
    sorted_final_edges = sorted(final_edges_to_draw, key=lambda x: (sort_key_strings_hierarchically([x[0]])[0], sort_key_strings_hierarchically([x[1]])[0], x[2]))

    for k1, k2, dep_char in sorted_final_edges:
        # Ensure both nodes in the edge were actually defined (relevant)
        if k1 not in defined_mermaid_nodes or k2 not in defined_mermaid_nodes:
            logger.debug(f"Skipping edge ({k1} {dep_char} {k2}) because one or both nodes were not rendered.")
            continue

        arrow_style, label_text = dep_char_to_style.get(dep_char, ('-->', dep_char)) # Default arrow
        
        source_node, target_node = k1, k2
        # Special handling for '>' where the visual direction is target -> source
        if dep_char == '>':
            source_node, target_node = k2, k1 # Flip for drawing: k2 requires k1 means k2 --> k1

        mermaid_string_parts.append(f'  {source_node} {arrow_style}|"{label_text}"| {target_node}')
            
    return "\n".join(mermaid_string_parts)