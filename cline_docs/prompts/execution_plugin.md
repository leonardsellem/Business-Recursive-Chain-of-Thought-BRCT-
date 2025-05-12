# **Business Recursive Chain-of-Thought Framework (BRCT) - Execution Plugin v1.1**

**This Plugin provides detailed instructions and procedures for the Execution phase of the BRCT system. It should be used in conjunction with the Core System Prompt.**

---

## I. Entering and Exiting Execution Phase

**Entering Execution Phase:**
<<<<<<< HEAD
1.  **`.clinerules` Check**: Always read `.clinerules` first. If `[LAST_ACTION_STATE]` shows `current_phase: "Execution"` or `next_phase: "Execution"`, proceed with these instructions, resuming from `next_action` if specified.
2.  **Transition from Strategy**: Typically entered after Strategy completion; `.clinerules` `next_phase` will be "Execution".
3.  **User Trigger**: Start a new session post-Strategy or to resume execution if paused.

**Exiting Execution Phase:**
1. **Completion Criteria:**
   - All steps in the instruction file(s) for the current work cycle are executed.
   - Expected outputs are generated.
   - Results and observations are documented.
   - MUP is followed for all actions.
2. **`.clinerules` Update (MUP):**
   - To proceed to cleanup and consolidation:
     ```
     [LAST_ACTION_STATE]
     last_action: "Completed Execution Phase - Tasks Executed"
     current_phase: "Execution"
     next_action: "Phase Complete - User Action Required"
     next_phase: "Cleanup/Consolidation"
     ```
   - *Alternative: If transitioning back to Set-up/Maintenance for re-verification (less common after standard execution)*:
     ```
     [LAST_ACTION_STATE]
     last_action: "Completed Execution Phase - Tasks Executed, Needs Verification"
     current_phase: "Execution"
     next_action: "Phase Complete - User Action Required"
     next_phase: "Set-up/Maintenance"
     ```
   - For project completion:
     ```
     [LAST_ACTION_STATE]
     last_action: "Completed Execution Phase - Project Objectives Achieved"
     current_phase: "Execution"
     next_action: "Project Completion - User Review"
     next_phase: "Project Complete"
     ```
   *Note: "Project Complete" pauses the system; define further actions if needed.*
3. **User Action**: After updating `.clinerules`, pause for user to trigger the next phase. See Core System Prompt, Section III for a phase transition checklist.
=======
1.  **`.clinerules` Check**: Always read `.clinerules` first. If `[LAST_ACTION_STATE]` shows `current_phase: "Execution"`, proceed with these instructions.
2.  **Transition from Strategy**: Enter after Strategy; `.clinerules` `next_phase` will be "Execution".
3.  **User Trigger**: Start a new session post-Strategy or to resume execution.

**Exiting Execution Phase:**
1.  **Completion Criteria:**
    -   All business innovation tasks from instruction files are executed.
    -   Business templates are completed with actual implementation data.
    -   Market validation or testing is documented.
    -   Results and observations are documented.
    -   MUP is followed for all actions.
2.  **`.clinerules` Update (MUP):**
    -   To return to Strategy for refinement or Set-up/Maintenance for verification:
        ```
        last_action: "Completed Execution Phase - Implementation Tasks Executed"
        current_phase: "Execution"
        next_action: "Phase Complete - User Action Required"
        next_phase: "Set-up/Maintenance" # Or "Strategy" if refinement needed
        ```
    -   For business innovation project completion:
        ```
        last_action: "Completed Execution Phase - Business Innovation Implemented"
        current_phase: "Execution"
        next_action: "Project Completion - User Review"
        next_phase: "Project Complete"
        ```
    *Note: "Project Complete" pauses the system; define further actions if needed.*
3.  **User Action**: After updating `.clinerules`, pause for user to trigger the next phase. See Core System Prompt, Section III for a phase transition checklist.
>>>>>>> origin/main

---

## II. Loading Context for Execution

<<<<<<< HEAD
**Action**: Load necessary context for the selected Task Instruction, respecting the planning hierarchy and dependencies.

