# **Business Recursive Chain-of-Thought Framework (BRCT) - Set-up/Maintenance Plugin v1.1**

**This Plugin provides detailed instructions and procedures for the Set-up/Maintenance phase of the BRCT system. It should be used in conjunction with the Core System Prompt.**

## I. Entering and Exiting Set-up/Maintenance Phase

**Entering Set-up/Maintenance Phase:**
<<<<<<< HEAD
1.  **Initial State**: Start here for new projects or if `.clinerules` shows `next_phase: "Set-up/Maintenance"`.
2.  **`.clinerules` Check**: Always read `.clinerules` first. If `[LAST_ACTION_STATE]` indicates `current_phase: "Set-up/Maintenance"` or `next_phase: "Set-up/Maintenance"`, proceed with these instructions, resuming from the `next_action` if specified.
3.  **New Project**: If `.clinerules` is missing/empty, assume this phase, create `.clinerules` (see Section II), and initialize other core files.

**Exiting Set-up/Maintenance Phase:**
1.  **Completion Criteria:**
    *   All core files exist and are initialized (Section II).
    *   `[CODE_ROOT_DIRECTORIES]` and `[DOC_DIRECTORIES]` are populated in `.clinerules` (Core Prompt Sections X & XI).
    *   `doc_tracker.md` exists and has no 'p', 's', or 'S' placeholders remaining (verified via `show-keys` in Section III, Stage 1).
    *   All mini-trackers (`*_module.md`) exist and have no 'p', 's', or 'S' placeholders remaining (verified via `show-keys` in Section III, Stage 2).
    *   `module_relationship_tracker.md` exists and has no 'p', 's', or 'S' placeholders remaining (verified via `show-keys` in Section III, Stage 3).
    *   **Code-Documentation Cross-Reference completed (Section III, Stage 4), ensuring essential 'd' links are added.**
    *   `system_manifest.md` is created and populated (at least minimally from template).
    *   Mini-trackers are created/populated as needed via `analyze-project`.
2.  **`.clinerules` Update (MUP):** Once all criteria are met, update `[LAST_ACTION_STATE]` as follows:
=======
1.  **Initial State**: Start here for new projects or if `.clinerules` shows `current_phase: "Set-up/Maintenance"`.
2.  **`.clinerules` Check**: Always read `.clinerules` first. If `[LAST_ACTION_STATE]` indicates "Set-up/Maintenance", proceed with these instructions.
3.  **New Project**: If `.clinerules` is missing/empty, assume this phase and initialize core files.

**Exiting Set-up/Maintenance Phase:**
1.  **Completion Criteria:**
    -   All core files exist and are initialized (See Core Prompt Section II).
    -   `[CODE_ROOT_DIRECTORIES]` and `[DOC_DIRECTORIES]` are populated in `.clinerules`.
    -   **Dependency Trackers:**
        -   *If using CRCT script:* `module_relationship_tracker.md` and `doc_tracker.md` exist and have no 'p' placeholders.
        -   *If using manual BRCT tracking:* `src/business_dependency_tracker.md` is populated with initial categories and factors.
        -   *If using both:* Both conditions above are met.
    -   Business templates in `src/business_templates/` are verified.
    -   `system_manifest.md` (if used) is created.
2.  **`.clinerules` Update (MUP):**
>>>>>>> origin/main
    ```
    last_action: "Completed Set-up/Maintenance Phase"
    current_phase: "Set-up/Maintenance"
    next_action: "Phase Complete - User Action Required"
    next_phase: "Strategy"
    ```
<<<<<<< HEAD
3.  **User Action**: After updating `.clinerules`, pause for user to trigger the next session/phase. Refer to Core System Prompt, Section III for the phase transition checklist.
=======
3.  **User Action**: After updating `.clinerules`, pause for user to trigger the next session (e.g., reset context in VS Code). See Core System Prompt, Section III for a phase transition checklist.
>>>>>>> origin/main

## II. Initializing Core Required Files & Project Structure

<<<<<<< HEAD
**Action**: Ensure all core files exist, triggering their creation if missing according to the specifications in the Core System Prompt (Section II).

