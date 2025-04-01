# Business Recursive Chain-of-Thought Framework (BRCT) - v1.1.1 (based on CRCT v7.2)

Welcome to the **Business Recursive Chain-of-Thought Framework (BRCT)**, an adaptation of the Cline Recursive Chain-of-Thought System (CRCT) v7.2 specifically designed for business innovation processes. Built upon the powerful CRCT system, BRCT leverages a recursive, file-based approach to support ideation, evaluation, and implementation of business innovations while maintaining comprehensive dependency tracking between business factors, now enhanced by CRCT's modular dependency system.

---

## Key Features

- **Business-Focused Recursive Decomposition**: Breaks complex business problems into manageable components, organized via structured templates for systematic analysis.
- **Comprehensive Business Templates**: Includes specialized templates for idea generation, evaluation, business model canvas, SWOT analysis, and market research.
- **Minimal Context Loading**: Loads only essential business data, expanding via dependency trackers as needed.
- **Persistent State**: Uses the VS Code file system to store context, ideas, evaluations, and business dependencies—maintained via the **Mandatory Update Protocol (MUP)**.
- **Modular Dependency System (from CRCT v7.2)**: Inherits the fully modularized dependency tracking system from CRCT for enhanced efficiency and structure.
- **Automated Operations (from CRCT v7.2)**: System operations are now largely automated and condensed into single commands, streamlining workflows.
- **New `show-dependencies` command (from CRCT v7.2)**: Simplifies viewing dependencies without manually reading tracker files.
- **Business-Specific Dependency Tracking**:
  - `src/business_dependency_tracker.md` (tracks relationships between business factors)
  - Custom dependency types for market, organizational, technological, financial, regulatory, competitive, and strategic dependencies (Needs review for integration with modular system)
- **Phase-Based Workflow**: Operates in distinct phases—**Set-up/Maintenance**, **Strategy**, **Execution**—controlled by `.clinerules`.
- **Business Chain-of-Thought Reasoning**: Ensures transparency with step-by-step reasoning and explicit documentation throughout the business innovation process.
- **Markdown-to-PDF Conversion**: Utility command available in Strategy and Execution phases to convert Markdown files (e.g., reports, deliverables) into professionally styled PDFs using Pandoc and WeasyPrint.

---

## Quickstart

1. **Clone the Repo**:
   ```bash
   git clone https://github.com/leonardsellem/Business-Recursive-Chain-of-Thought-BRCT-.git
   cd Business-Recursive-Chain-of-Thought-BRCT-
   ```

2. **Install Dependencies**:
   ```bash
   # Install Python dependencies
   pip install -r requirements.txt

   # Install tools for PDF conversion (macOS with Homebrew)
   # If not on macOS or not using Homebrew, install Pandoc and WeasyPrint manually
   brew install pandoc weasyprint
   ```

3. **Set Up Cline Extension**:
   - Open the project in VS Code with the Cline extension installed.
   - Copy the updated core prompt from `cline_docs/prompts/core_prompt(put this in Custom Instructions).md` into the Cline system prompt field (Note: This prompt file also has conflicts to resolve).

4. **Start the System**:
   - Type `Start.` in the Cline input to initialize the system.
   - The LLM will bootstrap from `.clinerules`, creating missing files and guiding you through setup.
   - Begin documenting your business innovation process using the provided templates in `src/business_templates/`.

*Note*: The Cline extension's LLM automates most commands and updates to `cline_docs/`. Minimal user intervention is required.

---

## Project Structure

