# Big Bug Data Storm - Task List

## Phase 1: Setup and Bronze Layer (Completed)
- [x] Initial repository setup and folder structure
- [x] Create `.gitignore` and clear large tracked files
- [x] Ingest raw data to Bronze layer (`Scripts/01_raw_to_bronze.py`)

## Phase 2: Exploratory Data Analysis (EDA)
### `transactions.csv`
- [x] Check for missing values in Date, Distributor_ID, and Volume_Litres.
- [x] Identify negative volumes (refunds/returns) and decide handling strategy.
- [x] Analyze date ranges and identify any gaps or anomalies (e.g., blackout periods).
- [x] Check distribution of transaction volumes and identify outliers.

### `outlet_master.csv`
- [x] Check for missing values in Outlet_Size.
- [x] Validate Cooler_Count distribution (expecting range 0-5).
- [x] Validate Outlet_Type categories.
- [x] Identify duplicates or inconsistencies in Outlet_ID.

### `outlet_coordinates.csv`
- [x] Identify missing coordinates.
- [x] Plot coordinates on a map to check for points outside Sri Lanka (lat: 5.9-9.9, lon: 79.5-81.9).
- [x] Identify swapped latitude and longitude values and plan correction strategy.

### `seasonality.csv`
- [x] Validate Year and Month ranges.
- [x] Check distribution of Seasonality_Index (Favorable, Moderate, Un-Favorable).
- [x] Ensure all distributors are represented across time periods.

### `holidays.csv`
- [x] Check for duplicate dates.
- [x] Validate Holiday_Type distributions.
- [x] Cross-reference holidays with transaction dips/spikes.

## Phase 3: Silver Layer (Data Cleaning & Quality)
### `dq_checks.py`
- [x] Implement schema validation against `DATA_CONTRACTS.md`.
- [x] Set up a quarantine mechanism for rejected records (e.g., `rejected_transactions.parquet`).
- [x] Generate `dq_report.csv` logging checked, passed, and quarantined records.

### `clean_transactions.py`
- [x] Parse raw dates to Python `date` objects.
- [x] Handle and filter out negative `Volume_Litres`.
- [x] Identify and flag blackout periods (`is_blackout_period`).
- [x] Validate `Outlet_ID` and `Distributor_ID` against master lists.

### `clean_outlets.py`
- [x] Impute missing `Outlet_Size` based on `Cooler_Count` heuristics.
- [x] Validate and standardize `Outlet_Type` categorical values.
- [x] Flag records where imputation occurred (`size_imputed`).

### `clean_coordinates.py`
- [x] Detect and fix swapped Latitude/Longitude values.
- [x] Quarantine records with missing, zero, or out-of-bounds coordinates.
- [x] Flag records that were corrected (`coords_swapped`).

### `clean_seasonality.py`
- [x] Extrapolate seasonality metrics to cover January 2026.
- [x] Flag extrapolated rows (`is_extrapolated`).

### `clean_holidays.py`
- [x] Map dates to specific holiday types (public, bank, mercantile, poya day).
- [x] Handle edge cases where multiple holidays fall on the same date.

## Phase 4: Gold Layer (Feature Engineering)
### `scrape_poi.py`
- [ ] Set up robust API querying (OSM/Google) with rate limiting and retries.
- [ ] Calculate POI counts within 500m and 1km radii.
- [ ] Compute weighted `footfall_score`.
- [ ] Handle POI imputation for the 40 outlets with quarantined coordinates.

### `build_sales_features.py`
- [ ] Calculate historical metrics (max, mean, p75, p90, std, CV).
- [ ] Compute January-specific aggregates and active months percentage.
- [ ] Identify `consecutive_zero_months_max` and handle new outlets lacking sufficient history.
- [ ] Calculate YoY growth rate and recent 3-month averages.

### `build_master_features.py`
- [ ] Join cleaned silver tables and gold feature tables safely.
- [ ] Compute `jan_2026_trading_days` accounting for weekends and holidays.
- [ ] Derive `province` or regional features from `distributor_id`.
- [ ] Ensure output has exactly 20,000 rows (no lost outlets).

## Phase 5: Modelling
### `baseline.py`
- [ ] Implement a naive heuristic (e.g., historical Jan average or last 3-month average).
- [ ] Generate baseline predictions and evaluate MAE/RMSE.

### `train.py`
- [ ] Handle temporal train/validation splitting (e.g., predict 2025 Jan using 2024 data).
- [ ] Address skewness in `Volume_Litres` (e.g., log transformation).
- [ ] Encode categorical features (Outlet_Type, Size, Province) robustly.
- [ ] Track experiments, save model artifacts, and log feature importances.

### `predict.py`
- [ ] Load the latest trained model and `master_features.parquet`.
- [ ] Apply post-processing bounds (e.g., ensure `Maximum_Monthly_Liters` > 0).
- [ ] Format output strictly to `teamname_predictions.csv` schema.

## Phase 6: Orchestration
### `run_pipeline.py`
- [ ] Create a sequential execution flow (Bronze -> Silver -> Gold -> Modelling).
- [ ] Add dependency checks (e.g., don't run Gold if Silver fails).
- [ ] Implement global logging and error handling.
