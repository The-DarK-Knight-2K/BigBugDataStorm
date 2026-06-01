# Big Bug Data Storm - Task List

# _ROUND 01_

## Phase 1: Setup and Bronze Layer (Completed)

- [x] Initial repository setup and folder structure
- [x] Create `.gitignore` and clear large tracked files
- [x] Ingest raw data to Bronze layer (`Scripts/ingest.py`)

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

### `scrape_poi_raw.py`

- [x] Set up robust API querying (OSM) with clustering, rate limiting, and retries.
- [x] Implement caching mechanism (`scrape_manifest.json`) for resumes.

### `build_poi_features.py`

- [x] Calculate POI counts within multiple radii (500m, 1km, 2km).
- [x] Compute weighted and normalized `footfall_score` (0-100).
- [x] Handle POI imputation (assigning 0s) for outlets with no coordinates or failed scrapes.

### `build_sales_features.py`

- [x] Calculate historical metrics (max, mean, p75, p90, std, CV).
- [x] Compute January-specific aggregates and active months percentage.
- [x] Identify `consecutive_zero_months_max` and handle inactive outlets.
- [x] Calculate YoY growth rate, EMA, and recent 3-month averages.

### `build_master_features.py`

- [x] Join cleaned silver tables and gold feature tables safely.
- [x] Load `jan_2026_trading_days` from the silver JSON file.
- [x] Derive `province` from `distributor_id`.
- [x] Add `has_transaction_history` flag (from `active_months > 0`).
- [x] Add `exclude_from_training` flag (outlets with no valid coordinates).
- [x] Fill `coords_swapped` NaN with `False` for quarantined outlets.
- [x] Round all float columns to 4 decimal places.
- [x] Ensure output has exactly 20,000 rows (no lost outlets).

## Phase 5: Modelling

### `baseline.py`

- [x] Implement a naive heuristic (e.g., historical Jan average or last 3-month average).
- [x] Generate baseline predictions and evaluate MAE/RMSE.

### `train.py`

- [x] Handle temporal train/validation splitting (e.g., predict 2025 Jan using 2024 data).
- [x] Address skewness in `Volume_Litres` (e.g., log transformation).
- [x] Filter out `exclude_from_training` records (invalid coordinates) before fitting.
- [x] Encode categorical features (Outlet_Type, Size, Province) robustly.
- [x] Track experiments, save model artifacts, and log feature importances.

### `predict.py`

- [x] Load the latest trained model and `master_features.parquet`.
- [x] Apply post-processing bounds (e.g., ensure `Maximum_Monthly_Liters` > 0).
- [x] Format output strictly to `teamname_predictions.csv` schema.

## Phase 6: Orchestration

### `run_pipeline.py`

