# **Business Recursive Chain-of-Thought Framework (BRCT) - Strategy Plugin**

**This Plugin provides detailed instructions and procedures for the Strategy phase of the BRCT system. It should be used in conjunction with the Core System Prompt.**

---

## I. Entering and Exiting Strategy Phase

**Entering Strategy Phase:**
1. **`.clinerules` Check**: Always read `.clinerules` first. If `[LAST_ACTION_STATE]` shows `current_phase: "Strategy"`, proceed with these instructions.
2. **Transition from Set-up/Maintenance**: Enter after Set-up/Maintenance; `.clinerules` `next_phase` will be "Strategy".
3. **User Trigger**: Start a new session after Set-up/Maintenance or to resume strategy.

**Exiting Strategy Phase:**
1. **Completion Criteria:**
   - Business ideas have been generated and evaluated
   - Business models have been developed
   - Strategic analyses (SWOT, market research) have been completed
   - Tasks are prioritized and ready for execution
2. **`.clinerules` Update (MUP):**
   ```
   last_action: "Completed Strategy Phase - Business Plan Developed"
   current_phase: "Strategy"
   next_action: "Phase Complete - User Action Required"
   next_phase: "Execution"
   ```
3. **User Action**: After updating `.clinerules`, pause for user to trigger Execution phase via a new session. See Core System Prompt, Section III for a phase transition checklist.

---

## II. Loading Context for Strategy

**Action**: Load context to guide business innovation strategy.
**Procedure:**
- Load core files: `.clinerules`, `projectbrief.md`, `productContext.md`, `activeContext.md`, `business_dependency_tracker.md`, `changelog.md`, `progress.md`.
- Review `activeContext.md` for current state, decisions, and priorities.
- Check `business_dependency_tracker.md` for business factor relationships.
- Revisit `projectbrief.md` and `productContext.md` to align with business goals and user needs.
- Examine `.clinerules` [LEARNING_JOURNAL] for past insights influencing strategy.
- Review available business templates in `src/business_templates/`.

---

## III. Business Idea Generation

**Action**: Generate business ideas using structured approaches and templates.
**Procedure:**
1. **Select Approach**: Choose an appropriate idea generation methodology based on the business context:
   - Brainstorming
   - Mind Mapping
   - Design Thinking
   - Problem-Solution Matching
   - Reverse Thinking
2. **Use Idea Generation Template**: Utilize `src/business_templates/idea_generation_template.md` to document the process:
   - Define the business challenge clearly
   - Identify target users/customers
   - Describe current solutions and limitations
   - Document brainstorming participants and techniques
   - Break down the problem into components (recursive decomposition)
   - List raw ideas generated
   - Refine into top ideas to explore
3. **Apply Business Chain-of-Thought**: Document the reasoning process that led to the ideas, including:
   - Explicit thought progression
   - Consideration of business factors (market, organizational, etc.)
   - Patterns and insights observed
   - Alternative directions considered
4. **MUP**: Follow Core MUP and Section VI additions after completing idea generation.

---

## IV. Business Idea Evaluation

**Action**: Evaluate generated business ideas using structured criteria.
**Procedure:**
1. **Use Idea Evaluation Template**: Utilize `src/business_templates/idea_evaluation_template.md` for each promising idea:
   - Summarize the idea (name, description, problem addressed)
   - Assess desirability (market need, differentiation, timing)
   - Assess feasibility (technical complexity, resource requirements)
   - Assess viability (revenue potential, profit margins, time to break-even)
   - Evaluate strategic alignment (fit with company vision, capabilities)
   - Perform SWOT analysis for the idea
   - Assess risks and mitigation strategies
2. **Apply Recursive Decomposition**:
   - Break down the idea into key components
   - Evaluate each component separately
   - Assess component dependencies
3. **Document Chain-of-Thought**:
   - Record key insights from the evaluation
   - Explain reasoning behind scores and assessments
   - Document decision rationale
4. **Make Recommendation**:
   - Determine whether to proceed, modify, or reject each idea
   - Prioritize ideas that should move forward
   - Define next steps for selected ideas
5. **MUP**: Follow Core MUP and Section VI additions after evaluating ideas.

---

## V. Business Model Development

**Action**: Develop business models for selected ideas.
**Procedure:**
1. **Use Business Model Canvas Template**: Utilize `src/business_templates/business_model_canvas.md` for each selected idea:
   - Define customer segments with recursive analysis
   - Craft value propositions with component breakdown
   - Identify channels and their effectiveness
   - Establish customer relationships
   - Define revenue streams
   - Identify key resources, activities, and partnerships
   - Define cost structure
