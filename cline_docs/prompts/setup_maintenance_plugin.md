# **Business Recursive Chain-of-Thought Framework (BRCT) - Set-up/Maintenance Plugin**

**This Plugin provides detailed instructions and procedures for the Set-up/Maintenance phase of the BRCT system. It should be used in conjunction with the Core System Prompt.**

---

## I. Entering and Exiting Set-up/Maintenance Phase

**Entering Set-up/Maintenance Phase:**
1. **Initial State**: Start here for new projects or if `.clinerules` shows `current_phase: "Set-up/Maintenance"`.
2. **`.clinerules` Check**: Always read `.clinerules` first. If `[LAST_ACTION_STATE]` indicates "Set-up/Maintenance", proceed with these instructions.
3. **New Project**: If `.clinerules` is missing/empty, assume this phase and initialize core files.

**Exiting Set-up/Maintenance Phase:**
1. **Completion Criteria:**
   - All core files exist and are initialized.
   - `business_dependency_tracker.md` is populated with business factor categories.
   - Business templates are available and accessible.
2. **`.clinerules` Update (MUP):**
   ```
   last_action: "Completed Set-up/Maintenance Phase"
   current_phase: "Set-up/Maintenance"
   next_action: "Phase Complete - User Action Required"
   next_phase: "Strategy"
   ```
3. **User Action**: After updating `.clinerules`, pause for user to trigger the next session (e.g., reset context in VS Code). See Core System Prompt, Section III for a phase transition checklist.

---

## II. Initializing Core Required Files

**Action**: Ensure all core files exist, creating them if missing as specified.