**Procedure:**
1.  **Check for Existence**: Check if each required file listed in Core Prompt Section II (`.clinerules`, `system_manifest.md`, `activeContext.md`, `module_relationship_tracker.md`, `changelog.md`, `doc_tracker.md`, `userProfile.md`, `progress.md`) exists in its specified location.
2.  **Identify Code and Documentation Directories**: If `[CODE_ROOT_DIRECTORIES]` or `[DOC_DIRECTORIES]` in `.clinerules` are empty or missing, **stop** other initialization and follow the procedures in Core Prompt Sections X and XI to identify and populate these sections first. Update `.clinerules` and perform MUP. Resume initialization checks afterwards.
3.  **Trigger Creation of Missing Files:**
    *   **Manual Creation Files** (`.clinerules`, `activeContext.md`, `changelog.md`, `userProfile.md`, `progress.md`): If missing, use `write_to_file` to create them with minimal placeholder content as described in Core Prompt Section II table. State: "File `{file_path}` missing. Creating with placeholder content."
        *   Example Initial `.clinerules` (if creating):
            ```
            [LAST_ACTION_STATE]
            last_action: "System Initialized"
            current_phase: "Set-up/Maintenance"
            next_action: "Initialize Core Files" # Or Identify Code/Doc Roots if needed first
            next_phase: "Set-up/Maintenance"

            [CODE_ROOT_DIRECTORIES]
            # To be identified
=======
## II. Initializing Core Required Files

**Action**: Ensure all core files exist, creating them if missing as specified in the Core Prompt (Section II).

**Procedure:**
1.  **Check for Existence**: Verify each core file listed in the Core Prompt Section II exists.
2.  **Create Missing Files:**
    *   **Manual Creation**: Use `write_to_file` for `.clinerules`, `activeContext.md`, `changelog.md`, `userProfile.md`, `projectbrief.md`, `progress.md`. Use the examples/structures provided in the Core Prompt Section II.
    *   **Business Dependency Tracker (Manual BRCT Method)**: If *not* using the CRCT script for this, create `src/business_dependency_tracker.md` manually using the structure in Core Prompt Section II.
    *   **System Manifest (Optional HDTA)**: If using HDTA, create `system_manifest.md` using `write_to_file`, potentially using a template if available.
    *   **CRCT Trackers (Script Method)**: If using the `dependency_processor.py` script, **do not create `module_relationship_tracker.md` or `doc_tracker.md` manually.** Run `analyze-project` instead (see Section III).
        ```bash
        # Run this if using the CRCT dependency script
        # python -m cline_utils.dependency_system.dependency_processor analyze-project
        ```
3.  **Check Business Templates**: Verify templates exist in `src/business_templates/`.
4.  **MUP**: Follow Core Prompt MUP after creating/verifying files. Update `.clinerules` `last_action` and `next_action` accordingly (e.g., `next_action: "Identify Code Root Directories"` or `next_action: "Analyze Project Dependencies"`).
>>>>>>> origin/main

            [DOC_DIRECTORIES]
            # To be identified

<<<<<<< HEAD
            [LEARNING_JOURNAL]
            -
            ```
    *   **Template-Based File** (`system_manifest.md`): If missing, first use `write_to_file` to create an empty file named `system_manifest.md` in `{memory_dir}/`. State: "File `system_manifest.md` missing. Creating empty file." Then, read the template content from `cline_docs/templates/system_manifest_template.md` and use `write_to_file` again to *overwrite* the empty `system_manifest.md` with the template content. State: "Populating `system_manifest.md` with template content."
    *   **Tracker Files** (`module_relationship_tracker.md`, `doc_tracker.md`, and mini-trackers `*_module.md`):
        *   **DO NOT CREATE MANUALLY.**
        *   If any of these are missing, or if significant project changes have occurred, or if you are starting verification, run `analyze-project`. This command will create or update all necessary trackers based on the current project structure and identified code/doc roots.
        ```bash
        # Ensure code/doc roots are set in .clinerules first!
        python -m cline_utils.dependency_system.dependency_processor analyze-project
        ```
        *   State: "Tracker file(s) missing or update needed. Running `analyze-project` to create/update trackers."
        *   *(Running `analyze-project` is also the first step in the verification workflow in Section III)*.
        *   *(Optional: Add `--force-analysis` or `--force-embeddings` if needed)*.        
        *   *(Mini-trackers in module directories are also created/updated by `analyze-project`)*.
4.  **MUP**: Follow Core Prompt MUP (Section VI) and Section V additions below after creating files or running `analyze-project`. Update `[LAST_ACTION_STATE]` to reflect progress (e.g., `next_action: "Verify Tracker Dependencies"`).

## III. Analyzing and Verifying Tracker Dependencies (Ordered Workflow)

**Objective**: Ensure trackers accurately reflect project dependencies by systematically resolving placeholders ('p') and verifying suggestions ('s', 'S'), followed by an explicit code-to-documentation cross-referencing step. **This process MUST follow a specific order:**
1.  `doc_tracker.md` (Placeholder/Suggestion Resolution)
2.  All Mini-Trackers (`*_module.md`) (Placeholder/Suggestion Resolution)
3.  `module_relationship_tracker.md` (Placeholder/Suggestion Resolution)
4.  **Code-Documentation Cross-Reference** (Adding explicit dependencies)

This order is crucial because Mini-Trackers capture detailed cross-directory dependencies within modules, which are essential for accurately determining the higher-level module-to-module relationships in `module_relationship_tracker.md`.

**IMPORTANT**:
*   **All tracker modifications MUST use `dependency_processor.py` commands.** See Core Prompt Section VIII for command details.
*   **Do NOT read tracker files directly** for dependency information; use `show-keys` and `show-dependencies`.
*   Run `analyze-project` *before* starting this verification process if significant code/doc changes have occurred since the last run, or upon entering this phase (as done in Section II).

