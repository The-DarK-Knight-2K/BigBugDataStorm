# Scenario Brainstorm — Round 3

## Current State Summary

| Rank | Scenario | Strategy                   | Algorithm | CV RMSE   | Features |
| ---- | -------- | -------------------------- | --------- | --------- | -------- |
| 🥇 1 | S6       | `strategyA_gravity_only`   | XGBoost   | **41.14** | 32       |
| 🥈 2 | S9       | `strategyC` (Optuna-tuned) | XGBoost   | 41.33     | 55       |
| 🥉 3 | S5       | `strategyC`                | XGBoost   | 41.78     | 55       |
| 4    | S3       | `strategyA`                | XGBoost   | 41.82     | 51       |
| 5    | S7       | `strategyA_flat_only`      | XGBoost   | 41.54     | 43       |
| 6    | S4       | `strategyA`                | LightGBM  | 43.50     | 51       |
| ❌   | S1, S2   | baseline / strategyA       | CatBoost  | 329.00    | —        |

**Decisions already made:**

- ❌ **Scenarios 1 & 2 (CatBoost baseline/strategyA): ABANDONED** — CatBoost GPU severely over-regularizes on this dataset
- ✅ XGBoost is the clear winner algorithm
- ✅ Gravity-only features (S6) beat both mixed (S3) and flat-only (S7) — cleaner is better

---

## 🔍 Feature Importance Analysis — Key Findings

Looking at the feature importance CSVs across runs, there is a clear pattern:

### The "Big 4" Dominate Everything

| Feature                           | Importance (S6)     | Importance (S5/C) |
| --------------------------------- | ------------------- | ----------------- |
| `Outlet_Size`                     | **78.1%**           | **67.9%**         |
| `seasonality_multiplier_jan_2026` | 7.6%                | 8.2%              |
| `active_months_pct`               | 0.4% (gravity_only) | **11.3%**         |
| `hist_cv`                         | 5.4%                | 5.0%              |

> [!IMPORTANT]
> **`Outlet_Size` alone captures 68-78% of all model gain.** This is both a strength (strong signal) and a risk (model is essentially a size lookup table with minor corrections).

### 🚨 Boolean Noise Features to REMOVE

These boolean flags contribute near-zero or literally zero importance but add dimensionality noise:

| Feature                  | Importance | Why it's noise                                                                                                                                                          |
| ------------------------ | ---------- | ----------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| `size_imputed`           | 2.2-2.5%   | **Leaks info about Outlet_Size** — it's a flag saying "we guessed the size", so the model uses it as a proxy for uncertain size bins. NOT a valid input for R2 outlets. |
| `coords_swapped`         | 0.02%      | Data cleaning artifact — whether coordinates were swapped during Silver layer. **NOT a demand driver.**                                                                 |
| `poi_data_available`     | **0.0%**   | Literal zero importance. Binary flag from scraping.                                                                                                                     |
| `gravity_data_available` | **0.0%**   | Literal zero importance. Binary flag from gravity pipeline.                                                                                                             |

> [!WARNING]
> **`size_imputed` is particularly dangerous.** It has 2.2% importance — but it's NOT a real feature. It's a data quality flag that tells the model "this outlet's size was imputed from cooler count." For Round 2 unactivated outlets, ALL sizes may be imputed, making this flag meaningless or misleading. **Must remove.**

---

## TIER 1: 9 New Scenarios to Run NOW

For each of the 3 best strategies (S5/S6/S7), we run:

1. **LightGBM** with original features (algorithm comparison)
2. **XGBoost** with boolean noise removed (feature pruning)
3. **LightGBM** with boolean noise removed (both improvements)

Boolean noise fields removed in "clean" variants:

```
size_imputed, coords_swapped, poi_data_available, gravity_data_available
```

---

### Group A: Strategy C — Feature Interactions (based on S5)

#### Scenario 10: Strategy C — LightGBM (original features)

```bash
python modelling/train.py --strategy strategyC --algorithm lightgbm --notes "Strategy C with LightGBM"
```

- **Rationale:** S5 ran strategyC with XGBoost only. LightGBM was only tested on strategyA (S4). Need algorithm diversity for ensembling.
- **Expected RMSE:** ~43 (LightGBM was ~2 points behind XGBoost on strategyA)
- **Expected features:** 55

#### Scenario 11: Strategy C Clean — XGBoost (boolean noise removed)

**New strategy: `strategyC_clean`**

```bash
python modelling/train.py --strategy strategyC_clean --algorithm xgboost --notes "Strategy C, boolean noise removed, XGBoost"
```

- **Rationale:** Test if removing boolean noise improves S5's XGBoost result (41.78).
- **Expected RMSE:** ~41.5-41.8
- **Expected features:** 51

#### Scenario 12: Strategy C Clean — LightGBM (boolean noise removed)

```bash
python modelling/train.py --strategy strategyC_clean --algorithm lightgbm --notes "Strategy C, boolean noise removed, LightGBM"
```

