# **Cline Recursive Chain-of-Thought System (CRCT) - Strategy Plugin (Iterative)**

This Plugin provides detailed instructions and procedures for the Strategy phase of the CRCT system. It guides an iterative, exhaustive process of **constructing and maintaining a comprehensive, dependency-aware project roadmap**. This roadmap is built by translating high-level system design and cycle goals into a fully sequenced and actionable implementation plan, embodied in the Hierarchical Design Token Architecture (HDTA). Planning is performed by focusing on **one defined area (module, feature set) at a time** to maintain minimal context, recursively building the roadmap until all components of the cycle's goals are planned and then unified. All `Strategy_*` tasks for planning and all `Execution_*` tasks comprising the roadmap for the targeted work of the cycle must be defined before transitioning to Execution.
Use this in conjunction with the Core System Prompt.

**Entering and Exiting Strategy Phase**

**Entering Strategy Phase:**
1.  **`.clinerules` Check (Mandatory First Step)**: Read `.clinerules` file content.
2.  **Determine Current State**:
    *   If `[LAST_ACTION_STATE]` indicates `current_phase: "Strategy"`, proceed with the instructions below, resuming from the action indicated by `next_action`. Consult `activeContext.md` for finer-grained state within that action.
    *   If `[LAST_ACTION_STATE]` indicates `next_phase: "Strategy"`, this signifies a transition from a previous phase (likely Set-up/Maintenance). Proceed with the instructions below, starting from **Section II, Step 0**.
3.  **User Trigger**: If starting a new session and `.clinerules` indicates the system *was* in Strategy or *should transition* to Strategy, proceed with these instructions.

**Exiting Strategy Phase:**
1.  **Completion Criteria (Mandatory Check)**: Verify ALL the following are met for the current Strategy cycle's goals, signifying a complete and actionable roadmap for this cycle:
    *   All identified areas/modules relevant to the cycle's goals have been planned according to the iterative process, and their respective HDTA documents are complete.
    *   A comprehensive implementation sequence based on dependency analysis has been defined for all planned work (documented in relevant Implementation Plans or `*_module.md` files, and unified in `roadmap_summary_[cycle_id].md`).
    *   All high-priority work planned for this strategy cycle has been decomposed into atomic Task Instructions (`*.md`), with clear phase prefixes (`Strategy_*`, `Execution_*`), and explicit minimal context links.
    *   All necessary HDTA documents (System Manifest, Domain Modules, Implementation Plans, Task Instructions) relevant to the planned work have been created or updated, forming a cohesive and linked roadmap. No placeholders or incomplete sections relevant to the planned work remain.
    *   `Execution_*` tasks have been sequenced and prioritized within their respective areas and reviewed for inter-area consistency during unification.
    *   All HDTA documents are correctly linked (Tasks from Plans, Plans from Modules, Modules from Manifest), reflecting the roadmap structure.
    *   All `Strategy_*` tasks identified and scoped for completion *during this Strategy phase* (including those for planning sub-components, HDTA creation/refinement, or resolving specific planning ambiguities) have been completed.
    *   The `hierarchical_task_checklist_[cycle_id].md` reflects the completed planning state for all cycle goals.
    *   The `roadmap_summary_[cycle_id].md` has been created, reviewed for coherence, and accurately reflects the unified roadmap for all cycle goals.
2.  **`.clinerules` Update (Mandatory MUP Step)**: If completion criteria are met, update `.clinerules` `[LAST_ACTION_STATE]` **exactly** as follows:
    ```
    last_action: "Completed Strategy Phase: Unified Roadmap for All Cycle Goals"
    current_phase: "Strategy"
    next_action: "Phase Complete - User Action Required"
    next_phase: "Execution"
    ```
    Also, consider if any profound, reusable insights were gained during this phase that warrant addition to the `[LEARNING_JOURNAL]` as per Core Prompt guidelines.
3.  **Pause for User Action**: After successfully updating `.clinerules`, state that the Strategy phase is complete and you are awaiting user action (e.g., a new session start) to begin the Execution phase. Do not proceed further in this session. Refer to Core System Prompt, Section III for the phase transition checklist.

## I. Phase Objective & Guiding Principles

**Objective**: The primary objective of the Strategy Phase is to **construct, refine, and maintain a comprehensive, dependency-aware, and actionable project roadmap** for the current development cycle's goals. This is achieved by iteratively planning **one defined area (module, feature, or task set) at a time**, like assembling Lego blocks. This roadmap is hierarchically structured using the HDTA (System Manifest → Domain Modules → Implementation Plans → Task Instructions). The process is iterative, focusing on one defined "area" (module, feature) at a time to manage complexity and context. For each area, the relevant segment of the roadmap is built by reviewing high-level context, deeply analyzing dependencies, decomposing work into atomic Task Instructions with minimal context, and sequencing these tasks. The phase culminates in unifying these area-specific plans into a cohesive `roadmap_summary_[cycle_id].md` and ensuring all `Strategy_*` planning tasks are complete before transitioning to Execution.

**CRITICAL CONSTRAINT: MINIMAL CONTEXT LOADING.** Due to LLM context window limitations, each planning step, especially within a loop for a specific area, MUST focus on loading and processing only the information strictly necessary for that step and area. Avoid loading entire large files if only sections or summaries are needed. Proactively manage what is loaded into your working context.

