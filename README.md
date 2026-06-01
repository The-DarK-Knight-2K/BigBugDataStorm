# Data Storm 7.0 — BigBug



---

## Project Overview

This repository contains a complete, reproducible data engineering and machine learning pipeline for predicting the **Maximum Monthly Sales Potential (in litres)** for 20,000 retail outlets across Sri Lanka. The pipeline follows a strict **Bronze → Silver → Gold** Lakehouse architecture, ensuring data quality, auditability, and modularity at every layer.

---

## Repository Structure

```
BigBugDataStorm/
├── Data/
│   ├── Raw/                         # Original CSV files (untouched)
│   ├── Bronze/                      # Raw -> Parquet (schema-preserved)
│   ├── Silver/                      # Cleaned, validated, type-safe tables
│   ├── Gold/                        # Engineered features (model-ready)
│   │   ├── poi_raw_cache/           # Cached OpenStreetMap API responses (400 JSON files)
│   │   ├── poi_features.parquet     # Geospatial footfall features
│   │   ├── sales_features.parquet   # Historical demand features
│   │   ├── gravity_features.parquet # Inverse-square POI gravity score features
│   │   ├── catchment_features.parquet # BallTree competitor density features
│   │   ├── cooler_features.parquet  # Cooler capacity physics-based ceiling features
│   │   ├── spatial_cluster_features.parquet # DBSCAN micro-market density cluster features
│   │   ├── tobit_features.parquet   # Predicted features from censored Tobit regression
│   │   ├── hurdle_features.parquet  # Predicted features from zero-inflated Hurdle model
│   │   ├── shap_values.parquet      # Cell-by-cell SHAP contribution values
│   │   └── master_features.parquet  # Consolidated model training features
│   ├── Optimization/                # Optimized trade marketing allocations (parquet format)
│   │   └── budget_features.parquet  # ROI, allocation tiers, and projected uplift
│   └── Quarantine/                  # Rejected records with failure reasons
│
├── pipeline/
│   ├── bronze/
│   │   └── ingest.py                # CSV -> Parquet ingestion
│   ├── silver/
│   │   ├── dq_checks.py             # Reusable data quality engine
│   │   ├── clean_outlets.py         # Outlet master cleaning + size imputation
│   │   ├── clean_coordinates.py     # GPS validation + swapped lat/lon correction
│   │   ├── clean_transactions.py    # Volume netting, blackout detection, outlier flags
│   │   ├── clean_seasonality.py     # Jan 2026 extrapolation
│   │   └── clean_holidays.py        # Holiday type mapping + trading day calculation
│   ├── gold/
│   │   ├── scrape_poi_raw.py        # Phase 1: KMeans clustering + Overpass API scraping
│   │   ├── build_poi_features.py    # Phase 2: Geodesic distance + footfall scoring
│   │   ├── build_sales_features.py  # Vectorized historical sales aggregation
│   │   ├── build_gravity_features.py # Inverse-square distance decay spatial POI scores
│   │   ├── build_catchment_features.py # BallTree neighbor competitor count density
│   │   ├── build_cooler_features.py # Physics-based cooler capacity ceiling estimation
│   │   ├── build_spatial_cluster_features.py # DBSCAN micro-market density clustering
│   │   └── build_master_features.py # Integrates all advanced features into master dataset
│   ├── optimizations/
│   │   └── optimise_budget.py       # Budget optimization logic
│   ├── xai/
│   │   ├── context_packager.py      # Prepares XAI context
│   │   └── prompt_builder.py        # Generates LLM prompts
│   └── utils/
│       └── logger.py                # Centralized logging (console + file)
│
├── modelling/
│   ├── artifacts/                   # Saved model pkl, runs registry, and optuna configurations
│   ├── baseline.py                  # Static baseline demand calculations
│   ├── train.py                     # XGBoost, LightGBM, Random Forest training + SHAP extraction
│   ├── predict.py                   # Blended inference + validation checks
│   ├── ensemble.py                  # Blends predictions from multiple model runs
│   ├── optuna_tune.py               # Optuna hyperparameter re-tuning
│   ├── tobit_model.py               # Tobit regression for censored demand
│   └── hurdle_model.py              # Two-stage zero-inflated demand model
│
├── notebooks/
│   ├── 01_eda_transactions.ipynb    # Exploratory Data Analysis — transactions
│   └── 02_eda_outlets.ipynb         # Exploratory Data Analysis — outlets
│
├── specs/                           # Technical specification documents
│   ├── architecture/                # Coding conventions, strict data contracts, and system overview
│   ├── bronze/                      # CSV data ingestion and schema preservation specs
│   ├── silver/                      # Data cleaning, validation, and quality check specs
│   ├── gold/                        # Feature engineering, POI scraping, and master features specs
│   ├── eda/                         # Notebook requirements and goals for exploratory analysis
│   ├── modelling/                   # Baseline, training, prediction, and Colab experiments specs
│   ├── webapp/                      # API contracts and frontend component specifications
│   └── orchestration/               # Pipeline execution and orchestration flow guidelines
│
├── outputs/
│   ├── pipeline.log                 # Full execution log
│   ├── prediction_diagnostics.csv   # Prediction diagnostics
│   ├── bigbug_predictions.csv       # Final predictions
│   ├── bigbug_budget_allocations.csv # Final trade marketing budget allocations (submission format)
│   ├── budget_diagnostics.csv       # Detailed budget allocation calculations and tiers
│   ├── roi_distribution.png         # ROI score distribution plot with tier boundaries
│   ├── round1/                      # Static archive of Round 1 predictions and configurations
│   ├── round2_lite/                 # Static archive of lightweight/intermediate Round 2 runs
│   └── round2_final/                # Static archive of the most recent final Round 2 model backup
│
├── docs/
│   ├── reference/                   # Project briefs and external requirements
│   ├── setup/                       # Setup and installation guides
│   ├── modelling/                   # Modelling and optimization strategies
│   ├── planning/                    # Project plans and task lists
│   ├── management/                  # Work summaries and tracking logs
│   ├── report/                      # Final reports and findings
│   └── advanced_features/           # Deep-dive analyses on advanced features
│
├── config.yaml                      # Centralized pipeline configuration
├── requirements.txt                 # Python dependencies (pinned versions)
└── README.md
```