- **Rationale:** Best-of-both: cleaned features + algorithm comparison.
- **Expected RMSE:** ~43
- **Expected features:** 51

---

### Group B: Gravity-Only (based on S6) ⭐ Highest Priority Group

#### Scenario 13: Gravity-Only — LightGBM (original features)

```bash
python modelling/train.py --strategy strategyA_gravity_only --algorithm lightgbm --notes "Gravity-only ablation with LightGBM"
```

- **Rationale:** Our best strategy (S6, gravity-only, RMSE 41.14) was only tested with XGBoost. LightGBM provides ensemble diversity.
- **Expected RMSE:** ~42-43
- **Expected features:** 32

#### Scenario 14: Gravity-Only Clean — XGBoost (boolean noise removed) ⭐

**New strategy: `strategyA_gravity_clean`**

```bash
python modelling/train.py --strategy strategyA_gravity_clean --algorithm xgboost --notes "Gravity-only, boolean noise removed, XGBoost"
```

- **Rationale:** Our reigning champion (S6, RMSE 41.14) had 4 boolean noise features. Removing them reduces dimensionality from 32→28. Could push below 41.0.
- **Expected RMSE:** ~40.8-41.1
- **Expected features:** ~28

#### Scenario 15: Gravity-Only Clean — LightGBM (boolean noise removed)

```bash
python modelling/train.py --strategy strategyA_gravity_clean --algorithm lightgbm --notes "Gravity-only, boolean noise removed, LightGBM"
```

- **Rationale:** Cleaned gravity features + LightGBM. Good ensemble candidate with S14.
- **Expected RMSE:** ~42-43
- **Expected features:** ~28

---

### Group C: Flat POI Only (based on S7)

#### Scenario 16: Flat-Only — LightGBM (original features)

```bash
python modelling/train.py --strategy strategyA_flat_only --algorithm lightgbm --notes "Flat-only ablation with LightGBM"
```

- **Rationale:** Completes the ablation study (S7 was XGBoost only). Good for the report.
- **Expected RMSE:** ~43-44
- **Expected features:** 43

#### Scenario 17: Flat-Only Clean — XGBoost (boolean noise removed)

**New strategy: `strategyA_flat_clean`**

```bash
python modelling/train.py --strategy strategyA_flat_clean --algorithm xgboost --notes "Flat-only, boolean noise removed, XGBoost"
```

- **Rationale:** Test if removing booleans helps the flat-only model (S7 had RMSE 41.54).
- **Expected RMSE:** ~41.3-41.5
- **Expected features:** ~39

#### Scenario 18: Flat-Only Clean — LightGBM (boolean noise removed)

```bash
python modelling/train.py --strategy strategyA_flat_clean --algorithm lightgbm --notes "Flat-only, boolean noise removed, LightGBM"
```

- **Rationale:** Cleaned flat features + LightGBM.
- **Expected RMSE:** ~43-44
- **Expected features:** ~39

---

### Tier 1 Summary Table

| #          | Strategy                  | Algorithm | Booleans    | Base Scenario | New Strategy? |
| ---------- | ------------------------- | --------- | ----------- | ------------- | ------------- |
| **S10**    | `strategyC`               | LightGBM  | Kept        | S5            | No            |
| **S11**    | `strategyC_clean`         | XGBoost   | **Removed** | S5            | ✅ Yes        |
| **S12**    | `strategyC_clean`         | LightGBM  | **Removed** | S5            | ✅ Yes        |
| **S13**    | `strategyA_gravity_only`  | LightGBM  | Kept        | S6            | No            |
| **S14** ⭐ | `strategyA_gravity_clean` | XGBoost   | **Removed** | S6            | ✅ Yes        |
| **S15**    | `strategyA_gravity_clean` | LightGBM  | **Removed** | S6            | ✅ Yes        |
| **S16**    | `strategyA_flat_only`     | LightGBM  | Kept        | S7            | No            |
| **S17**    | `strategyA_flat_clean`    | XGBoost   | **Removed** | S7            | ✅ Yes        |
| **S18**    | `strategyA_flat_clean`    | LightGBM  | **Removed** | S7            | ✅ Yes        |

