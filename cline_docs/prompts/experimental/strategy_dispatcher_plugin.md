# **Cline Recursive Chain-of-Thought System (CRCT) - Strategy Plugin (Dispatcher Focus)**

This Plugin provides detailed instructions and procedures for the **Dispatcher** role within the Strategy phase of the CRCT system. It guides an iterative, exhaustive process of constructing and maintaining the comprehensive, dependency-aware `project_roadmap.md` using a Dispatcher/Worker pattern facilitated by the `new_task` tool.

**Core Concept (Dispatcher Perspective):**
- The primary instance running this plugin acts as the **Dispatcher**. It orchestrates the overall Strategy phase for the defined cycle goals by updating `project_roadmap.md`.
- The Dispatcher identifies distinct planning "areas" (modules, features) relevant to the cycle goals.
- For each area, the Dispatcher uses the `<new_task>` tool to delegate detailed planning (Worker steps) to separate, fresh **Worker** instances (which will use `strategy_worker_plugin.md`).
- The Dispatcher reviews each Worker's output, updates overall progress, and dispatches further sub-tasks for an area or moves to the next area until all are planned for the cycle.
- Finally, the Dispatcher integrates the cycle's detailed plans into the main `project_roadmap.md` and performs final checks.

This pattern ensures maximal context separation for planning each area. All `Strategy_*` tasks for planning and all `Execution_*` tasks comprising the roadmap for the targeted work of the cycle must be defined before transitioning to Execution.
This plugin should be used in conjunction with the Core System Prompt.

**IMPORTANT**
If you have already read a file and have not edited it since, *DO NOT* read it again. Use the version in your context. Only load a new version of the file if *you* have recently altered the content.
Do not use the tool XML tags in general responses, as it will activate the tool unintentionally.
*system_manifest and other CRCT system files are not tracked by the *project* trackers*

**Entering and Exiting Strategy Phase (Dispatcher Role)**

**Entering Strategy Phase:**
1.  **`.clinerules` Check (Mandatory First Step)**: Read `.clinerules` file content.
2.  **Determine Current State & Assume Dispatcher Role**:
    *   If `[LAST_ACTION_STATE]` indicates `current_phase: "Strategy"`, resume from the action indicated by `next_action`, consulting `activeContext.md`. You are the Dispatcher.
    *   If `[LAST_ACTION_STATE]` indicates `next_phase: "Strategy"`, this signifies a transition from a previous phase. Assume the **Dispatcher** role and proceed starting from **Section II.A, Step 0** of this plugin.
3.  **User Trigger**: If starting a new session and `.clinerules` indicates Strategy, assume Dispatcher role. If fresh into Strategy, begin at Step 0.

**Exiting Strategy Phase:** (Performed by Dispatcher)
1.  **Completion Criteria (Mandatory Check)**: Verify ALL the following are met for the current Strategy cycle's goals:
    *   All identified areas/modules relevant to the cycle's goals have been planned (status "[x] Area Planned" in `current_cycle_checklist.md`) and their respective HDTA documents are complete.
    *   A comprehensive implementation sequence based on dependency analysis has been defined for all planned work (documented in relevant Implementation Plans or `*_module.md` files, and its relevant sections integrated into `project_roadmap.md`).
    *   All high-priority work planned for this strategy cycle has been decomposed into atomic Task Instructions (`*.md`), with clear phase prefixes (`Strategy_*`, `Execution_*`), and explicit minimal context links.
    *   All necessary HDTA documents (System Manifest, Domain Modules, Implementation Plans, Task Instructions) relevant to the planned work have been created or updated. No placeholders or incomplete sections relevant to the planned work remain.
    *   `Execution_*` tasks have been sequenced and prioritized within their respective areas and reviewed for inter-area consistency during the update of `project_roadmap.md` (Step 8).
    *   All HDTA documents are correctly linked (Tasks from Plans, Plans from Modules, Modules from Manifest).
    *   All `Strategy_*` tasks identified and scoped for completion *during this Strategy phase* (including those created by Workers for sub-component planning or plan refinement) have been completed.
    *   The `project_roadmap.md` (incorporating this cycle's plan) reflects the completed planning state for all cycle goals (all relevant areas marked "[x] Area Planned", and this cycle's plan integrated into `project_roadmap.md`).
    *   The `project_roadmap.md` has been updated with this cycle's plan, reviewed for coherence, and accurately reflects the unified roadmap for all cycle goals.
2.  **`.clinerules` Update (Mandatory MUP Step)**: If completion criteria are met, update `.clinerules` `[LAST_ACTION_STATE]` **exactly** as follows:
    ```
    last_action: "Completed Strategy Phase: Unified Roadmap for All Cycle Goals"
    current_phase: "Strategy"
    next_action: "Phase Complete - User Action Required"
    next_phase: "Execution"
    ```
    Also, add profound, reusable insights to `[LEARNING_JOURNAL]`.
