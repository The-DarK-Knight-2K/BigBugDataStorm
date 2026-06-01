# Data Storm 7.0 — BigBug (Final Submission)

<div align="center">
  <h3>End-to-End Data Engineering, Advanced Modeling & GenAI XAI Dashboard</h3>
</div>

---

## Project Overview

This repository contains Team BigBug's complete, end-to-end solution for the Data Storm v7.0 Final Round. Our system solves the problem of predicting **Maximum Monthly Sales Potential (in litres)** for 20,000 traditional retail outlets across Sri Lanka and optimally allocating a **LKR 5M trade marketing budget**.

The solution is divided into two primary, fully-integrated components:

1. **The Analytical Engine (Backend):** A reproducible, Medallion Lakehouse data pipeline featuring spatial inverse-square gravity models, DBSCAN clustering, Tobit censored regression, zero-inflated Hurdle models, and an Optuna-tuned Multi-Algorithm Ensemble.
2. **The Intelligence App (Frontend):** A Next.js interactive web dashboard that visualizes predictive results and utilizes Google Gemini 2.0 Flash to translate complex SHAP cell contributions into actionable, plain-English **Field Rep Negotiation Plans**.

---

## Key Innovations & Advanced Methodologies

Our methodology comprehensively fulfills all four evaluation criteria (Data Engineering, Base Math, Business Viability, and GenAI Utilization):

1. **Spatial Gravity & Micro-Markets:** Replaced flat radius counts with Reilly's Law distance-decay functions (inverse-square gravity) to measure true catchment pull. Used DBSCAN to discover natural neighborhood micro-markets.
2. **Censored & Zero-Inflated Math:** Integrated a **Tobit Model** to statistically estimate latent demand masked by physical constraints, and a two-stage **Hurdle Model** to cleanly isolate inactive dormancy from conditional volume.
3. **Physics-Based Constraints:** Formulated structural upper-bounds derived from physical cooler counts and 3-day distributor replenishment cycles to guarantee predictions never exceed physical reality.
4. **Spend Optimization:** A Tier-Budget Capped Greedy Knapsack algorithm that safely distributes the 5M LKR budget, enforcing commercial minimum-spend floors and protecting against distributor over-allocation.
5. **GenAI Transparency (XAI):** A fully operational Next.js application that fetches real-time LLM-driven justifications for every outlet's predicted target based on underlying SHAP explainability matrices.

---

## Repository Structure

```text
BigBugDataStorm/
├── app/                             # Next.js Interactive Intelligence Dashboard (Frontend UI & XAI)
│   ├── data/outlets.db              # High-performance SQLite database built from pipeline outputs
│   └── src/                         # Next.js React components, API routes, and styling
│
├── Data/                            # Medallion Lakehouse
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
│   │   ├── shap_values.parquet      # Cell-by-cell SHAP contribution values
│   │   └── master_features.parquet  # Consolidated model training features
│   ├── Optimization/                # Optimized trade marketing allocations
│   └── Quarantine/                  # Rejected records with failure reasons
│
├── pipeline/
│   ├── bronze/                      # CSV -> Parquet ingestion
│   ├── silver/                      # Data cleaning, size imputation, anomaly flagging
│   ├── gold/                        # Feature engineering (Gravity, POI, Catchment, Sales)
│   ├── optimizations/               # Budget optimization and greedy knapsack solver
│   ├── xai/                         # SHAP extraction and GenAI prompt context generation
│   └── run_pipeline.py              # Master execution orchestrator
│
├── modelling/
│   ├── train.py                     # XGBoost, LightGBM, Random Forest training with Optuna
│   ├── tobit_model.py               # Tobit maximum-likelihood estimation for censored data
│   ├── hurdle_model.py              # Zero-inflated 2-stage regression model
│   ├── ensemble.py                  # Blends predictions from multiple model runs
│   └── predict.py                   # Generates inference for 20,000 outlets
│
├── outputs/                         # Final submission CSVs, budget diagnostics, and execution logs
├── docs/                            # Research reports, technical methodology papers, and scoring audit
├── config.yaml                      # Centralized pipeline configuration
└── requirements.txt                 # Pinned Python dependencies
```

---

## How to Run the End-to-End System

### Part 1: The Analytical Data Pipeline (Backend)

The backend handles all data validation, feature engineering, model training, and budget optimization.

#### 1. Setup Environment

```bash
python -m venv venv
venv\Scripts\activate            # On Windows
pip install -r requirements.txt
```

#### 2. Place Raw Data

Ensure the 5 original competition CSV files (`transactions.csv`, `outlets.csv`, `outlet_coordinates.csv`, `seasonality.csv`, `holidays.csv`) are placed directly into the `Data/Raw/` directory.

#### 3. Using the Orchestrator (Recommended)

Our system features an automated, idempotent orchestrator that runs the full Bronze $\rightarrow$ Silver $\rightarrow$ Gold $\rightarrow$ Modelling execution chain.

```bash
# Fast Path: Skips API scraping & model training, using cached/pre-trained models
python pipeline/run_pipeline.py

# Full Run: Forces live OpenStreetMap scraping and trains fresh models
python pipeline/run_pipeline.py --run-scraping --train-models

# Resume execution from a specific stage
python pipeline/run_pipeline.py --start-from 7
```

**Available Flags:**

