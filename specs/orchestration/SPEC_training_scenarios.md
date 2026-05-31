## Training Scenarios — Detailed Transition Guide

### Code Preservation Strategy

> [!IMPORTANT]
> **No code file is ever overwritten between scenarios.** All scenario differences are controlled via:
>
> 1. **CLI arguments** (`--strategy`, `--algorithm`, `--notes`) passed to `train.py`
> 2. **Config overrides** in `train.py` that select different `EXCLUDE_COLS` lists and feature sets based on the `--strategy` flag
> 3. **Per-run folders** save the exact `run_config.json` (features used, params, strategy name) so any run can be reproduced
>
> You run the **same `train.py` file** for all scenarios. The strategy flag controls which features are included/excluded. No code changes needed between runs.

### How it works inside `train.py`

The updated `train.py` will contain a strategy registry:

```python
STRATEGIES = {
    "round1_baseline": {
        "exclude": [...],  # Original Round 1 exclusions
        "interaction_features": False,
    },
    "strategyA": {
        "exclude": [...],  # + hist_p90, hist_max, jan_avg, ema_3m
        "interaction_features": False,
    },
    "strategyC": {
        "exclude": [...],  # Same as A, but interaction features ON
        "interaction_features": True,
    },
    # ... etc
}
```

Running different scenarios:

```bash
python modelling/train.py --strategy strategyA --algorithm catboost
python modelling/train.py --strategy strategyA --algorithm xgboost
python modelling/train.py --strategy strategyC --algorithm catboost
```

---

### Round 1 Scenarios (1-9)

#### Scenario 1: Round 1 Baseline (Reference Run)

| Item                  | Detail                                                                 |
| --------------------- | ---------------------------------------------------------------------- |
| **Purpose**           | Establish the baseline RMSE with the Round 1 model on the updated `master_features.parquet` (which now includes gravity + catchment columns) |
| **Strategy**          | `round1_baseline`                                                      |
| **Algorithm**         | CatBoost (GPU)                                                         |
| **Excluded features** | Same as original `train.py` — keeps `hist_p90`, `hist_max`, `jan_avg`, `ema_3m` |
| **Expected features** | ~28 (Gravity + catchment auto-included; all leakage features kept)     |
| **Target**            | `hist_p90_monthly * seasonality * trading_days`                        |
| **Custom scripts**    | None                                                                   |
| **Code/data changes** | None — just run with the strategy flag                                 |
| **Expected RMSE**     | ~40 (leak features dominate)                                           |
| **Status**            | ❌ **ABANDONED** — CatBoost GPU over-regularised (RMSE 329.00)        |

```bash
python modelling/train.py --strategy round1_baseline --notes "Reference: R1 features on updated master_features"
```

---

#### Scenario 2: Strategy A — Remove Target Leakage (CatBoost)

| Item                  | Detail                                                                 |
| --------------------- | ---------------------------------------------------------------------- |
| **Purpose**           | Force the model to learn from structural/spatial features by removing the "answer key" |
| **Strategy**          | `strategyA`                                                            |
| **Algorithm**         | CatBoost (GPU)                                                         |
| **Excluded features** | All of Scenario 1 + `hist_p90_monthly`, `hist_max_monthly`, `jan_avg_volume`, `ema_3m` |
| **Expected features** | ~24 (leakage features removed)                                         |
| **Target**            | `hist_p90_monthly * seasonality * trading_days`                        |
| **Custom scripts**    | None                                                                   |
| **Code/data changes** | None — run with strategy flag                                          |
| **Expected RMSE**     | 55-65 (higher because leak features removed, but this is correct)      |
| **Status**            | ❌ **ABANDONED** — Same CatBoost GPU issue (RMSE 329.00)              |

```bash
python modelling/train.py --strategy strategyA --notes "Strategy A: no leak features, CatBoost GPU"
```

---

#### Scenario 3: Strategy A — XGBoost Comparison

