# **Business Recursive Chain-of-Thought Framework (BRCT) - Strategy Plugin v1.1**

**This Plugin provides detailed instructions and procedures for the Strategy phase of the BRCT system. It should be used in conjunction with the Core System Prompt.**

---

## I. Entering and Exiting Strategy Phase

**Entering Strategy Phase:**
1.  **`.clinerules` Check**: Always read `.clinerules` first. If `[LAST_ACTION_STATE]` shows `current_phase: "Strategy"`, proceed with these instructions.
2.  **Transition from Set-up/Maintenance**: Enter after Set-up/Maintenance; `.clinerules` `next_phase` will be "Strategy".
3.  **User Trigger**: Start a new session after Set-up/Maintenance or to resume strategy.

**Exiting Strategy Phase:**
1.  **Completion Criteria:**
    -   Business ideas have been generated and evaluated.
    -   Business models have been developed for selected ideas.
    -   Strategic analyses (SWOT, market research) have been completed.
    -   Key implementation tasks derived from the strategy are identified and prioritized.
    -   Instruction files (e.g., in `strategy_tasks/` or using HDTA format) for prioritized tasks are created with objectives, context, and steps defined.
2.  **`.clinerules` Update (MUP):**
    ```
    last_action: "Completed Strategy Phase - Business Plan & Tasks Developed"
    current_phase: "Strategy"
    next_action: "Phase Complete - User Action Required"
    next_phase: "Execution"
    ```
3.  **User Action**: After updating `.clinerules`, pause for user to trigger Execution phase via a new session. See Core System Prompt, Section III for a phase transition checklist.

---

## II. Loading Context for Strategy

**Action**: Load context to guide business innovation strategy.
**Procedure:**
-   Load core files: `.clinerules`, `projectbrief.md`, `userProfile.md`, `activeContext.md`, `src/business_dependency_tracker.md`, `changelog.md`, `progress.md`.
-   *If using CRCT script:* Load `module_relationship_tracker.md`, `doc_tracker.md`.
-   *If using HDTA:* Load `system_manifest.md`.
-   Review `activeContext.md` for current state, decisions, and priorities.
-   Check `src/business_dependency_tracker.md` (and script trackers if used) for relevant dependencies.
-   Revisit `projectbrief.md` to align with business goals.
-   Examine `.clinerules` [LEARNING_JOURNAL] for past insights.
-   Review available business templates in `src/business_templates/`.

---

## III. Business Idea Generation

**Action**: Generate business ideas using structured approaches and templates.
**Procedure:**
1.  **Select Approach**: Choose methodology (Brainstorming, Mind Mapping, Design Thinking, etc.).
2.  **Use Idea Generation Template**: Utilize `src/business_templates/idea_generation_template.md` to document:
    -   Business challenge, target users, current solutions.
    -   Brainstorming process, participants, techniques.
    -   Recursive decomposition of the problem.
    -   Raw ideas generated, refined top ideas.
3.  **Apply Business Chain-of-Thought**: Document reasoning, considered factors, insights, alternatives.
4.  **MUP**: Follow Core MUP and Section VIII additions.

---

## IV. Business Idea Evaluation

**Action**: Evaluate generated business ideas using structured criteria.
**Procedure:**
1.  **Use Idea Evaluation Template**: Utilize `src/business_templates/idea_evaluation_template.md` for each promising idea:
    -   Summarize idea (name, description, problem).
    -   Assess desirability, feasibility, viability, strategic alignment.
    -   Perform SWOT analysis for the idea.
    -   Assess risks and mitigation.
2.  **Apply Recursive Decomposition**: Evaluate key components of the idea.
3.  **Document Chain-of-Thought**: Record insights, reasoning, decision rationale.
4.  **Make Recommendation**: Proceed, modify, or reject; prioritize selected ideas; define next steps.
5.  **MUP**: Follow Core MUP and Section VIII additions.

---

## V. Business Model Development

