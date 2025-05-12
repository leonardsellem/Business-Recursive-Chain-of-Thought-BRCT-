<!--
Instructions: Fill in the placeholders below to create a Task Instruction document.
This document provides detailed, procedural guidance for a specific task. Provide ONLY the MINIMAL necessary context for THIS task.
- Use precise links to specific definitions/sections (e.g., `file.py#MyClass.my_method`, `doc_key#Section Title`).
- Link to prerequisite Task keys ONLY if they produce a direct, necessary input for THIS task.
*Do NOT include these comments in the created file.*
-->

# Task: {TaskName}
   **Parent:** `implementation_plan_{filename}.md` or {ParentTask}
   **Children:** {Optional: Links to specific, separate .md task files generated or delegated by this task}
<!-- Use sparingly. For pre-planned decomposition, nest tasks under an Implementation Plan. This field is for tasks that dynamically spawn other distinct, trackable .md tasks during their execution/planning. -->

## Objective
[Clear, specific goal statement]

## Context
[What the LLM needs to know about the current state]

## Steps
1. {Step 1}
2. {Step 2}
   - {Substep 2.1}
   - {Substep 2.2}
3. {Step 3}
...

## Dependencies **This *MUST* include dependencies from tracker files**
- Requires: [{Task1}], [{Module2}]  *(Manually manage these)*
- Blocks: [{Task3}], [{Task4}]   *(Manually manage these)*

## Expected Output
{Description of expected results}