***CRITICAL EMPHASIS***: *It is critical that the documentation is **Exhaustively** cross-referenced against the code. The code cannot be completed properly if the docs that define it are not listed as a dependency. The following verification stages, especially Stage 4, are designed to achieve this.*
=======
## III. Dependency Management: Setup and Verification

**Objective**: Establish and verify dependency tracking, either using the CRCT script or the manual BRCT method.
>>>>>>> origin/main

**Choose ONE primary method or decide how to combine them:**

<<<<<<< HEAD
1.  **Run Project Analysis (Initial & Updates)**:
    *   Use `analyze-project` to automatically generate/update keys, analyze files, suggest dependencies ('p', 's', 'S'), and update *all* trackers (`module_relationship_tracker.md`, `doc_tracker.md`, and mini-trackers). This command creates trackers if they don't exist and populates/updates the grid based on current code/docs and configuration.
    ```bash
    python -m cline_utils.dependency_system.dependency_processor analyze-project
    ```
    *   *(Optional: Add `--force-analysis` or `--force-embeddings` if needed, e.g., if configuration changed or cache seems stale)*.
    *   **Review logs (`debug.txt`, `suggestions.log`)** for analysis details and suggested changes, but prioritize the verification workflow below. State: "Ran analyze-project. Reviewing logs and proceeding with ordered verification."

2.  **Stage 1: Verify `doc_tracker.md`**:
    *   **A. Identify Keys Needing Verification**:
        *   Run `show-keys` for `doc_tracker.md`:
          ```bash
          python -m cline_utils.dependency_system.dependency_processor show-keys --tracker <path_to_doc_tracker.md>
          ```
          *(Use actual path, likely `{memory_dir}/doc_tracker.md` based on config)*
        *   Examine the output. Identify all lines ending with `(checks needed: ...)`. This indicates unresolved 'p', 's', or 'S' characters in that key's row *within this tracker*.
        *   Create a list of these keys needing verification for `doc_tracker.md`. If none, state this and proceed to Stage 2.
    *   **B. Verify Placeholders/Suggestions for Identified Keys**:
        *   Iterate through the list of keys from Step 2.A.
        *   For each `key_string` (row key):
            *   **Get Context**: Run `show-dependencies --key <key_string>`. This searches *all* trackers for relationships involving this key. Note the target keys (column keys) associated with 'p', 's', 'S' *in `doc_tracker.md`* specifically.
            *   **Plan Reading**: Identify the source file (for `key_string`) and relevant target files (for column keys needing verification). To improve efficiency, plan to read the source file and *multiple* relevant target files together in the next step. Suggest batch reading if files are co-located (e.g., "Suggest reading source file X and target files Y, Z from the same directory. Can you provide folder contents or should I read individually using `read_file`?"). Be mindful of context limits.
            *   **Examine Files**: Use `read_file` to examine the content of the source file and the relevant target files/folders identified.
            *   **Determine Relationship (CRITICAL STEP)**: Based on file contents, determine the **true functional or essential conceptual relationship** between the source (`key_string`) and each target key being verified.
                *   **Go Beyond Similarity**: Suggestions ('s', 'S') might only indicate related topics, not a *necessary* dependency for operation or understanding.
            *   **Focus on Functional Reliance**: Ask:
                *   Does the code in the *row file* directly **import, call, or inherit from** code in the *column file*? (Leads to '<' or 'x').
                *   Does the code in the *column file* directly **import, call, or inherit from** code in the *row file*? (Leads to '>' or 'x').
                *   Does the documentation in the *row file* **require information or definitions** present *only* in the *column file* to be complete or accurate? (Leads to '<' or 'd').
                *   Is the *row file* **essential documentation** for understanding or implementing the concepts/code in the *column file*? (Leads to 'd' or potentially '>').
                *   Is there a **deep, direct conceptual link** where understanding or modifying one file *necessitates* understanding the other, even without direct code imports? (Consider '<', '>', 'x', or 'd' based on the nature of the link).
            *   **Purpose of Dependencies**: Remember, these verified dependencies guide the **Strategy phase** (determining task order) and the **Execution phase** (loading minimal necessary context). A dependency should mean "You *need* to consider/load the related file to work effectively on this one."
            *   **Assign 'n' if No True Dependency**: If the relationship is merely thematic, uses similar terms, or is indirect, assign 'n' (verified no dependency). *It is better to mark 'n' than to create a weak dependency.*
            *   **State Reasoning (MANDATORY)**: Before using `add-dependency`, **clearly state your reasoning** for the chosen dependency character (`<`, `>`, `x`, `d`, or `n`) for *each specific relationship* you intend to set, based on your direct file analysis and the functional reliance criteria.
        *   **Correct/Confirm Dependencies**: Use `add-dependency`, specifying `--tracker <path_to_doc_tracker.md>`. The `--source-key` is always the `key_string` you are iterating on. The `--target-key` is the column key whose relationship you determined. Set the `--dep-type` based on your reasoned analysis. Batch multiple targets *for the same source key* if they share the *same new dependency type*.
              ```bash
              # Example: Set '>' from 1A2 (source) to 2B1 (target) in doc_tracker.md
              # Reasoning: docs/setup.md (1A2) details steps required BEFORE using API described in docs/api/users.md (2B1). Thus, 2B1 depends on 1A2.
              python -m cline_utils.dependency_system.dependency_processor add-dependency --tracker <path_to_doc_tracker.md> --source-key 1A2 --target-key 2B1 --dep-type ">"

              # Example: Set 'n' from 1A2 (source) to 3C1 and 3C2 (targets) in doc_tracker.md
              # Reasoning: Files 3C1 and 3C2 are unrelated examples; no functional dependency on setup guide 1A2.
              python -m cline_utils.dependency_system.dependency_processor add-dependency --tracker <path_to_doc_tracker.md> --source-key 1A2 --target-key 3C1 3C2 --dep-type "n"
              ```
        *   Repeat Step 2.B for all keys identified in Step 2.A.
    *   **C. Final Check**: Run `show-keys --tracker <path_to_doc_tracker.md>` again to confirm no `(checks needed: ...)` remain.
    *   **MUP**: Perform MUP. Update `last_action`. State: "Completed verification for doc_tracker.md. Proceeding to find and verify mini-trackers."