**Guiding Principles**:
1.  **Roadmap as Primary Output**: All activities in this phase contribute to building or refining the hierarchical project roadmap, embodied by the HDTA documents.
2.  **Iterative Area-Based Planning (Lego-Block Approach)**: Decompose the overall cycle goals into manageable "areas." Plan each area exhaustively in a dedicated loop (see Section II), treating it as a segment of the overall roadmap to be meticulously detailed with atomic tasks (Lego blocks).
3.  **Minimal Context Loading (CRITICAL)**: In each step of a planning loop, load only the documents, dependency information, and sections of files essential for the current area and task. **This is paramount to avoid context overload and maintain focus.**
4.  **Mandatory Dependency Analysis (Scoped & Deep)**:
    *   **CRITICAL FIRST STEP for each Area**: Before detailed planning for an area, analyze its specific dependencies using `show-keys` and `show-dependencies`.
   *   **Leverage Visualizations**: Utilize auto-generated diagrams located in `{memory_dir}\dependency_diagrams` or generate focused diagrams (`visualize-dependencies --key ...`) as aids to comprehend complex relationships within or between areas, complementing textual analysis.
    *   **Deep Understanding**: For these dependencies, use `read_file` on *relevant sections* of linked files to understand *why* the dependency exists (function call, data structure, conceptual prerequisite), what *specific parts* are relevant, and the *implication* for implementation order.
    *   **CRITICAL FAILURE**: Failure to check and understand relevant dependencies is a CRITICAL FAILURE, risking an inaccurate or unworkable roadmap and project failure.
5.  **Top-Down Review, Bottom-Up Task Building (Per Area)**: For each area, start by reviewing its high-level context within the roadmap (System Manifest (context) → relevant Domain Module → relevant Implementation Plan(s) for that area) to align planning. Then, build out atomic Task Instructions with minimal context links.
6.  **Atomic Task Instructions**: Decompose each area's work into small, actionable `Strategy_*` or `Execution_*` tasks, each in its own `*.md` file. Each task must have clear objectives, precise steps, and **explicitly listed minimal context links and dependencies**. If a task requires linking to more than 3-4 separate code files or many disparate documentation sections, consider if it's truly atomic.
7.  **HDTA as the Roadmap's Structure**: Create or update HDTA documents (Domain Modules, Implementation Plans, Task Instructions) *as needed* for the current area, ensuring they are complete, accurate, and correctly linked to form a coherent segment of the roadmap. Use templates from `cline_docs/templates/`.
8.  **Trackers for Progress & Transparency**:
    *   `hdta_review_progress_[session_id].md`: For logging document review status.
    *   `hierarchical_task_checklist_[cycle_id].md`: To track the planning status of areas and their constituent tasks within the cycle goals, effectively tracking roadmap completion.
9.  **Unification and Review for a Cohesive Roadmap**: After planning all areas relevant to the cycle goals, unify their individual plans. Review the combined tasks to ensure alignment, resolve inter-area dependency conflicts, and create a cohesive `roadmap_summary_[cycle_id].md` representing the complete plan for the cycle.
10. **Recursive Decomposition for Complexity**: If an aspect within an area is too complex for immediate atomic task definition (within context limits), create a specific `Strategy_PlanSubComponent_*.md` task. This task's objective will be to perform the detailed planning for that sub-component, effectively drilling down to a more granular level of the roadmap.
11. **Clear Phase Labeling**: Tasks must be prefixed with `Strategy_*` (for planning, analysis, HDTA creation/updates, roadmap construction completed in this phase) or `Execution_*` (for implementation tasks defined in the roadmap, to be passed to the Execution phase).

## II. Strategic Planning Workflow: Iterative Roadmap Development

**Directive**: Construct and refine a comprehensive implementation roadmap for the current cycle's goals by:
1. Defining overall cycle goals and identifying relevant areas of the roadmap to be detailed.
2. Iteratively planning one area/module at a time, using minimal context and following the steps below to build out its segment of the roadmap.
3. Completing all `Strategy_*` tasks associated with the planning process and roadmap construction.
4. Unifying the plans for all areas into a cohesive, final roadmap for the cycle.

**Procedure**:

**Phase Initialization & Overall Goal Definition**

0.  **Initialize Strategy Cycle & Define Overall Cycle Goals.**
    *   **Action A (.clinerules & Trackers Setup)**:
        *   Read `.clinerules` to confirm current state (`current_phase`, `next_action`).
        *   Check `{memory_dir}/` for unarchived `hdta_review_progress_*.md` or `hierarchical_task_checklist_*.md` files from previous cycles. Note in `activeContext.md` any incomplete items that might need transfer to new files for *this* cycle; mark old files for future Cleanup/Consolidation. State: "Checked for unarchived tracker files. Found: [List or 'None']."
        *   Create/Initialize `hdta_review_progress_[session_id].md` using `cline_docs/templates/hdta_review_progress_template.md`. Populate "Date Created" and "Session ID". State: "Initialized HDTA Review Progress Tracker: `hdta_review_progress_[session_id].md`."
    *   **Action B (Define Overall Cycle Goals)**:
        *   Read `activeContext.md`, `system_manifest.md` (for high-level project scope), and `progress.md` (for overall project status) to understand current project status and potential focus areas for roadmap development.
        *   Propose specific, high-level goals for *this entire Strategy engagement/cycle*. These goals will define the scope of the roadmap to be detailed. State: "Proposed overall goals for this Strategy cycle: [List of goals]."
        *   If goals are unclear or too broad for a single cycle, use `ask_followup_question` for user clarification and confirmation.
        *   Once confirmed, update `activeContext.md` with these *overall cycle goals* and any specific directives from the user regarding focus or priorities. State: "Confirmed overall cycle goals: [List]. Documented in `activeContext.md`."
    *   **Action C (Initialize Hierarchical Task Checklist with Areas for Roadmap)**:
        *   Create `hierarchical_task_checklist_[cycle_id].md` using `cline_docs/templates/hierarchical_task_checklist_template.md` (replace `[cycle_id]` with a unique identifier for the current planning cycle, e.g., date-time based).
        *   Populate this checklist by listing all major Domain Modules (from `system_manifest.md`) or distinct feature areas that are **directly relevant to the confirmed overall cycle goals**. These become the "areas" for which roadmap segments will be detailed. Mark them initially as "[ ] Unplanned." State: "Initialized `hierarchical_task_checklist_[cycle_id].md`. Populated with areas relevant to cycle goals for roadmap construction: [List of areas, e.g., Module A, Feature Set B]."
    *   **Action D (Initial High-Level Dependency Overview - Optional but Recommended)**:
        *   Briefly review `module_relationship_tracker.md` using `show-keys` and `show-dependencies` focused on very high-level keys from `system_manifest.md` or keys representing entire modules that are part of the overall cycle goals. The aim is to get a general sense of major interdependencies between these high-level areas *before* selecting the first one for detailed planning. Do *not* perform a deep dive yet. State: "Performed high-level dependency overview for cycle goals. Key inter-area interactions noted: [Summary if any, or 'None apparent at this level']." This can inform the order of area selection.
        *   **Check Auto-Generated Diagrams**: Check if `config["visualization"]["auto_generate_on_analyze"]` is true. If so, check for the existence of `<memory_dir>/dependency_diagrams/project_overview_dependencies.mermaid` and relevant `<memory_dir>/dependency_diagrams/module_[ModuleKey]_dependencies.mermaid` files.
        *   **Briefly Review Overview Diagram (if exists)**: Use `read_file` to load `project_overview_dependencies.mermaid`. Analyze the Mermaid structure *textually* to gain a visual sense of major component groupings and connections relevant to the cycle goals. State: "Reviewed auto-generated project overview diagram (if found). Initial visual insights: [Brief summary of structure/connections relevant to goals]." **Do not attempt to render the diagram.**
    *   **State**: "Strategy Cycle Initialized. Overall cycle goals defined and high-level areas for roadmap detailing identified. Ready to select first area for focused planning."
    *   **Update `.clinerules` `[LAST_ACTION_STATE]`**: `next_action: "Select Area for Planning"`. Update `activeContext.md` to note completion of Step 0.