**Action**: Develop business models for selected ideas.
**Procedure:**
1.  **Use Business Model Canvas Template**: Utilize `src/business_templates/business_model_canvas.md`:
    -   Define customer segments, value propositions, channels, relationships, revenue streams, key resources, activities, partnerships, cost structure. Apply recursive analysis where helpful.
2.  **Analyze Model Coherence**: Check fit, consistency, competitive comparison.
3.  **Document Chain-of-Thought**: Record insights, dependencies, differentiators.
4.  **Define Validation Plan**: List key assumptions to test in Execution, define methods, set success criteria.
5.  **MUP**: Follow Core MUP and Section VIII additions.

---

## VI. Strategic Analysis

**Action**: Perform comprehensive strategic analyses to inform business innovation.
**Procedure:**
1.  **SWOT Analysis**:
    -   Use `src/business_templates/swot_analysis_template.md`.
    -   Analyze internal strengths/weaknesses, external opportunities/threats.
    -   Apply recursive decomposition. Analyze cross-dependencies. Develop strategic implications.
2.  **Market Research**:
    -   Use `src/business_templates/market_research_template.md`.
    -   Define objectives. Analyze market overview, segments, trends. Perform competitive analysis. Develop personas/journeys. Apply recursive analysis. Document methodology.
3.  **Dependency Analysis**:
    -   Update `src/business_dependency_tracker.md` (and script trackers if used) with new insights. Refine relationships.
4.  **MUP**: Follow Core MUP and Section VIII additions.

---

## VII. Creating Implementation Task Instructions

**Action**: Create structured instruction files for prioritized tasks identified during strategy.

**Procedure:**
1.  **Identify Key Tasks**: Based on evaluated ideas, business models, and strategic analysis, identify the key tasks needed for the Execution phase (e.g., market validation, prototype development, operational setup).
2.  **Prioritize Tasks**:
    -   Review tasks identified.
    -   Assess dependencies (using `src/business_dependency_tracker.md` or script commands like `show-dependencies`).
    -   Consider project goals (`projectbrief.md`) and current state (`activeContext.md`).
    -   Update `activeContext.md` with prioritized task list and reasoning.
3.  **Choose Instruction Format & Location:**
    -   **Option A (Simple)**: Create `{task_name}_instructions.md` in `strategy_tasks/`. Use clear names.
    -   **Option B (HDTA)**: Create HDTA documents (`implementation_plan_{...}.md`, `{task_name}.md`) potentially within module directories, following CRCT templates if desired. Manually link these within the HDTA structure (e.g., link Task Instructions to Implementation Plans).
4.  **Populate Instruction File Sections (Adapt based on chosen format):**
    -   Set title: `# {Task Name} Instructions`
    -   Define **Objective**: Clear purpose and goals.
    -   Provide **Context**: Background, constraints, links to relevant strategy documents (e.g., evaluation, BMC).
    -   List **Dependencies**: Reference business factors, other tasks, required resources/information.
    -   Outline **Steps**: Break into actionable increments for the Execution phase.
    -   Specify **Expected Output**: Describe deliverables.
    -   Add **Notes**: Challenges, considerations, links.
    -   Example (Simple Format):
        ```
        # Market Validation Task Instructions

        ## Objective
        Validate assumptions about target market segment and value proposition via customer interviews.

        ## Context
        Derived from Business Model Canvas v1 and Idea Evaluation for 'Project X'. Key assumptions: customer willingness to pay, problem severity.

        ## Dependencies
        - Business Factors: Target Customer Segment definition, Value Proposition details.
        - Resources: Access to potential customer contacts.

        ## Steps
        1. Develop customer interview script focusing on problem validation and willingness to pay.
        2. Identify and schedule 10-15 interviews with target customer profile.
        3. Conduct interviews using the script, focusing on open-ended questions.
        4. Synthesize feedback, identifying patterns related to assumptions.
        5. Document findings and update relevant sections of BMC and Idea Evaluation.

        ## Expected Output
        - Finalized interview script.
        - Interview notes/summaries.
        - Report summarizing findings on key assumptions.
        - Updated BMC and Idea Evaluation documents.

        ## Notes
        - Seek disconfirming evidence during interviews.
        - Schedule buffer time between interviews for note-taking.
        ```