3.  **Stage 2: Find and Verify Mini-Trackers (`*_module.md`)**:
    *   **A. Find Mini-Tracker Files**:
        *   **Goal**: Locate all `*_module.md` files within the project's code directories.
        *   **Get Code Roots**: Read the `[CODE_ROOT_DIRECTORIES]` list from `.clinerules`. If empty, state this and this stage cannot proceed.
        *   **Scan Directories**: For each code root directory, recursively scan its contents using `list_files` or similar directory traversal logic.
        *   **Identify & Verify**: Identify files matching the pattern `{dirname}_module.md` where `{dirname}` exactly matches the name of the directory containing the file (e.g., `src/user_auth/user_auth_module.md`).
        *   **Create List**: Compile a list of the full, normalized paths to all valid mini-tracker files found.
        *   **Report**: State the list of found mini-tracker paths. If none are found but code roots exist, state this and confirm that `analyze-project` ran successfully (as it should create them if modules exist). If none are found, proceed to Stage 3.
    *   **B. Iterate Through Mini-Trackers**: If mini-trackers were found:
        *   Select the next mini-tracker path from the list. State which one you are processing.
        *   **Repeat Verification Steps**: Follow the same sub-procedure as in Stage 1 (Steps 2.A and 2.B), but substitute the current mini-tracker path for `<path_to_doc_tracker.md>` in all commands (`show-keys`, `add-dependency`).
            *   **Identify Keys**: Use `show-keys --tracker <mini_tracker_path>`. List keys needing checks.
            *   **Verify Keys**: Iterate through keys needing checks. Use `show-dependencies --key <key_string>` (searches globally for context). Examine source/target files (`read_file`). State reasoning based on functional/conceptual reliance. Use `add-dependency --tracker <mini_tracker_path> --source-key <key_string> --target-key <target_key> --dep-type <char>`.
            *   **Foreign Keys**: Remember, when using `add-dependency` on a mini-tracker, the `--target-key` can be an external (foreign) key if it exists globally (Core Prompt Section VIII). Use this to link internal code to external docs or code in other modules if identified during analysis. State reasoning clearly.
              ```bash
              # Example: Set 'd' from internal code file 1Ba2 to external doc 1Aa6 in agents_module.md
              # Reasoning: combat_agent.py (1Ba2) implements concepts defined in Multi-Agent_Collaboration.md (1Aa6), making doc essential.
              python -m cline_utils.dependency_system.dependency_processor add-dependency --tracker src/agents/agents_module.md --source-key 1Ba2 --target-key 1Aa6 --dep-type "d"
              ```
            *   **Proactive External Links**: While analyzing file content, actively look for explicit references or clear conceptual reliance on *external* files (docs or other modules) missed by automation. Add these using `add-dependency` with the foreign key capability if a true dependency exists. State reasoning.
        *   **C. Final Check (Mini-Tracker)**: Run `show-keys --tracker <mini_tracker_path>` again to confirm no `(checks needed: ...)` remain for *this* mini-tracker.
        *   Repeat Step 3.B and 3.C for all mini-trackers in the list found in Step 3.A.
    *   **MUP**: Perform MUP after verifying all mini-trackers found. Update `last_action`. State: "Completed verification for all identified mini-trackers. Proceeding to module_relationship_tracker.md."