**Procedure:**
1. **Check for Existence**: Check if each file (`.clinerules`, `projectbrief.md`, `productContext.md`, `activeContext.md`, `business_dependency_tracker.md`, `changelog.md`, `progress.md`) exists.
2. **Create Missing Files:**
   - For `.clinerules`: Use `write_to_file` to create with minimal content:
     ```
     [LAST_ACTION_STATE]
     last_action: "System Initialized"
     current_phase: "Set-up/Maintenance"
     next_action: "Initialize Core Files"
     next_phase: "Set-up/Maintenance"

     [CODE_ROOT_DIRECTORIES]
     - src

     [LEARNING_JOURNAL]
     ```
   - For `projectbrief.md`: Create with placeholder structure:
     ```
     # Project Brief: 

     **Project Name:** 

     **Project Goal:** 

     **Core Requirements:**

     **Source of Truth:** This document serves as the source of truth for the project's scope, core requirements, and overall vision. All other documentation and development efforts should align with the principles and goals outlined here.
     ```
   - For `productContext.md`: Create with placeholder sections:
     ```
     # Product Context

     ## Purpose

     [Describe the purpose of the product/project]

     ## User Needs

     [Outline the needs of the users/stakeholders]

     ## Key Features and Components

     [List and describe the key features and components]

     ## Success Metrics

     [Define the metrics that will be used to measure success]
     ```
   - For `activeContext.md`: Create with functional structure:
     ```
     # Active Context

     ## Current State

     [Document the current state of the project]

     ## Recent Decisions

     [List recent decisions that have been made]

     ## Immediate Priorities

     [List the immediate priorities for the project]

     ## Pending Issues

     [Document any pending issues or challenges]

     ## Dependencies

     | Component | Depends On | Status |
     |-----------|------------|--------|
     | [Component 1] | [Dependency] | [Status] |
     | [Component 2] | [Dependency] | [Status] |

     ## Notes

     [Include any additional notes or observations]
     ```
   - For `business_dependency_tracker.md`: Create with initial business factor categories:
     ```
     # Business Innovation Dependency Tracker

     ## Overview
     This tracker documents dependencies between various business innovation factors within the BRCT framework. Unlike code dependencies, business dependencies represent relationships between market factors, organizational capabilities, customer needs, and other business elements that influence innovation outcomes.

     ## Dependency Types and Symbols

     | Symbol | Type | Description |
     |--------|------|-------------|
     | `M` | Market | Dependency on market conditions or customer factors |
     | `O` | Organizational | Dependency on internal capabilities or resources |
     | `T` | Technological | Dependency on technological factors or capabilities |
     | `F` | Financial | Dependency on funding, investment, or financial metrics |
     | `R` | Regulatory | Dependency on legal or regulatory factors |
     | `C` | Competitive | Dependency on competitor actions or positioning |
     | `S` | Strategic | Dependency on strategic decisions or direction |
     | `<` | Input | The row depends on the column as an input |
     | `>` | Output | The column depends on the row as an input |
     | `x` | Bidirectional | Mutual dependency between factors |
     | `o` | Self | No dependency (diagonal only) |
     | `n` | None | Verified no dependency |
     | `p` | Placeholder | Unverified potential dependency |

     ## Business Factor Categories

     ### Market Factors
     - Customer needs and preferences
     - Market size and growth
     - Market segments and targeting
     - Market trends and opportunities

     ### Organizational Factors
     - Core competencies and capabilities
     - Resource availability
     - Organizational structure
     - Culture and innovation readiness

     ### Product/Service Factors
     - Value proposition components
     - Feature requirements
     - Service delivery elements
     - Quality metrics

     ### Financial Factors
     - Revenue models
     - Cost structures
     - Investment requirements
     - Profitability metrics

     ### Strategic Factors
     - Strategic goals and objectives
     - Competitive positioning
     - Strategic partnerships
     - Growth strategies

     ## Key Definitions

     ---KEY_DEFINITIONS_START---
     Key Definitions:
     1A: Market Factors
     1B: Organizational Factors
     1C: Product/Service Factors
     1D: Financial Factors
     1E: Strategic Factors
     ---KEY_DEFINITIONS_END---

     last_KEY_edit: 1E
     last_GRID_edit: 

     ---GRID_START---
     X 1A 1B 1C 1D 1E
     1A = op4
     1B = po4
     1C = pp3
     1D = pp3
     1E = pp3
     ---GRID_END---
     ```
   - For `changelog.md`: Create with format structure:
     ```
     # Changelog

     This document records significant changes to the project, including major updates, additions, and modifications to its structure and functionality.

     ## Format
     Each entry includes:
     - **Date**: When the change was made
     - **Type**: The nature of the change (Addition, Modification, Removal, Fix)
     - **Component**: The part of the framework affected
     - **Description**: Details about what was changed
     - **Reason**: Why the change was made
     - **Affected Files**: List of files modified

     ## Changes

     ### [YYYY-MM-DD]: [Change Title]

     **Type**: [Addition/Modification/Removal/Fix]  
     **Component**: [Affected Component]  
     **Description**: [Description of the change]  
     **Reason**: [Reason for making the change]  
     **Affected Files**:
     - [File 1]
     - [File 2]
     - [File 3]

     ---

     *Note: This changelog adheres to the principles of semantic versioning and transparent documentation. All significant changes should be recorded here to maintain a comprehensive history of the project's evolution.*
     ```
   - For `progress.md`: Create with implementation phase structure:
     ```
     # Project Implementation Progress

     ## Overview
     This document tracks the implementation progress of the project.

     ## Implementation Tasks

     ### Phase 1: [Phase Name]
     | Task | Status | Completion Date | Notes |
     |------|--------|----------------|-------|
     | [Task 1] | | | |
     | [Task 2] | | | |
     | [Task 3] | | | |

     ### Phase 2: [Phase Name]
     | Task | Status | Completion Date | Notes |
     |------|--------|----------------|-------|
     | [Task 1] | | | |
     | [Task 2] | | | |
     | [Task 3] | | | |

     ### Phase 3: [Phase Name]
     | Task | Status | Completion Date | Notes |
     |------|--------|----------------|-------|
     | [Task 1] | | | |
     | [Task 2] | | | |
     | [Task 3] | | | |

     ## Milestones
     | Milestone | Target Date | Status | Notes |
     |-----------|-------------|--------|-------|
     | [Milestone 1] | | | |
     | [Milestone 2] | | | |
     | [Milestone 3] | | | |

     ## Status Legend
     - ✅ Complete: Task finished and verified
     - ⏳ In Progress: Work actively ongoing
     - 🔄 Planned: Task identified but not yet started
     - ⚠️ Blocked: Unable to proceed due to dependencies or issues
     ```
3. **Check Business Templates**: Verify that the following templates exist in `src/business_templates/`:
   - `idea_generation_template.md`
   - `idea_evaluation_template.md`
   - `business_model_canvas.md`
   - `swot_analysis_template.md`
   - `market_research_template.md`
   - `README.md`
4. **MUP**: Follow Core Prompt MUP after creating files.

---

## III. Business Factor Definition and Categorization