3.  **Pause for User Action**: After successfully updating `.clinerules`, state completion and await user action.

## I. Phase Objective & Guiding Principles (Dispatcher Focus)

**Objective**: The primary objective of the Strategy Phase, from the Dispatcher's perspective, is to **orchestrate the construction (if not yet existing), refinement, and maintenance of the single, comprehensive `project_roadmap.md`**. This is achieved by defining cycle goals, identifying relevant "Areas" (modules/features), and delegating the detailed planning of each Area to Worker instances. The Dispatcher reviews Worker outputs, ensures integration of planned work into `project_roadmap.md`, and confirms all `Strategy_*` planning tasks for the cycle are complete before exiting.

**CRITICAL CONSTRAINT: MINIMAL CONTEXT LOADING.** Proactively manage what is loaded into working context.

**Guiding Principles**:

<<<**CRITICAL**>>>
*Before **any** planning activities (Dispatcher or Worker), you **MUST** first assess the current state of relevant project artifacts. This includes:*
    *   *Reading the actual code for any area/module/file being planned or potentially impacted.*
    *   *If any project tracker (`module_relationship_tracker.md`, `doc_tracker.md`, `*_module.md` mini-trackers) indicates a dependency (via `show-dependencies` or direct tracker review if necessary for context), the relevant sections of that dependent file (code or documentation) **MUST** be read to understand the nature and implications of the dependency.*
*Failure to perform this comprehensive assessment, including reading dependent files, will lead to incomplete or flawed planning.*
*   The files identified as dependencies through `show-dependencies` (sourced from project trackers) **MUST** then have their relevant sections read using `read_file`.

**(Dispatcher Focused Principles):**
1.  **Dispatcher/Worker Model**: Strategy phase orchestrated by Dispatcher delegating area planning to Workers via `<new_task>`. Workers will use `strategy_worker_plugin.md`.
2.  **Iterative Area-Based Dispatch**: Decompose cycle goals into "areas"; iteratively dispatch planning for each.
3.  **Review Cycle**: Review Worker output before accepting area plans or requesting revisions.
4.  **Unification and Cohesive Roadmap**: After all areas are planned, integrate their plans into the main `project_roadmap.md`, resolving inter-area conflicts.
5.  **Overall Progress Tracking**: Maintain high-level status of area planning using `current_cycle_checklist.md`.

**(Overall System Principles Referenced by Dispatcher):**
15. **Roadmap as Primary Output**: All activities contribute to building/refining `project_roadmap.md` via HDTA.
16. **Minimal Context Handover**: Dispatcher's `<new_task>` message provides minimal pointers for Workers.

## II. Dispatcher Workflow: Orchestrating Granular Roadmap Construction

This section details the procedures for the **Dispatcher** instance.

*   **Dispatcher Step 0: Initialize Strategy Cycle, Define Goals, & Load Core Project Plans.**

*   **Action A (CRITICAL Core System Initialization & Overall Cycle Goal Definition)**:
    *   1. **Read `.clinerules`**: Confirm current state.
    *   2. **CRITICAL PRE-CONDITION: Assess Current Project State**: Review `progress.md`, `system_manifest.md`, `activeContext.md`. If specific areas are targets, skim their existing HDTA and code. State: "Initial project state assessment complete."
    *   3. **Define/Confirm Overall Cycle Goals**: Formulate goals. Use `ask_followup_question` if unclear. Update `activeContext.md`. State: "Confirmed overall cycle goals... Documented in `activeContext.md`."

*   **Action B (Initialize/Load Core HDTA & Project Roadmap)**:
    *   1. **Initialize/Load `project_roadmap.md` (CRITICAL)**: Check for `project_roadmap.md`. If new, create from `project_roadmap_template.md`, perform initial population using `system_manifest.md` and dependency visualization (`visualize-dependencies`), and save. If exists, load. State creation/load status.
    *   2. **Verify and Load `system_manifest.md`**: Check for `system_manifest.md`. If missing, error and halt. If exists, load. State: "Loaded `system_manifest.md`."
    *   3. **Preliminary Identification of Relevant Domain Modules**: Based on cycle goals and manifest, list relevant `*_module.md` files. Check existence (do not read content). State: "Preliminarily identified relevant modules... Checked existence."

*   **Action C (Identify Areas for Current Cycle & Initialize/Load Cycle-Specific Trackers)**:
    *   1. **Identify Relevant Areas from Manifest**: Based on cycle goals and manifest, identify "Areas" for planning. State: "Identified Areas for cycle: `[List]`."
    *   2. **Handle `hierarchical_task_checklist_*.md`**: Search for existing checklists. If found and relevant, `ask_followup_question` to continue/consolidate/new. Create/load/update `current_cycle_checklist.md`. Populate with Areas from C.1, status `[ ] Unplanned`. State: "Active cycle checklist set to: `current_cycle_checklist.md`. Populated/updated."
    *   3. **Initialize `hdta_review_progress_[session_id].md`**: Create from template. State: "Initialized HDTA Review Progress Tracker."

