# Cline Recursive Chain-of-Thought System (CRCT) - v7.8

Welcome to the **Cline Recursive Chain-of-Thought System (CRCT)**, a framework designed to manage context, dependencies, and tasks in large-scale Cline projects within VS Code. Built for the Cline extension, CRCT leverages a recursive, file-based approach with a modular dependency tracking system to maintain project state and efficiency as complexity increases.

- Version **v7.8**: Introduces dependency visualization, overhauls the Strategy phase for iterative roadmap planning, and refines Hierarchical Design Token Architecture (HDTA) templates.
    - **Dependency Visualization (`visualize-dependencies`)**:
        - Added a new command to generate Mermaid diagrams visualizing project dependencies.
        - Supports project overview, module-focused (internal + interface), and multi-key focused views.
        - Auto-generates overview and module diagrams during `analyze-project` (configurable).
        - Diagrams saved by default to `<memory_dir>/dependency_diagrams/`.
    - **Strategy Phase Overhaul (`strategy_plugin.md`):**
        - Replaced monolithic planning with an **iterative, area-based workflow** focused on minimal context loading, making it more robust for LLM execution.
        - Clarified primary objective as **hierarchical project roadmap construction and maintenance** using HDTA.
        - Integrated instructions for leveraging dependency diagrams (auto-generated or on-demand) to aid analysis.
        - Refined state management (`.clinerules` vs. `activeContext.md`).
    - **HDTA Template Updates**:
        - Reworked `implementation_plan_template.md` for objective/feature focus.
        - Added clarifying instructions to `module_template.md` and `task_template.md`.
        - Created new `roadmap_summary_template.md` for unified cycle plans.
- Version **v7.7**: Restructured core prompt/plugins, introduced `cleanup_consolidation_plugin.md` phase (use with caution due to file operations), added `hdta_review_progress` and `hierarchical_task_checklist` templates.
- Version **v7.5**: Significant baseline restructuring, establishing core architecture, Contextual Keys (`KeyInfo`), Hierarchical Dependency Aggregation, enhanced `show-dependencies`, configurable embedding device, file exclusion patterns, improved caching & batch processing.

---

## Key Features

- **Recursive Decomposition**: Breaks tasks into manageable subtasks, organized via directories and files for isolated context management.
- **Minimal Context Loading**: Loads only essential data, expanding via dependency trackers as needed.
- **Persistent State**: Uses the VS Code file system to store context, instructions, outputs, and dependencies. State integrity is rigorously maintained via a **Mandatory Update Protocol (MUP)** applied after actions and periodically during operation.
- **Modular Dependency System**: Fully modularized dependency tracking system.
- **Contextual Keys**: Introduces `KeyInfo` for context-rich keys, enabling more accurate and hierarchical dependency tracking.
- **Hierarchical Dependency Aggregation**: Implements hierarchical rollup and foreign dependency aggregation for the main tracker, providing a more comprehensive view of project dependencies.
- **Enhanced Dependency Workflow**: A refined workflow simplifies dependency management.
    - `show-keys` identifies keys needing attention ('p', 's', 'S') within a specific tracker.
    - `show-dependencies` aggregates dependency details (inbound/outbound, paths) from *all* trackers for a specific key, eliminating manual tracker deciphering.
    - `add-dependency` resolves placeholder ('p') or suggested ('s', 'S') relationships identified via this process. **Crucially, when targeting a mini-tracker (`*_module.md`), `add-dependency` now allows specifying a `--target-key` that doesn't exist locally, provided the target key is valid globally (known from `analyze-project`). The system automatically adds the foreign key definition and updates the grid, enabling manual linking to external dependencies.**
      *   **Tip:** This is especially useful for manually linking relevant documentation files (e.g., requirements, design specs, API descriptions) to code files within a mini-tracker, even if the code file is incomplete or doesn't trigger an automatic suggestion. This provides the LLM with crucial context during code generation or modification tasks, guiding it towards the intended functionality described in the documentation (`doc_key < code_key`).
   - **Dependency Visualization (`visualize-dependencies`)**: **(NEW in v7.8)**
    - Generates Mermaid diagrams for project overview, module scope (internal + interface), or specific key focus.
    - Auto-generates overview/module diagrams via `analyze-project`.
- **Iterative Strategy Phase**: **(NEW in v7.8)**
    - Plans the project roadmap iteratively, focusing on one area (module/feature) at a time.
    - Explicitly integrates dependency analysis (textual + visual) into planning.
- **Refined HDTA Templates**: **(NEW in v7.8)**
    - Improved templates for Implementation Plans, Modules, and Tasks.
    - New template for Roadmap Summaries.
- **Configurable Embedding Device**: Allows users to configure the embedding device (`cpu`, `cuda`, `mps`) via `.clinerules.config.json` for optimized performance on different hardware. (Note: *the system does not yet install the requirements for cuda or mps automatically, please install the requirements manually or with the help of the LLM.*)
- **File Exclusion Patterns**: Users can now define file exclusion patterns in `.clinerules.config.json` to customize project analysis.
- **Caching and Batch Processing**: Significantly improves performance.
- **Modular Dependency Tracking**:
    - Utilizes main trackers (`module_relationship_tracker.md`, `doc_tracker.md`) and module-specific mini-trackers (`{module_name}_module.md`).
    - Mini-tracker files also serve as the HDTA Domain Module documentation for their respective modules.
    - Employs hierarchical keys and RLE compression for efficiency.