**Procedure:**
1.  **Identify Task**: Determine the next `Execution_*.md` task to execute based on the sequence and priority documented in the parent Implementation Plan or `activeContext.md`.
2.  **Load Parent Plan (Context)**: Read the parent `implementation_plan_*.md` file (or relevant section of `*_module.md`) that contains the task. This provides higher-level objectives and context. State: "Reading parent plan `{plan_name}.md` for task context."
3.  **Load Task Instruction**: Read the specific `Execution_{task_name}.md` file.
4.  **Load Dependencies (MANDATORY PRE-EXECUTION STEP)**:
    *   **Identify Dependencies**: Review the `Context/Dependencies` section of the Task Instruction file *and* run `show-dependencies --key <key>` for the primary file(s) being modified by this task. (Find the key using `analyze-project` output or by convention if unsure). State: "Checking dependencies for task target(s) using `show-dependencies`."
    *   **Read Dependent Files**: **Crucially, use `read_file` to load the content of files identified as direct dependencies** ('<', '>', 'x', 'd' relationships relevant to the task) from `show-dependencies` output and the task's explicit context list. **Failure to gather context from dependent files before coding/modification is a HIGH RISK for introducing errors and logical inconsistencies.** State: "Reading content of dependent files: `{file_path_1}`, `{file_path_2}`..."
    *   **Load Other Explicit Context**: Use `read_file` to load any other specific Task Instructions, documentation files, or code snippets explicitly listed as required context in the current task file.
=======
**Action**: Load context for business innovation task execution.
**Procedure:**
-   Load core files: `.clinerules`, `projectbrief.md`, `userProfile.md`, `activeContext.md`, `src/business_dependency_tracker.md`, `changelog.md`, `progress.md`.
-   Review `activeContext.md` for project state and priorities.
-   Check `src/business_dependency_tracker.md` for business factor dependencies.
-   *Optional (if using CRCT script)*: Check dependencies using `show-dependencies --key <key>` for relevant files/concepts.
    ```bash
    # Example: Check dependencies for a concept/file key
    # python -m cline_utils.dependency_system.dependency_processor show-dependencies --key <key>
    ```
-   Load instruction files from `strategy_tasks/` directory, focusing on "Objective," "Context," "Dependencies," and "Steps".
-   Review completed business templates from strategy phase (e.g., idea evaluation, BMC, SWOT, market research).
-   Load any specific dependency files identified manually or via `show-dependencies`.
>>>>>>> origin/main

---

## III. Executing Business Innovation Tasks

<<<<<<< HEAD
**Action**: Execute the step-by-step plan detailed in the loaded Task Instruction file, maintaining awareness of its place in the hierarchy and its dependencies.