4.  **Stage 3: Verify `module_relationship_tracker.md`**:
    *   Follow the same verification sub-procedure as in Stage 1 (Steps 2.A, 2.B, 2.C), targeting `<path_to_module_relationship_tracker.md>` (likely `{memory_dir}/module_relationship_tracker.md`).
        *   **Identify Keys**: Use `show-keys --tracker <path_to_module_relationship_tracker.md>`. List keys needing checks. If none, state this and verification is complete.
        *   **Verify Keys**: Iterate through keys needing checks.
            *   **Context**: Use `show-dependencies --key <key_string>` (searches globally). When determining relationships here (module-to-module), rely heavily on the verified dependencies established *within* the mini-trackers during Stage 2, as well as the overall system architecture (`system_manifest.md`). A module-level dependency often arises because *some file within* module A depends on *some file within* module B. Read key module files/docs (`read_file`) only if mini-tracker context is insufficient.
            *   **Determine Relationship & State Reasoning**: Base decision on aggregated dependencies from mini-trackers and high-level design intent.
            *   **Correct/Confirm**: Use `add-dependency --tracker <path_to_module_relationship_tracker.md>` with appropriate arguments.
        *   **Final Check**: Run `show-keys --tracker <path_to_module_relationship_tracker.md>` again to confirm no checks needed remain.
    *   **MUP**: Perform MUP after verifying `module_relationship_tracker.md`. Update `last_action`. State: "Completed verification for module_relationship_tracker.md. Proceeding to Code-Documentation Cross-Reference."
=======
**Method A: Using CRCT `dependency_processor.py` Script (Recommended for mixed code/business projects)**

1.  **Run Project Analysis**:
    *   Execute `analyze-project`. This command creates/updates `module_relationship_tracker.md`, `doc_tracker.md`, mini-trackers, generates keys, and suggests dependencies ('p', 's', 'S', '<', '>', 'x', 'd').
    ```bash
    python -m cline_utils.dependency_system.dependency_processor analyze-project
    ```
    *   Review logs (`debug.txt`, `suggestions.log`).

2.  **Verify Placeholders ('p') and Suggestions ('s', 'S')**:
    *   Read the generated tracker files.
    *   For each 'p', 's', 'S':
        *   Use `show-dependencies --key <key>` for context.
        *   Read related files (`read_file`).
        *   Determine the correct relationship ('<', '>', 'x', 'd', 'n'). Refer to Core Prompt Section V for characters.

3.  **Correct/Confirm Dependencies**:
    *   Use `add-dependency` to set the correct character for verified relationships or to mark 'n' for no dependency.
    ```bash
    # Example: Set dependency > between keys 2Aa and 3Aad in main tracker
    # python -m cline_utils.dependency_system.dependency_processor add-dependency --tracker cline_docs/module_relationship_tracker.md --source-key 2Aa --target-key 3Aad --dep-type ">"
    # Example: Set NO dependency 'n'
    # python -m cline_utils.dependency_system.dependency_processor add-dependency --tracker cline_docs/module_relationship_tracker.md --source-key 2Aa --target-key 3Aad --dep-type "n"
    ```

4.  **Iterate**: Repeat verification until no 'p' placeholders remain in `module_relationship_tracker.md` and `doc_tracker.md`.

5.  **Integrate Business Tracker (Optional)**: Decide if `src/business_dependency_tracker.md` is still needed. If so, manually update it based on insights or potentially map its factors to keys generated by the script.

**Method B: Manual BRCT `business_dependency_tracker.md` Management (Suitable for pure business projects)**

1.  **Define Business Factor Categories**:
    *   Review/refine categories in `src/business_dependency_tracker.md` (Market, Organizational, Product/Service, Financial, Strategic, etc.).
    *   Define specific factors under each category relevant to the project.
    *   Update the "Key Definitions" section in the tracker.

2.  **Define Business Dependencies**:
    *   Analyze relationships between the defined factors.
    *   Update the grid in `src/business_dependency_tracker.md`, replacing 'p' with appropriate business dependency types (M, O, T, F, R, C, S) and relationship characters (<, >, x).
    *   Document reasoning for key dependencies.

**MUP**: Apply Core MUP and Section VI additions after each major step (e.g., after running `analyze-project`, after a session of verifying placeholders, after defining factors).
>>>>>>> origin/main

*Keys must be set from each perspective, as each *row* has its own dependency list.*