**Iterative Area Planning Loop** (Repeat Steps 1-7 for each "area" identified in `hierarchical_task_checklist_[cycle_id].md` relevant to cycle goals)

1.  **Select ONE Area for Focused Planning (Loop Start).**
    *   **Directive**: Choose one "area" (e.g., a Domain Module, a specific feature set) from `hierarchical_task_checklist_[cycle_id].md` that is marked as "[ ] Unplanned" (or "[ ] Partially Planned" if resuming a previously started area) and falls under the overall cycle goals. Prioritize based on user input, `activeContext.md` notes, logical prerequisites (e.g., from Step 0.D), or potential to unblock other areas.
    *   **Action**: Consult `hierarchical_task_checklist_[cycle_id].md` and `activeContext.md`.
    *   **Action**: Select **one** area. State: "Selected area for this planning loop: `[Area Name]`. Current status in checklist: `[Status from checklist]`."
    *   **Action**: Define specific, measurable objectives for planning *this area* in this iteration. What specific HDTA outputs (segments of the roadmap) are expected for this area? Store these objectives in `activeContext.md` under a heading for the current area. State: "Objectives for planning `[Area Name]` in this loop: `[List objectives, e.g., Define Module_X_module.md, Create Implementation Plan for Feature Y, Decompose Feature Y into Execution Tasks]`. Objectives documented in `activeContext.md`."
    *   **Action**: Update `activeContext.md`: Set `current_planning_area: "[Area Name]"` and list its specific planning objectives for this loop.
    *   **State**: "Area `[Area Name]` selected. Objectives for this area's planning loop defined in `activeContext.md`. Proceeding to focused dependency analysis for this area."
    *   **Update `.clinerules` `[LAST_ACTION_STATE]`**: `next_action: "Analyze Dependencies for Selected Area"`. Update `activeContext.md` to note completion of Step 1 for this area.