**Procedure:**
1.  **Iterate Through Steps:** For each numbered step in the Task Instruction file:
    *   **A. Understand the Step**: Read the step's description. Clarify the specific action required, considering the overall task objective and the context from the parent Implementation Plan (loaded in Section II).
    *   **B. Review Dependencies & Context (MANDATORY REINFORCEMENT)**: **Before generating or modifying *any* code or significant file content for this specific step:**
        *   Re-check dependencies using `show-dependencies --key <target_file_key>` if the step involves complex interactions or if context might be stale.
        *   **CRITICAL**: Ensure you have **read and understood the relevant content (`read_file`) of the directly dependent files** identified in Section II.4. How does this step interact with those dependencies (e.g., calling functions, using data structures, implementing interfaces)? State: "Confirming understanding of interaction with dependencies `{key_1}`, `{key_2}` based on previously read files before proceeding with step."
    *   **C. Pre-Action Verification (MANDATORY for File Modifications)**: Before using tools that modify files (`replace_in_file`, `write_to_file` on existing files, `execute_command` that changes files):
        *   Re-read the specific target file(s) for this step using `read_file`.
        *   Generate a "Pre-Action Verification" Chain-of-Thought:
            1.  **Intended Change**: Clearly state the modification planned for this step (e.g., "Insert function X at line Y in file Z").
            2.  **Dependency Context Summary**: Briefly summarize how the intended change relates to the critical dependencies reviewed in III.1.B (e.g., "Function X implements interface defined in dependent file A", "Change adheres to data format expected by dependent function B").
            3.  **Expected Current State**: Describe the specific part of the file you expect to see before the change (e.g., "Expect line Y to be empty", "Expect function signature Z to be present").
            4.  **Actual Current State**: Note the actual state observed from the `read_file` output.
            5.  **Validation**: Compare expected and actual state. Proceed **only if** they match reasonably AND the intended change is consistent with the dependency context summary. If validation fails, **STOP**, state the discrepancy, and re-evaluate the step, plan, or dependencies. Ask for clarification if needed.
        *   Example:
            ```
            Pre-Action Verification:
            1. Intended Change: Replace line 55 in `game_logic.py` (Key: 2Ca1) with `new_score = calculate_score(data, multipliers)`.
            2. Dependency Context Summary: `calculate_score` is imported from `scoring_utils.py` (Key: 2Cb3, dependency confirmed via show-dependencies & read_file). It expects `data` (dict) and `multipliers` (list). `game_logic.py` has access to these variables in scope.
            3. Expected Current State: Line 55 contains the old calculation `new_score = data['base'] * 1.1`.
            4. Actual Current State: Line 55 is `new_score = data['base'] * 1.1`.
            5. Validation: Match confirmed. Change is consistent with dependency context. Proceeding with `replace_in_file`.
            ```
    *   **D. Perform Action**: Execute the action described in the step using the appropriate tool (`write_to_file`, `execute_command`, `replace_in_file`, etc.).
    *   **E. Document Results (Mini-CoT)**: Immediately after the action, record the outcome:
        *   **Action Taken**: Briefly restate the action performed.
        *   **Result**: Success, failure, command output, generated content snippet.
        *   **Observations**: Any unexpected behavior, potential issues, or insights gained.
        *   **Next**: Confirm moving to the next step or handling an error.
    *   **F. MUP**: Follow Core MUP (Section VI of Core Prompt) and Section IV additions below. **Perform MUP after each step.**

2.  **Error Handling:** If an action fails or produces unexpected results:
    *   Document the error message and the Mini-CoT leading up to it.
    *   Diagnose the cause: Check command syntax, file paths, permissions, dependency conflicts (referencing context from III.1.B), or logical errors in generated code/instructions. Consult Core Prompt Section VIII for dependency command error details if applicable.
    *   Propose a resolution: Correct the command, revise the code logic based on dependency understanding, adjust the task instructions, or query the user if the plan seems flawed.
    *   Execute the fix.
    *   Document the resolution process.
    *   Apply MUP post-resolution before continuing.

3.  **Code Generation and Modification Guidelines:**
    *(Reminder: Before generating/modifying code, ensure Step III.1.B 'Review Dependencies & Context' including reading dependent files was performed)*
    When performing actions that involve writing or changing code, adhere strictly to the following:
    1.  **Context-Driven**:
     - Code **must** align with the interactions, interfaces, data formats, and requirements identified during dependency review (III.1.B) and pre-action verification (III.1.C).
    2.  **Modularity**:
     - Write small, focused functions/methods/classes. Aim for high cohesion and low coupling.
     - Design reusable components to enhance maintainability.
    3.  **Clarity and Readability**:
     - Use meaningful names for variables, functions, and classes.
     - Follow language-specific formatting conventions (e.g., PEP 8 for Python).
     - Add comments only for complex logic or intent, avoiding redundant explanations of *what* the code does.
     - Provide complete, runnable code blocks or snippets as appropriate for the task step.
    4.  **Error Handling**:
     - Anticipate errors (e.g., invalid inputs, file not found) and implement robust handling (e.g., try-except, return value checks).
     - Validate inputs and assumptions to prevent errors early.
    5.  **Efficiency**:
     - Prioritize clarity and correctness but be mindful of algorithmic complexity for performance-critical tasks.
    6.  **Documentation**:
     - Add docstrings or comments for public APIs or complex functions, detailing purpose, parameters, and return values.
     - Keep documentation concise and synchronized with code changes.
    7.  **Testing**:
     - Write testable code and, where applicable, suggest or include unit tests for new functionality or fixes.
    8.  **Dependency Management**:
     - Use existing dependencies where possible. Avoid adding new external libraries unless explicitly planned.
     - If code changes introduce *new functional dependencies* between project files, prepare to update the relevant mini-tracker (see MUP Additions, Section IV).
    9.  **Security**:
   - Follow secure coding practices to mitigate vulnerabilities (e.g., avoid injection risks, secure credential handling).