- `--run-scraping`: Triggers live POI scraping via OpenStreetMap (Time-consuming).
- `--tune-hyperparameters`: Runs Optuna hyperparameter tuning before training.
- `--train-models`: Trains fresh tree models instead of using the cached final models.
- `--start-from <int>`: Resumes pipeline execution from a specific stage number.

#### 4. Step-by-Step Manual Execution (For Debugging)

If you prefer to run the pipeline steps individually:

**Step 1: Bronze Layer — Raw Ingestion**

```bash
python pipeline/bronze/ingest.py
```

**Step 2: Silver Layer — Data Cleaning & Validation**

```bash
$env:PYTHONPATH="."   # PowerShell (Windows default)
python pipeline/silver/clean_outlets.py
python pipeline/silver/clean_coordinates.py
python pipeline/silver/clean_transactions.py
python pipeline/silver/clean_seasonality.py
python pipeline/silver/clean_holidays.py
```

_(Handles coordinate correction, missing size imputation, and negative volume netting)_

**Step 3: Gold Layer — Feature Engineering**

```bash
python pipeline/gold/scrape_poi_raw.py                # Phase 1: K-Means clustering + Overpass API
python pipeline/gold/build_poi_features.py            # Phase 2: Geodesic distances
python pipeline/gold/build_gravity_features.py        # Phase 3: Distance-decay non-linear gravity
python pipeline/gold/build_catchment_features.py      # Phase 4: BallTree competitor density
python pipeline/gold/build_cooler_features.py         # Phase 5: Physics-based volumetric ceilings
python pipeline/gold/build_spatial_cluster_features.py # Phase 6: DBSCAN micro-market neighborhoods
python pipeline/gold/build_sales_features.py          # Phase 7: Vectorized temporal sales aggregation
python pipeline/gold/build_master_features.py         # Phase 8: Consolidated join for model training
```

**Step 4: Modelling**

```bash
python modelling/baseline.py        # Computes static statistical baseline floor
python modelling/tobit_model.py     # Runs censored regression feature creation
python modelling/hurdle_model.py    # Runs 2-stage zero-inflated probability models
python modelling/train.py           # Trains 5-Fold OOF ensembles (XGBoost, LightGBM, RF)
python modelling/ensemble.py        # Generates weighted model blending
python modelling/predict.py         # Infers maximum potential for all 20,000 outlets
```

**Step 5: Budget Optimization**

```bash
python pipeline/optimizations/optimise_budget.py
```

_(Produces `outputs/bigbug_predictions.csv` and `outputs/bigbug_budget_allocations.csv`)_

---

### Part 2: The Intelligence Web App (Frontend)

The frontend is an interactive Next.js application that brings the model's outputs to life for business stakeholders and frontline sales reps.

#### 1. Setup the Local Database

The web app runs on a highly optimized SQLite database constructed from the backend's Parquet files.

```bash
cd app
pip install pandas pyarrow sqlite3
python scripts/populate_real_db.py
```

#### 2. Configure Environment Variables

Create an `app/.env.local` file and add your Gemini API Key for the GenAI XAI module:

```env
GEMINI_API_KEY=your_gemini_api_key_here
```

#### 3. Install & Launch

```bash
npm install
npm run dev
```

Navigate to [http://localhost:3000](http://localhost:3000) to explore the interactive dashboard and generate Field Rep Negotiation Plans.

---

## Key Design Decisions

| Decision                    | Rationale                                                                                                                                                                               |
| --------------------------- | --------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| **Medallion Lakehouse**     | Clear separation of raw data, cleaned data, and engineered features. Each layer is independently auditable and re-runnable.                                                             |
| **Quarantine System**       | Invalid records are never silently dropped. Every rejection includes a `failure_reason` code for full traceability.                                                                     |
| **Inverse-Square Gravity**  | Dropped standard spatial counts in favor of Reilly's Law distance decay, proving empirically that closer POIs hold exponentially more weight.                                           |
| **Tobit Censored Models**   | Realized that historical volume is mathematically right-censored by physical cooler capacity, and statistically modeled the hidden latent demand rather than just using a simple proxy. |
| **Idempotent API Fetching** | POI Phase 1 saves progress after every cluster. Crashes or rate-limits never lose completed work, ensuring 100% data retrieval.                                                         |
| **Tier-Capped Knapsack**    | Optimizing the budget using raw ROI resulted in skewed distributor allocations. The Tier-capped Greedy algorithm forces minimum spend floors and balances investments.                  |

---

## Data Quality & Pipeline Integrity

The pipeline generates `outputs/dq_report.csv` documenting every quality check applied across all datasets, including:

- **Zero Silent Data Drops:** 100% of pipeline validation failures are safely routed to the `Data/Quarantine/` schema.
- **Target Leakage Proof:** Advanced algorithms are trained using strict 5-Fold Out-Of-Fold (OOF) cross-validation loops to prevent proxy feature memorization.
- **Data Contracts:** Every `.parquet` file has a strict schema. Runtime assertions enforce compliance before writing.

---

## Pre-Generated Outputs (Google Drive)

If you prefer to inspect the output data directly without running the pipeline, all generated `.parquet` feature files and audit logs are available:

> **Google Drive:** [Data Storm Pre-Generated Outputs Link](https://drive.google.com/drive/folders/1Uq_OTs4e2pElRrC3nFt3_EoDk2yUZdeP?usp=drive_link)