2.  **Focused Dependency Analysis for the SELECTED Area.**
    *   **CRITICAL STEP**: Ground this area's segment of the roadmap in its specific system constraints. Failure to perform this thoroughly is a CRITICAL FAILURE.
    *   **Directive**: Analyze dependencies specifically *within and immediately impacting* the `[Area Name]`. Load only necessary tracker information and file sections.
    *   **Action (Identify Keys)**: Identify keys relevant to `[Area Name]` (e.g., from its `*_module.md` if it exists, key files within its conceptual scope, or keys from `doc_tracker.md` if it's a documentation-heavy area). Use `show-keys --tracker <relevant_tracker>` *filtered for this area if possible, or on its mini-tracker*.
    *   **Action (Show Dependencies)**: For each primary key of interest *within this area's scope*, use `show-dependencies --key <key>`. State: "Executed `show-dependencies --key {key}` for `[Area Name]`. Reviewed dependencies: `{summary_of_relationships_and_their_types}`."
    *   **Action (Consult/Generate Diagram)**:
        *   **Check Auto-Generated:** If `[AreaName]` corresponds to a module key (e.g., "1B") and auto-generation is enabled, check for `<memory_dir>/dependency_diagrams/module_[AreaName]_dependencies.mermaid`. If found, `read_file` its content. State: "Reading auto-generated module diagram for `[AreaName]`."
        *   **Generate Focused (If Needed):** If no relevant auto-diagram exists, OR if the area is not a standard module, OR if a specific intersection of keys needs visualizing, generate an on-demand diagram. Use `python -m cline_utils.dependency_system.dependency_processor visualize-dependencies --key <key1> [--key <key2> ...] --output {memory_dir}/[AreaNameOrFocus]_deps_visualization.md`. State: "Generated focused dependency visualization for `[AreaName/Focus]` saved to `{memory_dir}/[AreaNameOrFocus]_deps_visualization.md`."
        *   **Analyze Diagram Structure**: Review the Mermaid code (from read file or output confirmation). Note key connections, groupings, or potential complexities highlighted visually. State: "Analyzed diagram structure. Visual insights: [e.g., Key X is highly connected internally, Key Y bridges to external Module Z]."
    *   **Action (Deep Understanding - MINIMAL LOAD & FOCUSED)**: For dependencies ('<', '>', 'x', 'd') identified above that *directly impact the plan for this area* (i.e., they suggest prerequisites or co-requisites for work *within this area*):
        *   Use `read_file` to examine *only relevant sections* of the source and target files (e.g., specific function signatures, class definitions, relevant documentation paragraphs).
        *   Ask and document (in `activeContext.md` or a temporary scratchpad if extensive, to be summarized):
            *   *Why* does A depend on B in the context of `[Area Name]`? (Is it a function call, data structure usage, a conceptual prerequisite for understanding, a direct include/import?)
            *   What *specific parts* of B are relevant to A for this area?
            *   What is the *implication* for implementation order or task definition *within this area's roadmap segment*?
        *   State: "Deepened analysis for dependency between `{key_a}` and `{key_b}` related to `[Area Name]`. Confirmed `{key_a}` requires/is_related_to `{key_b}` due to `{detailed_reason_based_on_file_content}`. Sequencing implication for this area: `[e.g., Task for key_b component must precede task for key_a component within this area's plan]`."
    *   **State**: "Completed focused dependency analysis for area `[Area Name]`. Key relationships and their implications for local sequencing and roadmap construction understood. Proceeding to HDTA review and creation for this area."
    *   **Update `.clinerules` `[LAST_ACTION_STATE]`**: `next_action: "Review/Create HDTA for Selected Area"`. Update `activeContext.md` to note completion of Step 2 for this area.

3.  **Review/Create HDTA Documents for the SELECTED Area (Strict Top-Down, Minimal Load).**
    *   **Directive**: Review, update, or create HDTA documents (System Manifest for context, then Domain Module, then Implementation Plan(s)) **strictly for the `[Area Name]`**, following a top-down hierarchy to build its segment of the roadmap. Load minimal content necessary for each step. Update `hdta_review_progress_[session_id].md` after each document action.
    *   **Action (System Manifest - Context Only)**:
        *   Briefly `read_file` `system_manifest.md`. Scan *only* for high-level architectural context, links to the Domain Module representing `[Area Name]` (if it exists), or to understand where a new module for `[Area Name]` would fit in the overall roadmap. **Do not load or parse the entire file if not needed for this area's context.**
        *   State: "Reviewed `system_manifest.md` for high-level context related to `[Area Name]`. `[Note any direct relevance or if [Area Name] as a new module needs adding later]`."
        *   Update `hdta_review_progress_[session_id].md` for `system_manifest.md` (likely "Reviewed").
    *   **Action (Domain Module - Focus on `[Area Name]`)**:
        *   Target the `[Area Name]_module.md` file (or equivalent if `[Area Name]` is a feature set within a larger existing module).
        *   Check existence. If missing and `[Area Name]` represents a new module, state intention to create it using `cline_docs/templates/module_template.md`.
        *   Use `read_file` to load its content (or the template if creating). **Load only this specific module file.**
        *   Review/Update/Create the module document. Ensure it comprehensively describes `[Area Name]`'s purpose, interfaces, key components, high-level implementation details, and lists its associated Implementation Plans (to be defined/linked next). This forms a key part of the roadmap for this area.
        *   `write_to_file` to save changes to `[Area Name]_module.md`. State: "Reviewed/Updated/Created `[Area Name]_module.md`."
        *   Update `hdta_review_progress_[session_id].md`: Mark `[Area Name]_module.md` status (Reviewed/Updated/Created) and add notes.
    *   **Action (Implementation Plan(s) - Focus on `[Area Name]` objectives)**:
        *   Based on the objectives for `[Area Name]` (from `activeContext.md`) and its `_module.md` (if applicable), identify or determine necessary `implementation_plan_*.md` files *specifically for achieving the objectives of `[Area Name]`*. (e.g., `implementation_plan_FeatureY_for_ModuleX.md`).
        *   For each such plan:
            *   Check existence. If missing, state intention to create using `cline_docs/templates/implementation_plan_template.md`.
            *   Use `read_file` to load its content (or template). **Load only this specific plan file.**
            *   Review/Update/Create the plan. Detail its specific objectives, affected components/files *within this area*, high-level steps, design decisions, algorithms, data flow, and a section for the sequence of atomic Task Instructions (to be populated in Step 4 & 5). This plan is a detailed segment of the roadmap.
            *   `write_to_file` to save changes. State: "Reviewed/Updated/Created `implementation_plan_[plan_name].md` for `[Area Name]`."
            *   Link this Implementation Plan from the `[Area Name]_module.md` if applicable. Update and save `[Area Name]_module.md`.
            *   Update `hdta_review_progress_[session_id].md`: Mark plan status and add notes.
    *   **Add Missing Functional Dependency Links (If Found)**: If, during HDTA creation for this area, you identify crucial functional dependency links (code-to-doc, or between code elements within this area) that were missed during Set-up/Maintenance and are necessary for context *for this area's plan*, use `add-dependency` to add them to the appropriate tracker (usually the mini-tracker for `[Area Name]_module.md` or a relevant file's mini-tracker if it has one). State your reasoning clearly. This is for immediate, critical needs, not a full re-verification.
    *   **State**: "Completed HDTA document review/creation (Manifest context, Domain Module, Implementation Plan(s)) for area `[Area Name]`, forming its core roadmap segment. Proceeding to decompose into atomic tasks."
    *   **Update `.clinerules` `[LAST_ACTION_STATE]`**: `next_action: "Decompose Area into Atomic Tasks"`. Update `activeContext.md` to note completion of Step 3 for this area.