---

## Pre-Generated Outputs (Google Drive)

If you prefer to skip running the pipeline and inspect the outputs directly, all generated `.parquet` files (Bronze, Silver, Gold) and audit logs are available here:

> **Google Drive:** [https://drive.google.com/drive/folders/1Uq_OTs4e2pElRrC3nFt3_EoDk2yUZdeP?usp=drive_link](https://drive.google.com/drive/folders/1Uq_OTs4e2pElRrC3nFt3_EoDk2yUZdeP?usp=drive_link)

---

## How to Run the Pipeline (End-to-End)

### Prerequisites

```bash
python -m venv venv
venv\Scripts\activate            # Windows
pip install -r requirements.txt
```

### Using the Orchestrator (Recommended)

The recommended way to run the entire system is via the master orchestrator script. This script sequentially executes all phases (Bronze -> Silver -> Gold -> Modelling -> Optimization) and handles global logging (to `outputs/pipeline.log`).

```bash
# Fast Path (Default): Skips POI scraping and model training, uses cached/pre-trained models.
python pipeline/run_pipeline.py

# Full Run: Forces live POI scraping and trains fresh models
python pipeline/run_pipeline.py --run-scraping --train-models
```

**Available Flags:**
- `--run-scraping`: Triggers live POI scraping via OpenStreetMap (Time-consuming).
- `--tune-hyperparameters`: Runs Optuna hyperparameter tuning before training.
- `--train-models`: Trains fresh XGBoost, LightGBM, and Random Forest models instead of using the cached `round2` models.

---

### Step-by-Step Manual Execution

If you prefer to run the pipeline steps individually for debugging or development:

### Step 0: Place Raw Data

Place the 5 original competition CSV files into the `Data/Raw/` directory:

```
Data/Raw/
├── transactions.csv
├── outlets.csv
├── outlet_coordinates.csv
├── seasonality.csv
└── holidays.csv
```

These files are provided by the competition organizers and are **not** included in the repository.

### Step 1: Bronze Layer — Raw Ingestion

```bash
python pipeline/bronze/ingest.py
```

Converts 5 raw CSV files into schema-preserved `.parquet` files in `Data/Bronze/`.

### Step 2: Silver Layer — Data Cleaning & Validation

Run all 5 cleaning scripts. Each script reads from Bronze, applies business logic and data quality checks, writes clean output to `Data/Silver/`, and quarantines rejected records to `Data/Quarantine/`.

```bash
$env:PYTHONPATH="."   # PowerShell (Windows default)
python pipeline/silver/clean_outlets.py
python pipeline/silver/clean_coordinates.py
python pipeline/silver/clean_transactions.py
python pipeline/silver/clean_seasonality.py
python pipeline/silver/clean_holidays.py
```

**Key transformations:**
- Imputes missing `Outlet_Size` using cooler count heuristics
- Detects and corrects swapped latitude/longitude coordinates
- Nets negative transaction volumes and flags blackout periods
- Extrapolates seasonality indices to cover January 2026
- Maps calendar dates to holiday types and computes trading days

### Step 3: Gold Layer — Feature Engineering

#### 3a. POI Scraping (Phase 1) — ~25 min, one-time only

```bash
$env:PYTHONPATH="."; python pipeline/gold/scrape_poi_raw.py
```

Uses KMeans spatial clustering to group 20,000 outlets into 400 geographic neighborhoods and queries the OpenStreetMap Overpass API with a 2 km bounding-box buffer per cluster. Raw JSON responses are cached locally with a manifest-based idempotent resumption system — if the script is interrupted, restart it and it resumes automatically.

#### 3b. POI Feature Building (Phase 2) — ~8 min, re-runnable

```bash
$env:PYTHONPATH="."; python pipeline/gold/build_poi_features.py
```

Parses the local cache (zero API calls), computes geodesic distances from every outlet to every nearby POI, and generates 18 count columns across 6 categories (schools, hospitals, transport, markets, worship, hospitality) and 3 radius bands (500m, 1000m, 2000m). Produces a normalized Footfall Score (0–100).

#### 3c. Sales Feature Building — ~90 sec

```bash
$env:PYTHONPATH="."; python pipeline/gold/build_sales_features.py
```

Aggregates 2.3M transaction rows into 21 outlet-level demand features using vectorized pandas operations. Includes historical percentiles, January-specific metrics, EMA momentum indicators, YoY growth rates, and activity/recency signals.

#### 3d. Master Feature Assembly

```bash
$env:PYTHONPATH="."; python pipeline/gold/build_master_features.py
```

Joins cleaned outlets, POI features, and sales features into the final analysis-ready dataset. Applies the "Clean Train, Predict All" strategy, filtering training data to remove coordinate imputation noise while keeping all 20,000 records for inference.

### Step 4: Modelling (Training and Prediction)

Our modelling workflow uses XGBoost as the final model, blending with a statistical baseline floor (Jan 2026 Seasonality * Dec 2025 Volume).

#### 4a. Calculate Baseline

```bash
$env:PYTHONPATH="."; python modelling/baseline.py
```

Computes the naive statistical baseline using cleaned transactions and seasonality data. This forms the conservative prediction floor for our final submission.

#### 4b. Train Model

```bash
$env:PYTHONPATH="."; python modelling/train.py
```

Trains the XGBoost regression model using hyperparameters defined in `config.yaml`. Performs an 80/20 chronological split, evaluates RMSE, calculates permutation feature importance, and saves the trained model artifact to `modelling/artifacts/`.

#### 4c. Generate Predictions

```bash
$env:PYTHONPATH="."; python modelling/predict.py
```

Loads the trained model, baseline predictions, and master features to predict the maximum monthly sales potential for all 20,000 outlets. Generates the final competition submission file: `outputs/bigbug_predictions.csv` along with a diagnostic breakdown.

---

## Key Design Decisions

| Decision | Rationale |
|---|---|
| **Lakehouse architecture** (Bronze/Silver/Gold) | Clear separation of raw data, cleaned data, and engineered features. Each layer is independently auditable and re-runnable. |
| **Quarantine system** | Invalid records are never silently dropped. Every rejection includes a `failure_reason` code for full traceability. |
| **Two-phase POI pipeline** | Decouples fragile network I/O (Phase 1) from fast local computation (Phase 2). Radius bands can be changed without re-scraping. |
| **Idempotent manifest** | Phase 1 saves progress after every cluster. Crashes or rate-limits never lose completed work. |
| **Vectorized sales features** | Replaced a 20,000-iteration Python loop with pandas `groupby` operations, achieving ~20x speedup. |
| **Data contracts** | Every `.parquet` file has a strict schema defined in `DATA_CONTRACTS.md`. Runtime assertions enforce compliance before writing. |

---

## Data Quality Report

The pipeline generates `outputs/dq_report.csv` documenting every quality check applied across all datasets, including:
- Records checked, passed, and quarantined per dataset
- Specific failure reason codes (e.g., `zero_coordinates`, `negative_volume`)

---

## Configuration

All tunable parameters are centralized in `config.yaml`:
- Sri Lanka geographic bounds (for coordinate validation)
- Outlet type/size correction mappings
- POI pipeline settings (cluster count, buffer size, radius bands, API URL)

---

## Dependencies

See `requirements.txt` for pinned versions. Core libraries:
- `pandas`, `numpy`, `pyarrow` — data manipulation and file I/O
- `scikit-learn` — KMeans spatial clustering
- `scipy` — linear regression for trend features
- `requests`, `geopy` — API scraping and geodesic distance math
- `xgboost`, `lightgbm` — gradient boosting models
- `tqdm` — progress tracking
