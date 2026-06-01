# Documentation Hub — Team BigBug

Welcome to the **Documentation Hub** for Team BigBug's end-to-end Data Storm v7.0 solution. This directory serves as the centralized repository for all planning, research, methodologies, modeling summaries, and evaluation reports.

---

## Directory Structure

Here is an overview of the documents organized by key phases and domains:

```text
docs/
├── README.md                          # This documentation entrypoint
├── advanced_features/                 # Deep dives into data engineering features
│   ├── scoring_gap_analysis.md        # Analysis of performance and evaluation scoring gaps
│   └── target_leakage_analysis.md     # Preventative analysis ensuring zero target leakage
├── analysis/                          # Competition grading and evaluations
│   ├── judge_evaluation.md            # Internal assessment of model against grading criteria
│   └── judge_evaluation.tex           # LaTeX source for judge evaluations
├── management/                        # Task planning and project execution summaries
│   ├── project_task_list.md           # Live checklist of completed, ongoing, and planned tasks
│   └── work_summary.md                # Comprehensive breakdown of team contributions
├── modelling/                         # Core machine learning reports
│   ├── model_results_summary.md       # Comparative overview of predictive performance across models
│   ├── strategy.md                    # Core architecture strategy for model training
│   ├── training_qa.md                 # Quality assurance logs and training verification tests
│   ├── training_scenario_results.md   # Model output comparisons under multiple hyperparameter scenarios
│   ├── tuning_and_ensemble_report.md  # Detailed Optuna tuning and blend configurations
│   └── optimizations/                 # Implemented and planned modeling strategies
│       ├── optimizations_implemented.md
│       ├── optimizations_unimplemented.md
│       ├── target_strategies_implemented.md
│       └── target_strategies_unimplemented.md
├── planning/                          # Architectural plans and mathematical formulations
│   ├── greedy_knapsack_budget_plan.md # Knapsack formulation for LKR 5M allocation
│   ├── parallel_execution_plan.md     # Execution plan for parallelized spatial operations
│   ├── phase2_optimization_plan.md    # Multi-phase scaling strategy
│   └── xai_handoff.md                 # Explainable AI integration specifications
├── reference/                         # External rules and boundary constraints
│   ├── known_edge_cases.md            # Handling strategies for null spatial nodes and outlier retailers
│   └── problem_statement.md           # Core competition guidelines and constraints
├── report/                            # Submission papers and presentations
│   ├── round_1/                       # Phase 1 data cleaning and caching reports
│   │   ├── data_forensics_and_decisions.md
│   │   ├── poi_data_acquisition.md
│   │   └── report.tex
│   └── round_2/                       # Phase 2 advanced methodology papers
│       ├── advanced_features_modeling.md
│       ├── budget_optimization_strategy.md
│       ├── methodology_technical_paper.md   # The primary technical methodology paper (PDF/Word source)
│       ├── methodology_technical_paper.tex  # LaTeX source code of the methodology paper
│       └── orchestration_summary.md         # Documentation on the execution pipeline
├── setup/                             # Execution and platform environments
│   └── eda_colab_setup.md             # Notebook setup for Google Colab/local GPU runs
└── web_app/                           # Dashboard interface planning
    ├── master_plan.md                 # UI/UX specifications for the XAI dashboard
    └── sample_outlets.json            # Mock outlet profiles for dashboard verification
```

---

## Key Documents & Quick Links

For a quick deep dive, we recommend reading these high-value files first:

| Document | Focus | Path |
| :--- | :--- | :--- |
| **Methodology Technical Paper** | Primary final report explaining math, pipeline & results | [methodology_technical_paper.md](file:///c:/Users/sithu/My%20Works/My%20Softwares/Competitions/DataStorm3_ML_DS/BigBugDataStorm/docs/report/round_2/methodology_technical_paper.md) |
| **Model Results & Tuning** | Optuna trials, ensembles, and baseline comparisons | [tuning_and_ensemble_report.md](file:///c:/Users/sithu/My%20Works/My%20Softwares/Competitions/DataStorm3_ML_DS/BigBugDataStorm/docs/modelling/tuning_and_ensemble_report.md) |
| **Budget Optimization Strategy** | Knapsack math and allocations under strict boundaries | [budget_optimization_strategy.md](file:///c:/Users/sithu/My%20Works/My%20Softwares/Competitions/DataStorm3_ML_DS/BigBugDataStorm/docs/report/round_2/budget_optimization_strategy.md) |
| **UI Master Plan** | Next.js architecture and Gemini-based XAI explanations | [master_plan.md](file:///c:/Users/sithu/My%20Works/My%20Softwares/Competitions/DataStorm3_ML_DS/BigBugDataStorm/docs/web_app/master_plan.md) |
| **Data Forensics & POI Caching** | OpenStreetMap (OSM) spatial scraping strategies & cleaning | [data_forensics_and_decisions.md](file:///c:/Users/sithu/My%20Works/My%20Softwares/Competitions/DataStorm3_ML_DS/BigBugDataStorm/docs/report/round_1/data_forensics_and_decisions.md) |

---

## Core Sections & Descriptions

### 1. Advanced Features & Data Forensics
*   **[scoring_gap_analysis.md](file:///c:/Users/sithu/My%20Works/My%20Softwares/Competitions/DataStorm3_ML_DS/BigBugDataStorm/docs/advanced_features/scoring_gap_analysis.md):** Breaks down the target metric evaluation delta and identifies optimizations to bridge gaps between regional benchmarks and model forecasts.
*   **[target_leakage_analysis.md](file:///c:/Users/sithu/My%20Works/My%20Softwares/Competitions/DataStorm3_ML_DS/BigBugDataStorm/docs/advanced_features/target_leakage_analysis.md):** Critical data engineering check that confirms features derived from transactions do not leak forward-looking target information.

### 2. Modeling & Scenario Evaluation
*   **[model_results_summary.md](file:///c:/Users/sithu/My%20Works/My%20Softwares/Competitions/DataStorm3_ML_DS/BigBugDataStorm/docs/modelling/model_results_summary.md):** Compiles RMSE, MAE, R², and boundary validations across baseline XGBoost, LightGBM, Random Forest, Tobit, and Hurdle regressions.
*   **[training_scenario_results.md](file:///c:/Users/sithu/My%20Works/My%20Softwares/Competitions/DataStorm3_ML_DS/BigBugDataStorm/docs/modelling/training_scenario_results.md):** Reports scores from different validation configurations (K-Fold vs. Spatial Cross-Validation).
*   **[tuning_and_ensemble_report.md](file:///c:/Users/sithu/My%20Works/My%20Softwares/Competitions/DataStorm3_ML_DS/BigBugDataStorm/docs/modelling/tuning_and_ensemble_report.md):** Highlights how hyperparameter tuning was conducted and how predictions were ensembled.

### 3. Budget & Mathematical Planning
*   **[greedy_knapsack_budget_plan.md](file:///c:/Users/sithu/My%20Works/My%20Softwares/Competitions/DataStorm3_ML_DS/BigBugDataStorm/docs/planning/greedy_knapsack_budget_plan.md):** Mathematical outline of the Tiered-Capped Greedy Knapsack allocation logic that maximizes ROI while strictly honors the LKR 5M cap and business rules.
*   **[parallel_execution_plan.md](file:///c:/Users/sithu/My%20Works/My%20Softwares/Competitions/DataStorm3_ML_DS/BigBugDataStorm/docs/planning/parallel_execution_plan.md):** Multi-threaded strategy for spatial computing to parse BallTrees and Reilly's gravity model rapidly.

### 4. Interactive Dashboard Specifications
*   **[master_plan.md](file:///c:/Users/sithu/My%20Works/My%20Softwares/Competitions/DataStorm3_ML_DS/BigBugDataStorm/docs/web_app/master_plan.md):** Outlines the client dashboard setup, SQLite database schema integration, Next.js routing, and the Gemini 2.0 API prompt strategies.

---

*For detailed technical guidelines, architecture contracts, and exact pipeline node details, please refer to the corresponding [Specifications Hub](file:///c:/Users/sithu/My%20Works/My%20Softwares/Competitions/DataStorm3_ML_DS/BigBugDataStorm/specs/README.md).*