4.  **Decompose Area into Atomic Tasks & Define Task Instructions.**
    *   **Directive**: Based on the Implementation Plan(s) for `[Area Name]`, break down work into the smallest logical, actionable `Strategy_*` or `Execution_*` Task Instructions. These tasks are the most granular part of the roadmap.
    *   **Action**: For each Implementation Plan associated with `[Area Name]`:
        *   Iterate through its high-level steps. For each step that requires distinct action:
            *   Determine if it's a `Strategy_*` (planning, analysis, further HDTA refinement for a sub-part of the roadmap) or `Execution_*` (implementation, file creation/modification, testing setup) task.
            *   Create a new task file (e.g., `Execution_ImplementFeatureXPart1.md`, `Strategy_RefineAlgorithmForSubmoduleY.md`) using `cline_docs/templates/task_template.md`.
            *   **Fill in ALL required sections of the task template meticulously**:
                *   `Objective`: Clear, atomic goal for this single task.
                *   **`Parent`**: Link to the parent Implementation Plan file.
                *   **`Context (Minimal Required)`**: Critically important. List *only* essential links and information:
                    *   Specific function/class definitions (e.g., `path/to/file.py#MyClass.my_method`).
                    *   Relevant documentation keys/sections (e.g., `doc_tracker_key:1A2#SectionName`).
                    *   Required data structures or interface definitions.
                    *   Links to prerequisite Task Instruction keys *if already defined and stable, especially if they produce a direct input for this task*.
                    *   **AVOID linking entire files unless absolutely unavoidable and the file is small and directly relevant in its entirety.** State justification if an entire file is linked.
                *   `Steps`: Precise, step-by-step instructions for the LLM executing this task.
                *   `Dependencies (Requires/Blocks)`: List keys/file names of other Task Instructions this task depends on (`Requires`) or that depend on it (`Blocks`). Focus primarily on tasks *within this area's plan* or to well-defined interface tasks from other *already planned* areas.
                *   `Expected Output`: What success looks like for this task (e.g., "Function X implemented in file Y.py", "Section Z of doc A.md updated").
            *   `write_to_file` to save the new Task Instruction file. State: "Created Task Instruction: `{task_file_name}` for area `[Area Name]`."
            *   Update `hdta_review_progress_[session_id].md` for this new task file (Status: Created).
            *   Link this new task from its parent Implementation Plan (in the `Tasks` section). `write_to_file` the updated Implementation Plan.
            *   Update `hierarchical_task_checklist_[cycle_id].md` under `[Area Name]` -> relevant Implementation Plan, to list this task and mark it as "[ ] Defined."
    *   **Action (Handling Complexity Recursively)**: If a part of `[Area Name]` (or a step in an Implementation Plan) is too complex or large for immediate atomic task definition within reasonable context limits:
        *   Create a `Strategy_PlanSubComponent_[SubComponentName].md` task. This task's objective will be to perform the detailed planning (further decomposition, more specific HDTA) for that sub-component, creating a more detailed sub-segment of the roadmap.
        *   This `Strategy_PlanSubComponent_*.md` task might effectively add `[SubComponentName]` as a new, smaller "area" to be addressed in a future planning loop, or it might be a `Strategy_*` task to be completed in Step 6 of the current area's loop if it's about refining existing plans rather than creating entirely new ones.
        *   State: "Created `Strategy_PlanSubComponent_[SubComponentName].md` to defer/manage detailed planning for complex part of `[Area Name]`. Linked from `[Parent Implementation Plan/Task]`."
    *   **State**: "Completed task decomposition for area `[Area Name]`. All identified work broken into atomic Task Instructions or deferred via `Strategy_PlanSubComponent_*` tasks, detailing this roadmap segment. Proceeding to sequence tasks for this area."
    *   **Update `.clinerules` `[LAST_ACTION_STATE]`**: `next_action: "Sequence and Prioritize Tasks for Area"`. Update `activeContext.md` to note completion of Step 4 for this area.