**Objective**: Define and categorize the key business factors that will be tracked in the business_dependency_tracker.md.

**Procedure:**
1. **Review Initial Categories**: Verify the business factor categories in `business_dependency_tracker.md`:
   - Market Factors
   - Organizational Factors
   - Product/Service Factors
   - Financial Factors
   - Strategic Factors
2. **Refine Categories as Needed**: Based on the specific business context of the project, add or modify categories to better match the project's needs.
3. **Define Specific Factors**: For each category, define the specific factors that will be tracked. For example:
   - Market Factors: Customer segments, market size, competitors, etc.
   - Organizational Factors: Team structure, resource availability, etc.
4. **Document in `business_dependency_tracker.md`**: Update the file with the refined categories and specific factors.
5. **MUP**: Apply Core MUP after updating the file.

---

## IV. Defining Business Dependencies

**Objective**: Establish clear relationships between business factors in the business_dependency_tracker.md.

**Procedure:**
1. **Review Current Grid**: Examine the grid structure in `business_dependency_tracker.md` to understand the current relationships between factors.
2. **Identify Dependencies**: For each business factor, analyze its relationships with other factors:
   - What other factors does it depend on?
   - What other factors depend on it?
   - Are there any mutual dependencies?
3. **Update the Grid**:
   - For each identified dependency, replace the placeholder 'p' with the appropriate dependency character (M, O, T, F, R, C, S) followed by the relationship character (<, >, x).
   - For example, 'M<' indicates a market dependency where the row depends on the column.
4. **Document Reasoning**:
   - For each update, document the rationale in the "Dependencies Notes" section of the file.
   - Explain why the dependency exists and how it affects the business innovation process.
5. **MUP**: Apply Core MUP after updating the file.

---

## V. Business Innovation Templates Review

**Objective**: Ensure that business innovation templates are available and appropriate for the project's needs.

**Procedure:**
1. **Review Template Content**: Examine each template in `src/business_templates/` to ensure it includes:
   - Clear instructions for use
   - Relevant sections for the business innovation process
   - Integration with the BRCT framework principles
   - Chain-of-thought documentation sections
2. **Customize if Needed**: If the templates need adjustments for the specific project:
   - Create copies with modifications
   - Update them to reflect project-specific terminology or processes
   - Add additional sections if required
3. **Document Templates**: Update `activeContext.md` with information about available templates and how they should be used in the project.
4. **MUP**: Apply Core MUP after any template modifications.

---

## VI. Set-up/Maintenance Plugin - MUP Additions

After Core MUP steps:
1. **Update `business_dependency_tracker.md`**: Save changes to factor definitions and dependencies.
2. **Update Business Templates**: If modified, save changes to templates.
3. **Update `.clinerules` [LAST_ACTION_STATE]:**

    - Example after initialization:

    ```
    [LAST_ACTION_STATE]
    last_action: "Initialized Core Files"
    current_phase: "Set-up/Maintenance"
    next_action: "Define Business Factors"
    next_phase: "Set-up/Maintenance"

    [CODE_ROOT_DIRECTORIES]
    - src

    [LEARNING_JOURNAL]
    ```

    - Example after completing setup:

    ```
    [LAST_ACTION_STATE]
    last_action: "Completed Set-up/Maintenance Phase"
    current_phase: "Set-up/Maintenance"
    next_action: "Phase Complete - User Action Required"
    next_phase: "Strategy"

    [CODE_ROOT_DIRECTORIES]
    - src

    [LEARNING_JOURNAL]
    ```

---

## VII. Quick Reference Guide for Set-up/Maintenance Phase

### Core Files to Initialize
- `.clinerules`: Controls phase and state
- `projectbrief.md`: Defines project mission and objectives
- `productContext.md`: Explains project purpose and user needs
- `activeContext.md`: Tracks current state and priorities
- `business_dependency_tracker.md`: Records business factor dependencies
- `changelog.md`: Logs significant changes
- `progress.md`: Tracks implementation progress

### Business Templates to Verify
- `idea_generation_template.md`: For business brainstorming
- `idea_evaluation_template.md`: For assessing business ideas
- `business_model_canvas.md`: For business model definition
- `swot_analysis_template.md`: For strategic analysis
- `market_research_template.md`: For market analysis

### Key Set-up/Maintenance Actions
1. Initialize core files
2. Define business factor categories
3. Establish dependency relationships
4. Review business templates
5. Complete MUP after each action