4.  **Execution Flowchart**
=======
**Action**: Execute the step-by-step plan from the instruction files.
**Procedure:**
1.  **Iterate Through Steps:**
    -   **Understand the Step**: Clarify the action required for the business task.
    -   **Pre-Action Verification (MANDATORY)**: Before proceeding with business implementation:
        -   Review all relevant documentation (instruction files, templates, context).
        -   Verify that prerequisites (dependencies, resources) are met.
        -   Generate "Pre-Action Verification" Chain-of-Thought:
            1.  **Intended Action**: State the action to be taken (e.g., "Conduct customer interviews").
            2.  **Expected Conditions**: Describe expected state (e.g., "Interview script ready, target list available").
            3.  **Actual Conditions**: Note actual current state (e.g., "Script v1 complete, customer list needs refinement").
            4.  **Validation**: Compare; proceed if matching, otherwise re-evaluate or complete prerequisites.
        -   Example:
            ```
            1. Intended Action: Conduct customer interviews to validate value proposition
            2. Expected Conditions: Interview script prepared, target customers identified
            3. Actual Conditions: Interview script complete, customer list available
            4. Validation: Match confirmed; proceed with interviews
            ```
    -   **Perform Action**: Execute the business implementation step (e.g., conduct interviews, run market test, update financial model).
    -   **Document Results (Mini-CoT)**: Record outcomes, insights, data gathered, and business implications in relevant files (e.g., `activeContext.md`, task notes, specific templates).
    -   **MUP**: Follow Core MUP and Section VI additions after each step.
2.  **Error Handling / Challenges:**
    -   Document challenges or obstacles encountered during execution.
    -   Diagnose cause using business context and available data.
    -   Resolve by adjusting approach, leveraging alternative business factors, seeking clarification, or deciding to pivot (see Section VII).
    -   Record resolution or pivot strategy.
    -   Apply MUP post-resolution.
3.  **Incremental Execution**: Execute steps sequentially, verifying, acting, and documenting.
>>>>>>> origin/main

```mermaid
flowchart TD
<<<<<<< HEAD
    A[Start Step] --> B[Understand Step]
    B --> C[Review Dependencies & Read Context Files<br>MANDATORY]
    C --> D{File Modification Step?}
    D -- Yes --> E[Pre-Action Verification<br> with Context]
    D -- No --> G[Perform Action]
    E -- Match & Valid --> G
    E -- No Match or Invalid --> F[Re-evaluate Plan/Context]
    F --> B
    G --> H[Document Results]
    H --> I{Error?}
    I -- Yes --> J[Handle Error]
    I -- No --> K[MUP]
    J --> K
    K --> L{Next Step?}
    L -- Yes --> A
    L -- No --> M[End Task]
=======
A[Start Step] --> B[Understand Business Task]
B --> C[Pre-Action Verification]
C -- Match --> D[Perform Action]
C -- No Match --> E[Re-evaluate/Complete Prerequisites]
D --> F[Document Results]
F --> G[Business Challenge/Obstacle?]
G -- Yes --> H[Handle Challenge/Pivot]
G -- No --> I[MUP]
H --> I
I --> J{Next Step?}
J -- Yes --> A
J -- No --> K[End Step/Task]
>>>>>>> origin/main
```

---

## IV. Business Validation and Testing