5.  **Pre-Action Verification (for file creation):** Check if instruction file already exists to avoid overwrites unless intended.
6.  **MUP**: Follow Core MUP and Section VIII additions after creating/updating instruction files.

---

## VIII. Strategy Plugin - MUP Additions

After Core MUP steps (Update `activeContext.md`, `changelog.md`, `.clinerules` [LAST_ACTION_STATE]):
1.  **Update Business Templates**: Save completed/updated templates (Idea Gen, Eval, BMC, SWOT, Market Research).
2.  **Update Dependency Trackers**: Save changes to `src/business_dependency_tracker.md` or confirm script commands completed.
3.  **Update Instruction Files**: Save newly created or modified task instruction files.
4.  **Update HDTA Documents (If used)**: Save changes and ensure manual links are correct (e.g., in `system_manifest.md`).
5.  **Update `activeContext.md` with Strategy Outcomes:**
    -   Summarize generated/evaluated ideas, developed models, strategic insights.
    -   List created instruction file locations/names.
    -   Document task priorities and reasoning.
6.  **Update `.clinerules` [LAST_ACTION_STATE]:**
    -   Example after completing a major strategy step:
        ```
        [LAST_ACTION_STATE]
        last_action: "Completed Idea Generation and Evaluation"
        current_phase: "Strategy"
        next_action: "Develop Business Model"
        next_phase: "Strategy"
        ```
    -   Example after completing the strategy phase:
        ```
        [LAST_ACTION_STATE]
        last_action: "Completed Strategy Phase - Business Plan & Tasks Developed"
        current_phase: "Strategy"
        next_action: "Phase Complete - User Action Required"
        next_phase: "Execution"
        ```

---

## IX. Quick Reference

### Business Innovation Templates (`src/business_templates/`)
-   `idea_generation_template.md`
-   `idea_evaluation_template.md`
-   `business_model_canvas.md`
-   `swot_analysis_template.md`
-   `market_research_template.md`

### Key Strategy Actions
1.  Generate business ideas.
2.  Evaluate ideas using structured criteria.
3.  Develop business models for selected ideas.
4.  Perform strategic analyses (SWOT, Market Research).
5.  Prioritize implementation tasks.
6.  Create task instructions (in `strategy_tasks/` or using HDTA).
7.  Follow MUP after each major action.

---

## X. Utility Commands

This section describes utility functions available during the Strategy phase.

### X.1 Convert Markdown to PDF

**Action**: Convert a specified Markdown file (e.g., a strategic report, evaluation summary) to a professionally styled PDF document.
**Trigger**: User request like "Convert `<markdown_file_path>` to PDF".
**Procedure**:
1.  **Identify Input**: Get the full path to the Markdown file (`<markdown_file_path>`) from the user request.
2.  **Identify Output (Optional)**: Check if the user specified an output directory. If not, the PDF will be saved in the same directory as the Markdown file.
3.  **Verify Input**: Ensure the path points to a valid `.md` file.
4.  **Execute Conversion**:
    -   Use the `execute_command` tool to run the `cline_utils/file_converter.py` script.
    -   Construct the command: `python cline_utils/file_converter.py "<absolute_markdown_path>" [--output_directory "<absolute_output_directory>"]`
    -   Ensure the `file_converter.py` script is executable and handles command-line arguments correctly (as updated previously).
5.  **Report Result**: Inform the user whether the conversion was successful and provide the path to the generated PDF file.
6.  **MUP**: Follow Core MUP (update `activeContext.md`, `changelog.md`, `.clinerules` [LAST_ACTION_STATE] reflecting the utility action).