*   **Action D (Initialize Dispatcher Area Planning Logs & Perform Initial Overview)**:
    *   1. **Initialize Dispatcher Area Planning Logs**: For each Area in C.1, create `[AreaName]_planning_log_[cycle_id].md` from template, set `next_atomic_planning_step: "Initial_Area_Assessment"`. State: "Initialized Dispatcher Area Planning Logs."
    *   2. **Initial Overview & Visualization Check**: Briefly review inter-Area dependencies (`show-dependencies`). Check for/review auto-generated diagrams. State overview findings.

*   **Action E (Finalize Step 0 State & MUP)**:
    *   1. **State**: "Dispatcher completed Strategy Cycle Initialization (Step 0)..."
    *   2. **Update MUP**: Perform Dispatcher MUP (Section V). Set `.clinerules` `next_action: "Orchestrate Area Planning"`. Update `activeContext.md`.

*   **Step 1: Main Orchestration Loop.**

*   **Directive**: Iteratively select a high-level Area. Within that Area, identify and dispatch the next required atomic planning sub-task to a Worker instance using `<new_task>`, pause, and upon the Worker's completion, review the results before dispatching the next task. Repeat until the Area's plan is complete. Then, select the next Area.
*   **OUTER LOOP START (Per High-Level Area):**
    *   **Action A (Select Next High-Level Area for Planning)**:
        *   Read `current_cycle_checklist.md`.
        *   Identify the first Area with status not equal to "[x] Area Planned". Prioritize any Area marked "[ ] Area Revision Required".
        *   **If None Found** (all Areas are "[x] Area Planned"): All planning complete. State: "Dispatcher confirms all cycle Areas are planned. Proceeding to final roadmap unification.". Update `.clinerules` `next_action: "Unify Cycle Plan and Update project_roadmap.md"`. **Go to Dispatcher Step 8.**
        *   **If Area Found**: Let this be `[Current_Orchestration_Area_Name]`.
        *   Update `activeContext.md`: Set `current_orchestration_area: "[Current_Orchestration_Area_Name]"`.
        *   State: "Dispatcher focusing on Area: `[Current_Orchestration_Area_Name]` (Status: `[Status from checklist]`)."
    *   **INNER LOOP START (Per Atomic Planning Sub-Task within `[Current_Orchestration_Area_Name]`):**
        *   **Action B (Determine Next Atomic Planning Sub-Task for `[Current_Orchestration_Area_Name]`)**:
            1.  **Assess Current Planning State for `[Current_Orchestration_Area_Name]`**:
                *   Read the Dispatcher Area Planning Log file for `[Current_Orchestration_Area_Name]` (located in `cline_docs/dispatch_logs/`) to find the `next_atomic_planning_step` and review the planning progress for this area.
                *   Review existing HDTA files for this Area (`_module.md`, `implementation_plan_*.md` files, lists of tasks).
                *   **If the planning log indicates the next step is "Initial_Area_Assessment"**: The first sub-task is to assess existing files. Set `atomic_sub_task_description` to "Perform Initial State Assessment for Area `[Current_Orchestration_Area_Name]` (read existing module/plan files, document current state summary in the Worker Output file)."
                *   **Otherwise (based on previous sub-task completion documented in the planning log)**: Determine the *next logical, granular planning action* based on the standard workflow (Initial Assessment -> Dependency Analysis -> HDTA Structure (Module -> Plan(s) -> Task Def) -> Sequencing -> Local Strategy Tasks). Examples:
                    *   If initial assessment done, next is "Perform Dependency Analysis for `[Key component/file of Current_Orchestration_Area_Name]`."
                    *   If `_module.md` outline needed: "Create/Update `[Current_Orchestration_Area_Name]_module.md` outline."
                    *   If a specific `implementation_plan_*.md` needs creation/update: "Create/Update `implementation_plan_[Feature]_for_[Area].md` with objectives & high-level steps."
                    *   If a plan section needs task decomposition: "Decompose `implementation_plan_[Feature].md#SectionX` into atomic `Execution_*` task files."
                    *   If tasks need sequencing in a plan: "Sequence tasks in `implementation_plan_[Feature].md`."
                    *   If a local `Strategy_*.md` task (like refining a plan detail) needs execution: "Execute `Strategy_RefinePlanDetail_For_Feature.md`."
            2.  **Check for Area Completion**: If assessment indicates all necessary planning sub-tasks (Module, Plans, Task Defs, Sequencing, Local Strategy Tasks) for `[Current_Orchestration_Area_Name]` appear complete *and their outputs have been accepted*:
                *   Update `current_cycle_checklist.md`: Mark `[Current_Orchestration_Area_Name]` as "[x] Area Planned".
                *   Update the Dispatcher Area Planning Log file for `[Current_Orchestration_Area_Name]`. Update the Area Status to "[x] Planned". Update the "Last Updated" timestamp.
                *   Update `activeContext.md`: Note "Area `[Current_Orchestration_Area_Name]` planning complete." Clear `current_orchestration_area`.
                *   State: "Dispatcher: Planning for Area `[Current_Orchestration_Area_Name]` is now complete."
                *   **GOTO Action A (Outer Loop Start)** to select the next high-level Area.
            3.  Let the determined next action be `[Atomic_Sub_Task_Description]`.
            4.  State: "Dispatcher identified next atomic planning sub-task for Area `[Current_Orchestration_Area_Name]`: `[Atomic_Sub_Task_Description]`."
        *   **Action C (Prepare Handoff Content for Worker - for the Atomic Sub-Task)**: Gather minimal pointers and craft the handoff content. This content **MUST precisely define ONLY the single `[Atomic_Sub_Task_Description]`**.
            *   **Content to include:**
                *   Instruction: "Assume Worker Role."
                *   Plugin Reference: "Load `strategy_worker_plugin.md`. Execute specific action from its Section I (Worker Task Execution) as instructed."
                *   Overall Area Context: `[Current_Orchestration_Area_Name]`.
                *   **Specific Sub-Task Directive**: `[Detailed instructions for the Atomic_Sub_Task_Description, referencing specific files, sections, or previous outputs if necessary]`. For example: "For Area `[Current_Orchestration_Area_Name]`, focus on file `path/to/specific_file.py`. Perform dependency analysis using `show-dependencies`. Document findings (key dependencies, implications) in `activeContext.md` under section `DepAnalysis_[specific_file_key]`." OR "Based on `implementation_plan_X.md#SectionY`, create atomic `Execution_*.md` task files. Ensure each has Objective, Min Context, Steps. Save to `tasks/exec/`. Link from Plan X."
                *   **Strict Scope Limitation**: "DO NOT perform any other planning steps beyond this specific sub-task."
                *   Expected Outputs: `[Specific files to be created/updated, or specific section in activeContext.md to be populated]`.
                *   MUP Reminder: "Worker MUP: Save outputs, update `hdta_review_progress`, update Worker Output file. NO `.clinerules` changes."
                *   Completion Signal: "Signal task completion to Dispatcher using the method specified by the current interface when THIS SPECIFIC SUB-TASK is fully complete."
                *   **Context Pointers**: (Minimal and relevant ONLY to the sub-task)
                    *   `checklist_path`: `current_cycle_checklist.md`
                    *   `active_context_path`: `activeContext.md` (for overall goals, and for Worker to write its output if specified)
                    *   Paths to *specific* files/diagrams directly needed for *this sub-task*.
                    *   Relevant `revision_notes` from Dispatcher if this is a re-dispatch of a failed sub-task.
            *   State: "Dispatcher prepared handoff content for Worker sub-task: `[Atomic_Sub_Task_Description]` for Area `[Current_Orchestration_Area_Name]`."
        *   **Action D (Use `<new_task>` Tool - Follow Interface Schema)**:
            *   **CRITICAL**: Use the `new_task` tool. Package the Handoff Content from Action C.
            *   **IMPORTANT**: Adhere strictly to the `new_task` tool's XML structure and parameters as specified by the current interface's system prompt/documentation.
            *   Execute the tool call.
            *   State: "Dispatcher invoking `<new_task>` for sub-task: `[Atomic_Sub_Task_Description]` for Area `[Current_Orchestration_Area_Name]`."
        *   **Action E (Update Dispatcher State & Pause)**:
            *   Update the Dispatcher Area Planning Log file for `[Current_Orchestration_Area_Name]` (located in `cline_docs/dispatch_logs/`). Add a new row to the "Atomic Planning Sub-Task Log" table: `| [Atomic_Sub_Task_Directive] | [Worker Instance ID] | Dispatched | In Progress (Worker) | [Link to expected Worker Output file - TBD by Worker] |`. Update the "Last Updated" timestamp.
            *   Update `activeContext.md`: Set `current_orchestration_area: "[Current_Orchestration_Area_Name]"`.
            *   Update `.clinerules` `[LAST_ACTION_STATE]`:
                ```
                last_action: "Dispatched sub-task '[Atomic_Sub_Task_Description]' for Area: [Current_Orchestration_Area_Name] to Worker."
                current_phase: "Strategy"
                next_action: "Review Worker Completion for Sub-Task: [Atomic_Sub_Task_Description], Area: [Current_Orchestration_Area_Name]"
                next_phase: "Strategy"
                ```
            *   State: "Dispatcher dispatched sub-task `[Atomic_Sub_Task_Description]` for Area `[Current_Orchestration_Area_Name]`. Logged in area planning file. Pausing and awaiting worker completion."
            *   **PAUSE EXECUTION.**

        *   **(Dispatcher Resumes Here)** **Action F (Review Worker Completion for Atomic Sub-Task)**: (Triggered when control returns after Worker's `<attempt_completion>`)
            *   Retrieve `[Current_Orchestration_Area_Name]` and `[Atomic_Sub_Task_Description]` from `.clinerules` `next_action` or `activeContext.md`.
            *   State: "Dispatcher resuming. Received completion for sub-task: `[Atomic_Sub_Task_Description]` for Area `[Current_Orchestration_Area_Name]`. Reviewing outputs."
            *   **Identify Outputs**: The primary output is the Worker Sub-Task Output file (located in `cline_docs/dispatch_logs/`). Check file system for this file and any other specified outputs (e.g., updated HDTA files).
            *   **Review Content**: Read the Worker Sub-Task Output file. Verify the Worker completed the *specific sub-task assigned* and documented its process and outputs accurately within that file. Check for quality and adherence to instructions. Did it overstep its scope?
                *   **Check for Child Tasks**: Explicitly check the Worker Output File and any parent Task Instruction files created/modified by the Worker for any listed "Children" (i.e., newly created `.md` task files linked from a parent task).
                *   If child tasks are identified:
                    1.  Note them.
                    2.  The Dispatcher is responsible for ensuring these child tasks are added to the `current_cycle_checklist.md` (likely nested under their parent task or the relevant Implementation Plan).
                    3.  The Dispatcher must also ensure these child tasks are appropriately considered for subsequent planning/sequencing sub-tasks within the current Area's workflow (e.g., they will need to be assessed, have dependencies analyzed, be sequenced, etc., potentially by dispatching new sub-tasks for them if they weren't fully detailed by the initial Worker).
            *   State: "Dispatcher review of sub-task `[Atomic_Sub_Task_Description]` output complete. Assessment: `[Brief assessment based on Worker Output file content, including note if child tasks were identified]`."
            *   **Action G (Accept or Request Revision for Sub-Task)**:
                *   **If Acceptable**:
                    *   State: "Dispatcher accepts output for sub-task: `[Atomic_Sub_Task_Description]`."
                    *   Integrate the Worker's output (e.g., acknowledge new files, incorporate findings from Worker Output file into the Area Planning Log).
                    *   Update the Dispatcher Area Planning Log file for `[Current_Orchestration_Area_Name]` (located in `cline_docs/dispatch_logs/`). Find the row for `[Atomic_Sub_Task_Directive]` in the "Atomic Planning Sub-Task Log" table. Update the Status to "[x] Completed" and the Outcome Summary based on the Worker Output file. Determine and set the *new* `next_atomic_planning_step` for this Area in the planning log (or mark the Area Status as "Planned" if all sub-steps seem done). Update the "Last Updated" timestamp.
                    *   Perform Dispatcher MUP (Section V). Set `.clinerules` `next_action: "Orchestrate Area Planning"`.
                    *   State: "Proceeding to identify next atomic planning sub-task for Area `[Current_Orchestration_Area_Name]`."
                    *   **GOTO Action B (Inner Loop Start for `[Current_Orchestration_Area_Name]`).**
                *   **If Revision Needed**:
                    *   State: "Dispatcher requires revisions for sub-task: `[Atomic_Sub_Task_Description]`. Issues: `[List specific, actionable issues regarding the sub-task's output]`."
                    *   Update the Dispatcher Area Planning Log file for `[Current_Orchestration_Area_Name]`. Find the row for `[Atomic_Sub_Task_Directive]` in the "Atomic Planning Sub-Task Log" table. Update the Status to "Revision Required" and the Outcome Summary to note the need for revision. Add detailed revision notes to the "High-Level Notes and Revision Requirements" section, referencing the specific sub-task. Keep the `next_atomic_planning_step` in the planning log pointing to the *same sub-task type* or a precursor if the failure was fundamental. Update the "Last Updated" timestamp.
                    *   Perform Dispatcher MUP (Section V). Set `.clinerules` `next_action: "Orchestrate Area Planning"`.
                    *   State: "Revision requirements noted for sub-task. Proceeding to re-dispatch."
                    *   **GOTO Action B (Inner Loop Start for `[Current_Orchestration_Area_Name]`).** (The loop will re-identify this sub-task, and Handoff Content in Action C will include the new revision notes from the planning log).