| Item                  | Detail                                                                 |
| --------------------- | ---------------------------------------------------------------------- |
| **Purpose**           | Compare XGBoost against CatBoost on the same feature set               |
| **Strategy**          | `strategyA`                                                            |
| **Algorithm**         | XGBoost (GPU)                                                          |
| **Excluded features** | Same as Scenario 2                                                     |
| **Expected features** | ~24                                                                    |
| **Target**            | `hist_p90_monthly * seasonality * trading_days`                        |
| **Custom scripts**    | None                                                                   |
| **Code/data changes** | None                                                                   |
| **Expected RMSE**     | 55-65 (similar to CatBoost, may be slightly better/worse)             |
| **Status**            | ✅ **Done** — RMSE 41.82 (massive breakthrough vs CatBoost's 329.00)  |

```bash
python modelling/train.py --strategy strategyA --algorithm xgboost --notes "XGBoost GPU comparison"
```

---

#### Scenario 4: Strategy A — LightGBM Comparison

| Item                  | Detail                                                                 |
| --------------------- | ---------------------------------------------------------------------- |
| **Purpose**           | Third algorithm comparison (LightGBM)                                  |
| **Strategy**          | `strategyA`                                                            |
| **Algorithm**         | LightGBM                                                               |
| **Excluded features** | Same as Scenario 2                                                     |
| **Expected features** | ~24                                                                    |
| **Target**            | `hist_p90_monthly * seasonality * trading_days`                        |
| **Custom scripts**    | None                                                                   |
| **Code/data changes** | None                                                                   |
| **Expected RMSE**     | 55-65                                                                  |
| **Status**            | ✅ **Done** — RMSE 43.50                                               |

```bash
python modelling/train.py --strategy strategyA --algorithm lightgbm --notes "LightGBM GPU comparison"
```

---

#### Scenario 5: Strategy C — Feature Interactions (XGBoost)

| Item                  | Detail                                                                 |
| --------------------- | ---------------------------------------------------------------------- |
| **Purpose**           | Test if cross-features improve the model                               |
| **Strategy**          | `strategyC`                                                            |
| **Algorithm**         | XGBoost (GPU)                                                          |
| **Excluded features** | Same as Strategy A                                                     |
| **Expected features** | ~55 (due to additional interaction features: `gravity_x_cooler`, etc.) |
| **Target**            | `hist_p90_monthly * seasonality * trading_days`                        |
| **Custom scripts**    | None                                                                   |
| **Code/data changes** | None                                                                   |
| **Expected RMSE**     | Slightly lower than Scenario 3 if interactions help                    |
| **Status**            | ✅ **Done** — RMSE 41.78                                               |

```bash
python modelling/train.py --strategy strategyC --algorithm xgboost --notes "Strategy C: Feature Interactions with XGBoost"
```

---

#### Scenario 6: Strategy A + Only Gravity Features (No Flat POI Counts)

| Item                  | Detail                                                                 |
| --------------------- | ---------------------------------------------------------------------- |
| **Purpose**           | Test if gravity scores can fully replace flat POI counts (cleaner model, less multicollinearity) |
| **Strategy**          | `strategyA_gravity_only`                                               |
| **Algorithm**         | XGBoost (GPU)                                                          |
| **Excluded features** | Strategy A exclusions + all 18 flat POI count columns (`schools_500m` through `hospitality_2000m`) + `footfall_score` |
| **Expected features** | 32 (keeps gravity scores, composite score, catchment, structural)      |
| **Target**            | `hist_p90_monthly * seasonality * trading_days`                        |
| **Custom scripts**    | None                                                                   |
| **Code/data changes** | None                                                                   |
| **Expected RMSE**     | Similar to Scenario 3 — if gravity scores capture the same signal as flat counts |
| **Status**            | ✅ **Done** — RMSE **41.14** (BEST untuned result, 32 features)       |

```bash
python modelling/train.py --strategy strategyA_gravity_only --algorithm xgboost --notes "Ablation: Gravity features only (XGBoost)"
```

---

#### Scenario 7: Strategy A + Only Flat POI Counts (No Gravity)

| Item                  | Detail                                                                 |
| --------------------- | ---------------------------------------------------------------------- |
| **Purpose**           | Ablation test — prove that gravity features add value over Round 1 flat counts |
| **Strategy**          | `strategyA_flat_only`                                                  |
| **Algorithm**         | XGBoost (GPU)                                                          |
| **Excluded features** | Strategy A exclusions + all 7 gravity columns + `raw_composite_gravity` |
| **Expected features** | 43 (keeps flat POI counts, footfall, catchment, structural)            |
| **Target**            | `hist_p90_monthly * seasonality * trading_days`                        |
| **Custom scripts**    | None                                                                   |
| **Code/data changes** | None                                                                   |
| **Expected RMSE**     | Higher than Scenario 3 (proving gravity adds value)                    |
| **Status**            | ✅ **Done** — RMSE 41.54                                               |

```bash
python modelling/train.py --strategy strategyA_flat_only --algorithm xgboost --notes "Ablation: Flat POI counts only (XGBoost)"
```

> [!TIP]
> **Scenarios 6 vs 7 vs 3** form an ablation study. Scenario 6 (gravity only, 41.14) beat Scenario 7 (flat only, 41.54) and Scenario 3 (both, 41.82). Gravity-only is the cleanest and best approach.

---

#### Scenario 8: Strategy A + Tuned Epsilon (epsilon = 0.02)

| Item                  | Detail                                                                 |
| --------------------- | ---------------------------------------------------------------------- |
| **Purpose**           | Test if a tighter epsilon gives better discrimination                   |
| **Strategy**          | `strategyA`                                                            |
| **Algorithm**         | CatBoost (GPU)                                                         |
| **Excluded features** | Same as Scenario 2                                                     |
| **Expected features** | ~24                                                                    |
| **Target**            | `hist_p90_monthly * seasonality * trading_days`                        |
| **Custom scripts**    | `data_pipeline/build_gravity_features.py` with `decay_epsilon: 0.02`   |
| **Code/data changes** | Parquet change required — rebuild gravity + master features             |
| **Expected RMSE**     | Lower than Scenario 2 if tighter epsilon works better                  |
| **Status**            | ⏸️ **DEFERRED** — Pending Round 3 results                              |

```bash
# Rebuild gravity features with epsilon=0.02 in config.yaml
python data_pipeline/build_gravity_features.py
python modelling/train.py --strategy strategyA --notes "Strategy A with tighter epsilon"
```

---

#### Scenario 9: Optuna Hyperparameter Re-tuning (XGBoost)

| Item                  | Detail                                                                 |
| --------------------- | ---------------------------------------------------------------------- |
| **Purpose**           | The Round 1 Optuna params were tuned with leak features. Re-tune for new feature set |
| **Strategy**          | `strategyC`                                                            |
| **Algorithm**         | XGBoost (GPU)                                                          |
| **Excluded features** | Same as Scenario 5                                                     |
| **Expected features** | ~55                                                                    |
| **Target**            | `hist_p90_monthly * seasonality * trading_days`                        |
| **Custom scripts**    | `modelling/optuna_tune.py` (50 trials)                                 |
| **Code/data changes** | Hyperparameter tuning config changes                                   |
| **Expected RMSE**     | 2-5% lower than the un-tuned version (S5)                              |
| **Status**            | ✅ **Done** — RMSE 41.33 (improved from 41.78 untuned)                |

```bash
python modelling/optuna_tune.py --strategy strategyC --algorithm xgboost --n-trials 50
python modelling/train.py --strategy strategyC --algorithm xgboost --use-optuna-params --notes "Optuna re-tuned (50 trials)"
```

---

#### ~~Original Scenario 10: Model Ensemble (Blending)~~ → Deferred

> [!NOTE]
> Original Scenario 10 (Ensemble blending) has been deferred. Scenarios 10-18 are now the Round 3 boolean cleanup runs. Ensemble will be run after Round 3.

---

### Round 3 — Boolean Noise Removal + Algorithm Expansion (Scenarios 10-18)

> [!IMPORTANT]
> **Decisions from Round 2 analysis:**
> - ❌ **Scenarios 1 & 2 (CatBoost): ABANDONED** — CatBoost GPU severely over-regularises on this dataset (RMSE 329.00)
> - ❌ **Scenario 8 (epsilon tuning): DEFERRED** — Pending Round 3 results
> - ✅ XGBoost is the clear winner algorithm (RMSE ~41 vs CatBoost ~329)
> - ✅ Gravity-only (S6, RMSE 41.14) is the best feature strategy
>
> **Feature importance analysis** revealed 4 boolean noise fields that must be removed:
> `size_imputed`, `coords_swapped`, `poi_data_available`, `gravity_data_available`
> These are data cleaning artifacts, not demand drivers. `size_imputed` (2.2% importance) leaks Outlet_Size uncertainty.

#### Code Changes Required

Add to `train.py` — new constant and 3 new strategies:

```python
_BOOLEAN_NOISE = [
    "size_imputed",
    "coords_swapped",
    "poi_data_available",
    "gravity_data_available",
]

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

#### Scenario 10: Strategy C — LightGBM (Original Features)

| Item                  | Detail                                                                    |
| --------------------- | ------------------------------------------------------------------------- |
| **Purpose**           | Algorithm comparison — LightGBM on the interaction feature set            |
| **Strategy**          | `strategyC`                                                               |
| **Algorithm**         | LightGBM                                                                  |
| **Excluded features** | Same as Scenario 5                                                        |
| **Target**            | Same formula                                                              |
| **Custom scripts**    | None                                                                      |
| **Code/data changes** | None — existing strategy + algorithm flag                                 |
| **Expected RMSE**     | ~43 (LightGBM was ~2 points behind XGBoost on strategyA in S4)           |

```bash
python modelling/train.py --strategy strategyC --algorithm lightgbm --notes "Strategy C with LightGBM"
```

---

#### Scenario 11: Strategy C Clean — XGBoost (Boolean Noise Removed)

| Item                    | Detail                                                                    |
| ----------------------- | ------------------------------------------------------------------------- |
| **Purpose**             | Test if removing 4 boolean noise flags improves S5 (RMSE 41.78)          |
| **Strategy**            | `strategyC_clean` **(NEW)**                                               |
| **Algorithm**           | XGBoost (GPU)                                                             |
| **Excluded features**   | Strategy C exclusions + `size_imputed`, `coords_swapped`, `poi_data_available`, `gravity_data_available` |
| **Target**              | Same formula                                                              |
| **Custom scripts**      | None                                                                      |
| **Code/data changes**   | New strategy definition in `train.py`                                     |
| **Expected RMSE**       | ~41.5-41.8                                                                |
| **Expected features**   | ~51                                                                       |

```bash
python modelling/train.py --strategy strategyC_clean --algorithm xgboost --notes "Strategy C, boolean noise removed, XGBoost"
```

---

#### Scenario 12: Strategy C Clean — LightGBM (Boolean Noise Removed)

| Item                  | Detail                                                                    |
| --------------------- | ------------------------------------------------------------------------- |
| **Purpose**           | Cleaned interactions + LightGBM — ensemble diversity candidate            |
| **Strategy**          | `strategyC_clean`                                                         |
| **Algorithm**         | LightGBM                                                                  |
| **Excluded features** | Same as Scenario 11                                                       |
| **Target**            | Same formula                                                              |
| **Custom scripts**    | None                                                                      |
| **Code/data changes** | None — reuses `strategyC_clean` from S11                                  |
| **Expected RMSE**     | ~43                                                                       |
| **Expected features** | ~51                                                                       |

```bash
python modelling/train.py --strategy strategyC_clean --algorithm lightgbm --notes "Strategy C, boolean noise removed, LightGBM"
```

---

#### Scenario 13: Gravity-Only — LightGBM (Original Features)

| Item                  | Detail                                                                    |
| --------------------- | ------------------------------------------------------------------------- |
| **Purpose**           | Algorithm comparison — LightGBM on the current best strategy (S6)         |
| **Strategy**          | `strategyA_gravity_only`                                                  |
| **Algorithm**         | LightGBM                                                                  |
| **Excluded features** | Same as Scenario 6                                                        |
| **Target**            | Same formula                                                              |
| **Custom scripts**    | None                                                                      |
| **Code/data changes** | None — existing strategy + algorithm flag                                 |
| **Expected RMSE**     | ~42-43                                                                    |
| **Expected features** | 32                                                                        |

```bash
python modelling/train.py --strategy strategyA_gravity_only --algorithm lightgbm --notes "Gravity-only ablation with LightGBM"
```

---

#### Scenario 14: Gravity-Only Clean — XGBoost (Boolean Noise Removed) ⭐

| Item                    | Detail                                                                    |
| ----------------------- | ------------------------------------------------------------------------- |
| **Purpose**             | **Highest priority** — remove noise from current champion (S6, RMSE 41.14). Could push below 41.0 |
| **Strategy**            | `strategyA_gravity_clean` **(NEW)**                                       |
| **Algorithm**           | XGBoost (GPU)                                                             |
| **Excluded features**   | Gravity-only exclusions + `size_imputed`, `coords_swapped`, `poi_data_available`, `gravity_data_available` |
| **Target**              | Same formula                                                              |
| **Custom scripts**      | None                                                                      |
| **Code/data changes**   | New strategy definition in `train.py`                                     |
| **Expected RMSE**       | ~40.8-41.1                                                                |
| **Expected features**   | ~28                                                                       |

```bash
python modelling/train.py --strategy strategyA_gravity_clean --algorithm xgboost --notes "Gravity-only, boolean noise removed, XGBoost"
```

---

#### Scenario 15: Gravity-Only Clean — LightGBM (Boolean Noise Removed)

| Item                  | Detail                                                                    |
| --------------------- | ------------------------------------------------------------------------- |
| **Purpose**           | Cleaned gravity features + LightGBM — ensemble diversity with S14         |
| **Strategy**          | `strategyA_gravity_clean`                                                 |
| **Algorithm**         | LightGBM                                                                  |
| **Excluded features** | Same as Scenario 14                                                       |
| **Target**            | Same formula                                                              |
| **Custom scripts**    | None                                                                      |
| **Code/data changes** | None — reuses `strategyA_gravity_clean` from S14                          |
| **Expected RMSE**     | ~42-43                                                                    |
| **Expected features** | ~28                                                                       |

```bash
python modelling/train.py --strategy strategyA_gravity_clean --algorithm lightgbm --notes "Gravity-only, boolean noise removed, LightGBM"
```

---

#### Scenario 16: Flat-Only — LightGBM (Original Features)

| Item                  | Detail                                                                    |
| --------------------- | ------------------------------------------------------------------------- |
| **Purpose**           | Algorithm comparison — LightGBM on flat POI ablation (S7)                 |
| **Strategy**          | `strategyA_flat_only`                                                     |
| **Algorithm**         | LightGBM                                                                  |
| **Excluded features** | Same as Scenario 7                                                        |
| **Target**            | Same formula                                                              |
| **Custom scripts**    | None                                                                      |
| **Code/data changes** | None — existing strategy + algorithm flag                                 |
| **Expected RMSE**     | ~43-44                                                                    |
| **Expected features** | 43                                                                        |

```bash
python modelling/train.py --strategy strategyA_flat_only --algorithm lightgbm --notes "Flat-only ablation with LightGBM"
```

---

#### Scenario 17: Flat-Only Clean — XGBoost (Boolean Noise Removed)

| Item                    | Detail                                                                    |
| ----------------------- | ------------------------------------------------------------------------- |
| **Purpose**             | Test if removing booleans helps the flat-only model (S7 had RMSE 41.54)   |
| **Strategy**            | `strategyA_flat_clean` **(NEW)**                                          |
| **Algorithm**           | XGBoost (GPU)                                                             |
| **Excluded features**   | Flat-only exclusions + `size_imputed`, `coords_swapped`, `poi_data_available`, `gravity_data_available` |
| **Target**              | Same formula                                                              |
| **Custom scripts**      | None                                                                      |
| **Code/data changes**   | New strategy definition in `train.py`                                     |
| **Expected RMSE**       | ~41.3-41.5                                                                |
| **Expected features**   | ~39                                                                       |

```bash
python modelling/train.py --strategy strategyA_flat_clean --algorithm xgboost --notes "Flat-only, boolean noise removed, XGBoost"
```

---

#### Scenario 18: Flat-Only Clean — LightGBM (Boolean Noise Removed)

| Item                  | Detail                                                                    |
| --------------------- | ------------------------------------------------------------------------- |
| **Purpose**           | Cleaned flat features + LightGBM                                          |
| **Strategy**          | `strategyA_flat_clean`                                                    |
| **Algorithm**         | LightGBM                                                                  |
| **Excluded features** | Same as Scenario 17                                                       |
| **Target**            | Same formula                                                              |
| **Custom scripts**    | None                                                                      |
| **Code/data changes** | None — reuses `strategyA_flat_clean` from S17                             |
| **Expected RMSE**     | ~43-44                                                                    |
| **Expected features** | ~39                                                                       |

```bash
python modelling/train.py --strategy strategyA_flat_clean --algorithm lightgbm --notes "Flat-only, boolean noise removed, LightGBM"
```

---

### Scenario Summary Table

| #     | Strategy                  | Algorithm | Key Difference                        | Custom Scripts   | Data Rebuild? | Status       |
| ----- | ------------------------- | --------- | ------------------------------------- | ---------------- | ------------- | ------------ |
| 1     | `round1_baseline`         | CatBoost  | Reference (leak features kept)        | None             | No            | ❌ Abandoned (329.00) |
| 2     | `strategyA`               | CatBoost  | **Remove 4 leak features**            | None             | No            | ❌ Abandoned (329.00) |
| 3     | `strategyA`               | XGBoost   | Algorithm comparison                  | None             | No            | ✅ Done (41.82)      |
| 4     | `strategyA`               | LightGBM  | Algorithm comparison                  | None             | No            | ✅ Done (43.50)      |
| 5     | `strategyC`               | XGBoost   | + Interaction features                | None             | No            | ✅ Done (41.78)      |
| 6     | `strategyA_gravity_only`  | XGBoost   | Drop flat POI counts                  | None             | No            | ✅ Done (41.14)      |
| 7     | `strategyA_flat_only`     | XGBoost   | Drop gravity scores                   | None             | No            | ✅ Done (41.54)      |
| 8     | `strategyA`               | CatBoost  | epsilon = 0.02 gravity rebuild        | None             | **Yes**       | ⏸️ Deferred          |
| 9     | `strategyC`               | XGBoost   | Optuna re-tuning (50 trials)          | `optuna_tune.py` | No            | ✅ Done (41.33)      |
|       |                           |           | **— Round 3: Boolean Cleanup —**      |                  |               |              |
| 10    | `strategyC`               | LightGBM  | LightGBM on interactions              | None             | No            | ✅ Done (43.64) |
| 11    | `strategyC_clean`         | XGBoost   | Interactions + booleans removed       | None             | No            | ✅ Done (42.70) |
| 12    | `strategyC_clean`         | LightGBM  | Interactions + booleans removed       | None             | No            | ✅ Done (44.50) |
| 13    | `strategyA_gravity_only`  | LightGBM  | LightGBM on gravity-only              | None             | No            | ✅ Done (43.46) |
| 14 ⭐ | `strategyA_gravity_clean` | XGBoost   | **Gravity-only + booleans removed**   | None             | No            | ✅ Done (42.10) |
| 15    | `strategyA_gravity_clean` | LightGBM  | Gravity-only + booleans removed       | None             | No            | ✅ Done (44.50) |
| 16    | `strategyA_flat_only`     | LightGBM  | LightGBM on flat-only                 | None             | No            | ✅ Done (43.54) |
| 17    | `strategyA_flat_clean`    | XGBoost   | Flat-only + booleans removed          | None             | No            | ✅ Done (42.50) |
| 18    | `strategyA_flat_clean`    | LightGBM  | Flat-only + booleans removed          | None             | No            | ✅ Done (44.12) |
|       |                           |           | **— Round 4: Random Forest (XAI) —**  |                  |               |              |
| 19    | `strategyA_gravity_only`  | RandomFor | RF on champion feature set            | None             | No            | ✅ Done (41.42) |
| 20    | `strategyC`               | RandomFor | RF on interaction features            | None             | No            | ✅ Done (41.76) |
| 21    | `strategyA_flat_only`     | RandomFor | RF on flat POI features               | None             | No            | ✅ Done (41.44) |

> [!WARNING]
> **Round 4 Findings (Random Forest):**
> RF performed remarkably well! S19 (Gravity-only) scored **41.42**, which is incredibly close to XGBoost's 41.14 and totally crushes LightGBM (43.46). This makes RF our definitive model for XAI/SHAP outputs because it achieves near state-of-the-art accuracy while maintaining a distributed, interpretable feature importance profile (unlike XGBoost's winner-take-all split behavior).

> [!WARNING]
> **Round 3 Findings:**
> 1. **Boolean Noise IS Signal**: Removing boolean fields (`size_imputed`, `coords_swapped`) *hurt* performance by ~1 full point across all strategies (e.g. S6 41.14 -> S14 42.10). XGBoost uses `size_imputed` effectively. **Do not remove.**
> 2. **XGBoost Dominates**: LightGBM lagged ~2 points behind XGBoost across all 3 strategies.
> **Champion Model Remains S6 (`strategyA_gravity_only`, XGBoost, RMSE 41.14)**

### Future Scenarios (Round 5)

| #    | Strategy                    | Algorithm | Key Difference              | Status          |
| ---- | --------------------------- | --------- | --------------------------- | --------------- |
| 22   | `strategyA_gravity_only`    | XGBoost   | Optuna re-tuning (S6)       | ✅ Done (40.66) |
| 23   | `strategyA_gravity_only`    | LightGBM  | Optuna re-tuning (S13)      | ✅ Done (41.55) |
| 24   | `strategyA_gravity_only`    | RandomFor | Optuna re-tuning (S19)      | ✅ Done (41.72) |
| 25   | Ensemble                    | Blend     | S22 + S23 + S24             | ✅ Done (Blend 40/40/20) |
| TBD  | `strategyC_v2`              | XGBoost   | Improved interaction terms  | Deciding        |
| TBD  | Log-transform target        | XGBoost   | `log1p(y)` optimisation     | Deciding        |

### Recommended Execution Order

```
Round 2 (COMPLETED):
  S1 -> S2 -> S3 -> S4 -> S5 -> S6 -> S7 -> S9
  (S1, S2 abandoned — CatBoost failure)
  (S6 won with RMSE 41.14)

Round 3 (COMPLETED):
  S10 through S18 (Boolean ablation & LightGBM expansion)
  (Failed to beat S6 — boolean fields should be kept, XGBoost > LightGBM)

Round 4 (NOW):
  Optuna tuning on S6 -> Ensemble -> Strategy C v2
```

> [!TIP]
> All 9 Round 3 scenarios require **3 new strategy definitions** in `train.py` (`strategyC_clean`, `strategyA_gravity_clean`, `strategyA_flat_clean`) but **zero other code changes**. Each run is just a CLI flag combination.
