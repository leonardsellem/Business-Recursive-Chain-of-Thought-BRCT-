<!--
Instructions: Fill in the placeholders below to create an Implementation Plan.
This document details the plan for a specific feature, refactor, or significant
change, potentially spanning multiple files/components within a Domain Module.
It forms a key segment of the project roadmap defined during the Strategy phase.
*Do NOT include these comments in the created file.*
-->

# Implementation Plan: {Brief Objective or Feature Name}

**Parent Module(s)**: [{Module1Name}_module.md], [{Module2Name}_module.md] <!-- Link to relevant Domain Module(s) -->
**Status**: [ ] Proposed / [ ] Planned / [ ] In Progress / [ ] Completed / [ ] Deferred

## 1. Objective / Goal
<!-- Clearly state the specific goal this plan aims to achieve. What user story, feature, or refactoring is being addressed? -->
{Describe the primary goal of this implementation plan.}

## 2. Affected Components / Files
<!-- List the key code files, documentation files, modules, or data structures expected to be created or modified by this plan. Link keys where possible. -->
*   **Code:**
    *   `{path/to/file1.py}` (Key: `{key1}`) - {Brief reason for involvement}
    *   `{path/to/moduleA/}` (Key: `{keyA}`) - {Brief reason for involvement}
*   **Documentation:**
    *   `{docs/path/doc1.md}` (Key: `{keyD1}`) - {Brief reason for involvement}
*   **Data Structures / Schemas:**
    *   {Schema Name / Data Structure} - {Brief reason for involvement}

## 3. High-Level Approach / Design Decisions
<!-- Describe the overall strategy for achieving the objective. Outline key design choices, algorithms, or patterns to be used. -->
*   **Approach:** {Describe the sequence or method.}
*   **Design Decisions:**
    *   {Decision 1}: {Rationale}
    *   {Decision 2}: {Rationale}
*   **Algorithms (if applicable):**
    *   `{Algorithm Name}`: {Brief description and relevance}
*   **Data Flow (if significant):**
    *   {Brief description or link to a diagram/section}

## 4. Task Decomposition (Roadmap Steps)
<!-- List the atomic Task Instructions required to execute this plan. Tasks should have Strategy_* or Execution_* prefixes. -->
*   [ ] [Task 1 File](path/to/Strategy_Task1.md) (`{task1_key}`): {Brief description of task objective}
*   [ ] [Task 2 File](path/to/Execution_Task2.md) (`{task2_key}`): {Brief description of task objective}
*   [ ] [Task 3 File](path/to/Execution_Task3.md) (`{task3_key}`): {Brief description of task objective}
*   ...

## 5. Task Sequence / Build Order
<!-- Define the required execution order for the tasks listed above, based on dependency analysis. Provide rationale if needed. -->
1.  Task 2 (`{task2_key}`) - *Reason: Prerequisite for Task 3.*
2.  Task 3 (`{task3_key}`)
3.  Task 1 (`{task1_key}`) - *Reason: Can be done after core logic.*
4.  ...

## 6. Prioritization within Sequence
<!-- Indicate the priority of tasks within the determined sequence (e.g., P1, P2, P3, or High/Medium/Low). -->
*   Task 2 (`{task2_key}`): P1 (Critical Path)
*   Task 3 (`{task3_key}`): P1
*   Task 1 (`{task1_key}`): P2
*   ...

## 7. Open Questions / Risks
<!-- Document any unresolved questions or potential risks associated with this plan. -->
*   {Question/Risk 1}
*   {Question/Risk 2}