2. **Analyze Model Coherence**:
   - Ensure all components of the business model fit together
   - Identify potential inconsistencies or conflicts
   - Compare with competing business models
3. **Document Chain-of-Thought**:
   - Record key insights about the business model
   - Document critical dependencies between components
   - Identify potential innovations or differentiators
4. **Define Validation Plan**:
   - List key assumptions to test
   - Define validation methods
   - Establish success criteria
5. **MUP**: Follow Core MUP and Section VI additions after developing business models.

---

## VI. Strategic Analysis

**Action**: Perform comprehensive strategic analyses to inform business innovation.
**Procedure:**
1. **SWOT Analysis**:
   - Use `src/business_templates/swot_analysis_template.md`
   - Analyze internal strengths and weaknesses
   - Identify external opportunities and threats
   - Apply recursive decomposition to core components
   - Analyze cross-dependencies between SWOT elements
   - Develop strategic implications (SO, ST, WO, WT strategies)
2. **Market Research**:
   - Use `src/business_templates/market_research_template.md`
   - Define research objectives and questions
   - Analyze market overview (size, growth, maturity)
   - Segment the market
   - Analyze trends
   - Perform competitive analysis
   - Develop customer personas and journey maps
   - Apply recursive component analysis
   - Document research methodology
3. **Dependency Analysis**:
   - Update `business_dependency_tracker.md` with new insights
   - Refine relationships between business factors
   - Document how market, organizational, and other factors influence each other
4. **MUP**: Follow Core MUP and Section VII additions after completing strategic analyses.

---

## VII. Strategy Plugin - MUP Additions

After Core MUP steps:
1. **Update Business Templates**: Save completed business templates with all generated content.
2. **Update `business_dependency_tracker.md`**: Reflect new dependencies discovered during strategy.
3. **Update `activeContext.md` with Strategy Outcomes:**
   - Summarize generated and evaluated ideas
   - List developed business models
   - Highlight key strategic insights
   - Document priorities and reasoning
4. **Update `.clinerules` [LAST_ACTION_STATE]:**
   ```
   [LAST_ACTION_STATE]
   last_action: "Completed Idea Generation and Evaluation"
   current_phase: "Strategy"
   next_action: "Develop Business Model"
   next_phase: "Strategy"

   [CODE_ROOT_DIRECTORIES]
   - src

   [LEARNING_JOURNAL]
   ```

---

## VIII. Creating Business Innovation Task Instructions

**Action**: Create structured instruction files for business innovation tasks.
**Procedure:**
1. **Identify Key Tasks**: Based on evaluated ideas and business models, identify the key tasks needed for implementation:
   - Market validation tasks
   - Product/service development tasks
   - Business model validation tasks
   - Marketing and sales strategy tasks
2. **Choose Task Location:**
   - Create `{task_name}_instructions.txt` in the `strategy_tasks/` directory
   - Use clear, descriptive names for task files
3. **Populate Instruction File Sections:**
   - Set title: `# {Task Name} Instructions`
   - Define objective: Clearly state purpose and goals
   - Provide context: Include background and constraints
   - List dependencies: Reference business factors from `business_dependency_tracker.md`
   - Outline steps: Break into actionable increments
   - Specify output: Describe deliverables
   - Add notes: Note challenges or considerations
   - Example Instruction File:
     ```
     # Market Validation Instructions

     ## Objective
     Validate assumptions about our target market segment and value proposition.

     ## Context
     Based on our business model canvas and evaluation, the key assumptions
     needing validation are customer willingness to pay and problem severity.

     ## Dependencies
     - Market Factors (customer segments, market size)
     - Product/Service Factors (value proposition)

     ## Steps
     1. Develop customer interview script
     2. Conduct 10-15 interviews with target customers
     3. Analyze feedback for patterns
     4. Update business model based on findings

     ## Expected Output
     - Interview results summary
     - Validated/invalidated assumptions list
     - Revised business model canvas

     ## Notes
     - Focus on open-ended questions
     - Seek disconfirming evidence
     ```
4. **MUP**: Follow Core MUP and Section VII additions after creating instruction files.

---

## IX. Quick Reference

### Business Innovation Templates
- `idea_generation_template.md`: For structured brainstorming
- `idea_evaluation_template.md`: For assessing business ideas
- `business_model_canvas.md`: For business model development
- `swot_analysis_template.md`: For strategic analysis
- `market_research_template.md`: For market research and analysis

### Key Strategy Actions
1. Generate business ideas
2. Evaluate ideas using structured criteria
3. Develop business models for selected ideas
4. Perform strategic analyses
5. Create task instructions for execution
6. Follow MUP after each action