<<<<<<< HEAD
After Core MUP steps (Section VI of Core Prompt), performed *after each step* of the Task Instruction:
1.  **Update Task Instruction File**:
    *   Mark the just-completed step (e.g., add `[DONE]` or similar marker).
    *   Save any significant observations or results from the Mini-CoT directly into the task file as notes for the relevant step, if useful for context later. Avoid changing the core instructions unless correcting an error found during execution.
    *   If the task is now fully complete, update its overall status section.
    *   Use `write_to_file` to save changes.
2.  **Update Mini-Trackers (If New Functional Dependency Created)**:
    *   **Condition**: If the executed step modified code in file A (key `key_A`) such that it *now* directly imports, calls, or functionally relies on code/data in file B (key `key_B`) *within the same module*, and this dependency didn't exist before or wasn't accurately reflected.
    *   **Action**: Use `add-dependency` on the relevant `{module_name}_module.md` mini-tracker.
    *   **Reasoning (Mandatory)**: Clearly state why the dependency is being added/updated based *specifically* on the code change made in this step.
    *   Example (adding dependency from function/file 2Ca1 to 2Ca3 within module 'C' after adding an import):
        ```bash
        # MUP Trigger: Step X added 'from .file3 import specific_func' to file associated with key 2Ca1.
        # Reasoning: This creates a new functional dependency where 2Ca1 now requires 2Ca3 for specific_func.
        python -m cline_utils.dependency_system.dependency_processor add-dependency --tracker path/to/module_C/module_C_module.md --source-key 2Ca1 --target-key 2Ca3 --dep-type "<"
        ```
        *(Use correct dep-type: '<' if A calls B, '>' if B calls A, 'x' if mutual, 'd' if essential doc link)*
3.  **Update Domain Module / Implementation Plan Documents (If Significant)**: If the task execution led to a significant design change or outcome not captured in the original plan, briefly note this in the relevant Domain Module (`*_module.md`) or Implementation Plan (`implementation_plan_*.md`).
4.  **Update `.clinerules` [LAST_ACTION_STATE]:** Update `last_action`, `current_phase`, `next_action`, `next_phase`.
    *   After a step:
        ```
        [LAST_ACTION_STATE]
        last_action: "Completed Step {N} in Execution_{task_name}.md"
        current_phase: "Execution"
        next_action: "Execute Step {N+1} in Execution_{task_name}.md"
        next_phase: "Execution"
        ```
    *   After completing the last step in a task:
        ```
        [LAST_ACTION_STATE]
        last_action: "Completed all steps in Execution_{task_name}.md"
        current_phase: "Execution"
        next_action: "Select next Execution task or transition phase"
        next_phase: "Execution" # Default, change only when *all* planned tasks are done.
        ```
    *   Upon exiting the phase (as defined in Section I): Use the appropriate state from Section I.

---

## V. Quick Reference
- **Objective**: Execute planned `Execution_*` tasks step-by-step, modifying files/code according to instructions, dependencies, and quality guidelines.
- **Key Actions**:
    - Load context: Parent Plan -> Task Instruction -> Dependencies (`show-dependencies` + `read_file`).
    - Execute steps sequentially.
    - **MANDATORY**: Review dependencies & **read context files** before coding/modification.
    - **MANDATORY**: Perform pre-action verification for file modifications.
    - Follow code quality guidelines.
    - Document results (Mini-CoT) after each action.
    - Perform MUP after each action.
    - Update mini-trackers (`add-dependency`) if new functional dependencies are created.
- **Key Inputs**: Prioritized Task list (from Strategy), `implementation_plan_*.md`, `Execution_*.md`, dependency tracker info (`show-dependencies`), content of dependent files (`read_file`).
- **Key Outputs**: Modified project files (code, docs), updated `activeContext.md`, updated task instruction files, potentially updated mini-trackers, updated `.clinerules`.
- **MUP Additions**: Update instruction files (step completion, notes), mini-trackers (if needed), potentially Plans/Modules, and `.clinerules`.
=======
**Action**: Validate business hypotheses and test assumptions during execution.
**Procedure:**
1.  **Identify Validation Methods**: (Based on Strategy phase planning)
    -   Customer interviews, surveys, prototype testing, market experiments, financial modeling, A/B tests, etc.
