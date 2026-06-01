# Specifications Hub — Team BigBug

Welcome to the **Specifications Hub** for Team BigBug's Data Storm v7.0 solution. This directory contains all technical specifications, system design schemas, data contracts, and architectural guidelines that enforce safety, reproducibility, and mathematical correctness across the entire codebase.

---

## Directory Structure

Here is a comprehensive index of the engineering specifications that govern our pipeline:

```text
specs/
├── README.md                          # This specifications entrypoint
├── architecture/                      # Global standards and architectural layouts
│   ├── CONVENTIONS.md                 # Code styling, git conventions, and variable naming
│   ├── DATA_CONTRACTS.md              # Medallion layer boundaries and schema schemas
│   ├── SPEC_pipeline_nodes.md         # Detailed sequence of execution and node contracts
│   └── SYSTEM_OVERVIEW.md             # Overall Lakehouse architecture and frontend linkage
├── bronze/                            # Raw data parsing specs
│   └── SPEC_ingest.md                 # Strict schemas for raw competition CSV parsing
├── eda/                               # Exploratory data analysis specs
│   ├── 01_transactions_spec.md        # Transaction historical volume patterns
│   ├── 02_outlets_spec.md             # Outlet attributes and spatial anomalies
│   └── 03_features_spec.md            # Initial candidate feature definitions
├── silver/                            # Quality assurance & cleaning standards
│   ├── SPEC_clean_coordinates.md      # Spatial imputation, geo-fencing, and coordinate validation
│   ├── SPEC_clean_holidays.md         # Date alignments and holiday scaling factors
│   ├── SPEC_clean_outlets.md          # Outlet profile validations (cooler counts, class)
│   ├── SPEC_clean_seasonality.md      # Regional and temporal trend metrics
│   ├── SPEC_clean_transactions.md     # Anomaly and transaction outlier filtering
│   └── SPEC_dq_checks.md              # High-integrity data quality rules and Quarantine triggers
├── gold/                              # Feature engineering & spatial algorithms
│   ├── SPEC_build_master_features.md  # Compilation contract for training matrices
│   ├── SPEC_build_sales_features.md   # Aggregated temporal and demand metrics
│   ├── SPEC_catchment_features.md     # BallTree competitor densities
│   ├── SPEC_cooler_features.md        # Cooler capacity boundaries and physical limits
│   ├── SPEC_gravity_model.md          # Reilly's Law Spatial Inverse-Square Gravity model
│   ├── SPEC_scrape_poi.md             # Overpass API (OSM) multi-category point-of-interest scraping
│   └── SPEC_spatial_cluster.md        # DBSCAN clustering for neighborhood micro-markets
├── modelling/                         # Machine learning execution guidelines
│   ├── SPEC_baseline.md               # Baseline constraints and validation splitting
│   ├── SPEC_budget_optimization.md    # Allocation mathematical constraints and objective functions
│   ├── SPEC_colab_experiments.md      # Remote GPU acceleration specifications
│   ├── SPEC_predict.md                # Inference execution and ceiling-capping safety rules
│   ├── SPEC_train.md                  # Ensemble training, Optuna tuning, and CV structures
│   └── SPEC_xai.md                    # SHAP explainability matrices and feature mappings
├── optimizations/                     # Operational decision-making models
│   └── SPEC_optimise_budget.md        # Tier-budget capped Greedy Knapsack algorithm spec
├── orchestration/                     # Automation and pipeline management
│   ├── SPEC_run_pipeline.md           # Master pipeline script execution requirements
│   ├── SPEC_run_setup.md              # Requirements for running environment setup tasks
│   └── SPEC_training_scenarios.md     # Cross-validation and training scenario automation
└── webapp/                            # Frontend dashboard & Gemini integration
    ├── 01_architecture.md             # React boundary, Next.js architecture, and API design
    ├── 02_database.md                 # SQLite database indexing, table structures, and relations
    ├── 03_llm_integration.md          # Google Gemini prompt templates, schemas, and LLM retry rules
    ├── 04_ui_pages.md                 # Page flow, charts (Recharts), and layout specifications
    └── 05_phase2_migration.md         # Scalability strategies and tech debt resolutions
```

---

## Key Specifications & Contracts

### 1. Global Architecture & Data Contracts
*   **[DATA_CONTRACTS.md](file:///c:/Users/sithu/My%20Works/My%20Softwares/Competitions/DataStorm3_ML_DS/BigBugDataStorm/specs/architecture/DATA_CONTRACTS.md):** Defines the exact schemas for every level of our Medallion Lakehouse (`Raw` $\rightarrow$ `Bronze` $\rightarrow$ `Silver` $\rightarrow$ `Gold` $\rightarrow$ `Optimization`). Every column, type, and verification constraint is explicitly detailed.
*   **[SPEC_pipeline_nodes.md](file:///c:/Users/sithu/My%20Works/My%20Softwares/Competitions/DataStorm3_ML_DS/BigBugDataStorm/specs/architecture/SPEC_pipeline_nodes.md):** Maps how execution nodes read and write datasets, ensuring that downstream runs have absolute dependency safety.

### 2. Silver Layer Quality & Cleaning
*   **[SPEC_dq_checks.md](file:///c:/Users/sithu/My%20Works/My%20Softwares/Competitions/DataStorm3_ML_DS/BigBugDataStorm/specs/silver/SPEC_dq_checks.md):** Outlines our data quality framework. Outlets with malformed geolocations or severe sales outliers are safely logged and redirected to `Data/Quarantine/` instead of breaking downstream training.
*   **[SPEC_clean_coordinates.md](file:///c:/Users/sithu/My%20Works/My%20Softwares/Competitions/DataStorm3_ML_DS/BigBugDataStorm/specs/silver/SPEC_clean_coordinates.md):** Standardizes geolocation formats, and specifies center-imputation for shops missing precise latitude/longitude attributes.

### 3. Gold Layer Spatial & Capacity Features
*   **[SPEC_gravity_model.md](file:///c:/Users/sithu/My%20Works/My%20Softwares/Competitions/DataStorm3_ML_DS/BigBugDataStorm/specs/gold/SPEC_gravity_model.md):** Details the inverse-square gravity calculation applied to OpenStreetMap POI targets. Formulates distance-decay features:
    $$G_i = \sum_{j} \frac{W_j}{d_{ij}^2}$$
*   **[SPEC_cooler_features.md](file:///c:/Users/sithu/My%20Works/My%20Softwares/Competitions/DataStorm3_ML_DS/BigBugDataStorm/specs/gold/SPEC_cooler_features.md):** Specifies boundary constraints derived from cooler sizes and distributor cycle replenishment ceilings to prevent un-scalable physical sales predictions.

### 4. Intelligence App Frontend
*   **[03_llm_integration.md](file:///c:/Users/sithu/My%20Works/My%20Softwares/Competitions/DataStorm3_ML_DS/BigBugDataStorm/specs/webapp/03_llm_integration.md):** Houses prompt engineering templates and schemas that translate highly complex SHAP indices into actionable, professional **Negotiation Action Cards** for sales representatives.

---

*For high-level project goals, submission methodologies, and model score analyses, refer to the corresponding [Documentation Hub](file:///c:/Users/sithu/My%20Works/My%20Softwares/Competitions/DataStorm3_ML_DS/BigBugDataStorm/docs/README.md).*