<<<<<<< HEAD
5.  **Stage 4: Code-Documentation Cross-Reference (Adding 'd' links)**:
    *   **Objective**: Systematically review code components and ensure they have explicit dependencies pointing to all essential documentation required for their understanding or implementation. This happens *after* initial placeholders/suggestions ('p', 's', 'S') are resolved in Stages 1-3.
    *   **A. Identify Code and Doc Keys**:
        *   Use `show-keys` on relevant trackers (mini-trackers, main tracker) to get lists of code keys.
        *   Use `show-keys --tracker <path_to_doc_tracker.md>` to get a list of documentation keys.
        *   *(Alternatively, use internal logic based on `ConfigManager` and the global key map if more efficient)*.
    *   **B. Iterate Through Code Keys**:
        *   Select a code key (e.g., `code_key_string` representing a specific code file).
        *   **Identify Potential Docs**: Determine which documentation keys (`doc_key_string`) are potentially relevant to `code_key_string`. Consider:
            *   The module the code belongs to.
            *   Functionality described in the code file (`read_file <code_file_path>`).
            *   Existing dependencies shown by `show-dependencies --key <code_key_string>`.
            *   Look for comments in the code referencing specific documentation.
            *   Ask questions like, "Does this documentation provide valuable or useful information for understanding how the code is intended to operate?", and "Does the code need to be aware of this information to perform its intended function?".
            *    Conceptual links and future planned directions should be considered as well. The more information available to inform how the code operates in relation to the systems, the higher quality the end result will be.
        *   **Examine Relevant Docs**: Use `read_file` to examine the content of the potentially relevant documentation files.
        *   **Determine Essential Documentation**: For each potential `doc_key_string`, decide if it provides *essential* context, definitions, specifications, or explanations required to understand, implement, or correctly use the code represented by `code_key_string`. This is more than just keyword similarity.
        *   **Add Dependencies (Bi-directionally)**: If `doc_key_string` is essential for `code_key_string`:
            *   **State Reasoning (Mandatory)**: Explain *why* the documentation is essential for the code.
            *   **Add Code -> Doc Link**: Use `add-dependency` targeting the tracker most relevant to the *code file*.
                ```bash
                # Reasoning: [Explain why doc_key_string is essential for code_key_string]
                python -m cline_utils.dependency_system.dependency_processor add-dependency --tracker <code_file_tracker_path> --source-key <code_key_string> --target-key <doc_key_string> --dep-type "<dep_char>"
                ```
            *   **Add Doc -> Code Link**: Use `add-dependency` targeting `doc_tracker.md`.
                ```bash
                # Reasoning: [Same reasoning as above, from doc's perspective]
                python -m cline_utils.dependency_system.dependency_processor add-dependency --tracker <path_to_doc_tracker.md> --source-key <doc_key_string> --target-key <code_key_string> --dep-type "<dep_char>"
                ```
        *   Repeat for all relevant documentation keys for the current `code_key_string`.
    *   **C. Repeat for All Code Keys**: Continue Step 5.B until all relevant code keys have been reviewed against the documentation corpus.
    *   **MUP**: Perform MUP. Update `last_action`. State: "Completed Code-Documentation Cross-Reference."

6.  **Completion**: Once all four stages are complete and `show-keys` reports no `(checks needed: ...)` for `doc_tracker.md`, all mini-trackers, and `module_relationship_tracker.md`, the tracker verification part of Set-up/Maintenance is done. Check if all other phase exit criteria (Section I) are met (e.g., core files exist, code/doc roots identified, system manifest populated). If so, prepare to exit the phase by updating `.clinerules` as per Section I.

*If a dependency is detected in **either** direction 'n' should not be used. Choose the best character to represent the directional dependency or 'd' if it is a more general documentation dependency.*

## IV. Set-up/Maintenance Dependency Workflow Diagram

```mermaid
graph TD
    A[Start Set-up/Maintenance Verification] --> B(Run analyze-project);
    B --> C[Stage 1: Verify doc_tracker.md];

    subgraph Verify_doc_tracker [Stage 1: doc_tracker.md]
        C1[Use show-keys --tracker doc_tracker.md] --> C2{Checks Needed?};
        C2 -- Yes --> C3[Identify Key(s)];
        C3 --> C4[For Each Key needing check:] ;
        C4 --> C5(Run show-dependencies --key [key]);
        C5 --> C6(Plan Reading / Suggest Batch);
        C6 --> C7(Read Source + Target Files);
        C7 --> C8(Determine Relationship & State Reasoning);
        C8 --> C9(Use add-dependency --tracker doc_tracker.md);
        C9 --> C4;
        C4 -- All Keys Done --> C10[Final Check: show-keys];
        C2 -- No --> C10[doc_tracker Verified];
=======
## IV. Business Innovation Templates Review

**Objective**: Ensure that business innovation templates in `src/business_templates/` are available and appropriate.

**Procedure:**
1.  **List Templates**: Confirm presence of standard templates (Idea Gen, Eval, BMC, SWOT, Market Research).
2.  **Review Content**: Briefly check if templates include necessary sections and chain-of-thought prompts.
3.  **Customize if Needed**: If project requires specific adjustments, modify existing templates or create new ones.
4.  **Document Templates**: Note available templates in `activeContext.md`.
5.  **MUP**: Apply Core MUP if templates were modified.

---

## V. Dependency Tracker Management Details (CRCT Script Method)

*(Refer to Core Prompt Section V & VIII for full details on characters and commands)*

### V.1 Hierarchical Key System
- Encodes hierarchy: Tier(num), Dir(Upper), Subdir(lower), File(num). e.g., `1A`, `2Ba3`.

### V.2 Dependency Processor Commands (Setup Focus)
-   **`analyze-project`**: Core command for analysis, key generation, tracker updates.
-   **`show-dependencies --key <key>`**: View dependencies for a specific key.
-   **`add-dependency --tracker <file> --source-key <key> --target-key <key> --dep-type <char>`**: Manually set dependency character.
-   **`update-config <key_path> <value>`**: Adjust settings in `.clinerules.config.json` (e.g., similarity thresholds, model names).
-   **`reset-config`**: Reset config to defaults.
-   **`remove-file <tracker_file> <file>`**: Remove a file/key from a tracker.

### V.3 Set-up/Maintenance Dependency Workflow (CRCT Script Method)
```mermaid
flowchart TD
    A[Start Set-up/Maintenance] --> B(Run<br>analyze-project);
    B --> C{Review Trackers & Logs};
    C --> D{"Placeholders ('p') or Suggestions ('s'/'S') Found?"};
    D -- Yes --> E[Identify Relationship];
    E --> F("Use<br>show-dependencies --key [key]");
    F --> G(Read Related Files);
    G --> H{Determine Correct Character};
    H --> I(Use<br>add-dependency);
    I --> C;
    D -- No --> J[Trackers Verified];
    J --> K[End Set-up/Maintenance Phase];

    subgraph Verification Loop
        direction LR
        E; F; G; H; I;