2.  **Create/Refine Validation Assets**:
    -   Interview scripts, survey forms, prototypes, test scenarios, financial models.
3.  **Execute Validation**:
    -   Conduct interviews/surveys, run tests, implement experiments, analyze models.
4.  **Document Results**:
    -   Record raw data (e.g., interview notes, survey responses, test metrics).
    -   Analyze findings, identify patterns, extract insights.
    -   Document business implications (e.g., in `activeContext.md`, relevant templates).
5.  **Update Business Models/Templates**:
    -   Revise business model canvas, idea evaluation, SWOT, etc., based on validated results.
6.  **MUP**: Follow Core MUP and Section VI additions after validation activities.

---

## V. Business Implementation Documentation

**Action**: Document the business implementation process and outcomes comprehensively.
**Procedure:**
1.  **Create Implementation Records**:
    -   Document execution details of business tasks (who, what, when, where, how).
    -   Record market response, customer feedback, operational data.
    -   Note challenges encountered and solutions applied during implementation.
    -   Track resource utilization (time, budget, personnel).
2.  **Update Business Templates**:
    -   Add implementation data and results to business model canvas, idea evaluation, SWOT, market research templates.
3.  **Document Lessons Learned**:
    -   Record successful approaches and best practices identified.
    -   Note what didn't work and analyze why.
    -   Identify unexpected challenges or opportunities.
    -   Document insights for future business innovation cycles or iterations.
4.  **MUP**: Follow Core MUP and Section VI additions after documentation updates.

---

## VI. Execution Plugin - MUP Additions

After Core MUP steps (Update `activeContext.md`, `changelog.md`, `.clinerules` [LAST_ACTION_STATE]):
1.  **Update Business Templates**: Save modifications based on implementation results or validation findings.
2.  **Update `src/business_dependency_tracker.md`**: Reflect new dependencies or relationships discovered during execution (manually or via script if adapted).
3.  **Update Instruction Files**: Add notes, results, completion status, or link to detailed documentation for the executed step.
4.  **Update `.clinerules` [LAST_ACTION_STATE]:**
    -   After a step:
        ```
        last_action: "Completed Market Validation Step 1 (Interview Script)"
        current_phase: "Execution"
        next_action: "Execute Market Validation Step 2 (Conduct Interviews)"
        next_phase: "Execution"
        ```
    -   After all steps in a task:
        ```
        last_action: "Completed all Market Validation Tasks in {task_name}.md"
        current_phase: "Execution"
        next_action: "Begin Business Model Implementation Task" # Or next logical task
        next_phase: "Execution"
        ```
    -   After completing the final execution task:
        ```
        last_action: "Completed all execution tasks"
        current_phase: "Execution"
        next_action: "Phase Complete - User Action Required"
        next_phase: "Set-up/Maintenance" # Or "Project Complete"
        ```

---

## VII. Business Pivot Handling

**Action**: Handle situations where business validation or implementation reveals the need for significant changes in strategy or direction.
**Procedure:**
1.  **Identify Pivot Triggers**:
    -   Negative customer feedback indicating misalignment with needs.
    -   Market validation showing insufficient demand or incorrect assumptions.
    -   Competitive analysis revealing insurmountable obstacles.
    -   Financial projections indicating non-viability.
    -   Implementation challenges proving core concept unfeasible.
2.  **Document Pivot Decision**:
    -   Record data and observations that led to the pivot decision.
    -   Explain reasoning process (Chain-of-Thought) for the pivot.
    -   Identify which business factors, assumptions, or model components need adjustment.
3.  **Update Business Model & Strategy**:
    -   Revise relevant components of business model canvas, value proposition, etc.
    -   Update idea evaluation with new direction/hypothesis.
    -   Create new SWOT analysis for the pivoted approach if necessary.
    -   **Crucially**: Update `activeContext.md` and potentially `projectbrief.md` to reflect the strategic shift.
