Links - https://drive.google.com/drive/folders/1Uq_OTs4e2pElRrC3nFt3_EoDk2yUZdeP?usp=drive_link

# Work Summary

---

# ROUND 1: Core Pipeline & Initial Submission

## Phase 1: Infrastructure & Setup

1. Created `.gitignore` to exclude datasets and environment files.
2. Initialized Lakehouse directory structure (`Data/Raw/`, `Bronze/`, `Silver/`, `Gold/`) with `.gitkeep` files.
3. Cleaned Git history by removing a large 161MB tracked `.csv` file and amending the initial commit.
4. Successfully pushed the cleaned `main` branch to GitHub.
5. Created and executed `Scripts/01_raw_to_bronze.py` to ingest raw CSV data directly into `.parquet` format in the `Data/Bronze/` directory.
6. Upgraded project to a modular pipeline structure, adding `pipeline/utils/logger.py` and refactoring `pipeline/bronze/01_raw_to_bronze.py` to use professional file logging (`outputs/pipeline.log`).
7. Initialized Silver Layer architecture by creating the `Data/Quarantine/` directory and root `config.yaml` with geographical and string-correction constants.

## Phase 2: Exploratory Data Analysis (EDA)

8. Reviewed `01_eda_transactions.ipynb` and verified coverage of missing values, distributions, and holiday/seasonality impact.
9. Finalized strategies for transactions data: netting/quarantining negative volumes and contextualizing/log-transforming outliers for the LightGBM model.
10. Successfully conducted comprehensive Exploratory Data Analysis on `outlets.csv`, identifying and rectifying data quality issues including missing Outlet_Size values, validating cooler count ranges, and standardizing outlet type categories.
11. Successfully conducted comprehensive Exploratory Data Analysis on `holidays.csv`, validating date ranges, identifying duplicate entries, and standardizing holiday categories (Public, Bank, Mercantile, Poya Day).

## Phase 3: Silver Layer (Data Quality & Cleaning)

12. Successfully wrote Phase 1 of the Silver Layer: `dq_checks.py` library and 5 specific dataset cleaning scripts packed with all business logic and anomaly detection algorithms.
13. Executed `pipeline/Silver/clean_outlets.py`, implementing business logic to impute missing outlet sizes based on cooler count heuristics and quarantining malformed records.
14. Successfully diagnosed and resolved latitude/longitude coordinate discrepancies in `outlet_coordinates.csv` using advanced geocoding validation and bounding box checks, correcting swapped values.
15. Executed `pipeline/Silver/clean_coordinates.py`, implementing business logic to correct swapped latitude/longitude values and quarantine malformed records.
16. Executed `pipeline/Silver/clean_seasonality.py`, successfully extrapolating seasonality metrics to cover January 2026 and flagging imputed rows.
17. Executed `pipeline/Silver/clean_holidays.py`, implementing business logic to map dates to specific holiday types and quarantining malformed records.

## Phase 4: Gold Layer (Feature Engineering)

18. Designed and implemented a two-phase Gold Layer POI data acquisition pipeline to enrich outlet data with geospatial features from OpenStreetMap. **Phase 1** (`scrape_poi_raw.py`) used K-Means spatial clustering to group 19,960 outlets into 400 geographic neighborhoods, reducing API calls by 98%. Each cluster was queried via the Overpass API with a 2 km bounding-box buffer, and raw JSON responses were cached to `Data/Gold/poi_raw_cache/`. A `scrape_manifest.json` tracker enabled idempotent resumption — if the script crashed mid-run, it safely resumed from the last incomplete cluster without re-querying completed ones. Achieved 100% cluster retrieval (400/400).
19. Developed `build_poi_features.py` to calculate outlet-specific POI density metrics across multiple radii (500m, 1km, 2km) and compute a weighted, normalized `footfall_score` for all 20,000 outlets.
20. Implemented `build_sales_features.py` to derive advanced historical metrics, including YoY growth, EMA trends, and January-specific seasonality patterns to support target variable estimation.
21. Designed and implemented `build_master_features.py` to join outlets, POI features, and historical sales features into a single, cohesive dataset. Integrated the "Clean Train, Predict All" strategy to exclude coordinate-imputed records from model training while preserving all 20,000 records for downstream predictions.

## Phase 5: Repository Management

22. Synchronized local repository with `origin/main`, resolving complex merge conflicts and file locks on `outputs/pipeline.log` to ensure alignment with the latest team updates.
23. Updated git configurations (`.gitignore`) to safely package and track finalized `.parquet` gold-layer features for reproducible, zero-compute-loss deployments.

## Phase 6: Modelling (Training and Prediction)

24. Developed and executed `modelling/baseline.py` to compute a naive statistical baseline potential (using January seasonality and December transaction history). This defined the conservative prediction floor for unconstrained demand.
25. Implemented `modelling/train.py` to train a CatBoost regressor on the pseudo-labelled target variable using 41 Gold-layer structural features. Set up a 5-fold cross-validation scheme that achieved a robust CV RMSE of $5.50 \pm 0.38$ (CV MAE of $2.34 \pm 0.02$), validating model stability and feature efficacy.
26. Implemented `modelling/predict.py` to run full inference on the 20,000 outlets. Blended the CatBoost predictions with the statistical baseline potentials using a max-blend approach, clamped any non-positive values, rounded results to 2 decimal places, and generated the final competition-ready submission `outputs/bigbug_predictions.csv` along with detailed diagnostics.