>>>>>>> origin/main
    end

    C --> Verify_doc_tracker;
    C10 --> D[MUP after Stage 1];

    D --> E[Stage 2: Find & Verify Mini-Trackers];
    subgraph Find_Verify_Minis [Stage 2: Mini-Trackers (`*_module.md`)]
        E1[Identify Code Roots from .clinerules] --> E2[Scan Code Roots Recursively];
        E2 --> E3[Find & Verify *_module.md Files];
        E3 --> E4[Compile List of Mini-Tracker Paths];
        E4 --> E5{Any Mini-Trackers Found?};
        E5 -- Yes --> E6[Select Next Mini-Tracker];
        E6 --> E7[Use show-keys --tracker <mini_tracker>];
        E7 --> E8{Checks Needed?};
        E8 -- Yes --> E9[Identify Key(s)];
        E9 --> E10[For Each Key needing check:];
        E10 --> E11(Run show-dependencies --key [key]);
        E11 --> E12(Plan Reading / Suggest Batch);
        E12 --> E13(Read Source + Target Files);
        E13 --> E14(Determine Relationship & State Reasoning - Consider Foreign Keys/External);
        E14 --> E15(Use add-dependency --tracker <mini_tracker>);
        E15 --> E10;
        E10 -- All Keys Done --> E16[Final Check: show-keys];
        E8 -- No --> E16[Mini-Tracker Verified];
        E16 --> E17{All Mini-Trackers Checked?};
        E17 -- No --> E6;
        E17 -- Yes --> E18[All Mini-Trackers Verified];
        E5 -- No --> E18; // Skip if no minis found
    end

    E --> Find_Verify_Minis;
    E18 --> F[MUP after Stage 2];

    F --> G[Stage 3: Verify module_relationship_tracker.md];
    subgraph Verify_main_tracker [Stage 3: module_relationship_tracker.md]
        G1[Use show-keys --tracker module_relationship_tracker.md] --> G2{Checks Needed?};
        G2 -- Yes --> G3[Identify Key(s)];
        G3 --> G4[For Each Key needing check:];
        G4 --> G5(Run show-dependencies --key [key]);
        G5 --> G6(Plan Reading / Use Mini-Tracker Context / Read Key Module Files);
        G6 --> G7(Determine Relationship & State Reasoning - Module Level);
        G7 --> G8(Use add-dependency --tracker module_relationship_tracker.md);
        G8 --> G4;
        G4 -- All Keys Done --> G9[Final Check: show-keys];
        G2 -- No --> G9[Main Tracker Verified];
    end

    G --> Verify_main_tracker;
    G9 --> H[MUP after Stage 3];

    H --> J[Stage 4: Code-Documentation Cross-Ref];
    subgraph CodeDocRef [Stage 4: Code-Doc Cross-Ref]
        J1[Identify Code & Doc Keys] --> J2[For Each Code Key:];
        J2 --> J3(Identify Potential Docs);
        J3 --> J4(Read Code & Docs);
        J4 --> J5(Determine Essential Docs & Reason);
        J5 -- Yes --> J6(add-dependency -> tracker);
        J6 --> J2;
        J5 -- No --> J2;
        J2 -- All Code Keys Done --> J7[Stage 4 Complete];
    end

    J --> CodeDocRef;
    J7 --> K[MUP after Stage 4];
    K --> L[End Verification Process - Check All Exit Criteria (Section I)];

    style Verify_doc_tracker fill:#e6f7ff,stroke:#91d5ff
    style Find_Verify_Minis fill:#f6ffed,stroke:#b7eb8f
    style Verify_main_tracker fill:#fffbe6,stroke:#ffe58f