*   **(Dispatcher) Step 8: Unify Cycle Plan and Update `project_roadmap.md`.**
*   **Directive**: Consolidate the individually planned area roadmaps for the current cycle (represented by their HDTA documents) and integrate this cycle's plan into the main `project_roadmap.md`. Review for inter-area consistency, dependency conflicts, and overall logical flow of the *cycle's contribution* to the project.
*   **Action A (Verify All Areas Planned for Cycle)**: As a final check, read `current_cycle_checklist.md` (the active checklist for this cycle, identified in Step 0) and confirm all areas relevant to the current cycle goals have the status "[x] Planned". If not, return to Step 1 (Dispatch Loop) to address the discrepancies. State: "Dispatcher confirms all required cycle Areas are marked '[x] Planned' in `current_cycle_checklist.md`. Proceeding with unification and `project_roadmap.md` update."
*   **Action B (Load Cycle Plans & Identify Interfaces)**:
    *   For each planned area in `current_cycle_checklist.md`, load its primary `implementation_plan_*.md` file(s) using `read_file`. These contain the task lists, sequences, and objectives for each area *for this cycle*.
    *   Optionally, load the `[AreaName]_module.md` files for high-level context relevant to this cycle's changes.
    *   **Identify Interface Tasks**: Scan the Implementation Plans and Task Instructions (`Dependencies` sections) for *this cycle's tasks* to identify key tasks that represent interfaces or integration points *between* different planned areas for this cycle. Note these tasks and their dependencies.
    *   **Minimize Loading**: Avoid reloading all individual Task Instruction files from this cycle unless a specific conflict or dependency requires deep inspection.