**3 new strategies required** in [train.py](file:///c:/Users/sithu/My%20Works/My%20Softwares/Competitions/DataStorm3_ML_DS/BigBugDataStorm/modelling/train.py#L116-L142): `strategyC_clean`, `strategyA_gravity_clean`, `strategyA_flat_clean`

---

## Strategy Registry Changes Needed

Add these to `STRATEGIES` in [train.py](file:///c:/Users/sithu/My%20Works/My%20Softwares/Competitions/DataStorm3_ML_DS/BigBugDataStorm/modelling/train.py#L116-L142):

```python
# Boolean noise columns to remove (data quality flags, not demand drivers)
_BOOLEAN_NOISE = [
    "size_imputed",
    "coords_swapped",
    "poi_data_available",
    "gravity_data_available",
]

# --- Clean variants (boolean noise removed) ---

STRATEGIES["strategyC_clean"] = {
    "description": "Strategy C (interactions) + remove boolean noise flags.",
    "exclude": _BASE_EXCLUDE + _R1_REDUNDANT + _LEAK_FEATURES + _BOOLEAN_NOISE,
    "interaction_features": True,
}

STRATEGIES["strategyA_gravity_clean"] = {
    "description": "Gravity-only + remove boolean noise. Cleanest spatial model.",
    "exclude": _BASE_EXCLUDE + _R1_REDUNDANT + _LEAK_FEATURES + _FLAT_POI_COLS + _BOOLEAN_NOISE,
    "interaction_features": False,
}

STRATEGIES["strategyA_flat_clean"] = {
    "description": "Flat POI only + remove boolean noise.",
    "exclude": _BASE_EXCLUDE + _R1_REDUNDANT + _LEAK_FEATURES + _GRAVITY_COLS + _BOOLEAN_NOISE,
    "interaction_features": False,
}
```

---

## Recommended Execution Order

All 9 scenarios are independent and can be run sequentially:

```
Group B (Highest Priority — our best strategy):
  S14 → strategyA_gravity_clean + XGBoost   ⭐ Most likely to beat current best
  S13 → strategyA_gravity_only  + LightGBM
  S15 → strategyA_gravity_clean + LightGBM

Group A (Second — feature interactions):
  S11 → strategyC_clean + XGBoost
  S10 → strategyC      + LightGBM
  S12 → strategyC_clean + LightGBM

Group C (Third — flat POI ablation):
  S17 → strategyA_flat_clean + XGBoost
  S16 → strategyA_flat_only  + LightGBM
  S18 → strategyA_flat_clean + LightGBM
```

---

## Future Scenarios (Pending Tier 1 Results)

> [!NOTE]
> These will be decided after reviewing Tier 1 results. Not committed yet.

### Optuna Tuning (Not decided — trial count TBD)

- **Optuna on gravity-only or gravity-clean:** S9 proved tuning works (41.78→41.33 on strategyC). Tuning our best model could push sub-40.
- **Run on:** whichever gravity variant wins from Tier 1

### Strategy C v2 — Better Interactions

Replace the low-importance interactions with domain-driven ones:

- `size_x_seasonality`, `size_x_competition`, `gravity_x_competition`, `cv_x_active`
- Remove: `gravity_x_cooler` (0.024%), `gravity_x_active_months` (0.021%), `transport_x_school` (0.031%)

### Aggressive Feature Pruning (`strategyA_gravity_minimal`)

Push gravity-clean further by dropping features with <0.05% importance:

- Drop: `Outlet_Type`, `consecutive_zero_months_max`, `raw_composite_gravity`, individual gravity scores (keep only composite + transport + hospitality)
- Target: ~20 features

### Log-Transform Target (Not decided)

- Transform `y = log1p(target)` to make the model optimize for relative error
- Requires code changes to `train.py` and `predict.py`

### Ratio Features

- `cooler_per_competitor = Cooler_Count / (competitors_1km + 1)`
- `gravity_per_competitor = composite_gravity_score / (competition_density_score + 1)`

### Binned/Bucketed Features

- `outlet_size_x_province` — Province-specific size effects
- `gravity_quartile` — Binned gravity as categorical
- `competition_tier` — Low/medium/high from `competition_density_score`

### Coordinate Cluster Features

- **Not currently implemented anywhere** — this was a proposal to use K-Means (k=10-20) on `(Latitude, Longitude)` to create a `location_cluster` categorical feature inside `train.py` on-the-fly
- **Why:** Lat/Long have low importance as raw numbers (0.2%, 0.07%). Clustering captures "neighbourhood" effects that individual coordinates miss.
- Also: `distance_to_colombo` — Euclidean distance to Colombo center (6.93, 79.85)

### Ensemble — Blend Top Models

- Blend 2-3 best models from Tier 1 results
- Run after all single-model scenarios are complete

---

## Resolved Questions

| Question                               | Decision                                                                                                                                                                                   |
| -------------------------------------- | ------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------ |
| `size_imputed` A/B test?               | **No separate test.** Remove booleans as part of Tier 1 clean variants. The clean vs original comparison IS the A/B test (e.g., S6 vs S14, S5 vs S11).                                     |
| Outlet_Size encoding for interactions? | **Not needed for Tier 1.** `Outlet_Size` stays categorical. XGBoost/LightGBM handle it natively via category codes. Interaction encoding only relevant for future Strategy C v2 scenarios. |
| Log-transform target?                  | **Deferred.** Will decide after Tier 1 results.                                                                                                                                            |
| Optuna trial count?                    | **Deferred.** Will decide after Tier 1 results.                                                                                                                                            |
| K-Means clustering?                    | **Clarified.** Not used anywhere currently — it was a new proposal for a `location_cluster` feature. Deferred to future scenarios.                                                         |