```
Business-Recursive-Chain-of-Thought-BRCT-/
│   .clinerules              # Controls phase and state
│   .gitignore
│   INSTRUCTIONS.md          # (Needs update from upstream)
│   LICENSE
│   README.md                # This file
│   requirements.txt         # Python dependencies
│
├───cline_docs/              # Operational memory
│   │   activeContext.md     # Current state and priorities
│   │   changelog.md         # Logs significant changes
│   │   userProfile.md       # User profile and preferences (Adopted from upstream)
│   │   projectbrief.md      # Mission and objectives (Kept from BRCT)
│   │   # Other files like productContext, progress, projectPatterns, systemPatterns, techContext were deleted upstream, decide if needed for BRCT
│   ├───backups/             # Backups of tracker files (Adopted from upstream)
│   └───prompts/             # System prompts and plugins
│       │ core_prompt.md     # Core system instructions (Needs merge)
│       │ execution_plugin.md # (Needs merge)
│       │ setup_maintenance_plugin.md # (Needs merge)
│       │ strategy_plugin.md # (Needs merge)
│   # Upstream has cline_docs/templates/ - Decide if BRCT needs these
│
├───cline_utils/             # Utility scripts (Adopted CRCT v7.2 structure)
│   │ __init__.py
│   └─dependency_system/
│     │ __init__.py
│     │ dependency_processor.py # Core dependency script (Adopted from upstream)
│     ├──analysis/            # Analysis modules (Adopted from upstream)
│     │  └── __init__.py
│     ├──cli/                 # CLI modules (Adopted from upstream)
│     │  └── __init__.py
│     ├──config/              # Config modules (Adopted from upstream)
│     │  └── __init__.py
│     ├──core/                # Core modules (Adopted from upstream)
│     │  └── __init__.py
│     ├──io/                  # IO modules (Adopted from upstream)
│     │  └── __init__.py
│     └──utils/               # Utility modules (Adopted from upstream)
│        └── __init__.py
│
├───docs/                    # Project documentation
│    └── .gitkeep
│
├───src/                     # Source code and BRCT specifics
│   │ .gitkeep
│   ├───business_templates/  # Business innovation templates (Kept from BRCT)
│   │   │ README.md
│   │   │ business_model_canvas.md
│   │   │ idea_evaluation_template.md
│   │   │ idea_generation_template.md
│   │   │ market_research_template.md
│   │   │ swot_analysis_template.md
│   └───business_dependency_tracker.md # Business factor dependency tracking (Kept from BRCT, needs review)
│
└───strategy_tasks/          # Strategic plans (Kept from BRCT)
     └── .gitkeep
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

These dependency types are used in the `src/business_dependency_tracker.md` to document relationships between business factors. *Note: The integration of these types with the new modular dependency system needs further review and potential adaptation.*

---

## Current Status & Future Plans

- **v1.1.1**: Added Markdown-to-PDF conversion utility using Pandoc/WeasyPrint.
- **v1.1**: Merged with CRCT v7.2, incorporating its modular dependency system, automated operations, and other enhancements.
- **Next Steps**: Resolve remaining merge conflicts, adapt business dependency tracking to the new modular system, update documentation (`INSTRUCTIONS.md`, prompts), and test the integrated framework.
- **Future Enhancements**: Planning to add more specialized templates, enhanced visualization for business dependencies, and integration with business intelligence tools.

Feedback is welcome! Please report bugs or suggestions via GitHub Issues.

---

## Getting Started with Your Business Innovation Project

To start using BRCT for your business innovation project:
1. Initialize the framework by typing `Start.` in Cline.
2. Define your project brief, user profile, and initial active context.
3. Use the business templates in the `src/business_templates/` directory to document your innovation process.
4. Track business dependencies using `src/business_dependency_tracker.md` (pending adaptation to the new system).

The system will guide you through the process, helping you decompose complex business problems and maintain clear documentation of your reasoning and decisions.

---

## Acknowledgments

The Business Recursive Chain-of-Thought Framework is built upon the excellent Cline Recursive Chain-of-Thought System (CRCT) created by [RPG-fan](https://github.com/RPG-fan) and available at [https://github.com/RPG-fan/Cline-Recursive-Chain-of-Thought-System-CRCT-](https://github.com/RPG-fan/Cline-Recursive-Chain-of-Thought-System-CRCT-). We extend our sincere thanks to RPG-fan for developing such a robust foundation (v7.2) that made this business adaptation possible.