*   **Action C (Review and Resolve Inter-Area Issues for Cycle's Plan Cohesion)**:
    *   Check for logical flow and dependencies *between tasks planned in different areas for this cycle*.
    *   Ensure task granularity and instruction clarity are reasonably consistent.
    *   Identify and resolve any conflicting instructions, timing issues, or resource contention *within this cycle's planned tasks*. This might require targeted updates to specific Task Instructions or Implementation Plans for this cycle.
    *   Use `show-dependencies --key <key_of_interfacing_task_or_file>` if needed.
    *   State: "Reviewed inter-area plans for current cycle. `[No major issues found / Identified issue: {description}, Resolution: {action_taken}]`."
    *   **Consult Diagrams**: Review relevant dependency diagrams.
    *   **Generate Focused Diagram (If Needed)** for complex inter-area connections *within this cycle's scope*.
    *   **Identify & Resolve Conflicts** within the cycle's plan. If significant rework is needed for an area, note it, mark area as "[ ] Revision Required" in `current_cycle_checklist.md`, set `.clinerules` `next_action: "Orchestrate Area Planning"`, and loop back to Step 1.
    *   State: "Dispatcher reviewed inter-area plans for cycle. `[Issues/Resolutions / No major conflicts found]`."
*   **Action D (Update `project_roadmap.md` with Cycle's Plan - CRITICAL)**:
    *   **Action**: `read_file` the main `project_roadmap.md` (loaded in Step 0.B).
    *   **Goal**: To integrate a summary of this cycle's planned work into the overall `project_roadmap.md`, ensuring it reflects the current, detailed intentions for the cycle's goals.
    *   **Procedure**:
        1.  Determine where and how to best integrate this cycle's information. This might involve:
            *   Adding new sub-sections under existing major features/modules in `project_roadmap.md` if this cycle details them further.
            *   Creating new top-level sections in `project_roadmap.md` if this cycle introduces entirely new major features.
            *   Updating existing status markers or timelines within `project_roadmap.md` based on this cycle's detailed planning.
        2.  The information to integrate should include:
            *   A clear reference to the current cycle (e.g., using the `[cycle_id]` from `current_cycle_checklist.md`).
            *   The overall cycle goals that were addressed.
            *   A list of all Areas planned in this cycle.
            *   For each Area, a concise summary of its main objectives for this cycle and a high-level overview of its `Execution_*` task sequence (linking to its Implementation Plan(s)).
            *   A unified, high-level execution sequence or flow diagram (e.g., Mermaid) for *this cycle's tasks*, showing inter-area dependencies and key milestones for the cycle.
        3.  **Use `apply_diff` or `write_to_file` (if changes are extensive) to update `project_roadmap.md`**. Ensure the update is a logical integration, not just an append, maintaining the integrity of the overall project roadmap.
    *   State: "Updated main `project_roadmap.md` with the unified plan and detailed contributions from the current strategy cycle."
    *   Update `hdta_review_progress_[session_id].md` for `project_roadmap.md` (Status: Updated).
*   **Action E (Update Checklist for Cycle Completion)**:
    *   Update `current_cycle_checklist.md`: Add an entry like "[x] Cycle Plan Integrated into `project_roadmap.md`."
    *   State: "Main `project_roadmap.md` updated with current cycle's plan. `current_cycle_checklist.md` marked accordingly. Proceeding to final phase checks."
    *   **Update `.clinerules` `[LAST_ACTION_STATE]`**: `next_action: "Final Checks and Exit Strategy Phase"`. Update `activeContext.md` to note completion of Step 8 and that `project_roadmap.md` has been updated.

*   **(Dispatcher) Step 9: Final Checks and Exit Strategy Phase.**
*   **Directive**: As the Dispatcher, verify all conditions for exiting the *entire* Strategy phase are met, ensuring the roadmap for the current cycle goals is complete, consistent, and actionable.
*   **Action A (Perform Completion Criteria Check)**: Meticulously review **ALL** points listed in the "Exiting Strategy Phase" section at the beginning of this plugin document (Section I). Verify each one against the current state of the project files, HDTA documents, checklists, and the `project_roadmap.md`. Pay special attention to:
    *   Completeness of all planned areas.
    *   Existence and completeness of the `project_roadmap.md` content reflecting this cycle's plan.
    *   Absence of placeholders in relevant HDTA.
    *   Correct linking between all HDTA tiers.
    *   Completion of all `Strategy_*` tasks identified *during this entire phase* (including any created by workers and potentially missed).
    *   Accuracy of `current_cycle_checklist.md`.
*   **Action B (Decision and Exit/Correct)**:
    *   **If ALL criteria are met**:
        1.  State: "Dispatcher confirms all Strategy Phase completion criteria are met."
        2.  Perform final Dispatcher MUP (Section IV):
            *   Update `activeContext.md` noting phase completion.
            *   Add any novel, reusable insights to `.clinerules` `[LEARNING_JOURNAL]`.
            *   Update `.clinerules` `[LAST_ACTION_STATE]` **exactly** as specified in the "Exiting Strategy Phase" section (Section I preamble) which includes:
            ```
            last_action: "Completed Strategy Phase: Unified Roadmap for All Cycle Goals"
            current_phase: "Strategy"
            next_action: "Phase Complete - User Action Required"
            next_phase: "Execution"
            ```
        3.  State: "Strategy phase complete. Unified roadmap for all cycle goals created, verified, and documented. All completion criteria met. Awaiting user action to proceed to Execution."
        4.  **PAUSE EXECUTION.** Await user trigger for the next phase.
    *   **If ANY criteria are NOT met**:
        1.  State clearly: "Strategy phase completion criteria **NOT** fully met. Missing/Issues: `[List specific unmet criteria and details, e.g., Placeholder found in implementation_plan_X.md, Task linking incomplete for Plan Y, Strategy_TaskZ was not completed, project_roadmap.md needs refinement based on conflict Z]`."
        2.  Determine the corrective action needed. This might involve:
            *   Revisiting Step 8 (Unification) to fix the `project_roadmap.md` or resolve missed conflicts.
            *   Looping back to Step 1 (Dispatch Loop) to dispatch a revision task for a specific area's HDTA.
            *   Manually (as the Dispatcher) completing a missed `Strategy_*` task or fixing linking issues if simple enough.
        3.  Update `activeContext.md` detailing the identified issues and the plan/next step to address them.
        4.  Perform Dispatcher MUP (Section IV). Update `.clinerules` `[LAST_ACTION_STATE]` reflecting the current incomplete status (e.g., `last_action: "Dispatcher: Strategy Phase Final Check Failed - [Specific Issue Summary]."`) and set `next_action` to the required corrective step (e.g., `"Unify Cycle Plan and Update project_roadmap.md"`, `"Orchestrate Area Planning"`, or a specific action like `"Complete Final Linking"`).
        5.  State: "Corrective actions required before exiting Strategy Phase. Proceeding with `[Corrective Step]`."
        6.  **Continue execution** based on the determined corrective step.

## V. Mandatory Update Protocol (MUP) Additions (Strategy Plugin - Dispatcher Focus)
(This is Section V.A from the original combined plugin, lines 513-583, with `hierarchical_task_checklist_[cycle_id].md` changed to `current_cycle_checklist.md` and `roadmap_summary` to `project_roadmap.md` where appropriate.)

*   **(After Dispatcher Step 0 - Initialization):** Save/Update `hdta_review_progress` and `current_cycle_checklist.md`. Update `activeContext.md`. `.clinerules` `last_action: "Dispatcher: Completed Strategy Cycle Initialization (Step 0).", next_action: "Orchestrate Area Planning"`.
*   **(After Dispatcher Step 1.E - Dispatching an Atomic Sub-Task):** `.clinerules` `last_action: "Dispatcher: Dispatched sub-task...", next_action: "Review Worker Completion..."`.
*   **(After Dispatcher Step 1.G - Reviewing Worker Output):** Update `current_cycle_checklist.md`. Update Area Planning Log. Update `activeContext.md`. `.clinerules` `last_action: "Dispatcher: Reviewed Worker...", next_action: "Orchestrate Area Planning"`.
*   **(After Dispatcher Step 1.A - Area planning complete):** Update `current_cycle_checklist.md`. Update `activeContext.md`. `.clinerules` `last_action: "Dispatcher: Completed all planning for Area...", next_action: "Orchestrate Area Planning"`.
*   **(After Dispatcher Step 8 - Unification):** Ensure `project_roadmap.md` saved. Update `hdta_review_progress`. Update `current_cycle_checklist.md`. `.clinerules` `last_action: "Dispatcher: Completed Roadmap Unification (Step 8).", next_action: "Final Checks and Exit Strategy Phase"`.
*   **(After Dispatcher Step 9 - Final Checks):** If Exiting: Update `activeContext.md`, Learning Journal, `.clinerules` for Execution. If Not Exiting: Update `activeContext.md`, `.clinerules` for corrective step.

## VI. Quick Reference (Dispatcher Focus)
(This is tailored from Section VI of the original plugin, lines 599-639, focusing on Dispatcher items and updated file names.)

**Primary Goal**: Orchestrate construction/refinement of `project_roadmap.md` by defining cycle goals, identifying Areas, delegating Area planning to Workers, reviewing outputs, integrating plans into `project_roadmap.md`.

**Dispatcher Workflow Outline:**
*   **Step 0: Initialize Strategy Cycle & Overall Goals**: Define cycle goals. ID Areas. Init `project_roadmap.md`, `current_cycle_checklist.md`. Output: Goals, Areas, trackers. Next Action: `Orchestrate Area Planning`.
*   **Step 1: Main Orchestration Loop**: Outer Loop (Per Area): Select Area. Inner Loop (Per Sub-Task): Determine Sub-Task. Prep Handoff. `<new_task>` to Worker. Pause. Review Worker. Accept/Reject. If Area complete, mark in checklist. Output: Built HDTA for Areas.
*   **Step 8: Unify Cycle Plan and Update `project_roadmap.md`**: (After all Areas planned). Consolidate Area plans. Review inter-area dependencies. Update `project_roadmap.md`. Output: Updated `project_roadmap.md`. Next Action: `Final Checks...`.
*   **Step 9: Final Checks and Exit**: Verify completion criteria. If OK: MUP for Execution. Pause. If Not OK: Plan corrections, MUP for corrective step. Output: Validated roadmap, updated `.clinerules`.

**Key Trackers & Files (Dispatcher Perspective):**
*   `current_cycle_checklist.md`: Tracks high-level Area planning status for the cycle.
*   `activeContext.md`: Overall cycle goals, current orchestration area, sub-task handoff details, revision notes.
*   `hdta_review_progress_[session_id].md`: Tracks Dispatcher's review of `project_roadmap.md`.
*   `.clinerules`: `[LAST_ACTION_STATE]` managed by Dispatcher.
*   `project_roadmap.md`: Main project-wide roadmap, initialized in Step 0, updated in Step 8.
*   `cline_docs/dispatch_logs/`: Contains Dispatcher Area Planning Logs and Worker Sub-Task Output Logs (read by Dispatcher).
*   HDTA Files (created/updated by Workers, reviewed by Dispatcher).

## VII. Flowchart (Dispatcher Focus)
(This is adapted from Section VII of the original plugin, lines 670-720, focusing on the Dispatcher Instance subgraph and using updated file names.)
```mermaid
graph TD
    %% Dispatcher Workflow
    subgraph Dispatcher Instance
        D_S0[Step 0: Initialize Cycle & Goals, ID Areas, Init Roadmap & Checklist] --> D_S1_OuterLoop{Outer Loop: Select Next Area};
        
        D_S1_OuterLoop -- Area Found --> D_S1_InnerLoop{Inner Loop: Determine Next Atomic Sub-Task};
        D_S1_OuterLoop -- No More Areas --> D_S8[Step 8: Unify & Update project_roadmap.md];

        D_S1_InnerLoop -- Sub-Task ID'd --> D_PrepareHandoff[Prep Handoff];
        D_PrepareHandoff --> D_NewTask[<new_task> to Worker];
        D_NewTask -- MUP --> D_Pause[Update .clinerules, Pause];
        
        D_Pause --> D_ReviewWorker[Review Worker Output];
        D_ReviewWorker --> D_AcceptSubTask{Sub-Task OK?};
        
        D_AcceptSubTask -- Yes --> D_IntegrateSubTask[Integrate, Update Area Log/activeContext for Next Sub-Task];
        D_IntegrateSubTask -- MUP --> D_S1_InnerLoop;

        D_AcceptSubTask -- No --> D_NoteRevisions[Note Revisions in Area Log/activeContext];
        D_NoteRevisions -- MUP --> D_S1_InnerLoop; 

        D_S1_InnerLoop -- Area Planning Complete --> D_AreaComplete[Mark Area Planned];
        D_AreaComplete -- MUP --> D_S1_OuterLoop;
        
        D_S8 --> D_S8_UpdateProjectRoadmap[Update project_roadmap.md];
        D_S8_UpdateProjectRoadmap -- MUP --> D_S9[Step 9: Final Checks & Exit];
        D_S9 -- All Criteria Met --> D_Exit[Phase Complete];
        D_S9 -- Criteria NOT Met --> D_Corrections[Plan Corrections];
        D_Corrections -- MUP --> D_S1_OuterLoop; 
    end
```
*Note: This iterative Strategy phase, from the Dispatcher's view, focuses on orchestrating the creation of a detailed and actionable project roadmap by managing cycle goals and worker delegations, ensuring the main `project_roadmap.md` is consistently updated.*