- **Automated Operations**: System operations are now largely automated and condensed into single commands, streamlining workflows and reducing manual command execution.
- **Phase-Based Workflow**: Operates in distinct phases: Set-up/Maintenance -> Strategy -> Execution -> Cleanup/Consolidation, controlled by `.clinerules`.
- **Chain-of-Thought Reasoning**: Ensures transparency with step-by-step reasoning and reflection.

---

## Quickstart

1. **Clone the Repo**:
   ```bash
   git clone https://github.com/RPG-fan/Cline-Recursive-Chain-of-Thought-System-CRCT-.git
   cd Cline-Recursive-Chain-of-Thought-System-CRCT-
   ```

2. **Install Dependencies**:
   ```bash
   pip install -r requirements.txt
   ```

3. **Set Up Cline Extension**:
   - Open the project in VS Code with the Cline extension installed.
   - Copy `cline_docs/prompts/core_prompt(put this in Custom Instructions).md` into the Cline Custom Instructions field.

4. **Start the System**:
   - Type `Start.` in the Cline input to initialize the system.
   - The LLM will bootstrap from `.clinerules`, creating missing files and guiding you through setup if needed.

*Note*: The Cline extension’s LLM automates most commands and updates to `cline_docs/`. Minimal user intervention is required (in theory!).

---

## Project Structure

```
Cline-Recursive-Chain-of-Thought-System-CRCT-/
│   .clinerules
│   .clinerules.config.json       # Configuration for dependency system
│   .gitignore
│   INSTRUCTIONS.md
│   LICENSE
│   README.md
│   requirements.txt
│
├───cline_docs/                   # Operational memory
│   │  activeContext.md           # Current state and priorities
│   │  changelog.md               # Logs significant changes
│   │  userProfile.md             # User profile and preferences
│   │  progress.md                # High-level project checklist
│   │
│   ├──backups/                   # Backups of tracker files
│   ├──dependency_diagrams/       # Default location for auto-generated Mermaid diagrams <NEW>
│   ├──prompts/                   # System prompts and plugins
│   │    core_prompt.md           # Core system instructions
|   |    cleanup_consolidation_plugin.md <NEWer>
│   │    execution_plugin.md
│   │    setup_maintenance_plugin.md
│   │    strategy_plugin.md         <REVISED>
│   ├──templates/                 # Templates for HDTA documents
│   │    hdta_review_progress_template.md <NEWer>
│   │    hierarchical_task_checklist_template.md <NEWer>
│   │    implementation_plan_template.md <REVISED>
│   │    module_template.md         <Minor Update>
│   │    roadmap_summary_template.md  <NEW>
│   │    system_manifest_template.md
│   │    task_template.md           <Minor Update>
│
├───cline_utils/                  # Utility scripts
│   └─dependency_system/
│     │ dependency_processor.py   # Dependency management script <REVISED>
│     ├──analysis/                # Analysis modules <REVISED project_analyzer.py>
│     ├──core/                    # Core modules <REVISED key_manager.py>
│     ├──io/                      # IO modules
│     └──utils/                   # Utility modules <REVISED config_manager.py>, <NEW visualize_dependencies.py>
│
├───docs/                         # Project documentation
└───src/                          # Source code root

```
*(Added/Updated relevant files/dirs)*

---

## Current Status & Future Plans

- **v7.8**: Focus on **visual comprehension and planning robustness**. Introduced Mermaid dependency diagrams (`visualize-dependencies`, auto-generation via `analyze-project`). Overhauled the Strategy phase (`strategy_plugin.md`) for iterative, area-based roadmap planning, explicitly using visualizations. Refined HDTA templates, including a new `roadmap_summary_template.md`.
- **v7.7**: Introduced `cleanup_consolidation` phase, added planning/review tracker templates.
- **v7.5**: Foundational restructure: Contextual Keys, Hierarchical Aggregation, `show-dependencies`, configuration enhancements, performance improvements (cache/batch).

**Future Focus**: Continue refining performance, usability, and robustness. Areas include improving error handling in file operations (Cleanup), and further optimizing LLM interaction within each phase based on usage patterns. The remainder of the v7.x series will mainly be improving how embeddings, analysis, and similarity suggestions are handled. These releases might come a bit slower than previous areas due to the amount of research and testing needed to genuinely improve upon the current analysis/suggestion system.
- *tentative* v8.x will be focused on transition to MCP based tool use, with later stages planned to move from filesystem storage/operations to database focused operation.

Feedback is welcome! Please report bugs or suggestions via GitHub Issues.

---

## Getting Started (Optional - Existing Projects)

To test on an existing project:
1. Copy your project into `src/`.
2. Use these prompts to kickstart the LLM:
   - `Perform initial setup and populate dependency trackers.`
   - `Review the current state and suggest next steps.`

The system will analyze your codebase, initialize trackers, and guide you forward.

---

## Thanks!

A big Thanks to https://github.com/biaomingzhong for providing detailed instructions that were integrated into the core prompt and plugins! (PR #25)

This is a labor of love to make Cline projects more manageable. I’d love to hear your thoughts—try it out and let me know what works (or doesn’t)!