```

## V. Locating and Understanding Mini-Trackers

<<<<<<< HEAD
**Purpose**: Mini-trackers (`{dirname}_module.md`) serve a dual role:
1.  **HDTA Domain Module**: They contain the descriptive text for the module (purpose, components, etc.), managed manually during Strategy.
2.  **Dependency Tracker**: They track file/function-level dependencies *within* that module and potentially *to external* files/docs. The dependency grid is managed via `dependency_processor.py` commands.

**Locating Mini-Trackers:**
1.  **Get Code Roots**: Read the `[CODE_ROOT_DIRECTORIES]` list from `.clinerules`. These are the top-level directories containing project source code.
2.  **Scan Code Roots**: For each directory listed in `[CODE_ROOT_DIRECTORIES]`:
    *   Recursively scan its contents.
    *   Look for files matching the pattern `{dirname}_module.md`, where `{dirname}` is the exact name of the directory containing the file.
    *   Example: In `src/auth/`, look for `auth_module.md`. In `src/game/state/`, look for `state_module.md`.
3.  **Compile List**: Create a list of the full, normalized paths to all valid mini-tracker files found. This list will be used in Section III when it's time to verify mini-trackers.

**Creation and Verification**:
*   **Creation/Update**: The `analyze-project` command (run in Section II.4 and potentially before Section III) automatically creates `{dirname}_module.md` files for detected modules if they don't exist, or updates the dependency grid within them if they do. It populates the grid with keys and initial placeholders/suggestions.
*   **Verification**: The detailed verification process in **Section III** is used to resolve placeholders ('p', 's', 'S') within these mini-trackers *after* `doc_tracker.md` is verified and *before* `module_relationship_tracker.md` is verified. Use the list compiled above to iterate through the mini-trackers during that stage.
=======
## VI. Set-up/Maintenance Plugin - MUP Additions

After Core MUP steps (Update `activeContext.md`, `changelog.md`, `.clinerules` [LAST_ACTION_STATE]):
1.  **Update Dependency Trackers**: Save changes made manually to `src/business_dependency_tracker.md` OR confirm `analyze-project` / `add-dependency` commands completed successfully if using the script.
2.  **Update Business Templates**: If modified, save changes.
3.  **Update `system_manifest.md`**: If used and modified.
4.  **Update `.clinerules` [LAST_ACTION_STATE]:**
    -   Example after initialization:
        ```
        [LAST_ACTION_STATE]
        last_action: "Initialized Core Files"
        current_phase: "Set-up/Maintenance"
        next_action: "Identify Code Root Directories" # Or "Analyze Project Dependencies"
        next_phase: "Set-up/Maintenance"
        ```
    -   Example after completing setup:
        ```
        [LAST_ACTION_STATE]
        last_action: "Completed Set-up/Maintenance Phase"
        current_phase: "Set-up/Maintenance"
        next_action: "Phase Complete - User Action Required"
        next_phase: "Strategy"
        ```

---
>>>>>>> origin/main

## VII. Quick Reference Guide for Set-up/Maintenance Phase

<<<<<<< HEAD
After performing the Core MUP steps (Core Prompt Section VI):
1.  **Update `system_manifest.md` (If Changed)**: If Set-up actions modified the project structure significantly (e.g., adding a major module requiring a mini-tracker), ensure `system_manifest.md` reflects this, potentially adding the new module.
2.  **Update `.clinerules` [LAST_ACTION_STATE]:** Update `last_action`, `current_phase`, `next_action`, `next_phase` to reflect the specific step completed within this phase. Examples:
    *   After identifying roots:
        ```
        last_action: "Identified Code and Doc Roots"
        current_phase: "Set-up/Maintenance"
        next_action: "Initialize Core Files / Run analyze-project"
        next_phase: "Set-up/Maintenance"
        ```
    *   After initial `analyze-project`:
        ```
        last_action: "Ran analyze-project, Initialized Trackers"
        current_phase: "Set-up/Maintenance"
        next_action: "Verify doc_tracker.md Dependencies"
        next_phase: "Set-up/Maintenance"
        ```
    *   After verifying `doc_tracker.md`:
        ```
        last_action: "Verified doc_tracker.md"
        current_phase: "Set-up/Maintenance"
        next_action: "Verify Mini-Trackers"
        next_phase: "Set-up/Maintenance"
        ```
    *   After verifying the last tracker:
        ```
        last_action: "Completed All Tracker Verification"
        current_phase: "Set-up/Maintenance"
        next_action: "Perform Code-Documentation Cross-Reference"
        next_phase: "Set-up/Maintenance"
        ```
    *   After completing Code-Documentation Cross-Reference:
        ```
        last_action: "Completed Code-Documentation Cross-Reference ('d' links added)"
        current_phase: "Set-up/Maintenance"
        next_action: "Phase Complete - User Action Required"
        next_phase: "Strategy"
        ```
=======
### Core Files to Initialize/Verify
-   `.clinerules`
-   `activeContext.md`, `changelog.md`, `userProfile.md`, `projectbrief.md`, `progress.md`
-   `src/business_dependency_tracker.md` (Manual method)
-   `module_relationship_tracker.md`, `doc_tracker.md` (Script method)
-   `system_manifest.md` (Optional HDTA)

### Business Templates to Verify (`src/business_templates/`)
-   Idea Generation, Idea Evaluation, Business Model Canvas, SWOT Analysis, Market Research

### Key Set-up/Maintenance Actions
1.  Initialize/Verify core files.
2.  Identify Code Root & Doc Directories (See Core Prompt Section XI).
3.  Setup & Verify Dependency Tracking (Manual or Script method).
4.  Review/Verify Business Templates.
5.  Complete MUP after each major action.
>>>>>>> origin/main
