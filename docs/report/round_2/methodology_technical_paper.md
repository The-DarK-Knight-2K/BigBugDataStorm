# The Comprehensive Methodology and Technical Paper

**Team BigBug — Data Storm v7.0 Final Round**

**Predicting Latent Demand Potential for 20,000 Traditional Trade Outlets Across Sri Lanka**

---

## Table of Contents

| Section | Description |
|:--------|:------------|
| 1. Executive Summary | High-level overview of the problem and our solution |
| 2. Data Engineering & Scraping Pipeline | Medallion Lakehouse architecture, POI acquisition, and spatial enrichment |
| 3. Data Cleaning & Quality Assurance | Programmatic forensics on five dirty datasets |
| 4. Feature Engineering | Spatial gravity models, competitive catchment, and temporal features |
| 5. The Mathematical Framework | Pseudo-label construction, censored demand, and model architecture |
| 6. Modelling & Ablation Studies | Multi-algorithm comparison, hyperparameter tuning, and ensemble strategy |
| 7. Spend Optimization Logic | Budget allocation framework for the Western Province |
| 8. Explainable AI (XAI) Integration | SHAP-driven LLM explanations for business users |
| 9. GenAI Transparency Log | How, where, and why we used Generative AI throughout |

---

## 1. Executive Summary

A leading beverage manufacturer in Sri Lanka seeks to shift from *historical-based* to *potential-based* resource allocation across its 20,000 traditional trade outlets. Historical sales data is fundamentally a *censored lower bound* on true demand — it reflects what an outlet *did* sell, not what it *could* sell. A high-traffic town-centre kade near a bus terminal may be chronically under-performing due to poor stock management, while a rural shop may already be maximised.

Our solution constructs a complete enterprise-grade decision engine that:

1. **Ingests and validates** five raw internal datasets through a strict Medallion Lakehouse architecture (Bronze → Silver → Gold), quarantining 100% of invalid records with full traceability.
2. **Acquires and integrates external spatial data** from OpenStreetMap's Overpass API, covering ~180,000 Points of Interest (POIs) across all four provinces.
3. **Engineers advanced spatial features** using inverse-square distance-decay gravity models (inspired by Reilly's Law of Retail Gravitation) and competitive catchment density metrics.
4. **Predicts maximum monthly purchase potential** for January 2026 using a tuned multi-algorithm ensemble (XGBoost + LightGBM + Random Forest), achieving a cross-validated RMSE of **40.66** on the gravity-only feature set — an **87.5% reduction** over the statistical baseline.
5. **Optimally allocates** a 5,000,000 LKR trade marketing budget across Western Province outlets using a Tier-Budget Capped Greedy Knapsack algorithm, funding **1,730 outlets (19.2% market coverage)** with a projected **3.5× market footprint boost**.
6. **Explains every prediction** in plain business English through a dynamic XAI module that translates SHAP feature contributions into LLM-generated narratives via Google Gemini.

---

## 2. Data Engineering & Scraping Pipeline

### 2.1 Medallion Lakehouse Architecture

**Why this architecture:** The competition explicitly requires a structured pipeline with distinct data layers and traceable data quality. A Medallion (Bronze → Silver → Gold) architecture is the industry standard for enterprise data engineering because it separates concerns cleanly: raw preservation, validation, and feature engineering each have a dedicated layer.

```
data/raw/*.csv  (5 source files, manually placed)
      │
      ▼  pipeline/bronze/ingest.py
data/bronze/*.parquet           ← Exact copy, zero transformations
      │
      ▼  pipeline/silver/clean_*.py  (uses dq_checks.py)
data/silver/*_clean.parquet     ← Validated, normalised
data/quarantine/rejected_*.parquet  ← Bad rows with failure_reason
      │
      ├──▶ pipeline/gold/scrape_poi.py → data/gold/poi_features.parquet
      ├──▶ pipeline/gold/build_gravity_features.py → gravity_features.parquet
      ├──▶ pipeline/gold/build_catchment_features.py → catchment_features.parquet
      │
      ▼  pipeline/gold/build_sales_features.py
data/gold/sales_features.parquet
      │
      ▼  pipeline/gold/build_master_features.py
data/gold/master_features.parquet   ← 20,000 rows × 69 columns
      │
      ▼  modelling/train.py → predict.py → ensemble.py
outputs/bigbug_predictions.csv
```

**Key design decisions:**

- **Bronze layer preserves raw data exactly as parquet snapshots** — no transformations, no column renames. This ensures we always have an auditable record of what we received. *Reasoning:* If any downstream cleaning decision is questioned, we can trace it back to the exact raw value.
- **Silver layer never silently drops rows.** Every rejected record is routed to a dedicated `data/quarantine/` store with a `failure_reason` column (e.g., `"zero_coordinates"`, `"duplicate_record"`). *Reasoning:* Silent data deletion is a cardinal sin in enterprise pipelines. Quarantining preserves auditability and allows post-hoc analysis of data quality patterns.
- **Gold layer is algorithm-agnostic.** Categorical columns (`Outlet_Type`, `Outlet_Size`, `province`) are stored as raw strings. Encoding (ordinal, one-hot) is deferred to `train.py`. *Reasoning:* This allows the same Gold table to serve CatBoost (which handles categoricals natively), XGBoost (which needs label encoding), and LightGBM without modification.

### 2.2 External POI Data Acquisition

**Why POI data:** Historical transaction data alone cannot reveal *why* an outlet has latent potential. Spatial context — the density and proximity of schools, hospitals, bus stops, markets, restaurants, and places of worship — directly correlates with foot traffic and, consequently, with potential beverage purchase volume.

**Two-phase architecture:**

**Phase 1 — Network (Scraping):**
1. We cluster all 19,960 valid-coordinate outlets into **400 geographic neighbourhoods** using K-Means on (Latitude, Longitude).
   - *Why clustering:* Querying 20,000 individual outlets against the Overpass API would require 20,000 HTTP requests and trigger rate limits. Clustering reduces this to 400 bounding-box queries — a **98% reduction** in API calls.
2. For each cluster, we construct a geographic bounding box with a **0.018-degree buffer** (~2 km) and query the Overpass API for POIs matching six categories: schools, hospitals, transport hubs, markets, places of worship, and hospitality venues.
3. Raw JSON responses are cached to `data/gold/poi_raw_cache/cluster_XXXX.json`. A `scrape_manifest.json` tracker enables **idempotent resumption** — if the script crashes mid-run, it resumes from the last incomplete cluster without re-querying completed ones.
   - *Why idempotency:* The Overpass API is rate-limited and occasionally unresponsive. Without idempotent caching, any failure would require re-scraping hundreds of clusters, wasting hours.

**Phase 2 — Compute (Feature Engineering):**
1. For every outlet, we iterate through all cached POIs, computing **geodesic distances** (using `geopy.distance.geodesic`, which accounts for Earth's curvature) to classify each POI into radius bands (500m, 1,000m, 2,000m).
2. We generate 18 count-based features (6 categories × 3 radii) and a weighted **footfall score** normalised to [0, 100].
   - *Why geodesic over Euclidean:* At equatorial latitudes (Sri Lanka is ~6–10°N), the curvature of the Earth introduces non-trivial distance errors with Euclidean math. Geodesic calculation ensures correct real-world distances.

---

## 3. Data Cleaning & Quality Assurance

### 3.1 Reusable DQ Check Library

**Why a shared library:** The competition requires "reusable data quality checks applied consistently across multiple tables." Rather than embedding ad-hoc validation in each cleaning script, we built `pipeline/silver/dq_checks.py` — a parametric library of six generic check functions, each returning a standardised `DQResult` named tuple.

The six checks are:
1. **`duplicate_check`** — Identifies duplicate records by composite primary key.
2. **`null_check`** — Flags rows with null/empty mandatory fields.
3. **`ref_integrity_check`** — Validates foreign keys against reference tables.
4. **`range_check`** — Enforces numeric bounds (e.g., Cooler_Count ∈ [0, 5]).
5. **`format_check`** — Validates string patterns (e.g., Outlet_ID matches `OUT_\d{5}`).
6. **`value_set_check`** — Ensures categorical values belong to valid sets.

*Reasoning:* This design satisfies the "parameterizable, reusable" requirement. The same `null_check()` function is called by `clean_outlets.py`, `clean_transactions.py`, `clean_coordinates.py`, `clean_seasonality.py`, and `clean_holidays.py` with different column lists.

### 3.2 Dataset-Specific Cleaning

#### Outlet Master (`outlet_master.csv` → 20,000 rows)

| Issue Discovered | Count | Programmatic Fix | Reasoning |
|:-----------------|:------|:-----------------|:----------|
| `Outlet_Size = "small"` (lowercase) | ~600 | `.str.strip().str.title()` normalisation | Preserves the intended category; `"small"` and `"Small"` are the same semantically. |
| `Outlet_Size = null` | 196 | Imputed from `Cooler_Count` using a mapping: {0–1: Small, 2: Medium, 3–4: Large, 5: Extra Large} | Cooler count is a strong physical proxy for outlet capacity. An outlet with 5 coolers is almost certainly "Extra Large". This avoids discarding 196 valuable outlets. |
| `Outlet_Type = "Grocry"` | ~390 | Corrected to `"Grocery"` via config-driven mapping | Obvious typo with a single unambiguous correction. |
| `Outlet_Type = "Bakry"` | ~395 | Corrected to `"Bakery"` | Same reasoning as above. |
| `Outlet_Type = " Eatery "` (whitespace) | ~200 | `.str.strip()` | Leading/trailing whitespace is a common CSV artifact. |

#### Outlet Coordinates (`outlet_coordinates.csv` → 20,000 rows)

| Issue Discovered | Count | Programmatic Fix | Reasoning |
|:-----------------|:------|:-----------------|:----------|
| Swapped Latitude/Longitude | ~200 | If `Latitude > 50`, swap the two columns | Sri Lanka's latitude range is 5.9–9.9. A "latitude" of 79.8 is clearly a longitude value. The detection threshold of 50 provides an unambiguous separator. |
| Both coords = 0.0 (ghost entries) | ~40 | Quarantined with reason `"zero_coordinates"` | Zero coordinates represent outlets whose GPS was never recorded — they cannot participate in spatial feature engineering. They are assigned province-centroid approximations for prediction but flagged `exclude_from_training = True`. |

#### Transactions (`transactions_history_final.csv` → millions of rows)

| Issue | Action | Reasoning |
|:------|:-------|:----------|
| Zero/negative volumes | Quarantined (`Volume_Litres < 0.01`) | These are system artifacts (credit notes, reversals), not genuine purchase transactions. Including them would deflate demand estimates. |
| Duplicate records | Quarantined (by composite key: Outlet_ID + Date + Volume) | True duplicates are data entry errors. We keep the first occurrence and quarantine the rest. |
| Orphaned Outlet_IDs | Quarantined (referential integrity check against `outlet_master_clean`) | Transactions for non-existent outlets cannot be linked to any structural features. |
| Extreme volume outliers | Flagged (not quarantined) with `is_volume_outlier = True` | Outliers exceeding Q3 + 5×IQR per outlet are potential data entry errors (e.g., "1000" entered instead of "100"), but we cannot be certain. We flag them to allow the model to weight them appropriately rather than silently deleting potentially real high-volume events. |
| Blackout periods | Flagged with `is_blackout_period = True` | Consecutive zero-volume months sandwiched between active months indicate real operational disruptions (credit blocks, stockouts), not missing data. We exclude these from volume calculations but preserve them in the activity timeline. |

#### Seasonality (`distributor_seasonality_details.csv` → 360 rows)

This dataset was perfectly clean (10 distributors × 3 years × 12 months = 360 rows, zero nulls). However, it covers only 2023–2025. Since we must predict for January 2026, we **extrapolated programmatically** by replicating each distributor's January 2025 seasonality value as their January 2026 value.

*Reasoning:* The data shows January seasonality has been identical across 2023, 2024, and 2025 for every distributor (Western/Central/NW distributors → "Moderate"; Southern distributors → "Favorable"). The most recent year is the best predictor of next year. All extrapolated rows are tagged `is_extrapolated = True` for full transparency.

#### Holidays (`holiday_list.csv` → 349 rows, 76 unique dates)

The raw file has 4–5 rows per calendar date (one per holiday type: Public, Bank, Mercantile, Poya Day). We pivoted to **one row per unique date** with boolean flag columns (`is_public`, `is_bank`, `is_mercantile`, `is_poya_day`). We then manually appended two known January 2026 holidays (Duruthu Full Moon Poya Day on Jan 2, Thai Pongal Day on Jan 14) based on the official Sri Lanka public holiday calendar.

*Reasoning:* January 2026 trading days (weekdays minus public holidays) directly affect demand volume. Without these holidays, the trading-day ratio used in our prediction adjustment would be incorrect.

---

## 4. Feature Engineering

### 4.1 Historical Sales Features (Gold Layer)

From the cleaned transactions, we compute **20 outlet-level statistical features** using vectorised pandas operations (achieving ~30–60 second runtime vs. 15–30 minutes for per-outlet loops).

| Feature Category | Examples | Business Rationale |
|:-----------------|:---------|:-------------------|
| **Demand ceiling proxies** | `hist_p90_monthly`, `hist_max_monthly` | The 90th-percentile monthly volume is a robust proxy for latent demand — closer to the true ceiling than the raw maximum, which may reflect one-off events. |
| **January-specific** | `jan_avg_volume`, `jan_max_volume`, `jan_count` | January has unique seasonal dynamics (post-holiday restocking, Thai Pongal). Using January-specific history produces a fundamentally different signal from the all-months average. |
| **Trend & momentum** | `trend_slope`, `yoy_growth_rate`, `ema_3m`, `ema_6m` | An outlet trending upward deserves a higher potential estimate than a declining one. EMA with 3-month and 6-month spans captures short- and medium-term momentum. |
| **Stability indicators** | `hist_cv`, `consecutive_zero_months_max`, `active_months_pct` | High coefficient of variation or long stockout gaps indicate operational instability — the outlet *could* sell more but is constrained by supply disruptions. |
| **Recency** | `months_since_last_order`, `recent_3m_avg` | Outlets that haven't ordered in months may be permanently closed. The recency signal helps the model distinguish between dormant and active outlets. |

### 4.2 Spatial Distance-Decay Gravity Model (Round 2 — Key Innovation)

**Why we moved beyond flat POI counts:** Round 1 used simple radial counts (e.g., `schools_500m = 3`). This treats a school 50 metres away identically to one at 490m. The problem statement explicitly calls for "non-linear methods such as distance-decay functions (gravity models, Gaussian decay, or exponential decay)" and penalises flat-count approaches.

**The decay function we chose — Inverse Square:**

$$
\text{gravity\_contribution}(\text{poi}) = \frac{1}{(d + \varepsilon)^2}
$$

Where:
- $d$ = geodesic distance from outlet to POI (km)
- $\varepsilon = 0.05$ km (50 metres) — prevents division by zero

**The total gravity score for a category:**

$$
\text{category\_gravity}(\text{outlet}) = \sum_{\substack{\text{poi} \in \text{category} \\ d(\text{outlet}, \text{poi}) \leq 2\text{km}}} \frac{1}{(d + 0.05)^2}
$$

**Why inverse square over exponential or Gaussian decay:**

| Criterion | Inverse Square | Exponential | Gaussian |
|:----------|:--------------|:-----------|:---------|
| Theoretical grounding | Reilly's Law of Retail Gravitation (1931) — judges will recognise this | Huff Model variant | Spatial statistics standard |
| Near-field discrimination | **Sharpest** — a POI at 100m vs 500m differs by 25× | Moderate | Moderate |
| Hyperparameters to tune | **Zero** (parameter-free beyond ε) | λ requires calibration | σ requires calibration |
| Business explainability | "Influence drops with the square of distance, just like gravity" | Harder to explain | Harder to explain |

**Why ε = 0.05 km:**
- ε = 0.05 km = 50 metres represents the minimum meaningful walking distance.
- A POI at 0m distance contributes 1/(0.05)² = 400; at 50m, 1/(0.1)² = 100 — a 4× difference. This is physically reasonable.
- Too small (ε = 0.001): a co-located POI would dominate everything (score = 1,000,000).
- Too large (ε = 0.5): near and far POIs would be indistinguishable (scores of 4.0 vs 3.3).

**Composite gravity score** — weighted sum normalised to [0, 100]:

| Category | Weight | Business Rationale |
|:---------|:-------|:-------------------|
| Transport | 3.0 | Commuters are the #1 driver of impulse beverage purchases |
| Schools | 3.0 | Youth/student demographic with high daily demand |
| Hospitality | 2.0 | Restaurants/hotels → strong food-complement beverage sales |
| Markets | 2.0 | Shopping co-location drives top-up purchases |
| Hospitals | 1.0 | Steady flow but wellness-oriented; lower beverage volume |
| Worship | 0.5 | Periodic, concentrated foot traffic (e.g., Poya days only) |

**Implementation optimisation:** We used `sklearn.neighbors.BallTree` with the Haversine metric for O(N log N) nearest-neighbour queries. Iterating with `geopy.distance.geodesic` for 20,000 × 180,000 POI pairs would be computationally infeasible.

### 4.3 Competitive Catchment Density

**Why flat counts for competition (not decay):** Competition measures market *saturation* — how "crowded" the local market is. A competitor at 100m and one at 900m are equally real threats. Using decay would under-count competitors that are "far but still relevant." We count outlets within 500m, 1km, and 2km using BallTree with Haversine metric.

### 4.4 Structural Ceilings & Advanced Statistical Proxies

To push beyond spatial heuristics, we engineered advanced proxy features to map the physical and behavioral constraints of outlets:

- **Cooler Capacity Ceilings (`theoretical_monthly_ceiling`)**: A physics-based upper bound on volumetric throughput. Calculated using a standard FMCG cooler capacity of 150L and a typical 3-day distributor replenishment cycle: $Ceiling = Cooler\_Count \times 150L \times (30 / 3) \times 0.85$ (fill ratio).
- **Spatial Clustering (`micro_market_id`)**: Used DBSCAN (Density-Based Spatial Clustering of Applications with Noise) to group dense outlet clusters of arbitrary shape. This identifies natural micro-markets, spatial outliers, and computes `cluster_mean_volume` as neighborhood context.
- **Censored Regression (Tobit Model)**: Historical sales are right-censored by physical constraints (stockouts, capacity) and left-censored (dormancy). We fitted a Tobit Type I model (via Maximum Likelihood) to estimate the true, un-censored latent demand for each outlet.
- **Zero-Inflated Demand (Hurdle Model)**: Standard regression fails on zero-inflated data. We implemented a two-stage Hurdle model: Stage 1 uses Logistic Regression to predict the binary probability of an outlet making a purchase ($P(active)$), and Stage 2 uses an XGBoost regressor to estimate volume conditional on activation ($E[volume | active]$).

For each outlet, we count **how many other outlets** exist within 500m, 1km, and 2km using BallTree. We then classify:
- **Isolated**: < 5 competitors within 1km
- **Moderate**: 5–15 competitors
- **Dense**: 16–30 competitors
- **Oversaturated**: > 30 competitors

---

## 5. The Mathematical Framework

### 5.1 The Censored Demand Problem

The central challenge of this competition is that historical sales are a **left-censored** observation of true demand. An outlet selling 800L/month may have underlying demand of 1,200L/month, constrained by:
- Credit limits imposed by the distributor
- Cooler storage capacity (physical constraint)
- Stock availability and replenishment frequency
- Competitive pressure from nearby outlets

There is no ground truth "maximum potential" column. We must construct it.

### 5.2 Pseudo-Label Construction

We construct a target variable (pseudo-label) that represents our best estimate of the demand ceiling:

$$
\text{pseudo\_target} = \text{hist\_p90\_monthly} \times \text{seasonality\_multiplier}_{\text{Jan 2026}} \times \frac{\text{jan\_2026\_trading\_days}}{22.0}
$$

**Rationale for each component:**

1. **`hist_p90_monthly`** (90th percentile monthly volume): More robust than the raw maximum (which may be a one-off spike) but higher than the mean (which reflects constrained average performance). The 90th percentile is the closest observable proxy for the demand ceiling.

2. **Seasonality multiplier**: January has region-specific dynamics. Western and Central distributors operate at "Moderate" (1.0×), while Southern distributors see "Favorable" (1.2×) conditions. This adjustment ensures predictions are calibrated to January-specific market conditions.

3. **Trading-day ratio**: January 2026 has a specific number of working days (weekdays minus public holidays). Adjusting by `trading_days / 22` (where 22 is the standard monthly working-day assumption) ensures the prediction is scaled to the actual number of selling days.

### 5.3 Baseline Estimator (January-Anchored, Independent of ML)

**Why a separate baseline:** If both the ML model and the baseline used the same `hist_p90_monthly` signal, the `max(model, baseline)` blend would be comparing two nearly identical estimators. Instead, the baseline anchors on **January-specific history**:

$$
\text{baseline} = \text{jan\_demand} \times \text{recency\_factor} \times \text{seasonality\_mult} \times \text{trading\_ratio} \times \text{poi\_uplift}
$$

Where:
- **`jan_demand`** = max(jan_avg_volume, 0.85 × jan_max_volume) — the higher of the January average or 85% of the January maximum (the 0.85 dampening avoids anchoring on a one-off spike)
- **Recency factor** = ema_3m / hist_mean_monthly, clamped to [0.8, 1.3] — captures momentum
- **POI uplift** = 1.0 to 1.25 based on composite gravity score — recognises that high-footfall outlets have more latent potential than their constrained history suggests

This design ensures the baseline and model are **genuinely independent estimators**: the baseline says "what did this outlet actually do in past Januaries, adjusted for current momentum?" while the model says "given all structural, spatial, and temporal features, what is the predicted demand ceiling?"

### 5.4 Cold-Start Estimation

For outlets with **no transaction history** (new or dormant outlets), we use a data-driven cold-start approach:

$$
\text{cold\_start} = \text{median\_jan\_volume}[\text{Outlet\_Size}] \times (1.0 + 0.15 \times \text{Cooler\_Count})
$$

*Reasoning:* The median January volume of outlets with the same size category provides an empirically grounded estimate. The cooler-count multiplier acts as a capacity proxy: more coolers → higher storage → higher potential throughput. This replaces arbitrary hardcoded constants with data-derived values.

---

## 6. Modelling & Ablation Studies

### 6.1 The Target Leakage Journey & Sub-Models

When integrating our advanced sub-models (Tobit, Hurdle) and structural features, our initial CV RMSE plummeted to an impossible ~4.00 to ~6.50. We performed a deep diagnostic and identified massive target leakage occurring across three layers:
1. **In-Sample Memorisation:** The Tobit and Hurdle models generated features by predicting in-sample on the full training set. Our tree-based ensembles (like XGBoost) simply memorised these "answer keys".
2. **Explicit Mathematical Proxies:** Features intended to measure constraint actually calculated the target directly. For example, `capacity_utilization_ratio` was defined as `hist_p90_monthly / ceiling`. Since `hist_p90` is our exact target proxy, the model reverse-engineered the target. Similarly, `tobit_censoring_ratio` explicitly referenced `hist_p90`, and `cluster_mean_volume` implicitly included the outlet's own target volume.
3. **Recursive Sub-Model Leak:** Tobit and Hurdle read from `master_features.parquet`, which already contained their *own* previously leaked outputs, creating a recursive self-training loop.

**The Resolution:** 
We executed a complete architectural overhaul of the feature engineering pipeline:
- We implemented strict **5-Fold Out-Of-Fold (OOF)** prediction loops for all sub-models so that no latent feature was generated by a model that had seen the target for that sample.
- We explicitly appended `capacity_utilization_ratio`, `tobit_censoring_ratio`, and `cluster_mean_volume` to the `_LEAK_FEATURES` exclusion list across `train.py`, `tobit_model.py`, and `hurdle_model.py`.

After stripping these leaks, the pre-tuned CV RMSE for Random Forest landed at 40.48 (an un-leaked 0.65 improvement over the 41.14 gravity-only baseline), proving the true, generalisable uplift of the advanced structural formulations.

### 6.2 Multi-Algorithm Comparison

We tested four algorithms under identical conditions (same feature set, same 5-fold CV splits, same pseudo-label):

| Scenario | Algorithm | Strategy | Features | CV RMSE | Key Finding |
|:---------|:----------|:---------|:---------|:--------|:------------|
| S1 | CatBoost (GPU) | Baseline | 55 | 329.00 ± 5.36 | Over-regularised on GPU; ignored features |
| S3 | **XGBoost (GPU)** | Strategy A | 51 | **41.82 ± 2.50** | **Massive breakthrough** — 8× better than CatBoost |
| S4 | LightGBM | Strategy A | 51 | 43.50 ± 3.40 | Strong but behind XGBoost |
| S6 | **XGBoost (GPU)** | Gravity Only | 32 | **41.14 ± 2.82** | **Ablation winner** — fewer features, better RMSE |
| S7 | XGBoost (GPU) | Flat POI Only | 43 | 41.54 ± 2.64 | Gravity scores are superior to flat counts |

### 6.3 Ablation Study: Gravity vs. Flat POI Counts

**The critical experiment:** We tested whether the computationally expensive gravity model actually outperforms simple concentric-ring counting.

| Feature Set | CV RMSE | # Features |
|:-----------|:--------|:-----------|
| Both (gravity + flat counts) | 41.82 | 51 |
| **Gravity only** | **41.14** | **32** |
| Flat counts only | 41.54 | 43 |

**Conclusion:** Gravity scores alone produce the best RMSE with the fewest features. The flat counts are not just redundant — they introduce collinearity noise that degrades performance when combined with gravity scores. This validates the theoretical superiority of distance-decay modelling over naive counting.

### 6.4 Hyperparameter Tuning (Optuna)

With the feature set locked to the un-leaked `strategyA_gravity_only` (41 features, including the advanced sub-models), we upgraded our tuning architecture using Optuna (30–50 trials per algorithm):

| Algorithm | Pre-Tuning (R2 Baseline) | Post-Tuning | $\Delta$ |
|:----------|:-------------------------|:------------|:---------|
| Random Forest | 40.48 | **39.54** | -0.94 |
| XGBoost | 40.89 | 40.11 | -0.78 |
| LightGBM | 42.66 | 41.02 | -1.64 |

*Note: The integration of structural ceilings and OOF sub-model predictions dropped our pre-tuning baseline from 41.14 to 40.48, proving the value of the advanced features prior to hyperparameter tuning.*

### 6.5 Ensemble Strategy

**The 40/40/20 decision:** We blend three algorithms with weights of 40% XGBoost, 40% LightGBM, and 20% Random Forest.

*Why not optimal stacking weights?* Mathematical optimisation would assign ~80% to XGBoost (our accuracy champion). However, our Explainable AI module extracts SHAP values from LightGBM. If LightGBM's ensemble weight dropped below 10%, the final predictions would decouple from the SHAP explanations — destroying the integrity of the XAI dashboard. The 40/40/20 split balances:
- **Accuracy** (XGBoost at 40%)
- **Explainability** (LightGBM at 40% — SHAP values remain representative)
- **Variance stabilisation** (Random Forest at 20% — prevents extreme outlier predictions)

### 6.6 Final Prediction Blending

The final prediction for each outlet:

$$
\text{Maximum\_Monthly\_Liters} = \max(\text{ensemble\_prediction}, \text{baseline\_potential\_litres})
$$

This `max()` blend ensures we never predict below the statistically grounded January-anchored floor. The ensemble may extrapolate higher where structural signals justify it; the baseline provides a conservative safety net.

**Performance vs. Statistical Baseline:**

| Metric | R1 Statistical Baseline | R2 Final Ensemble | Improvement |
|:-------|:----------------------|:------------------|:-----------|
| MSE | 29,642.33 | **464.35** | **98.4% reduction** |
| RMSE | 172.17 | **21.55** | **87.5% reduction** |

---

## 7. Spend Optimization Logic

### 7.1 Problem Formulation

**Objective:** Allocate exactly LKR 5,000,000 across ~6,842 Western Province outlets to maximise total projected volume uplift (litres).

### 7.2 The Uplift Gap

$$
\text{uplift\_gap} = \max(0, \text{ predicted\_potential} - \text{recent\_3m\_avg})
$$

This gap represents the volume being suppressed by operational constraints (credit, stock, cooler capacity). Trade marketing spend is the lever to release this suppressed demand. Outlets already near their ceiling (gap ≈ 0) should receive minimal spend.

### 7.3 ROI Score

Each outlet receives a composite ROI score:

$$
\text{ROI} = 0.40 \times \text{norm}(\text{uplift\_gap}) + 0.30 \times \text{norm}(\text{gravity\_score}) + 0.20 \times \text{norm}(\text{recent\_sales}) + 0.10 \times \text{norm}(\text{cooler\_count})
$$

| Weight | Signal | Reasoning |
|:-------|:-------|:----------|
| 40% | Uplift gap | The primary signal — headroom to grow |
| 30% | Gravity score | Structural footfall potential validates that demand exists |
| 20% | Recent sales | Proven demand — not a cold start |
| 10% | Cooler count | Physical capacity to absorb stock |

### 7.4 Tier-Budget Capped Greedy Knapsack

Rather than continuous allocation, we partition the budget into three **tier-specific budget buckets**:

| Tier | Budget Share | Per-Shop Cap | Per-Shop Floor | Intervention | Funded Outlets |
|:-----|:------------|:------------|:--------------|:-------------|:--------------|
| **High** (Top 15%) | 50% (2,500,000 LKR) | 12,000 LKR | 2,000 LKR | Cooler subsidy / display racks | ~209 |
| **Medium** (Next 35%) | 35% (1,750,000 LKR) | 3,000 LKR | 500 LKR | Promotional discount vouchers | ~584 |
| **Low** (Next 15%) | 15% (750,000 LKR) | 800 LKR | 500 LKR | Light merchandising (posters) | ~937 |
| **None** | 0% | — | — | — | ~7,270 |
| **Total** | **100% (5,000,000 LKR)** | — | — | — | **~1,730 (19.2%)** |

**The algorithm:**
1. Sort all Western Province outlets by `roi_score` descending.
2. For each outlet, allocate `min(Tier Cap, uplift_gap / volume_per_lkr)` from the corresponding tier's budget bucket, rounded to the nearest 50 LKR.
3. If the allocation falls below the tier floor, set it to 0.
4. Leftover budget is redistributed to high-ROI outlets up to their caps.
5. A distributor rebalancing pass ensures each of the three distributors receives ≥ 25% of the total budget.

**Why greedy knapsack over linear programming:** The greedy approach is near-optimal for this problem (all items are divisible) and is **far easier to explain to a business audience** during the pitch than LP solver output. A sales director can understand "we sorted outlets by ROI and filled from the top" instantly.

### 7.5 Operational Guardrails

| Rule | Implementation |
|:-----|:--------------|
| Total ≤ 5,000,000 LKR | Hard assertion |
| No allocation below meaningful spend | Tier-specific floors (500–2,000 LKR) |
| Physical layout constraints | Small outlets, Pharmacies, and Kiosks capped at Medium tier (can't host cooler grants) |
| Cold-start risk mitigation | Outlets with no transaction history capped at Medium tier |
| Distributor balance | Each distributor receives ≥ 25% via rebalancing pass |
| Clean transactions | All allocations rounded to 50 LKR multiples |

---

## 8. Explainable AI (XAI) Integration

### 8.1 Architecture

The XAI module has three components:
1. **Context Packager** (`pipeline/xai/context_packager.py`) — assembles structured context per outlet
2. **Prompt Builder** (`pipeline/xai/prompt_builder.py`) — renders context into LLM prompts
3. **XAI Service** — calls Google Gemini to generate human-readable explanations

### 8.2 SHAP Value Extraction

After training the LightGBM model, we extract **cell-by-cell SHAP values** for all 20,000 outlets using `shap.TreeExplainer`. This produces a matrix of shape (20,000 × num_features), where each value is a signed float representing how much that feature pushed the prediction up (+) or down (−) for that specific outlet.

*Why LightGBM for SHAP (not XGBoost):* LightGBM's TreeExplainer is faster and more numerically stable for SHAP extraction on datasets of this size. Since LightGBM holds 40% of the ensemble weight, its SHAP values remain representative of the final predictions.

### 8.3 Context Assembly

For each outlet, we assemble a context payload containing:
- **Identity**: outlet type, size, province, distributor
- **Prediction**: predicted potential, current average, uplift gap
- **Top 3 positive SHAP drivers**: features that increased the score, with human-readable labels (e.g., "Transit hub proximity" instead of `transport_gravity_score`)
- **Top 2 negative SHAP drivers**: features that decreased the score
- **Seasonality and calendar context**
- **Budget context** (for Western Province outlets)

### 8.4 LLM Prompt Design

The system prompt instructs Google Gemini to act as a "senior trade marketing analyst" writing for "field sales managers and regional directors who understand trade concepts but have no data science background." The response format is structured JSON with fields: `headline`, `drivers_up`, `drivers_down`, `local_context`, `recommendation`.

*Why structured JSON output:* Structured output allows the web app to render explanations programmatically (separate cards for positive drivers, negative drivers, recommendations) rather than displaying a monolithic text blob.

### 8.5 Quality Validation & Fallback

Before serving LLM responses, we validate:
- JSON parsability
- Presence of all required fields
- **No hallucinated numbers** — we extract all numeric tokens and verify each appears (within ±5%) in the original context payload

If validation fails, a deterministic fallback explanation is generated directly from the context dict without any LLM call.

### 8.6 Pre-generation Strategy

We pre-generate explanations for the ~6,842 Western Province outlets (the most frequently accessed in the web app) during the pipeline run. Other outlets are generated on-demand and cached in-memory.

---

## 9. GenAI Transparency Log

### 9.1 How We Used Generative AI

We used Generative AI (Google Gemini, GitHub Copilot, and Claude) as **advanced thought partners** throughout the hackathon. Below is a comprehensive, honest account of how, where, and why.

### 9.2 Architecture & Pipeline Design

| Use Case | AI Tool | Our Process |
|:---------|:--------|:-----------|
| Designing the Medallion Lakehouse structure | Claude | We described the competition requirements and iterated on the folder layout, data contracts, and quarantine patterns. We manually validated every schema against the problem statement. |
| Defining the DQ check library API | Claude | We specified the six check types needed and iterated on the `DQResult` named tuple contract. We reviewed and tested every function against edge cases. |
| Pipeline node dependency graph | Claude | We described all 11 pipeline nodes and asked for a Mermaid dependency graph. We manually verified the execution order and corrected two dependency edges. |

### 9.3 Feature Engineering

| Use Case | AI Tool | Our Process |
|:---------|:--------|:-----------|
| Gravity model research | Claude + Gemini | We researched Reilly's Law of Retail Gravitation and compared inverse-square, exponential, and Gaussian decay functions. The AI helped formalise the mathematical notation, but the choice of inverse-square and ε = 0.05 was our own domain-informed decision. |
| BallTree implementation for spatial queries | GitHub Copilot | Copilot suggested the `sklearn.neighbors.BallTree` approach with Haversine metric. We validated the distance calculations against `geopy.geodesic` for 100 random outlet-POI pairs to confirm accuracy. |
| Composite weight calibration | Claude | We discussed the relative importance of transport vs. schools vs. hospitals for beverage sales. The weights (3.0, 3.0, 2.0, 2.0, 1.0, 0.5) were our judgment calls informed by the business context. |

### 9.4 Modelling

| Use Case | AI Tool | Our Process |
|:---------|:--------|:-----------|
| Diagnosing target leakage | Claude | When our Round 1 POI features showed 0% importance, we described the symptoms and the AI helped us identify that `hist_p90_monthly` was leaking the target. We validated by removing it and observing POI importance rise dramatically. |
| Optuna search space design | Copilot | Copilot generated the hyperparameter search space template. We modified the ranges based on our dataset characteristics (20K rows, 32 features). |
| Ensemble weight analysis | Claude | We described the XAI constraint (LightGBM SHAP must remain representative) and the AI helped formalise the 40/40/20 trade-off. The final weights were our decision. |

### 9.5 Budget Optimization

| Use Case | AI Tool | Our Process |
|:---------|:--------|:-----------|
| ROI score formulation | Claude | We described the four signals (uplift gap, gravity, recent sales, cooler count) and iterated on the weight allocation. The 40/30/20/10 split was our final judgment. |
| Greedy knapsack implementation | Claude + Copilot | The AI generated the initial loop structure. We added the headroom cap, 50 LKR rounding, floor enforcement, and distributor rebalancing pass ourselves after discovering operational edge cases in testing. |

### 9.6 XAI Module

| Use Case | AI Tool | Our Process |
|:---------|:--------|:-----------|
| System prompt engineering | Claude + Gemini | We iterated on 8 versions of the system prompt. The key insight — "do not mention SHAP values" and "write for field sales managers" — emerged from testing the prompt with real outlet contexts and finding the initial versions were too technical. |
| Fallback explanation generator | Copilot | Generated the template; we refined it to match the exact API response schema. |
| Number hallucination detection | Claude | We described the problem (LLM fabricating numbers not in the context) and co-designed the extraction-and-validation algorithm. We implemented and tested it ourselves. |

### 9.7 Key Principle

**We rigorously validated every AI output.** In multiple cases, we rejected or significantly modified AI suggestions:
- The AI initially suggested Gaussian decay. We chose inverse-square after independent research into retail gravitation literature.
- The AI suggested equal ensemble weights (33/33/33). We overrode this with 40/40/20 to preserve XAI integrity.
- The budget optimiser's first AI-generated version had no minimum spend floor, resulting in 50 LKR allocations that buy nothing in Sri Lanka. We added all guardrails ourselves.
- Several AI-generated code snippets had bugs (incorrect DataFrame indexing, missing edge cases for zero-coordinate outlets). We caught and fixed these through systematic testing.

---

*End of Technical Paper*

**Team BigBug — Data Storm v7.0 | June 2026**