- [ ] Create a sequential execution flow (Bronze -> Silver -> Gold -> Modelling).
- [ ] Add dependency checks (e.g., don't run Gold if Silver fails).
- [ ] Implement global logging and error handling.

# **ROUND 02**

## Phase 1: Advanced Features & Modeling

### `build_gravity_features.py`

- [x] Read POI cache and calculate inverse-square gravity scores for 6 categories.
- [x] Calculate composite gravity score and normalise.
- [x] Output `gravity_features.parquet`.

### `build_catchment_features.py`

- [x] Calculate flat competition counts within 500m, 1km, and 2km using BallTree.
- [x] Calculate market saturation metrics.
- [x] Output `catchment_features.parquet`.

### `build_master_features.py` (Update)

- [x] Left-join `gravity_features` and `catchment_features`.

### `train.py` (Update)

- [x] Remove target leakage features (e.g., `hist_p90_monthly`) from training (Strategy A).
- [x] Implement Run Tracking (timestamped folders and `run_registry.csv`).
- [x] Enable GPU training (`task_type="GPU"`).
- [x] Extract cell-by-cell SHAP values using `TreeExplainer` into `shap_values.parquet`.

### Model Training Scenarios (Execution)

#### Round 2 (Completed)

- [x] ~~**Scenario 1:** Round 1 Baseline — `round1_baseline` with CatBoost (GPU)~~ ❌ ABANDONED (CatBoost over-regularised, RMSE 329.00)
- [x] ~~**Scenario 2:** Strategy A — Remove Target Leakage with CatBoost (GPU)~~ ❌ ABANDONED (Same CatBoost issue)
- [x] **Scenario 3:** Strategy A — XGBoost Comparison (GPU) — RMSE 41.82
- [x] **Scenario 4:** Strategy A — LightGBM Comparison — RMSE 43.50
- [x] **Scenario 5:** Strategy C — Feature Interactions with XGBoost (GPU) — RMSE 41.78
- [x] **Scenario 6:** Strategy A + Only Gravity Features with XGBoost (GPU) — RMSE **41.14** (BEST)
- [x] **Scenario 7:** Strategy A + Only Flat POI Counts with XGBoost (GPU) — RMSE 41.54
- [ ] **Scenario 8:** Strategy A + Tuned Epsilon (epsilon = 0.02) — ⏸️ DEFERRED
- [x] **Scenario 9:** Optuna Hyperparameter Re-tuning (XGBoost GPU, `strategyC`) — RMSE 41.33

#### Round 3 — Boolean Noise Removal + Algorithm Expansion (Pending)

- [x] **Scenario 10:** Strategy C — LightGBM (original features) — RMSE 43.64
- [x] **Scenario 11:** Strategy C Clean — XGBoost (boolean noise removed) — RMSE 42.70
- [x] **Scenario 12:** Strategy C Clean — LightGBM (boolean noise removed) — RMSE 44.50
- [x] **Scenario 13:** Gravity-Only — LightGBM (original features) — RMSE 43.46
- [x] **Scenario 14:** Gravity-Only Clean — XGBoost (boolean noise removed) — RMSE 42.10
- [x] **Scenario 15:** Gravity-Only Clean — LightGBM (boolean noise removed) — RMSE 44.50
- [x] **Scenario 16:** Flat-Only — LightGBM (original features) — RMSE 43.54
- [x] **Scenario 17:** Flat-Only Clean — XGBoost (boolean noise removed) — RMSE 42.50
- [x] **Scenario 18:** Flat-Only Clean — LightGBM (boolean noise removed) — RMSE 44.12

#### Round 4 — Random Forest for XAI (Pending)

- [x] **Scenario 19:** Gravity-Only — Random Forest (XAI focus) — RMSE 41.42
- [x] **Scenario 20:** Strategy C — Random Forest (XAI focus) — RMSE 41.76
- [x] **Scenario 21:** Flat-Only — Random Forest (XAI focus) — RMSE 41.44

#### Future Scenarios (Round 5)

- [x] Optuna tuning on best strategy (`strategyA_gravity_only`) for XGBoost, LightGBM, and Random Forest.
- [ ] Strategy C v2 — improved interaction features
- [x] Model Ensemble (Blending) — `ensemble.py` created (ready to run)

### `predict.py` (Re-run)

- [x] Generate updated predictions CSV.

## Phase 2: Budget Optimization

### `pipeline/optimizations/optimise_budget.py`

- [x] Implement greedy knapsack allocation for 5M LKR budget (Western Province only).
- [x] Distribute budget based on ROI composite scores with tier caps.
- [x] Assign Sri Lankan specific trade spend packages (Cooler Subsidy, Promotional Discount, etc.).
- [x] Output `bigbug_budget_allocations.csv`, `budget_diagnostics.csv` to `outputs/` and `budget_features.parquet` to `data/Optimization/`.
- [x] Generate `roi_distribution.png` (Frequency vs ROI Score).
- [x] Enforce Pareto principle rounding to 50 LKR multiples and strictly output Western province outlets.

## Round 2: Gap Filling Advanced Optimizations

### Feature Engineering (Gold Layer)

- [x] `pipeline/gold/build_cooler_features.py`: Generate physics-based cooler capacity ceiling features.
- [x] `pipeline/gold/build_spatial_cluster_features.py`: Use DBSCAN to generate micro-market clusters and density features.

### Statistical Modeling

- [x] `modelling/tobit_model.py`: Implement Tobit regression for censored demand.
- [x] `modelling/hurdle_model.py`: Implement Hurdle model for two-stage zero-inflated demand.

### Re-integration & Re-training

- [x] `pipeline/gold/build_master_features.py`: Re-merge Tobit, Hurdle, Cooler, and DBSCAN features into `master_features.parquet`.
- [x] `modelling/baseline.py`: Re-compute baseline using the new physics-based cooler capacity ceiling.
- [x] `modelling/train.py`: Re-train XGBoost, LightGBM, and Random Forest with the expanded feature set.
- [x] `modelling/ensemble.py`: Re-generate the 40/40/20 ensemble blending.
- [x] `modelling/predict.py`: Generate updated final submission predictions.
- [x] `pipeline/optimizations/optimise_budget.py`: Re-run budget optimization with the updated predictions.

## Phase 3: XAI Pipeline & Data Export

### `context_packager.py`

- [ ] Assemble outlet identity, prediction, SHAP drivers, and budget data into a JSON context string per outlet.
- [ ] Output `xai_context.parquet`.

### `prompt_builder.py`

- [ ] Render context payloads into structured LLM prompts.

### `export_for_webapp.py`

- [ ] Export parquets into JSON files (`outlets.json`, `budget_summary.json`) for Next.js.
- [ ] Coordinate payload structure with Next.js frontend.

## Phase 4: Pre-generation & Orchestrator

### `pregenerate_western.py`

- [ ] Iterate through Western Province outlets and query Gemini LLM.
- [ ] Output `xai_pregenerated.parquet`.

### `run_pipeline.py`

- [ ] Build orchestrator for Round 2 scripts with idempotency logic.
# WebApp Task List — Outlet Intelligence Dashboard

Track progress here. Check off each item as it is completed.
Work through phases in order — later phases depend on earlier ones.

---

## Pre-work (before writing any code)

- [ ] Read `webapp/API_SPEC.md` end to end
- [ ] Read `webapp/WEBAPP_COMPONENTS.md` end to end
- [ ] Skim `gold/GRAVITY_MODEL.md` (understand gravity scores for labels/tooltips)
- [ ] Skim `gold/SPEC_build_sales_features.md` (understand sales_history field meanings)
- [ ] Copy `sample_outlets.json` into `app/fixtures/`
- [ ] Set up `.env` from `.env.example` with `VITE_API_MODE=mock`

---

## Phase 1 — Scaffold & Static Layout (mock data, no API calls)

### Project setup
- [ ] Initialise Vite + React project under `app/`
- [ ] Install dependencies: Tailwind CSS, React Router v6, Recharts, React-Leaflet, Axios, Zustand, TanStack Table v8
- [ ] Configure Tailwind
- [ ] Set up React Router v6 with routes for `/outlets`, `/map`, `/outlets/:id`, `/budget`, `/pipeline`
- [ ] Confirm `npm run dev` starts cleanly on `http://localhost:5173`

### Layout shell
- [ ] Build `Sidebar.jsx` with navigation links to all 5 routes
- [ ] Build `TopBar.jsx`
- [ ] Active route highlighted with left border accent in sidebar
- [ ] Sidebar collapses to hamburger on < 1024px

### Shared components
- [ ] `Badge.jsx` — province (blue/teal/amber/coral), tier (blue/teal/gray), outlet_type
- [ ] `StatCard.jsx` — label, value, unit, delta, deltaDirection
- [ ] `LoadingSkeleton.jsx` — pulsing rectangle, configurable width/height
- [ ] `ErrorBanner.jsx` — generic error message with optional retry button

### View 1 — Outlet Explorer (static)
- [ ] Filter bar: Province, Distributor, Type dropdowns + Search input (hardcoded options, no API)
- [ ] Table with columns: Outlet ID, Type/Size, Potential (L), Gap (L), Footfall Score
- [ ] Populate table rows from `sample_outlets.json` (hardcoded, no API call yet)
- [ ] Clicking a row navigates to `/outlets/:id`
- [ ] Pagination controls rendered (static, no logic yet)
- [ ] Potential and Gap values formatted with thousand separators + "L" suffix

### View 2 — Map View (static)
- [ ] Leaflet map centred on Sri Lanka (`lat: 7.8731, lng: 80.7718`, zoom 8)
- [ ] `<CircleMarker>` for each outlet from `sample_outlets.json`
- [ ] Marker colour encodes province (matches badge palette)
- [ ] Marker radius encodes `predicted_potential_litres` (4px–14px scaled)
- [ ] Popup on click: Outlet ID, Type, Size, Predicted Potential, "View details →" link

### View 3 — Outlet Detail (static shell)
- [ ] Header: Outlet ID, type, size, province, distributor
- [ ] Prediction section: potential, current avg, gap, seasonality, trading days
- [ ] `ShapWaterfall.jsx` — horizontal bar chart with hardcoded SHAP data from `sample_outlets.json`
  - [ ] Positive SHAP → blue bars right
  - [ ] Negative SHAP → amber bars left
  - [ ] Top 5 contributors only
  - [ ] Tooltip with feature label and value
- [ ] AI Explanation panel — "Generate explanation ▶" button (no API call yet, show placeholder text on click)
- [ ] POI Context section — gravity scores with emoji icons
- [ ] Budget Allocation section — allocation_lkr, tier, ROI score, spend type (null-safe)
- [ ] "Outlet not found" fallback page with back button

---

## Phase 2 — Wire up API (mock server running)

### API layer
- [ ] `api/client.js` — Axios instance with `VITE_API_BASE_URL` as baseURL
- [ ] Mock adapter: when `VITE_API_MODE=mock`, intercept calls and return data from `sample_outlets.json`
- [ ] `api/outlets.js` — `getOutlets(params)` and `getOutletById(id)`
- [ ] `api/explain.js` — `getExplanation(id)`
- [ ] `api/budget.js` — `getBudgetSummary(params)`
- [ ] `api/pipeline.js` — `getPipelineHealth()`

### Zustand store
- [ ] `store/useFilters.js` — province, distributor, outlet_type, outlet_size filter state
- [ ] Filter state shared between Explorer and Map views

### View 1 — Outlet Explorer (live)
- [ ] Replace hardcoded rows with `GET /outlets` API call
- [ ] Filters update query params and re-fetch
- [ ] Server-side sorting via `sort_by` + `sort_dir` params (clicking column headers)
- [ ] Pagination: `page` param updates on Prev/Next; display "Showing X–Y of Z"
- [ ] TanStack Table virtualisation active (do not render all rows to DOM)
- [ ] Loading skeleton while fetching

### View 2 — Map View (live)
- [ ] Fetch outlets in batches of 1000 via paginated `GET /outlets` calls
- [ ] Add markers progressively as each batch loads
- [ ] Progress bar while loading all batches
- [ ] Active filters from Zustand store applied to map markers

### View 3 — Outlet Detail (live)
- [ ] Replace hardcoded data with `GET /outlets/:id`
- [ ] Handle 404 — show "Outlet not found" page
- [ ] Handle network error — show `ErrorBanner` with retry

### View 4 — Budget Dashboard
- [ ] Banner: "Western Province only — January 2026"
- [ ] `BudgetDonut.jsx` — Recharts `PieChart` with 60% inner radius, tier legend below
  - [ ] High: `#2563eb`, Medium: `#0d9488`, Low: `#9ca3af`
- [ ] Distributor split horizontal bar chart
- [ ] Outlet type split horizontal bar chart
- [ ] Projected volume uplift stat card
- [ ] Top 20 outlets table (Western, sorted by `budget_allocation_lkr` desc)
- [ ] Distributor + tier filter dropdowns update `GET /budget/summary` params and re-render

### View 5 — Pipeline Health
- [ ] Dataset summary table: name, checked, passed, quarantined, rate
- [ ] Pass rate icon: ≥ 99% → ✅, 95–99% → ⚠️, < 95% → ❌
- [ ] Per-check accordion (collapsed by default, expand on click)
- [ ] "Corrected (not quarantined)" column shown when `corrected` field is non-zero

---

## Phase 3 — Real backend + XAI (backend team hands off)

- [ ] Receive real backend URL from backend team
- [ ] Set `VITE_API_MODE=real` and `VITE_API_BASE_URL` in `.env`
- [ ] Smoke-test all 5 views against real backend
- [ ] Fix any shape mismatches between mock and real responses

### XAI panel (Outlet Detail)
- [ ] "Generate explanation ▶" button triggers `GET /explain/:id`
- [ ] Loading skeleton shown with "Generating business insight…" while awaiting (5–10s)
- [ ] On response: fade-in animation for text content
- [ ] `headline` rendered in larger font weight above driver lists
- [ ] `drivers_up` rendered with ✅ icon (green)
- [ ] `drivers_down` rendered with ⚠️ icon (amber)
- [ ] `local_context` paragraph below driver lists
- [ ] `recommendation` paragraph at bottom
- [ ] Collapsed "Model transparency" section: `prompt_tokens_used` + `completion_tokens_used`
- [ ] 503 error → "Explanation service is temporarily unavailable. Try again." + retry button

### SHAP chart (live data)
- [ ] `ShapWaterfall.jsx` now reads real SHAP data from `GET /outlets/:id`
- [ ] Verify sort order: top 3 positive + top 2 negative displayed correctly

---

## Phase 4 — Polish & submission prep

- [ ] Loading skeletons on every async section across all views
- [ ] Error states (404, 503, network) on all API calls
- [ ] Responsive layout: sidebar → hamburger on < 1024px
- [ ] Numbers formatted consistently: thousand separators, 2 decimal places, "L" / "LKR" suffixes
- [ ] Page titles set correctly for each route (browser tab)
- [ ] Write `app/README.md` with setup instructions (`npm install && npm run dev`)
- [ ] End-to-end walkthrough: start mock server → open all 5 views → verify no console errors
- [ ] End-to-end walkthrough: switch to real backend → repeat above

---

## Definition of done

The app is submission-ready when:
- `npm install && npm run dev` works with zero manual steps
- All 5 views render correctly against the mock server
- All 5 views render correctly against the real backend
- No console errors in any view
- XAI panel works end-to-end (button → loading → result)
- Budget Dashboard correctly scopes to Western Province only
- Map renders outlet markers for all loaded outlets

