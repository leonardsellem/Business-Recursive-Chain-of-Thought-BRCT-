# Business Recursive Chain-of-Thought Framework (BRCT) - v1.0

Welcome to the **Business Recursive Chain-of-Thought Framework (BRCT)**, an adaptation of the Cline Recursive Chain-of-Thought System (CRCT) specifically designed for business innovation processes. Built upon the powerful CRCT system, BRCT leverages a recursive, file-based approach to support ideation, evaluation, and implementation of business innovations while maintaining comprehensive dependency tracking between business factors.

This is **v1.0**, a functional release that adapts the core CRCT principles for business contexts. It includes specialized templates for business innovation processes and a custom dependency tracking system for business factors.

---

## Key Features

- **Business-Focused Recursive Decomposition**: Breaks complex business problems into manageable components, organized via structured templates for systematic analysis.
- **Comprehensive Business Templates**: Includes specialized templates for idea generation, evaluation, business model canvas, SWOT analysis, and market research.
- **Minimal Context Loading**: Loads only essential business data, expanding via dependency trackers as needed.
- **Persistent State**: Uses the VS Code file system to store context, ideas, evaluations, and business dependencies—maintained via the **Mandatory Update Protocol (MUP)**.
- **Business-Specific Dependency Tracking**: 
  - `business_dependency_tracker.md` (tracks relationships between business factors)
  - Custom dependency types for market, organizational, technological, financial, regulatory, competitive, and strategic dependencies
  - Supports recursive analysis of business factor relationships
- **Phase-Based Workflow**: Operates in distinct phases—**Set-up/Maintenance**, **Strategy**, **Execution**—controlled by `.clinerules`.
- **Business Chain-of-Thought Reasoning**: Ensures transparency with step-by-step reasoning and explicit documentation throughout the business innovation process.

---

## Quickstart

1. **Clone the Repo**: 
   ```bash
   git clone https://github.com/YourUsername/Business-Recursive-Chain-of-Thought-BRCT-.git
   cd Business-Recursive-Chain-of-Thought-BRCT-
   ```

2. **Install Dependencies**:
   ```bash
   pip install -r requirements.txt
   ```

3. **Set Up Cline Extension**:
   - Open the project in VS Code with the Cline extension installed.
   - Copy `cline_docs/prompts/core_prompt(put this in Custom Instructions).md` into the Cline system prompt field.

4. **Start the System**:
   - Type `Start.` in the Cline input to initialize the system.
   - The LLM will bootstrap from `.clinerules`, creating missing files and guiding you through setup.
   - Begin documenting your business innovation process using the provided templates.

*Note*: The Cline extension's LLM automates most commands and updates to `cline_docs/`. Minimal user intervention is required.

---

## Project Structure

```
business-recursive-chain-of-thought/
│   .clinerules              # Controls phase and state
│   README.md                # This file
│   requirements.txt         # Python dependencies
│
├───cline_docs/              # Operational memory
│   │   activeContext.md     # Current state and priorities
│   │   changelog.md         # Logs significant changes
│   │   productContext.md    # Project purpose and user needs
│   │   progress.md          # Tracks progress
│   │   projectbrief.md      # Mission and objectives
│   │   ...                  # Additional templates
│   └───prompts/             # System prompts and plugins
│       core_prompt.md       # Core system instructions
│       setup_maintenance_plugin.md
│       strategy_plugin.md
│       execution_plugin.md
│
├───cline_utils/             # Utility scripts
│   └───dependency_system/
│       dependency_processor.py # Dependency management script
│
├───docs/                    # Project documentation
│
├───src/                     # Source code and templates
│   ├───business_templates/  # Business innovation templates
│   │   ├───idea_generation_template.md
│   │   ├───idea_evaluation_template.md
│   │   ├───business_model_canvas.md
│   │   ├───swot_analysis_template.md
│   │   └───market_research_template.md
│   └───business_dependency_tracker.md # Business factor dependency tracking
│
└───strategy_tasks/          # Strategic plans
```

---

## Business Templates

The BRCT framework includes specialized templates for various aspects of the business innovation process:

- **Idea Generation Template**: Structured approach to generating business ideas with recursive decomposition
- **Idea Evaluation Template**: Framework for evaluating ideas based on feasibility, viability, and desirability
- **Business Model Canvas**: Enhanced canvas with recursive analysis and dependency tracking
- **SWOT Analysis Template**: Comprehensive SWOT analysis with component-level breakdown
- **Market Research Template**: Structured approach to market analysis with recursive decomposition

Each template incorporates chain-of-thought documentation sections to ensure transparency in reasoning and decision-making.

---

## Business Dependency Tracking

The BRCT framework extends CRCT's dependency tracking system with business-specific dependency types:

- Market Dependencies (M): Relationships with market conditions and customer factors
- Organizational Dependencies (O): Relationships with internal capabilities and resources
- Technological Dependencies (T): Relationships with technological capabilities and trends
- Financial Dependencies (F): Relationships with funding, investment, and financial metrics
- Regulatory Dependencies (R): Relationships with legal and compliance factors
- Competitive Dependencies (C): Relationships with competitor actions and positioning
- Strategic Dependencies (S): Relationships with strategic decisions and direction

These dependency types are used in the business_dependency_tracker.md to document relationships between business factors.

---

## Current Status & Future Plans

- **v1.0**: Initial release adapting CRCT for business innovation processes with specialized templates and dependency tracking.
- **Future Enhancements**: Planning to add more specialized templates, enhanced visualization for business dependencies, and integration with business intelligence tools.

Feedback is welcome! Please report bugs or suggestions via GitHub Issues.

---

## Getting Started with Your Business Innovation Project

To start using BRCT for your business innovation project:
1. Initialize the framework by typing `Start.` in Cline.
2. Define your project brief, product context, and initial active context.
3. Use the business templates in the src/business_templates/ directory to document your innovation process.
4. Track business dependencies using the business_dependency_tracker.md.

The system will guide you through the process, helping you decompose complex business problems and maintain clear documentation of your reasoning and decisions.

---

## Acknowledgments

The Business Recursive Chain-of-Thought Framework is built upon the excellent Cline Recursive Chain-of-Thought System (CRCT) created by [RPG-fan](https://github.com/RPG-fan) and available at [https://github.com/RPG-fan/Cline-Recursive-Chain-of-Thought-System-CRCT-](https://github.com/RPG-fan/Cline-Recursive-Chain-of-Thought-System-CRCT-). We extend our sincere thanks to RPG-fan for developing such a robust foundation that made this business adaptation possible.
