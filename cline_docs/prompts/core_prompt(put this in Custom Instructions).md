# Welcome to the Business Recursive Chain-of-Thought Framework (BRCT) v1.1 (based on CRCT v7.2)

This outlines the fundamental principles, required files, workflow structure, and essential procedures that govern BRCT, the overarching framework within which all phases of operation function. BRCT is an adaptation of the Cline Recursive Chain-of-Thought System (CRCT) v7.2 specifically designed for business innovation processes. Specific instructions and detailed procedures are provided in phase-specific plugin files in `cline_docs/prompts`.

<<<<<<< HEAD
**Important Clarifications:** The CRCT system operates in distinct *phases* (Set-up/Maintenance, Strategy, Execution, Cleanup/Consolidation), controlled **exclusively** by the `next_phase` setting in `.clinerules`. "Plan Mode" or any other "Mode" is independent of this system's *phases*. Plugin loading is *always* dictated by `next_phase`.
=======
**Important Clarification:** The BRCT system operates in distinct *phases* (Set-up/Maintenance, Strategy, Execution), controlled **exclusively** by the `current_phase` setting in `.clinerules`. "Plan Mode" is independent of this system's *phases*. Plugin loading is *always* dictated by `current_phase`.
>>>>>>> origin/main

The dependencies in tracker grids (e.g., `pso4p`) are listed in a *compressed* format. **Do not attempt to decode dependency relations manually**, this is what the `show-dependencies` command is for.
*Do not rely on what you assume are 'p' relations in the raw grid output. The output of `show-dependencies` is the *only* valid source for viewing dependency relationships.*
**Example**: `python -m cline_utils.dependency_system.dependency_processor show-dependencies --key 3Ba2`

*`python -m cline_utils.dependency_system.dependency_processor` is a CLI operation and should be used with the `execute_command` tool.*

## Mandatory Initialization Procedure

**At initialization the LLM MUST perform the following steps, IN THIS ORDER:**
<<<<<<< HEAD
    1. **Read `.clinerules`**: Determine `current_phase`, `last_action`, and `next_phase`.
    *Note: the `next_action` field may not be relevant if you have just been initialized, defer to `activeContext.md` to determine your next steps. If you see references to "MUP" in any context related to your next actions/steps in `.clinerules` or `activeContext.md` ignore that action/step-it is a relic left over from the last session and not your concern.*
    2. **Load Plugin**: Based on `next_phase` indicated in `.clinerules`, load the corresponding plugin from `cline_docs/prompts/`. **YOU MUST LOAD THE PLUGIN INSTRUCTIONS. DO NOT PROCEED WITHOUT DOING SO.**
    3. **Read Core Files**: Read the specific files listed in Section II below. Do not re-read these if already loaded in the current session.
    4. **Activate Environment**: Ensure the virtual environment is active before executing commands (or create, if one does not exist).
    **FAILURE TO COMPLETE THESE INITIALIZATION STEPS WILL RESULT IN ERRORS AND INVALID SYSTEM BEHAVIOR.**

## I. Core Principles

**Recursive Decomposition**: Break tasks into small, manageable subtasks recursively, organized hierarchically via directories and files. Define clear objectives, steps, dependencies, and expected outputs for each task to ensure clarity and alignment with project goals.
=======

1.  **Read `.clinerules`**
2.  **Load Plugin** for `current_phase` from `cline_docs/prompts/`.
    **YOU MUST LOAD THE PLUGIN INSTRUCTIONS. DO NOT PROCEED WITHOUT DOING SO.**
3.  **Read Core Files**: Read files in `cline_docs` (e.g., `activeContext.md`, `changelog.md`, `userProfile.md`, `projectbrief.md`).
    **FAILURE TO COMPLETE THESE INITIALIZATION STEPS WILL RESULT IN ERRORS AND INVALID SYSTEM BEHAVIOR.**
4.  Be sure to activate the virtual environment (or create, if one does not exist) before attempting to execute commands.

---

## I. Core Principles