5.  **Sequence and Prioritize Tasks for the SELECTED Area.**
    *   **Directive**: Based on dependencies identified in Step 2 (Focused Dependency Analysis) and the `Dependencies (Requires/Blocks)` section of Task Instructions defined in Step 4, determine the execution order for tasks *within `[Area Name]`'s roadmap segment*.
    *   **Action (Sequence)**:
        *   Review the `Dependencies (Requires/Blocks)` section of all Task Instructions created for `[Area Name]`.
        *   Identify foundational tasks (those with no unmet 'Requires' dependencies from other tasks *within this area's current plan*).
        *   Order subsequent tasks ensuring prerequisites are met. For 'x' (mutual) code dependencies from Step 2, plan for potentially iterative or closely coordinated implementation steps across the linked tasks.
        *   Document this build sequence in the "Task Sequence / Build Order" section of the relevant Implementation Plan(s) for `[Area Name]`. For each task in the sequence, briefly state its rationale if not obvious from dependencies.
        *   State: "Determined task sequence for area `[Area Name]`. Sequence documented in `[Implementation Plan file(s)]`."
    *   **Action (Prioritize)**: Within this determined sequence, prioritize tasks. Considerations:
        *   Urgency/importance if any specific to this area (from `activeContext.md` or area objectives).
        *   Potential to unblock the maximum number of subsequent tasks.
        *   Logical grouping of related work for efficiency.
        *   Critical path tasks.
        *   Document the prioritization (e.g., by reordering within the sequence, or adding priority labels like P1, P2, P3) and reasoning in the "Prioritization within Sequence" section of the Implementation Plan(s).
        *   State: "Prioritized tasks for area `[Area Name]`. Priorities documented in `[Implementation Plan file(s)]`."
    *   **Action (Update Checklist)**: Update tasks in `hierarchical_task_checklist_[cycle_id].md` under `[Area Name]` from "[ ] Defined" to "[ ] Sequenced & Prioritized".
    *   `write_to_file` the updated Implementation Plan(s).
    *   **State**: "Tasks for area `[Area Name]` sequenced and prioritized, refining its roadmap segment. Proceeding to complete local Strategy_* tasks for this area's planning."
    *   **Update `.clinerules` `[LAST_ACTION_STATE]`**: `next_action: "Complete Strategy Tasks for Area"`. Update `activeContext.md` to note completion of Step 5 for this area.

6.  **Complete `Strategy_*` Tasks for the SELECTED Area's Planning.**
    *   **Directive**: Identify and execute any `Strategy_*` tasks that were created for `[Area Name]` *and are intended to be resolved within this area's current planning loop*. These are tasks related to refining the plan for *this area* (e.g., `Strategy_RefineAlgorithmForFeatureX.md`) or resolving a `Strategy_PlanSubComponent_*.md` task if its scope is limited to further detailing parts of the current area's plan without creating a new major "area." These tasks ensure the roadmap segment for this area is fully detailed.
    *   **Action**:
        *   Identify such `Strategy_*` tasks from the `hierarchical_task_checklist_[cycle_id].md` for `[Area Name]` that are marked as "[ ] Sequenced & Prioritized" (or similar status indicating they are ready for action).
        *   For each such `Strategy_*` task:
            *   Read its instructions and follow its steps (e.g., perform analysis, update specific HDTA sections, further decompose a complex part into more granular `Execution_*` tasks).
            *   Update or create any HDTA documents as specified by the task. Ensure these changes are saved and linked appropriately, further solidifying the roadmap.
            *   Mark the `Strategy_*` task as complete in its own file (e.g., add a "Status: Completed" section) and update its status in the `hierarchical_task_checklist_[cycle_id].md` to "[x] Completed `Strategy_{task_name}`."
            *   State: "Completed `Strategy_{task_name}` for area `[Area Name]`. Updated `{affected_files}`. Task marked as complete in checklist."
    *   **Action (Verification)**: Ensure no `Strategy_*` tasks scoped for *this area's planning refinement* remain incomplete before proceeding. Major `Strategy_PlanSubComponent` tasks that define *new areas* will be handled by looping back to Step 1 for that new area.
    *   **State**: "Applicable `Strategy_*` tasks for refining the plan of area `[Area Name]` completed. This segment of the roadmap is now fully detailed. Proceeding to check for more areas or move to unification."
    *   **Update `.clinerules` `[LAST_ACTION_STATE]`**: `next_action: "Check Loop or Proceed to Unification"`. Update `activeContext.md` to note completion of Step 6 for this area.

7.  **Check Loop or Proceed to Unification.**
    *   **Action (Mark Area as Planned)**: In `hierarchical_task_checklist_[cycle_id].md`, mark the current `[Area Name]` as "[x] Planned" (or a similar status indicating its individual roadmap segment is complete for this cycle). State: "Marked area `[Area Name]` as Planned in `hierarchical_task_checklist_[cycle_id].md`."
    *   **Action (Check for More Areas)**: Review `hierarchical_task_checklist_[cycle_id].md`. Are there any other areas (modules/features relevant to the overall cycle goals for roadmap construction) still marked as "[ ] Unplanned" or "[ ] Partially Planned"?
    *   **If YES (more areas to plan for this cycle)**:
        *   Update `activeContext.md`: Set `current_planning_area: "None"` (as we are about to select a new one). Note that planning for `[Area Name]` is complete for this iteration.
        *   Update `.clinerules` `[LAST_ACTION_STATE]`:
            ```
            last_action: "Completed planning for area: [Area Name]. More areas pending for roadmap construction within cycle goals."
            current_phase: "Strategy"
            next_action: "Select Area for Planning" // Points back to Step 1
            next_phase: "Strategy"
            ```
        *   State: "Completed planning for area: `[Area Name]`. More areas within the current cycle goals need roadmap detailing. Returning to select next area."
        *   **Return to Step 1.**
    *   **If NO (all areas for this cycle's goals are planned)**:
        *   Update `activeContext.md`: Set `current_planning_area: "None"`. Note that all individual area planning is complete.
        *   State: "All areas relevant to the current cycle goals have had their roadmap segments planned individually. Proceeding to unify the overall roadmap."
        *   **Update `.clinerules` `[LAST_ACTION_STATE]`**: `next_action: "Unify and Review Roadmap"`.
        *   **Proceed to Step 8.**

**Roadmap Unification & Phase Completion**

8.  **Unify and Review Roadmap for Cycle Goals.**
    *   **Directive**: Consolidate the individually planned area roadmaps into a cohesive, unified roadmap for the *entire set of current cycle goals*. Review for inter-area consistency, dependency conflicts, and overall logical flow. Create the `roadmap_summary_[cycle_id].md`.
    *   **Action (Load Minimal Summaries & Key Interfaces)**:
        *   For each planned area (marked "[x] Planned" in `hierarchical_task_checklist_[cycle_id].md`), primarily review its Implementation Plan(s) which list task sequences, objectives, and affected components.
        *   Identify tasks that represent interfaces or integration points *between areas*. For these, you might need to `read_file` their specific Task Instruction files to understand their inputs/outputs and ensure smooth transitions in the overall roadmap.
        *   **Avoid reloading all individual task files unless a specific conflict or dependency requires deep inspection.**
    *   **Action (Review and Resolve Inter-Area Issues for Roadmap Cohesion)**:
        *   Check for logical flow and dependencies *between tasks in different areas*. Are there `Requires/Blocks` relationships that cross area boundaries? Are they correctly sequenced in the overall roadmap?
        *   Ensure task granularity and instruction clarity are reasonably consistent across different areas.
        *   Identify and resolve any conflicting instructions, timing issues, or resource contention between tasks in different (but related) areas. This might require targeted updates to specific Task Instructions or Implementation Plans (e.g., adding a `Requires` link to a task in another area's plan, adjusting sequence).
        *   Use `show-dependencies --key <key_of_interfacing_task_or_file>` if inter-area code/doc dependencies are suspected to cause conflicts not caught by task-level links, ensuring roadmap integrity.
        *   State: "Reviewed inter-area plans for roadmap unification. `[No major issues found / Identified issue: {description}, Resolution: {action_taken, e.g., updated Task_A.md to require Task_B.md from different area, adjusted sequence in roadmap_summary}]`."
        *   **Consult Diagrams**: Review the auto-generated `project_overview_dependencies.mermaid` and relevant `module_..._dependencies.mermaid` files for a visual perspective on inter-area connections.
        *   **Generate Focused Diagram (If Needed):** If specific inter-area connections are complex or conflicting, use `visualize-dependencies --key <interface_key1> --key <interface_key2> ... --output {memory_dir}/unification_focus_deps.md` to get a targeted view.
        *   Analyze diagrams and textual dependencies to identify and resolve conflicts (update Tasks/Plans as needed). State: "Reviewed inter-area plans using Implementation Plans and dependency diagrams. `[Issues/Resolutions or No issues found]`."
    *   **Action (Create Roadmap Summary Document)**:
        *   Create `roadmap_summary_[cycle_id].md` (a new template will be provided for this). This document is the capstone of the cycle's roadmap.
        *   This document should:
            *   Clearly state the overall cycle goals that this roadmap addresses.
            *   List all planned areas (from `hierarchical_task_checklist_[cycle_id].md`).
            *   For each area, provide a concise summary of its main objectives and a high-level overview of its `Execution_*` task sequence (referencing its Implementation Plan(s)).
            *   Present a unified, high-level execution sequence or flow diagram (e.g., using Mermaid syntax if appropriate, or a numbered list) that shows how tasks from different areas interleave or depend on each other. Highlight key milestones or integration points in the overall roadmap.
            *   Note any critical path tasks across the entire unified roadmap.
        *   `write_to_file` `roadmap_summary_[cycle_id].md`. State: "Created `roadmap_summary_[cycle_id].md` unifying plans for all cycle goals into a cohesive roadmap."
        *   Update `hdta_review_progress_[session_id].md` for `roadmap_summary_[cycle_id].md` (Status: Created).
    *   **Action (Update Checklist)**: Update `hierarchical_task_checklist_[cycle_id].md`: Add an entry like "[x] Roadmap Unified and Summarized for Cycle Goals."
    *   **State**: "Overall project roadmap for current cycle goals unified, reviewed, and summarized in `roadmap_summary_[cycle_id].md`. Proceeding to final checks for Strategy Phase completion."
    *   **Update `.clinerules` `[LAST_ACTION_STATE]`**: `next_action: "Final Checks and Exit Strategy Phase"`. Update `activeContext.md` to note completion of Step 8.

9.  **Final Checks and Exit Strategy Phase.**
    *   **Directive**: Verify all conditions for exiting the Strategy phase (as defined at the beginning of this plugin) are met, ensuring the roadmap for the *current cycle goals* is complete and actionable.
    *   **Action**: Meticulously perform the **Completion Criteria** check from the "Exiting Strategy Phase" section at the start of this document. Ensure every point is satisfied for the *current cycle goals*.
    *   If all criteria are met:
        *   Update `.clinerules` `[LAST_ACTION_STATE]` as specified in "Exiting Strategy Phase" (including `next_phase: "Execution"`).
        *   If any genuine, novel insights were gained about the planning process or system that would benefit future work and are not covered by existing documentation, add them to the `[LEARNING_JOURNAL]` in `.clinerules`.
        *   State: "Strategy phase complete. Unified roadmap for all cycle goals created, verified, and documented. All completion criteria met. Awaiting user action to proceed to Execution."
        *   Pause and await user action.
    *   If any criteria are NOT met:
        *   State: "Strategy phase completion criteria not fully met. Missing: `[List specific unmet criteria and for which area/document if applicable]`. Must address these before exiting."
        *   Determine the step needed to address the unmet criteria (e.g., return to Step 4 for a specific area to decompose more tasks, Step 6 to complete an overlooked `Strategy_*` task, Step 8 to fix unification issues or complete `roadmap_summary.md`).
        *   Update `activeContext.md` with the list of unmet criteria and the plan to address them.
        *   Update `.clinerules` `[LAST_ACTION_STATE]` with the current status (e.g., `last_action: "Strategy Phase Unification Incomplete - [Specific Issue]"`) and set `next_action` to point to the corrective step (e.g., `next_action: "Decompose Area into Atomic Tasks"` if more decomposition is needed for a specific area, or `next_action: "Unify and Review Roadmap"` if issues are in Step 8).
        *   Provide a clear plan in your response to address the missing criteria.

## III. Mandatory Update Protocol (MUP) Additions (Strategy Plugin)

**After Core MUP steps (Section VI of Core Prompt):**
*   **Save HDTA Documents**: Ensure ALL new or modified Domain Modules, Implementation Plans, and Task Instructions created/updated *during the last action or loop iteration* are saved using `write_to_file`. This should happen frequently (e.g., after each task definition, after updating a plan, after an area's HDTA is reviewed/created).
*   **Update `system_manifest.md`**: If new Domain Modules were created/defined for an area and planning for that area is now considered complete (end of Step 7 for that area, or during Step 8 - Unification), ensure the manifest is updated to link/reference them. This can be batched to minimize frequent manifest reloading but must be done before exiting the phase.
*   **Update Linking HDTA Docs**: Ensure Implementation Plans correctly link to their Task Instructions, and Domain Modules link to their Implementation Plans, reflecting changes *for the currently focused area or during unification*. This is often part of the `write_to_file` action for those documents. These links are vital for roadmap navigability.
*   **Update Checklists & Trackers**:
    *   `hdta_review_progress_[session_id].md`: Update to reflect the status of any documents reviewed/updated/created in the last action.
    *   `hierarchical_task_checklist_[cycle_id].md`: Update to reflect the status of areas planned, tasks defined/completed/sequenced. This is the primary tracker for roadmap completion status.
    *   `roadmap_summary_[cycle_id].md` (during Step 8): Ensure it is saved and its creation logged in `hdta_review_progress`.
*   **Update `activeContext.md` with Strategy Outcomes**:
    *   Summarize planning actions taken for the current area, or for the unification step (e.g., "Completed task definition for area X", "Sequenced tasks for area Y", "Unified roadmap started").
    *   Reference key HDTA documents created/updated that form part of the roadmap.
    *   Update `current_planning_area` and its status (e.g., `current_planning_area: "ModuleX"`, `current_planning_area_status: "Tasks Sequenced"`). Note any specific sub-objectives completed for the current area.
    *   If exiting a loop for an area (end of Step 7), set `current_planning_area: "None"` and note its planning completion.
*   **Update `.clinerules` `[LAST_ACTION_STATE]`**: Update `last_action` to reflect the last significant planning action. Update `current_phase` (will be "Strategy"). Update `next_action` to point to the correct subsequent major step in this plugin's workflow. `next_phase` remains "Strategy" until all completion criteria are met. The `[LEARNING_JOURNAL]` should only be updated with novel, reusable insights, not routine process logs.

## IV. Quick Reference & Flowchart

**Primary Goal**: Construct, refine, and maintain a comprehensive, dependency-aware, and actionable **project roadmap** for defined cycle goals, structured by HDTA.
**Key Iterative Loop Steps (per Area within Cycle Goals):**
0.  **Initialize Cycle**: Define overall goals for the entire Strategy engagement, set up main checklist with relevant areas for roadmap detailing.
1.  **Select ONE Area** relevant to cycle goals. Define planning objectives for this area in `activeContext.md`.
2.  **Focused Dependency Analysis** (for the selected area, deep understanding of 'why').
3.  **Review/Create HDTA** (Manifest (context) → Module → Plan(s) for the area, minimal load, top-down, building roadmap segment).
4.  **Decompose Area into Atomic Tasks** (`Strategy_*` or `Execution_*` with explicit minimal context links). Handle complexity with `Strategy_PlanSubComponent_*` tasks. These are the roadmap's leaves.
5.  **Sequence & Prioritize Tasks** (for the area, document in Implementation Plan).
6.  **Complete `Strategy_*` Tasks** (for refining this area's plan/roadmap segment).
7.  **Check Loop**: If more areas for cycle goals, return to Step 1; else proceed to Unification (Step 8).

**Post-Loop Steps:**
8.  **Unify & Review Roadmap** (for all planned areas of the cycle goals), resolve inter-area conflicts, create `roadmap_summary_[cycle_id].md` (the unified roadmap document).
9.  **Final Checks & Exit Strategy Phase** (verify all completion criteria for the roadmap).

**Key Trackers & Outputs (Roadmap Artifacts):**
*   `hdta_review_progress_[session_id].md`: Logs HDTA document review/creation status.
*   `hierarchical_task_checklist_[cycle_id].md`: Tracks planning status of *areas within cycle goals* and their tasks (roadmap completion tracker).
*   `roadmap_summary_[cycle_id].md`: The final unified roadmap document for the current cycle's goals.
*   New/Updated HDTA: `*_module.md`, `implementation_plan_*.md`, `Strategy_*.md`, `Execution_*.md` files – these collectively form the detailed roadmap.

**Key Inputs**: `activeContext.md` (overall cycle goals, current area focus, sub-objectives), `system_manifest.md`, `progress.md`, Verified Trackers (`show-keys`, `show-dependencies`), HDTA Templates.
**Key Outputs**: Updated `activeContext.md`, new/updated HDTA documents (the roadmap), `roadmap_summary_[cycle_id].md`, updated `.clinerules`, session trackers.
**MUP Additions**: Frequent saves of HDTA, update manifest/links (can be batched per area or during unification), update checklists and `activeContext.md` per action/loop, update `.clinerules` with precise `last_action` and `next_action`. `[LEARNING_JOURNAL]` for novel insights only.

```mermaid
graph TD
    AA[Start Strategy Phase: Read .clinerules, Load Plugin] --> S0[Step 0: Initialize Cycle & Define Overall Cycle Goals];
    S0 --> S0A[Create/Update hdta_review_progress & hierarchical_task_checklist (with Areas for Roadmap)];
    S0A --> S1[Step 1: Select ONE Area for Focused Planning (from Checklist)];

    subgraph "Iterative Planning Loop (for each Area's Roadmap Segment)"
        S1 --> S2[Step 2: Focused Dependency Analysis for Area (Deep Understanding)];
        S2 --> S3[Step 3: Review/Create HDTA for Area (Top-Down, Minimal Load: Manifest CTX -> Module -> Plans)];
        S3 --> S4[Step 4: Decompose Area into Atomic Tasks (Min Context, Task Templates, Strategy_PlanSubComponent for complexity)];
        S4 --> S5[Step 5: Sequence & Prioritize Tasks for Area (Update Impl. Plan)];
        S5 --> S6[Step 6: Complete Strategy_* Tasks for Area's Plan Refinement];
        S6 --> S7{Step 7: More Areas for Cycle Goals? (Check Checklist)};
    end

    S7 -- Yes --> S1;
    S7 -- No --> S8[Step 8: Unify & Review Roadmap for ALL Cycle Goals (Resolve Inter-Area Conflicts)];
    S8 --> S8A[Create roadmap_summary.md (Unified Roadmap Document)];
    S8A --> S9[Step 9: Final Checks & Exit Strategy Phase (Verify All Completion Criteria for Roadmap)];
    S9 -- All Criteria Met --> Z[End Strategy Phase: Update .clinerules, Await User for Execution];
    S9 -- Criteria NOT Met --> SC[Address Missing Criteria: Determine Corrective Step, Update .clinerules & activeContext.md, Loop back to e.g. S4, S6, S8];
    SC --> S1
    SC --> S4
    SC --> S6
    SC --> S8


    S3 --> UDT[Update hdta_review_progress_tracker (for Manifest, Module, Plans)];
    S4 --> UDT2[Update hdta_review_progress_tracker (for Tasks)];
    S4 --> UHTC1[Update hierarchical_task_checklist (Tasks Defined)];
    S5 --> UHTC2[Update hierarchical_task_checklist (Tasks Sequenced & Prioritized)];
    S6 --> UHTC3[Update hierarchical_task_checklist (Strategy_* Tasks for Area Done)];
    S7 -.-> UHTC4[Update hierarchical_task_checklist (Area Marked as Planned)];
    S8A --> UDT3[Update hdta_review_progress_tracker (for roadmap_summary)];
    S8A --> UHTC5[Update hierarchical_task_checklist (Roadmap Unified)];

    %% MUP happens after each significant action / loop iteration as per Core Prompt & Plugin Additions
    %% .clinerules [LAST_ACTION_STATE] updated with last_action & next_action.
    %% activeContext.md updated with detailed progress, objectives for current area/step.
    %% [LEARNING_JOURNAL] in .clinerules for novel insights only.
```

*Note: This iterative Strategy phase is designed to be robust against context window limitations by forcing focused planning on manageable "areas" within the larger cycle goals, all contributing to the construction of a detailed and actionable project roadmap. Strict adherence to minimal context loading, scoped dependency analysis, and meticulous HDTA management at each step is paramount for success.*
```