## Phase 7: Documentation & Reporting

27. Authored a thorough `README.md` outlining the environment setup, project structure, and sequential command-line execution steps required to run the pipeline end-to-end (Bronze -> Silver -> Gold -> Modelling -> Inference).
28. Produced the comprehensive 5-page LaTeX technical report (`docs/report/round_1/report.tex`) strictly conforming to Storming Round submission guidelines, covering Data Forensics, POI Acquisition, Causal Base Logic, and the Generative AI Transparency Log.

---

# ROUND 2: Advanced Features, Modeling & XAI

## Phase 1: Advanced Features & Integration

29. **Implemented Gravity Model Feature Engineering (`build_gravity_features.py`)**:
    - Designed and implemented a spatial gravity model based on inverse-square distance decay ($1/(d + \epsilon)^2$) with a decay epsilon of 0.05km and a maximum radius of 2.0km.
    - Utilized a spatial `BallTree` with the Haversine metric for high-performance query execution across all 20,000 outlets against scrape-cached OpenStreetMap POIs.
    - Generated 6 distinct POI category gravity scores (School, Hospital, Transport, Market, Worship, Hospitality), along with a weighted `raw_composite_gravity` score and min-max normalized `composite_gravity_score` $[0, 100]$.
    - Gracefully handled zero-coordinate / quarantined outlets by setting scores to 0 and tagging `gravity_data_available` as `False`. Output compiled to `data/Gold/gravity_features.parquet`.
30. **Implemented Catchment Feature Engineering (`build_catchment_features.py`)**:
    - Built a high-performance spatial competitor density pipeline using a `BallTree` coordinate model.
    - Calculated flat competitor (outlet-to-outlet) counts within three key catchment bands: 500m, 1km, and 2km.
    - Derived a normalized `competition_density_score` based on P25/P75 thresholds of the 1km competitor count, classifying outlets into `isolated` (bottom quartile), `moderate`, or `dense` (top quartile) `market_saturation_class` cohorts.
    - Successfully handled zero-coordinate outlets by assigning 0 competitors and classifying them as `isolated`. Output compiled to `data/Gold/catchment_features.parquet`.
31. **Upgraded Master Features Pipeline (`build_master_features.py`)**:
    - Updated the master integration script to seamlessly `left-join` both `gravity_features.parquet` (10 columns) and `catchment_features.parquet` (6 columns) onto the existing Gold structural features.
    - Strictly maintained the user-requested constraint of rounding all numerical columns to exactly 4 decimal places using pyarrow-friendly float64 upcasting to prevent spurious precision or trailing noise.
    - Resolved Windows console-specific encoding (`UnicodeEncodeError`) issues by replacing special logging indicators (e.g. `≤`, `≥`, `×`, `→`) with clean, fully compatible ASCII equivalents (`<=`, `>=`, `x`, `->`).
    - Successfully generated `data/Gold/master_features.parquet` containing exactly 20,000 rows and 69 columns (representing 55 original features plus 14 newly engineered advanced spatial and competitor features), passing all data contract schema validations.

## Phase 2: Model Training & Ablation Studies

32. Upgraded `train.py` to support multi-algorithm training (XGBoost, LightGBM, Random Forest), configurable feature exclusion strategies, run tracking with timestamped folders and `run_registry.csv`, and optional SHAP extraction via `--shap` flag.
33. Executed 21 model training scenarios across 4 rounds of ablation studies, testing CatBoost, XGBoost, LightGBM, and Random Forest with 8 different feature strategies (`round1_baseline`, `strategyA`, `strategyC`, `strategyA_gravity_only`, `strategyA_flat_only`, and their `_clean` variants).
34. Ran Optuna hyperparameter tuning (`optuna_tune.py`) for XGBoost, LightGBM, and Random Forest on the best-performing `strategyA_gravity_only` feature set. XGBoost achieved a new pipeline best CV RMSE of **40.66**.
35. Extracted cell-by-cell SHAP values via `TreeExplainer` on the Optuna-tuned LightGBM model, saving to `Data/Gold/shap_values.parquet` for downstream XAI dashboard integration.

## Phase 3: Ensemble & Final Predictions

36. Created `ensemble.py` to blend predictions from multiple model runs using configurable weights. Executed with 40% XGBoost, 40% LightGBM, 20% Random Forest split.
37. Extended `predict.py` with `--predictions-csv` and `--output-path` CLI arguments to support loading pre-blended ensemble predictions and custom output paths.
38. Generated the final Round 2 submission at `outputs/round2/bigbug_predictions.csv` (20,000 rows) by running the ensemble through the full post-processing pipeline (baseline floor blending, clamping, rounding, assertions).