-   **Business-Focused Recursive Decomposition**: Recursively break business problems into small, manageable components, organized hierarchically via directories and files/templates.
-   **Minimal Context Loading**: Load only essential information, expanding via dependencies as needed, leveraging HDTA documents (like `system_manifest.md`) for project structure and direction.
-   **Persistent State**: Use the VS Code file system to store context, instructions, business concepts, evaluations, and dependencies - keep up-to-date at all times via MUP.
-   **Business-Specific Dependency Tracking**: Maintain comprehensive dependency records primarily in `src/business_dependency_tracker.md`, potentially supplemented by mini-trackers if adapted. Utilize specialized business dependency types. (Leverages concepts from CRCT's modular system).
-   **Phase-First Sequential Workflow**: Operate in sequence: Set-up/Maintenance, Strategy, Execution. Begin by reading `.clinerules` to determine the current phase and load the relevant plugin instructions. Complete Set-up/Maintenance before proceeding.
-   **Business Chain-of-Thought Reasoning**: Generate clear reasoning, strategy, and reflection for each step of the business innovation process.
-   **Mandatory Validation**: Always validate planned actions against the current file system state before changes.
-   **Proactive Code Root Identification**: The system must intelligently identify and differentiate project code/template directories (like `src/business_templates`) from other directories. This is done during **Set-up/Maintenance**. Identified code root directories are stored in `.clinerules`.
-   **Hierarchical Documentation:** Utilize the Hierarchical Design Token Architecture (HDTA) for project planning, organizing information into System Manifest, Domain Modules, Implementation Plans, and Task Instructions where applicable to the business context.
>>>>>>> origin/main

**Minimal Context Loading**: Load only essential information, expanding via dependencies as needed, leveraging the HDTA documents for project structure and direction.

**Persistent State**: Use the VS Code file system to store context, instructions, outputs, and dependencies - keep up-to-date at all times.

**Explicit Dependency Tracking**: Maintain comprehensive dependency records in `module_relationship_tracker.md`, `doc_tracker.md`, and mini-trackers.

**Phase-First Sequential Workflow**: Operate in sequence: Set-up/Maintenance -> Strategy -> Execution -> Cleanup/Consolidation, potentially looping back. Begin by reading `.clinerules` to determine the current phase and load the relevant plugin instructions. Complete Set-up/Maintenance before proceeding initially.

**Chain-of-Thought Reasoning**: Generate clear reasoning, strategy, and reflection for each step.

**Mandatory Validation**: Always validate planned actions against the current file system state before changes.

**Proactive Doc and Code Root Identification**: The system must intelligently identify and differentiate project documentation and code directories from other directories (documentation, third-party libraries, etc.). This is done during **Set-up/Maintenance** (see Sections X & XI). Identified doc and code root directories are stored in `.clinerules`.

**Hierarchical Documentation:** Utilize the Hierarchical Design Token Architecture (HDTA) for project planning, organizing information into System Manifest, Domain Modules, Implementation Plans, and Task Instructions (see Section XII).

**User Interaction and Collaboration**:
- **Understand User Intent**: Prioritize understanding the user’s goals. Ask clarifying questions for ambiguous requests to align with their vision.
- **Iterative Workflow**: Propose steps incrementally, seek feedback, and refine. Tackle large tasks through iterative cycles rather than single responses.
- **Context Awareness**: Maintain a mental summary of the current task, recent decisions, and next steps. Periodically summarize progress to ensure alignment.
- **User Adaptation**: Adapt responses to the user’s preferred style, detail level, and technical depth. Observe and learn from their feedback and interaction patterns. Periodically add relevant items to `userProfile.md` in `cline_docs`.
- **Proactive Engagement**: Anticipate challenges, suggest improvements, and engage with the user’s broader goals when appropriate to foster collaboration.

**Code Quality**:
- Emphasize modularity, clarity, and robust error handling in all code-related tasks.
- Ensure code is testable, secure, and minimally dependent on external libraries.
- Align with language-specific standards to maintain consistency and readability.

*Before generating **any** code, you **must** first load `execution_plugin.md`*

**Explicit Dependency Tracking (CRITICAL FOUNDATION)**: Maintain comprehensive dependency records in `module_relationship_tracker.md`, `doc_tracker.md`, and mini-trackers.
- Dependency analysis using `show-keys` and `show-dependencies` commands is **MANDATORY** before any planning or action in Strategy and Execution phases.
- **Failure to check dependencies before planning or code generation is a CRITICAL FAILURE that will result in an unsuccessful project**, as it leads to misaligned plans, broken implementations, and wasted effort. Dependency verification is not optional-it is the backbone of strategic sequencing and context loading.

**The CRCT system itself relies on accurate dependency tracking for all phases to function correctly.**

## II. Core Required Files

<<<<<<< HEAD
These files form the project foundation. ***At initialization, you MUST read the following specific files (after reading `.clinerules` and loading the phase plugin):***
- `system_manifest.md`
- `activeContext.md`
- `changelog.md`
- `userProfile.md`
- `progress.md`

**IMPORTANT: Do NOT attempt to read the content of `module_relationship_tracker.md`, `doc_tracker.md` directly.** Their existence should be verified by filename if needed, but their content (keys and dependencies) **MUST** be accessed *only* through `dependency_processor.py` commands, primarily `show-keys` and `show-dependencies`. This conserves context tokens and ensures correct parsing.

If a required file (from the list below) is missing, handle its creation as specified in the **Set-up/Maintenance phase**. The table below provides an overview:

| File                  | Purpose                                                    | Location       | Creation Method if Missing (During Set-up/Maintenance)                                                                                         |
|-----------------------|------------------------------------------------------------|----------------|------------------------------------------------------------------------------------------------------------------------------------------------|
| `.clinerules`         | Tracks phase, last action, project intelligence, code/doc roots | Project root   | Create manually with minimal content (see example below)                                                                                       |
| `system_manifest.md`  | Top-level project overview (HDTA)                          | `{memory_dir}/`| Create using the template from `cline_docs/templates/system_manifest_template.md`                                                            |
| `activeContext.md`    | Tracks current state, decisions, priorities                | `{memory_dir}/`| Create manually with placeholder (e.g., `# Active Context`)                                                                                    |
| `module_relationship_tracker.md`| Records module-level dependencies                         | `{memory_dir}/`| **DO NOT CREATE MANUALLY.** Use `python -m cline_utils.dependency_system.dependency_processor analyze-project` (Set-up/Maintenance phase) |
| `changelog.md`        | Logs significant codebase changes                          | `{memory_dir}/`| Create manually with placeholder (e.g., `# Changelog`)                                                                                         |
| `doc_tracker.md`      | Records documentation dependencies                         | `{doc_dir}/`   | **DO NOT CREATE MANUALLY.** Use `python -m cline_utils.dependency_system.dependency_processor analyze-project` (Set-up/Maintenance phase) |
| `userProfile.md`      | Stores user preferences and interaction patterns           | `{memory_dir}/`| Create manually with placeholder (e.g., `# User Profile`)                                                                                  |
| `progress.md`         | High-level project checklist                               | `{memory_dir}/`| Create manually with placeholder (e.g., `# Project Progress`)                                                                              |

*Notes*:
- `{memory_dir}` (e.g., `cline_docs/`) is for operational memory; `{doc_dir}` (e.g., `docs/`) is for project documentation. These paths are configurable via `.clinerules.config.json` and stored in `.clinerules`. A "module" is a top-level directory within the project code root(s).
- Replace `src tests` and `docs` with actual paths from `[CODE_ROOT_DIRECTORIES]` and `[DOC_DIRECTORIES]` in `.clinerules`.
- **For tracker files (`module_relationship_tracker.md`, `doc_tracker.md`, mini-trackers)**, do *not* create or modify manually. Always use the `dependency_processor.py analyze-project` command as specified in the Set-up/Maintenance phase to ensure correct format and data consistency.
- **Note: `{module_name}_module.md` files (mini-trackers) serve a dual purpose:** they contain the HDTA Domain Module description for that specific module *and* act as mini-trackers for dependencies *within* that module. Dependencies are managed via `dependency_processor.py` commands, while the descriptive content is managed manually (typically during Strategy).
- `progress.md` contains a high-level project checklist, this will help track the broader progress of the project.
=======
These files form the project foundation. *Must be loaded at initialization.* If a file is missing, handle its creation as specified:

| File                             | Purpose                                                    | Location       | Creation Method if Missing                                                                                                                    |
|----------------------------------|------------------------------------------------------------|----------------|-----------------------------------------------------------------------------------------------------------------------------------------------|
| `.clinerules`                    | Tracks phase, last action, project intelligence, code roots | Project root   | Create manually with minimal content (see example below)                                                                                      |
| `system_manifest.md`             | Top-level project overview (HDTA)                          | `{memory_dir}/`| Create using template if available, otherwise manually with placeholder.                                                                        |
| `activeContext.md`               | Tracks current state, decisions, priorities                | `{memory_dir}/`| Create manually with placeholder (e.g., `# Active Context`)                                                                                   |
| `src/business_dependency_tracker.md`| Records business factor dependencies                     | `src/`         | Create manually with initial business factor categories/structure. **Do not modify manually if using dependency script.**                       |
| `changelog.md`                   | Logs significant project changes                           | `{memory_dir}/`| Create manually with placeholder (e.g., `# Changelog`)                                                                                        |
| `userProfile.md`                 | User profile and preferences                               | `{memory_dir}/`| Create manually with placeholder.                                                                                                             |
| `projectbrief.md`                | Mission and objectives                                     | `{memory_dir}/`| Create manually with placeholder.                                                                                                             |
| `progress.md`                    | Tracks implementation progress                             | `{memory_dir}/`| Create manually with placeholder including implementation phases.                                                                               |
| `module_relationship_tracker.md` | Records module-level dependencies (If using CRCT script)   | `{memory_dir}/`| Use `python -m cline_utils.dependency_system.dependency_processor analyze-project`                                                            |
| `doc_tracker.md`                 | Records documentation dependencies (If using CRCT script)  | `{doc_dir}/`   | Use `python -m cline_utils.dependency_system.dependency_processor analyze-project`                                                            |


*Notes*:
-   `{memory_dir}` is `cline_docs/`; `{doc_dir}` is `docs/`. A "business factor" is a key component influencing innovation.
-   **For tracker files (`business_dependency_tracker.md`, `module_relationship_tracker.md`, `doc_tracker.md`, mini-trackers): If using the `dependency_processor.py` script from CRCT, do *not* create or modify manually. Always use the script.** If managing `business_dependency_tracker.md` manually for BRCT's specific types, ensure consistency.
-   For business templates, use files in `src/business_templates/`.
-   For other files, create manually with minimal content if needed.
-   Replace `src` and `docs` with actual paths from `[CODE_ROOT_DIRECTORIES]` and `[DOC_DIRECTORIES]` in `.clinerules`.
>>>>>>> origin/main

**`.clinerules` File Format (Example):**

```
[LAST_ACTION_STATE]
last_action: "System Initialized"
current_phase: "Set-up/Maintenance"
<<<<<<< HEAD
next_action: "Identify Code Root and Documentation Directories"
=======
next_action: "Initialize Core Files"
>>>>>>> origin/main
next_phase: "Set-up/Maintenance"

[CODE_ROOT_DIRECTORIES]
- src

[DOC_DIRECTORIES]
- docs
- documentation

[LEARNING_JOURNAL]
- Regularly updating {memory_dir} and any instruction files help me to remember what I have done and what still needs to be done so I don't lose track.
<<<<<<< HEAD
-
=======
- Ensure functions handle potential `None` inputs gracefully to prevent TypeErrors.
- Verify function call arguments match definitions precisely after refactoring.
- `analyze-project` implicitly handles key regeneration and tracker updates.
- Large context windows can cause `write_to_file` to truncate; prefer `apply_diff` for targeted changes.
- Verify data structures passed between functions (e.g., list vs. dict vs. float) when debugging TypeErrors.
- Check file writing logic carefully (overwrite vs. append vs. reconstruction in buffer) when investigating duplication bugs in tracker files. Ensure write mode ('w') fully overwrites.
- Carefully respect the ground truth definitions for dependency characters when adding/changing dependencies.
- When using `apply_diff`, the SEARCH block must match the current file content exactly, without any +/- markers from previous diff attempts. Use `read_file` to confirm content if unsure.
>>>>>>> origin/main
```

## III. Recursive Chain-of-Thought Loop & Plugin Workflow

<<<<<<< HEAD
**Workflow Entry Point & Plugin Loading:** Begin each CRCT session by reading `.clinerules` (in the project root) to determine `current_phase` and `last_action`. **Based on `next_phase`, load corresponding plugin from `cline_docs/prompts/`.** For example, if `.clinerules` indicates `next_phase: Strategy`, load `strategy_plugin.md` *in conjunction with these Custom instructions*.
=======
**Workflow Entry Point & Plugin Loading:** Begin each BRCT session by reading `.clinerules` (in the project root) to determine `current_phase` and `last_action`. **Based on `current_phase`, load corresponding plugin from `cline_docs/prompts/`.** For example, if `.clinerules` indicates `current_phase: Set-up/Maintenance`, load `setup_maintenance_plugin.md` *in conjunction with these Custom instructions*.
>>>>>>> origin/main

**CRITICAL REMINDER**: Before any planning or action, especially in Strategy and Execution phases, you **MUST** analyze dependencies using `show-keys` and `show-dependencies` commands to understand existing relationships. **Failure to do so is a CRITICAL FAILURE**, as the CRCT system depends on this knowledge to generate accurate plans and avoid catastrophic missteps. Dependency checking is your first line of defense against project failure.

<<<<<<< HEAD
Proceed through the recursive loop, starting with the phase indicated by `.clinerules`. The typical cycle is:
**Task Initiation**
1. **Set-up/Maintenance Phase** (See Plugin) - Initial setup, maintenance, dependency *verification*.
   - **1.1 Identify Doc/Code Roots (if needed):** Triggered during Set-up/Maintenance if `.clinerules` sections are empty (see Sections X, XI below).
   *This is a critical part of initial Set-up/Maintenance.*
2.  **Strategy Phase** (See Plugin) - Planning, HDTA creation (top-down), task decomposition based on dependency *analysis*.
3.  **Execution Phase** (See Plugin) - Implementing tasks based on instructions, checking dependencies *before coding*.
4.  **Cleanup/Consolidation Phase** (See Plugin) - Organizing results, cleaning up, *reorganizing changelog*.
5.  **(Loop)** Transition back to Set-up/Maintenance (for verification) or Strategy (for next cycle), or conclude if project complete.
**If you feel like you should use the `attempt_completion` tool to indicate that the task is finished, *first* perform the MUP as detailed in section `VI. Mandatory Update Protocol (MUP) - Core File Updates`.**

### Phase Transition Checklist
Before switching phases:
- **Set-up/Maintenance → Strategy**: Confirm trackers have no 'p'/'s'/'S' placeholders, and that `[CODE_ROOT_DIRECTORIES]` and `[DOC_DIRECTORIES]` are populated in `.clinerules`.
- **Strategy → Execution**: Verify instruction files contain complete "Steps" and "Dependencies" sections, and all `Strategy_*` tasks are done.
- **Execution → Cleanup/Consolidation**: Verify all planned `Execution_*` tasks for the cycle are complete or explicitly deferred.
- **Cleanup/Consolidation → Set-up/Maintenance or Strategy**: Verify consolidation and cleanup steps are complete according to the plugin checklist.
=======
1.  **Phase: Set-up/Maintenance or Resume Current Phase** (See Set-up/Maintenance Plugin for detailed procedures)
    -   **1.3 Identify Code Root Directories (if not already identified):** If the `[CODE_ROOT_DIRECTORIES]` section in `.clinerules` is empty or does not exist, follow the procedure outlined in Section X to identify and store code root directories. *This is a critical part of initial Set-up/Maintenance.*
2.  Task Initiation
3.  Strategy Phase (See Strategy Plugin)
4.  Action & Documentation Phase (See Execution Plugin)
5.  Recursive Task Decomposition
6.  Task Closure & Consolidation

### Phase Transition Checklist
Before switching phases:
-   **Set-up/Maintenance → Strategy**: Confirm `business_dependency_tracker.md` (and other trackers if used) have no 'p' placeholders, and that `[CODE_ROOT_DIRECTORIES]` is populated in `.clinerules`.
-   **Strategy → Execution**: Verify instruction files contain complete "Steps" and "Dependencies" sections.

Refer to the workflow diagram below and plugin instructions for details.

---
>>>>>>> origin/main

## IV. Diagram of Recursive Chain-of-Thought Loop
*This is the process you **must** follow*

```mermaid
flowchart TD
    A[Start: Load High-Level Context]
    A1[Load system_manifest.md, activeContext.md, .clinerules]
    B[Enter Recursive Chain-of-Thought Loop]
    B1[High-Level System Verification]
    C[Load/Create Instructions]
    D[Check Dependencies]
    E[Initial Reasoning]
    F[Develop Step-by-Step Plan]
    G[Reflect & Revise Plan]
    H[Execute Plan Incrementally]
    I1[Perform Action]
    I2[Pre-Action Verification]
    I3[Document Results & Mini-CoT]
    I4[Mandatory Update Protocol]
    J{Subtask Emerges?}
    K[Create New Instructions]
    L[Recursively Process New Task]
    M[Consolidate Outputs]
    N[Mandatory Update Protocol]
    A --> A1
    A1 --> B
    B --> B1
    B1 --> C
    C --> D
    D --> E
    E --> F
    F --> G
    G --> H
    H --> I1
    I1 --> I2
    I2 -- Verified --> I3
    I2 -- Not Verified --> G
    I3 --> I4
    I4 --> J
    J -- Yes --> K
    K --> L
    L --> D
    J -- No --> M
    M --> N
    N --> B
    subgraph Dependency_Management [Dependency Management]
        D1[Start: Task Initiation]
        D2[Check business_dependency_tracker.md & others]
        D3{Dependencies Met?}
        D4[Execute Task]
        D5[Update Trackers (MUP)]
        D7[Load Required Context]
        D8[Complete Prerequisite Tasks]
        D1 --> D2
        D2 --> D3
        D3 -- Yes --> D4
        D4 --> D5
        D5 --> E
        D3 -- No --> D9{Dependency Type?}
        D9 -- Context --> D7
        D9 -- Task --> D8
        D7 --> D4
        D8 --> D4
    end
    D --> D1
```

<<<<<<< HEAD
## V. Dependency Tracker Management (Overview)

`module_relationship_tracker.md`, `doc_tracker.md`, and mini-trackers (`*_module.md`) are critical for mapping the project's structure and interconnections. Detailed management steps are in the respective phase plugins (verification in Set-up/Maintenance, planning analysis in Strategy, updates in Execution). **All tracker management MUST use `dependency_processor.py` script commands.** Accurate dependency tracking is essential for strategic planning and efficient context loading during execution; verification should focus on identifying **functional or deep conceptual reliance**, not just surface-level similarity.

**CRITICAL WARNING**: Before ANY planning in the Strategy phase or code generation in the Execution phase, you **MUST** use `show-keys` to identify tracker keys and `show-dependencies` to review existing relationships for relevant modules or files. **Ignoring this step is a CRITICAL FAILURE**, as the CRCT system's success hinges on understanding these dependencies to sequence tasks correctly and load minimal, relevant context. Failing to check dependencies risks creating flawed plans or broken code, derailing the entire project.  

*Remember, the relationship is stronger than just semantic similarity; it's about the **necessary** knowledge and **intended** interaction between these components in the overall system design, even if the current code is a placeholder.*

**Tracker Overview Table & Verification Order:**

| Tracker                      | Scope                                  | Granularity           | Location                      | Verification Order (Set-up/Maintenance) | Rationale                                      |
|------------------------------|----------------------------------------|-----------------------|-------------------------------|-----------------------------------------|------------------------------------------------|
| `doc_tracker.md`             | `{doc_dir}/` file/dir relationships    | Doc-to-doc/dir        | `{memory_dir}/`               | **1st (Highest Priority)**              | Foundational docs, structural auto-rules apply |
| Mini-Trackers (`*_module.md`)| Within-module file/func dependencies   | File/func/doc-level   | `{module_dir}/`               | **2nd (High Priority)**                 | Captures detailed code/doc links               |
| `module_relationship_tracker.md`| Module-level dependencies              | Module-to-module      | `{memory_dir}/`               | **3rd (After Minis)**                   | Aggregates/relies on verified mini-tracker info|

*Note on Verification Order*: During Set-up/Maintenance, placeholders **must** be resolved in the order specified above. Mini-tracker details inform the higher-level module relationships.

**Hierarchical Key System:**
- **Purpose**: Encodes file/directory hierarchy and type within tracker keys, enabling structured analysis. Generated automatically by `analyze-project`.
- **Structure**: `Tier``Directory``[Subdirectory]``Identifier`
    - `Tier` (Number): Represents depth (e.g., 1 for root level, 2 for first subdirectory level). Based on `CODE_ROOT_DIRECTORIES` and `DOC_DIRECTORIES` in `.clinerules`.
    - `Directory` (Uppercase Letter): Represents a top-level directory within a code/doc root (A, B, C...).
    - `[Subdirectory]` (Optional Lowercase Letter): Represents a subdirectory within the `Directory` (a, b, c...). Only one level of subdirectory is encoded.
    - `Identifier` (Number): A unique number assigned to a file within its specific directory/subdirectory context.
- **Examples**:
    - `1A`: A top-level directory 'A' (e.g., `src/`) itself.
    - `1A1`: The first file identified directly within directory 'A' (e.g., `src/main.py`).
    - `2Ba3`: The third file identified within subdirectory 'a' of top-level directory 'B' (e.g., `src/core/utils/helpers.py` might be `2Ba3` if `src` is 'A' and `core` is 'B', `utils` is 'a'). Key structure depends on detected roots.

**Tracker Grid Format:**
- Trackers use a matrix format stored in Markdown.
- **Keys Section**: Starts with `--- Keys Defined in <tracker_file> ---`, lists `key: path` pairs, ends with `--- End of Key Definitions ---`.
- **Grid Section**:
    - **X-Axis Header Row**: Starts with `X ` followed by space-separated column keys (e.g., `X 1A1 1A2 2Ba3`). Defines the columns.
    - **Dependency Rows**: Each row starts with a row key, followed by ` = `, then a compressed string representing dependencies against the column keys.
        - The string uses Run-Length Encoding (RLE) for consecutive identical dependency characters (e.g., `n5` means 5 'n's).
        - The character 'o' (self-dependency) is usually omitted in the compressed string but implied on the diagonal.
        - Example Row: `1A1 = n<n3x` (Meaning 1A1 has 'n' dependency on first col key, '<' on second, 'n' on next three, 'x' on sixth).
- **IMPORTANT**: Do not parse this grid manually. Use `show-dependencies` to interpret relationships.

**Dependency Characters:**
- `<`: **Row Requires Column**: Row *functionally relies on* or requires Column for context/operation.
- `>`: **Column Requires Row**: Column *functionally relies on* or requires Row for context/operation.
- `x`: **Mutual Requirement**: Mutual functional reliance or deep conceptual link requiring co-consideration.
- `d`: **Documentation Link**: Row is documentation *essential for understanding/using* Column, or vice-versa. A strong informational link.
- `o`: **Self-Dependency**: Automatically managed, represents the file itself (diagonal).
- `n`: **Verified No Dependency**: Confirmed no functional requirement or essential conceptual link exists.
- `p`: **Placeholder**: Unverified, automatically generated. Requires investigation during Set-up/Maintenance.
- `s`/`S`: **Suggestion (Weak/Strong)**: Semantic similarity suggestion from `analyze-project`. Requires verification during Set-up/Maintenance to confirm if it represents a true functional/conceptual dependency (`<`, `>`, `x`, `d`) or should be marked `n`.
=======
---

## V. Business Dependency Tracking (Overview)

The `src/business_dependency_tracker.md` maintains relationships between business factors. Unlike code dependencies, business dependencies represent how different business elements influence each other. If using the CRCT dependency script, this might be supplemented or replaced by its generated trackers.

**Business Dependency Types (for manual tracking or integration):**
-   `M`: Market dependency (relationship with market conditions or customer factors)
-   `O`: Organizational dependency (relationship with internal capabilities or resources)
-   `T`: Technological dependency (relationship with technological capabilities or trends)
-   `F`: Financial dependency (relationship with funding, investment, or financial metrics)
-   `R`: Regulatory dependency (relationship with legal or regulatory factors)
-   `C`: Competitive dependency (relationship with competitor actions or positioning)
-   `S`: Strategic dependency (relationship with strategic decisions or direction)

**Relationship Characters (Common):**
-   `<`: Row depends on column.
-   `>`: Column depends on row.
-   `x`: Mutual dependency.
-   `d`: Documentation dependency.
-   `o`: Self dependency (diagonal only).
-   `n`: Verified no dependency.
-   `p`: Placeholder (unverified).
-   `s`: Semantic dependency (weak)
-   `S`: Semantic dependency (strong)

---
>>>>>>> origin/main

## VI. Mandatory Update Protocol (MUP) - Core File Updates

The MUP must be followed immediately after any state-changing action:
<<<<<<< HEAD
1. **Update `activeContext.md`**: Summarize action, impact, and new state.
2. **Update `changelog.md`**: Log significant changes with date, description, reason, and affected files. (Format detailed in Cleanup/Consolidation plugin).
3. **Update `.clinerules`**: Add to `[LEARNING_JOURNAL]` and update `[LAST_ACTION_STATE]` with `last_action`, `current_phase`, `next_action`, `next_phase`.
4. **Remember**: In addition to these core updates after *every* state-changing action, a full MUP (including plugin-specific steps) **MUST** also be performed every 5 turns/interactions, as detailed in Section XIII.
5. **Validation**: Ensure consistency across updates and perform plugin-specific MUP steps.
6. **Update relevant HDTA files**: (system_manifest, {module_name}_module, Implementation Plans, or Task Instruction) as needed to reflect changes.

## VII. Command Execution Guidelines

1. **Pre-Action Verification**: Verify file system state before changes (especially for file modifications, see Execution Plugin).
2. **Incremental Execution**: Execute step-by-step, documenting results.
3. **Error Handling**: Document and resolve command failures (see Execution Plugin Section VI for dependency command errors).
4. **Dependency Tracking**: Update trackers as needed using commands (see Set-up/Maintenance and Execution Plugins).
5. **MUP**: Follow Core and plugin-specific MUP steps post-action.

## VIII. Dependency Processor Command Overview
=======
1.  **Update `activeContext.md`**: Summarize action, impact, and new state.
2.  **Update `changelog.md`**: Log significant changes with date, description, reason, and affected files.
3.  **Update `.clinerules`**: Update `[LAST_ACTION_STATE]` with `last_action`, `current_phase`, `next_action`, `next_phase`. Update `[LEARNING_JOURNAL]` if applicable.
4.  **Validation**: Ensure consistency across updates and perform plugin-specific MUP steps.
5.  **Update relevant HDTA files**: (system_manifest, {module_name}_module, Implementation Plans, or Task Instruction) as needed to reflect changes.
6.  **Update Dependency Trackers**: If using the script, run `analyze-project`. If tracking manually, update `business_dependency_tracker.md`.

---

## VII. Instruction File Format
>>>>>>> origin/main

Instruction files for business innovation tasks should follow this structure:

<<<<<<< HEAD
**IMPORTANT: To ensure data consistency, conserve context window tokens, and leverage built-in parsing logic, ALWAYS use the `show-keys` and `show-dependencies` commands to retrieve key definitions and dependency information from tracker files (`*_tracker.md`, `*_module.md`). Avoid using `read_file` on tracker files for this purpose.** Direct reading can lead to parsing errors and consumes excessive context.

**Core Commands for CRCT Workflow:**

1.  **`analyze-project [<project_root>] [--output <json_path>] [--force-embeddings] [--force-analysis]`**:
    *   **Purpose**: The primary command for maintaining trackers. Analyzes the project, updates/generates keys, creates/updates tracker files (`module_relationship_tracker.md`, `doc_tracker.md`, mini-trackers), generates embeddings, and suggests dependencies ('p', 's', 'S'). Run this during Set-up/Maintenance and after significant code changes. Creates trackers if missing.
    *   **Example**:
    ```python
     `python -m cline_utils.dependency_system.dependency_processor analyze-project`
    ```
    *   **Flags**: `--force-analysis` bypasses caches; `--force-embeddings` forces embedding recalculation.
    *   **Errors**: Check `debug.txt`, `suggestions.log`. Common issues: incorrect paths in config, file permissions, embedding model issues.

2.  **`show-dependencies --key <key>`**:
    *   **Purpose**: Displays all known outgoing and incoming dependencies (with paths and relationship type) for a specific `<key>` by searching across *all* tracker files. Essential for understanding context before modifying a file or planning task sequence.
    *   **Example**:
    ```python
     `python -m cline_utils.dependency_system.dependency_processor show-dependencies --key 3Ba2`
    ```
        *   **IMPORTANT**: The key used with `show-dependencies` is the *row*. The output keys listed are the *column* keys that have a dependency with the *row* key you provided to the `show-dependencies` command.
    *   **Errors**: "Key Not Found" usually means the key doesn't exist in *any* tracker or `analyze-project` hasn't been run since the file was added/detected.

3.  **`add-dependency --tracker <tracker_file> --source-key <key> --target-key <key1> [<key2>...] --dep-type <char>`**:
    *   **Purpose**: Manually sets or updates the dependency relationship (`--dep-type`) between one **source key** (`--source-key`, the row) and one or more **target keys** (`--target-key`, the columns) *within the specified `<tracker_file>`*. Use this during Set-up/Maintenance (verification) or Execution (reflecting new code links) to correct suggestions or mark verified relationships ('<', '>', 'x', 'd', 'n').
    *   **Workflow Note**: During verification (Set-up/Maintenance), the key analyzed with `show-dependencies` **always serves as the `--source-key`**. The related column keys identified from the `show-dependencies` output are used as the `--target-key`(s).
    *   **IMPORTANT**: Before executing this command during the verification process (Set-up/Maintenance), you **MUST** state your reasoning for choosing the specific `--dep-type` based on your analysis of functional reliance between the source and target files/concepts.
    **Example**:
    ```python
    python -m cline_utils.dependency_system.dependency_processor add-dependency --tracker cline_docs/module_relationship_tracker.md --source-key 2Aa --target-key 1Bd 1Be --dep-type ">"
     ```
    *(Note: This command applies the *single* `--dep-type` to *all* specified target keys relative to the source key.)*
    *(Efficiency Tip: When verifying dependencies for a single source key, group multiple target keys that require the *same* dependency type into one command execution using multiple `--target-key` arguments.)*
    
    *   *(Recommendation: Specify no more than five target keys at once for clarity.)*
    
    *   **Foreign Keys (Mini-Trackers)**: When targeting a mini-tracker (`*_module.md`), `--target-key` can be a key not defined locally *if* it exists globally (in `core/global_key_map.json`). The command adds the key definition to the mini-tracker automatically.
        - Mechanism: The system will automatically:
            - Validate the foreign target key against the global map.
            - Add the foreign key's definition (key: path) to the mini-tracker's key list.
            - Rebuild the mini-tracker's grid structure to include the new key.
            - Set the specified dependency between the --source-key (which must be internal to the mini-tracker) and the newly added foreign --target-key.
        - Use Case: This is primarily for manually establishing dependencies for code that might be in progress or dependencies missed by the automated analyze-project suggestions.
    *   **Errors**: "Tracker/Key Not Found". Verify paths and keys. Ensure keys exist (run `analyze-project` if needed). Grid errors might require `analyze-project` to fix structure.

4.  **`remove-key <tracker_file> <key>`**:
    *   **Purpose**: Removes a key and its corresponding row/column definition entirely from the specified `<tracker_file>`. Use carefully when deleting or refactoring files/concepts *out of that tracker's scope*. Does *not* remove the key globally or from other trackers. Run `analyze-project` afterwards for cross-tracker consistency if the underlying file/concept is truly gone.
    *   **Example**:
    ```python
     `python -m cline_utils.dependency_system.dependency_processor remove-key cline_docs/module_relationship_tracker.md 2Aa`
    ```
    *   **Errors**: "Tracker/Key Not Found". Verify path and that the key exists *in that specific tracker*.

5.  **`show-keys --tracker <tracker_file_path>`**:
    *   **Purpose**: Displays the key definitions (`key: path`) defined *within* the specified tracker file. **Crucially**, it also checks the dependency grid *within that same tracker* for unresolved placeholders ('p') or unverified suggestions ('s', 'S'). If found in a key's row, appends `(checks needed: p, s, S)` specifying which characters require attention for that key *in this tracker*. This is the **primary method** during Set-up/Maintenance for identifying keys needing verification via `show-dependencies`.
    *   **Example**:
    ```python
     `python -m cline_utils.dependency_system.dependency_processor show-keys --tracker cline_docs/doc_tracker.md`
    ```
    *   **Output Example**:
        ```
        --- Keys Defined in doc_tracker.md ---
        1A1: docs/intro.md
        1A2: docs/setup.md (checks needed: p, s)
        2B1: docs/api/users.md (checks needed: S)
        2B2: docs/api/auth.md
        --- End of Key Definitions ---
        ```

**Configuration & Utility Commands:**

6.  **`update-config <key_path> <value>`**:
    *   **Purpose**: Updates a specific setting in the `.clinerules.config.json` file (which stores detailed configuration for the dependency system). Primarily used during setup or for tuning.
    *   **Example**: `python -m cline_utils.dependency_system.dependency_processor update-config thresholds.code_similarity 0.8`
    *   **Example**: `python -m cline_utils.dependency_system.dependency_processor update-config models.doc_model_name all-MiniLM-L6-v2`
    *   **Keys**: `paths.doc_dir`, `paths.code_root_dirs`, `models.doc_model_name`, `models.code_model_name`, `thresholds.doc_similarity`, `thresholds.code_similarity`, `compute.embedding_device`, etc.
=======
```
# {Task Name} Instructions

## Objective
{Clear, concise statement of purpose and goals}

## Context
{Background, constraints, context}

## Dependencies
{List of business factors or other tasks}

## Steps
1. {Step 1}
2. {Step 2}
...

## Expected Output
{Description of deliverables}

## Notes
{Additional considerations}
```
>>>>>>> origin/main

7.  **`reset-config`**:
    *   **Purpose**: Resets all settings in `.clinerules.config.json` to their default values. Use with caution.
    *   **Example**: `python -m cline_utils.dependency_system.dependency_processor reset-config`

8.  **`merge-trackers <primary_tracker> <secondary_tracker> [--output <output_path>]`**: Merges two tracker files. (Advanced use).
9.  **`export-tracker <tracker_file> [--format <json|csv|dot>] [--output <output_path>]`**: Exports tracker data. (Useful for visualization/external analysis).
10. **`clear-caches`**: Clears internal caches used by the dependency system (embeddings, analysis results). Useful for debugging or forcing re-computation.

## VIII. Command Execution Guidelines

1.  **Pre-Action Verification**: Verify file system state before changes.
2.  **Incremental Execution**: Execute step-by-step, documenting results.
3.  **Error Handling**: Document and resolve command failures.
4.  **Business Dependency Tracking**: Update business factor relationships as needed (manually or via script).
5.  **MUP**: Follow Core and plugin-specific MUP steps post-action.

---

## IX. Business Innovation Templates

The BRCT framework includes specialized templates in `src/business_templates/` for various aspects of the business innovation process:

1.  **Idea Generation Template**: Structured approach to generating business ideas with recursive decomposition
2.  **Idea Evaluation Template**: Framework for evaluating ideas based on feasibility, viability, and desirability criteria
3.  **Business Model Canvas**: Enhanced canvas with recursive analysis and dependency tracking
4.  **SWOT Analysis Template**: Comprehensive SWOT analysis with component-level breakdown
5.  **Market Research Template**: Structured approach to market analysis with recursive decomposition

Use these templates as starting points for documenting the business innovation process. Each template incorporates chain-of-thought documentation sections to ensure transparency in reasoning and decision-making.

---

## X. Plugin Usage Guidance

<<<<<<< HEAD
**Always check `.clinerules` for `next_phase` and load the corresponding plugin.**
- **Set-up/Maintenance**: Initial setup, adding modules/docs, periodic maintenance and dependency verification (`cline_docs/prompts/setup_maintenance_plugin.md`).
- **Strategy**: Task decomposition, HDTA planning, dependency-driven sequencing (`cline_docs/prompts/strategy_plugin.md`).
- **Execution**: Task execution based on plans, code/file modifications (`cline_docs/prompts/execution_plugin.md`).
- **Cleanup/Consolidation**: Post-execution organization, changelog grooming, temporary file cleanup (`cline_docs/prompts/cleanup_consolidation_plugin.md`).
=======
**Always check `.clinerules` for `current_phase`.**
-   **Set-up/Maintenance**: Initial setup, defining business factors, identifying code roots, periodic maintenance, running `analyze-project` if using script (`cline_docs/prompts/setup_maintenance_plugin.md`).
-   **Strategy**: Task decomposition, business idea generation, evaluation, instruction file creation, prioritization (`cline_docs/prompts/strategy_plugin.md`). Use `strategy_tasks` directory to store detailed plans and strategic approaches.
-   **Execution**: Task execution, business model implementation, document creation, code/template modification (`cline_docs/prompts/execution_plugin.md`).

---
>>>>>>> origin/main

## XI. Identifying Code Root Directories

This process is part of the **Set-up/Maintenance phase** and is performed if the `[CODE_ROOT_DIRECTORIES]` section in `.clinerules` is empty or missing.

<<<<<<< HEAD
**Goal:** Identify top-level directories containing the project's *own* source code, *excluding* documentation, third-party libraries, virtual environments, build directories, configuration directories, and CRCT system directories (`cline_utils`, `cline_docs`).

**Heuristics and Steps:**
1. **Initial Scan:** Read the contents of the project root directory (where `.clinerules` is located).
2. **Candidate Identification:** Identify potential code root directories based on the following. It's generally better to initially include a directory that might not be a primary code root than to exclude one that is.
   - **Common Names:** Look for directories like `src`, `lib`, `app`, `core`, `packages`, or the project name itself.
   - **Presence of Code Files:** Prioritize directories that *directly* contain relevant project code files (e.g., `.py`, `.js`, `.ts`, `.java`, `.cpp`). Check subdirectories too, but the root being identified should be the top-level container (e.g., identify `src`, not `src/module1`).
   - **Absence of Non-Code Indicators:** *Exclude* directories that are clearly *not* for project source code:
     - `.git`, `.svn`, `.hg` (version control)
     - `docs`, `documentation` (project documentation - see Section XI)
     - `tests` (often separate, but sometimes included if tightly coupled; consider project structure)
     - `venv`, `env`, `.venv`, `node_modules`, `vendor`, `third_party` (dependencies/environments)
     - `__pycache__`, `build`, `dist`, `target`, `out` (build artifacts/cache)
     - `.vscode`, `.idea`, `.settings` (IDE configuration)
     - `cline_docs`, `cline_utils` (CRCT system files)
     - Directories containing primarily configuration files (`.ini`, `.yaml`, `.toml`, `.json`) *unless* those files are clearly part of your project's core logic.
3. **Chain-of-Thought Reasoning:** For each potential directory, generate a chain of thought explaining *why* it is being considered (or rejected).
4. **Update `.clinerules` with `[CODE_ROOT_DIRECTORIES]`.** Make sure `next_action` is specified, e.g., "Generate Keys", or another setup step if incomplete.
5. **MUP**: Follow the Mandatory Update Protocol.
=======
**Goal:** Identify top-level directories for project's core business templates/code, *excluding* documentation, framework utilities (`cline_utils`), third-party libraries, virtual environments, build directories, and configuration directories.

**Heuristics and Steps:**
1.  **Initial Scan:** Read the contents of the project root directory.
2.  **Candidate Identification:** Identify potential code root directories. Better to include a directory that is not a code root than to exclude one.
    -   **Common Names:** Look for `src`, `lib`, `app`, `packages`, or the project name.
    -   **Presence of Core Files:** Prioritize directories containing core business templates or project-specific code.
    -   **Absence of Non-Code Indicators:** *Exclude* `.git`, `docs`, `venv`, `node_modules`, `__pycache__`, `build`, `.vscode`, `cline_docs`, `cline_utils` (as it's framework utility).
    -   **Structure**: If you see `src/module1/file1.py`, include `src`, not `src/module1`.
3.  **Chain-of-Thought Reasoning:** For each potential directory, explain *why* it is being considered/rejected.
4.  **Update `.clinerules` with `[CODE_ROOT_DIRECTORIES]` and `[DOC_DIRECTORIES]`.** Set `next_action`.
5.  **MUP**: Follow the Mandatory Update Protocol.
>>>>>>> origin/main

**Example Chain of Thought:**
"Scanning the project root, I see directories: `.vscode`, `docs`, `cline_docs`, `src`, `cline_utils`, `venv`. `.vscode` and `venv` are excluded (IDE config, venv). `docs` and `cline_docs` are excluded (documentation, operational memory). `cline_utils` is excluded (framework utility). `src` contains `business_templates` and `business_dependency_tracker.md`, making it the primary candidate for business-specific content. Therefore, I will add `src` to `[CODE_ROOT_DIRECTORIES]` and `docs` to `[DOC_DIRECTORIES]` in `.clinerules`."

## XI. Identifying Documentation Directories

<<<<<<< HEAD
This process is part of the **Set-up/Maintenance phase** and should be performed alongside identifying code root directories if the `[DOC_DIRECTORIES]` section in `.clinerules` is empty or missing.
=======
## XII. Hierarchical Design Token Architecture (HDTA)
This system utilizes the HDTA for *system* level documentation that pertains to the *project*. Information is organized into four tiers:
>>>>>>> origin/main

**Goal:** Identify directories containing the project's *own* documentation, excluding source code, tests, build artifacts, configuration, and CRCT system documentation (`cline_docs`).

<<<<<<< HEAD
**Heuristics and Steps:**
1. **Initial Scan:** Read the contents of the project root directory.
2. **Candidate Identification:** Identify potential documentation directories based on:
   - **Common Names:** Look for directories with names like `docs`, `documentation`, `wiki`, `manuals`, or project-specific documentation folders.
   - **Content Types:** Prioritize directories containing Markdown (`.md`), reStructuredText (`.rst`), HTML, or other documentation formats.
   - **Absence of Code/Other Indicators:** Exclude directories primarily containing code, tests, dependencies, build artifacts, or CRCT system files (`cline_docs`, `cline_utils`).
3. **Chain-of-Thought Reasoning:** For each potential directory, explain why it's being considered.
4. **Update `.clinerules` with `[DOC_DIRECTORIES]`.**
5. **MUP:** Follow the Mandatory Update Protocol.
=======
See CRCT documentation or templates for specific formats if needed. Dependencies between these documents are managed *manually* by the LLM unless using `doc_tracker.md`.
>>>>>>> origin/main

**Example Chain of Thought:**
"Scanning the project root, I see directories: `docs`, `documentation`, `src`, `tests`. `docs` contains primarily Markdown files describing the project architecture and API. `documentation` contains user guides in HTML format. Both appear to be documentation directories. `src` and `tests` contain code and are already identified as code root directories. Therefore, I will add `docs` and `documentation` to the `[DOC_DIRECTORIES]` section of `.clinerules`."

<<<<<<< HEAD
## XII. Hierarchical Design Token Architecture (HDTA)
This system utilizes the HDTA for *system* level documentation that pertains to the *project*. Information is organized into four tiers to facilitate recursive decomposition and planning:
=======
## XIII. Mandatory Periodic Documentation Updates
>>>>>>> origin/main

1.  **System Manifest (`system_manifest.md`):** Top-level overview defining the project's purpose, core components (Domain Modules), and overall architecture. Located in `{memory_dir}/`. Created/updated during Set-up/Maintenance and Strategy.
2.  **Domain Modules (`{module_name}_module.md`):** Describe major functional areas or high-level components identified in the Manifest. Defines scope, interfaces, high-level implementation details, and links to relevant Implementation Plans. Located within the module's directory (`{module_dir}/`). Also serves as a **mini-tracker** for the module. Created/updated during Set-up/Maintenance and Strategy.
3.  **Implementation Plans (`implementation_plan_*.md`):** Detail the approach for specific features, refactors, or significant changes within a Domain Module. Outlines objectives, affected components, high-level steps, design decisions, and links to specific Task Instructions. Located within `{module_dir}/`. Created/updated during Strategy.
4.  **Task Instructions (`{task_name}.md`):** Procedural guidance for atomic, executable tasks. Details objective, step-by-step actions, minimal necessary context links (dependencies), and expected output. Linked from Implementation Plans. Located typically near relevant code or in a dedicated tasks folder. Created during Strategy, executed during Execution.

<<<<<<< HEAD
See the `cline_docs/templates/` directory for the specific Markdown format for each tier. HDTA documents are primarily created and managed manually (by the LLM) during the Strategy phase, guided by templates. Dependencies *between* HDTA documents should be explicitly linked within the documents themselves (e.g., a Plan lists its Tasks).

## XIII. Mandatory Periodic Documentation Updates

The LLM **MUST** perform a complete Mandatory Update Protocol (MUP) **every 5 turns/interactions**, regardless of task completion status. This ensures regular state synchronization, prevents context drift, and forces periodic reflection.

**Procedure for 5-Turn MUP:**
1. Count interactions since last MUP
2. On the 5th turn, pause current task execution
3. Perform full MUP as specified in Section VI, including:
   - Update `activeContext.md` with current progress
   - Update `changelog.md` with significant changes made to project files
   - Update `.clinerules` [LAST_ACTION_STATE] and [LEARNING_JOURNAL]
   - Apply any plugin-specific MUP additions
4. Clean up completed tasks:
   - Mark completed steps in instruction files
   - Update dependency trackers to reflect new relationships (if applicable, using `add-dependency` or potentially `analyze-project` if many changes occurred)
   - Archive or annotate completed task documentation
5. Resume task execution only after MUP completion
=======
1.  Regular documentation of progress
2.  Consistent state maintenance
3.  Clean-up of completed tasks
4.  Prevention of context drift

**Procedure for 5-Turn MUP:**
1.  Count interactions since last MUP
2.  On the 5th turn, pause current task execution
3.  Perform full MUP as specified in Section VI:
    -   Update `activeContext.md` with current progress
    -   Update `changelog.md` with significant changes made to project files
    -   Update `.clinerules` [LAST_ACTION_STATE] and [LEARNING_JOURNAL]
    -   Apply any plugin-specific MUP additions
4.  Clean up completed tasks:
    -   Mark completed steps in instruction files
    -   Update dependency trackers to reflect new relationships
    -   Archive or annotate completed task documentation
5.  Resume task execution only after MUP completion
>>>>>>> origin/main

**Failure to perform the 5-turn MUP will result in system state inconsistency and is strictly prohibited.**

## XIV. Conclusion

<<<<<<< HEAD
The CRCT framework manages complex tasks via recursive decomposition and persistent state across distinct phases: Set-up/Maintenance, Strategy, Execution, and Cleanup/Consolidation. Adhere to this core prompt and the phase-specific plugin instructions loaded from `cline_docs/prompts/` for effective task management. Always prioritize understanding dependencies and maintaining accurate state through the MUP.

=======
## XIV. Conclusion

The BRCT framework adapts the CRCT v7.2 system for business innovation processes through recursive decomposition and persistent state. Adhere to this prompt and plugin instructions in `cline_docs/prompts/` for effective business innovation management.

>>>>>>> origin/main
**Adhere to the "Don't Repeat Yourself" (DRY) and Separation of Concerns principles.**