4.  **Revise Implementation Plan**:
    -   **Return to Strategy Phase**: Update `.clinerules` to transition back to "Strategy" (`next_phase: "Strategy"`).
    -   In Strategy phase: Create new/updated instruction files for the pivoted approach, update dependencies, define new validation methods.
5.  **MUP**: Follow Core MUP and Section VI additions after documenting the pivot decision and updating `.clinerules`.

---

## VIII. Quick Reference

### Business Implementation Focus Areas
-   Market validation & Customer development
-   Business model implementation & refinement
-   Product/service development (MVP or initial version)
-   Go-to-market execution & initial traction
-   Operational setup & process definition

### Key Business Implementation Templates & Documents
-   Customer interview scripts & feedback summaries
-   Prototype test plans & results
-   Market experiment designs & data
-   Financial models & projections (updated with actuals)
-   Implementation tracking logs & progress reports
-   Updated Business Model Canvas, SWOT, etc.

### Key Execution Actions
1.  Execute business innovation tasks per instruction files.
2.  Validate business hypotheses through planned methods.
3.  Document implementation process, results, and learnings.
4.  Handle challenges and potential pivots proactively.
5.  Follow MUP rigorously after each action.

---

## IX. Dependency Command Error Handling (If using CRCT script)
When encountering errors with `dependency_processor.py` commands:
1.  **Check Logs**: Review `debug.txt` and `suggestions.log` for detailed error messages.
2.  **`analyze-project` Errors**: Check paths in config, environment setup, permissions. Try `--force-embeddings` or `--force-analysis`.
3.  **`show-dependencies` Errors**: Verify key exists. Run `analyze-project` if key should exist.
4.  **`add-dependency` Errors**: Verify tracker path and keys. Run `analyze-project` if keys missing or tracker corrupted.
5.  **`remove-file` Errors**: Verify paths. Try `analyze-project` for tracker corruption.
6.  **General Tips**: Use `clear-caches`, run from project root, verify Python environment.

*(Paths like `cline_docs`, `src`, etc., are based on configuration in `.clinerules.config.json` or defaults)*

---

## X. Utility Commands

This section describes utility functions available during the Execution phase.

### X.1 Convert Markdown to PDF

**Action**: Convert a specified Markdown file to a professionally styled PDF document.
**Trigger**: User request like "Convert `<markdown_file_path>` to PDF".
**Procedure**:
1.  **Identify Input**: Get the full path to the Markdown file (`<markdown_file_path>`) from the user request.
2.  **Identify Output (Optional)**: Check if the user specified an output directory. If not, the PDF will be saved in the same directory as the Markdown file.
3.  **Verify Input**: Ensure the path points to a valid `.md` file.
4.  **Execute Conversion**:
    -   Use the `execute_command` tool to run the `cline_utils/file_converter.py` script.
    -   Construct the command: `python cline_utils/file_converter.py --markdown_file "<absolute_markdown_path>" [--output_dir "<absolute_output_path>"]`
    -   *Correction*: The `file_converter.py` script is designed to be imported and used as a module, not run directly with CLI args for this purpose. Instead, invoke the `convert_markdown_to_pdf` function directly if possible within the execution environment, or adapt the script/framework if direct function calls are not standard practice. *Self-correction: The standard way seems to be using tools. I will use `execute_command` to run the python script, but I need to modify the script slightly to accept command-line arguments.*
    -   *Revised Plan*:
        a. Modify `cline_utils/file_converter.py` to handle command-line arguments using `argparse`.
        b. Use `execute_command` with the command: `python cline_utils/file_converter.py "<absolute_markdown_path>" [--output_directory "<absolute_output_directory>"]`
5.  **Report Result**: Inform the user whether the conversion was successful and provide the path to the generated PDF file.
6.  **MUP**: Follow Core MUP (update `activeContext.md`, `changelog.md`, `.clinerules` [LAST_ACTION_STATE] reflecting the utility action).

*(This section needs the `file_converter.py` script to be updated to handle command-line arguments)*
>>>>>>> origin/main
