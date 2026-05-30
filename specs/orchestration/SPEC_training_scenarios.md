## Q6: 10 Training Scenarios â€” Detailed Transition Guide

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

### The 10 Scenarios

#### Scenario 1: Round 1 Baseline (Reference Run)

| Item                  | Detail                                                                                                                                                                                                                       |
| --------------------- | ---------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| **Purpose**           | Establish the baseline RMSE with the Round 1 model on the **updated** `master_features.parquet` (which now includes gravity + catchment columns)                                                                             |
| **Strategy**          | `round1_baseline`                                                                                                                                                                                                            |
| **Algorithm**         | CatBoost (GPU)                                                                                                                                                                                                               |
| **Excluded features** | Same as current [train.py L63-80](file:///c:/Users/sithu/My%20Works/My%20Softwares/Competitions/DataStorm3_ML_DS/BigBugDataStorm/modelling/train.py#L63-L80) â€” keeps `hist_p90`, `hist_max`, `jan_avg`, `ema_3m` as features |
| **New features used** | Gravity scores + catchment features are auto-included (they're in `master_features.parquet`)                                                                                                                                 |
| **Target**            | `hist_p90_monthly Ã— seasonality Ã— trading_days`                                                                                                                                                                              |
| **Custom scripts**    | None                                                                                                                                                                                                                         |
| **Code/data changes** | None â€” just run with the strategy flag                                                                                                                                                                                       |
| **Expected RMSE**     | ~40 (similar to Colab experiments, since leak features dominate)                                                                                                                                                             |

```bash
python modelling/train.py --strategy round1_baseline --notes "Reference: R1 features on updated master_features"
```

**Transition to Scenario 2:** No changes needed, just switch the flag.

---

#### Scenario 2: Strategy A â€” Remove Target Leakage (CatBoost)

| Item                  | Detail                                                                                                                     |
| --------------------- | -------------------------------------------------------------------------------------------------------------------------- |
| **Purpose**           | Force the model to learn from structural/spatial features by removing the "answer key"                                     |
| **Strategy**          | `strategyA`                                                                                                                |
| **Algorithm**         | CatBoost (GPU)                                                                                                             |
| **Excluded features** | All of Scenario 1 + `hist_p90_monthly`, `hist_max_monthly`, `jan_avg_volume`, `ema_3m`                                     |
| **New features used** | Gravity (6 individual + composite), catchment (3 radii + density + saturation class), POI flat counts, structural features |
| **Target**            | Same formula (no change)                                                                                                   |
| **Custom scripts**    | None                                                                                                                       |
| **Code/data changes** | None â€” strategy flag controls exclusions                                                                                   |
| **Expected RMSE**     | 55-65 (higher because leak features removed, but this is correct)                                                          |

```bash
python modelling/train.py --strategy strategyA --notes "Strategy A: no leak features, CatBoost GPU"
```

**Transition to Scenario 3:** Just switch `--algorithm`.

---

#### Scenario 3: Strategy A â€” XGBoost Comparison

| Item                  | Detail                                                                                                      |
| --------------------- | ----------------------------------------------------------------------------------------------------------- |
| **Purpose**           | Compare XGBoost against CatBoost on the same feature set (proves systematic algorithm evaluation)           |
| **Strategy**          | `strategyA`                                                                                                 |
| **Algorithm**         | XGBoost (GPU)                                                                                               |
| **Excluded features** | Same as Scenario 2                                                                                          |
| **Target**            | Same formula                                                                                                |
| **Custom scripts**    | None â€” `train.py` handles XGBoost via `--algorithm xgboost`                                                 |
| **Code/data changes** | XGBoost requires label-encoding categoricals â€” `train.py` does this automatically when algorithm â‰  catboost |
| **Dependencies**      | `pip install xgboost` (add to `requirements.txt`)                                                           |
| **Expected RMSE**     | 55-65 (similar to CatBoost, may be slightly better/worse)                                                   |

```bash
pip install xgboost
python modelling/train.py --strategy strategyA --algorithm xgboost --notes "XGBoost GPU comparison"
```

**Transition to Scenario 4:** Just switch `--algorithm`.

---

#### Scenario 4: Strategy A â€” LightGBM Comparison

| Item                  | Detail                                                                                                                                                                           |
| --------------------- | -------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| **Purpose**           | Third algorithm comparison (LightGBM already installed)                                                                                                                          |
| **Strategy**          | `strategyA`                                                                                                                                                                      |
| **Algorithm**         | LightGBM (GPU)                                                                                                                                                                   |
| **Excluded features** | Same as Scenario 2                                                                                                                                                               |
| **Target**            | Same formula                                                                                                                                                                     |
| **Custom scripts**    | None                                                                                                                                                                             |
| **Code/data changes** | LightGBM requires `astype("category")` for categoricals â€” `train.py` handles automatically                                                                                       |
| **Dependencies**      | Already installed (`lightgbm==4.3.0` in [requirements.txt](file:///c:/Users/sithu/My%20Works/My%20Softwares/Competitions/DataStorm3_ML_DS/BigBugDataStorm/requirements.txt#L26)) |
| **Expected RMSE**     | 55-65                                                                                                                                                                            |

```bash
python modelling/train.py --strategy strategyA --algorithm lightgbm --notes "LightGBM GPU comparison"
```

> [!NOTE]
> LightGBM GPU requires the `lightgbm` package built with GPU support. The pip version may be CPU-only. If GPU fails, it'll fall back to CPU (still fast for 20K rows). We'll test this during the first run.

**Transition to Scenario 5:** Switch to `strategyC`.

---

#### Scenario 5: Strategy C â€” Feature Interactions (CatBoost)

| Item                    | Detail                                                                                                                                                                                                       |
| ----------------------- | ------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------ |
| **Purpose**             | Test if cross-features improve the model â€” per [modelling_strategy.md #6](file:///c:/Users/sithu/My%20Works/My%20Softwares/Competitions/DataStorm3_ML_DS/BigBugDataStorm/docs/modelling_strategy.md#L36-L38) |
| **Strategy**            | `strategyC`                                                                                                                                                                                                  |
| **Algorithm**           | CatBoost (GPU)                                                                                                                                                                                               |
| **Excluded features**   | Same as Strategy A                                                                                                                                                                                           |
| **Additional features** | Auto-generated interaction features:                                                                                                                                                                         |
|                         | `gravity_x_cooler = composite_gravity_score Ã— Cooler_Count`                                                                                                                                                  |
|                         | `gravity_x_active_months = composite_gravity_score Ã— active_months_pct`                                                                                                                                      |
|                         | `catchment_x_cooler = competition_density_score Ã— Cooler_Count`                                                                                                                                              |
|                         | `transport_x_school = transport_gravity_score Ã— school_gravity_score`                                                                                                                                        |
| **Target**              | Same formula                                                                                                                                                                                                 |
| **Custom scripts**      | None â€” `train.py` auto-creates interaction columns when `--strategy strategyC`                                                                                                                               |
| **Code/data changes**   | No parquet changes. `train.py` computes interactions on-the-fly in memory                                                                                                                                    |
| **Expected RMSE**       | Slightly lower than Scenario 2 if interactions help                                                                                                                                                          |

```bash
python modelling/train.py --strategy strategyC --algorithm catboost --notes "Strategy C: interaction features"
```

**Transition to Scenario 6:** Switch strategy flag.

---

#### Scenario 6: Strategy A + Only Gravity Features (No Flat POI Counts)

| Item                  | Detail                                                                                                                |
| --------------------- | --------------------------------------------------------------------------------------------------------------------- |
| **Purpose**           | Test if gravity scores can fully replace flat POI counts (cleaner model, less multicollinearity)                      |
| **Strategy**          | `strategyA_gravity_only`                                                                                              |
| **Algorithm**         | CatBoost (GPU)                                                                                                        |
| **Excluded features** | Strategy A exclusions + all 18 flat POI count columns (`schools_500m` through `hospitality_2000m`) + `footfall_score` |
| **Features kept**     | 6 individual gravity scores + `composite_gravity_score` + catchment features + structural                             |
| **Target**            | Same formula                                                                                                          |
| **Custom scripts**    | None                                                                                                                  |
| **Code/data changes** | None                                                                                                                  |
| **Expected RMSE**     | Similar to Scenario 2 â€” if gravity scores capture the same signal as flat counts                                      |

```bash
python modelling/train.py --strategy strategyA_gravity_only --notes "Gravity only, no flat POI counts"
```

**Transition to Scenario 7:** Switch strategy flag.

---

#### Scenario 7: Strategy A + Only Flat POI Counts (No Gravity)

| Item                  | Detail                                                                         |
| --------------------- | ------------------------------------------------------------------------------ |
| **Purpose**           | Ablation test â€” prove that gravity features add value over Round 1 flat counts |
| **Strategy**          | `strategyA_flat_only`                                                          |
| **Algorithm**         | CatBoost (GPU)                                                                 |
| **Excluded features** | Strategy A exclusions + all 7 gravity columns + `raw_composite_gravity`        |
| **Features kept**     | 18 flat POI counts + `footfall_score` + catchment + structural                 |
| **Target**            | Same formula                                                                   |
| **Custom scripts**    | None                                                                           |
| **Code/data changes** | None                                                                           |
| **Expected RMSE**     | Higher than Scenario 2 (proving gravity adds value)                            |

```bash
python modelling/train.py --strategy strategyA_flat_only --notes "Ablation: flat POI only, no gravity"
```

> [!TIP]
> **Scenarios 6 vs 7 vs 2** form an ablation study. If Scenario 2 (both) beats Scenario 6 (gravity only) and Scenario 7 (flat only), it proves both feature sets contribute unique signal. This is excellent for the judges.

**Transition to Scenario 8:** Switch strategy flag.

---

#### Scenario 8: Strategy A + Tuned Epsilon (Îµ = 0.02)

| Item                  | Detail                                                                                                                                                                                                                    |
| --------------------- | ------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| **Purpose**           | Test if a tighter epsilon gives better discrimination â€” per [modelling_strategy.md #9](file:///c:/Users/sithu/My%20Works/My%20Softwares/Competitions/DataStorm3_ML_DS/BigBugDataStorm/docs/modelling_strategy.md#L54-L56) |
| **Strategy**          | `strategyA`                                                                                                                                                                                                               |
| **Algorithm**         | CatBoost (GPU)                                                                                                                                                                                                            |
| **Excluded features** | Same as Scenario 2                                                                                                                                                                                                        |
| **Target**            | Same formula                                                                                                                                                                                                              |
| **Custom scripts**    | **Yes â€” must re-run `build_gravity_features.py`** with `decay_epsilon: 0.02`                                                                                                                                              |
| **Code/data changes** | **Parquet change required:**                                                                                                                                                                                              |
|                       | 1. Edit `config.yaml`: change `gravity_model.decay_epsilon` from `0.05` to `0.02`                                                                                                                                         |
|                       | 2. Re-run `python pipeline/gold/build_gravity_features.py` â†’ regenerates `gravity_features.parquet`                                                                                                                       |
|                       | 3. Re-run `python pipeline/gold/build_master_features.py` â†’ regenerates `master_features.parquet`                                                                                                                         |
|                       | 4. Then train                                                                                                                                                                                                             |
| **Expected RMSE**     | May improve if closer POIs deserve more extreme weighting                                                                                                                                                                 |

```bash
# Step 1: Update config.yaml (decay_epsilon: 0.05 â†’ 0.02)
# Step 2: Rebuild gravity features
python pipeline/gold/build_gravity_features.py
python pipeline/gold/build_master_features.py
# Step 3: Train
python modelling/train.py --strategy strategyA --notes "Epsilon=0.02 gravity rebuild"
```

> [!WARNING]
> **This scenario modifies `gravity_features.parquet` and `master_features.parquet`.** After testing, you MUST revert `config.yaml` back to `decay_epsilon: 0.05` and re-run the gravity + master feature pipeline to restore the original data for other scenarios. Alternatively, back up the parquets before changing epsilon.

**Transition to Scenario 9:** Revert config, rebuild parquets, then switch strategy.

---

#### Scenario 9: Optuna Hyperparameter Re-tuning (CatBoost)

| Item                  | Detail                                                                                                                                                                                                                                                                         |
| --------------------- | ------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------ |
| **Purpose**           | The Round 1 Optuna params were tuned with leak features. The optimal params will be different without them â€” per [modelling_strategy.md #5](file:///c:/Users/sithu/My%20Works/My%20Softwares/Competitions/DataStorm3_ML_DS/BigBugDataStorm/docs/modelling_strategy.md#L32-L34) |
| **Strategy**          | `strategyA` (or whichever performed best in Scenarios 2-7)                                                                                                                                                                                                                     |
| **Algorithm**         | CatBoost (GPU)                                                                                                                                                                                                                                                                 |
| **Excluded features** | Same as the best strategy                                                                                                                                                                                                                                                      |
| **Target**            | Same formula                                                                                                                                                                                                                                                                   |
| **Custom scripts**    | **Yes â€” `modelling/optuna_tune.py`** (new script)                                                                                                                                                                                                                              |
| **Code/data changes** | New script that runs 50 Optuna trials, saves the best params, then trains with them                                                                                                                                                                                            |
| **Expected RMSE**     | 2-5% lower than the un-tuned version of the same strategy                                                                                                                                                                                                                      |

```bash
# Step 1: Run Optuna tuning (50 trials, ~5-10 min on GPU)
python modelling/optuna_tune.py --strategy strategyA --n-trials 50

# Step 2: Train with the best found params
python modelling/train.py --strategy strategyA --use-optuna-params --notes "Optuna re-tuned (50 trials)"
```

**Transition to Scenario 10:** Decide on the best single-model result first.

---

#### Scenario 10: Model Ensemble (Blending)

| Item                  | Detail                                                                                                                                                                                                                            |
| --------------------- | --------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| **Purpose**           | Blend the 2-3 best single models for a final RMSE improvement â€” per [modelling_strategy.md #7](file:///c:/Users/sithu/My%20Works/My%20Softwares/Competitions/DataStorm3_ML_DS/BigBugDataStorm/docs/modelling_strategy.md#L46-L48) |
| **Strategy**          | N/A (uses predictions from multiple prior runs)                                                                                                                                                                                   |
| **Algorithm**         | Weighted average of 2-3 models                                                                                                                                                                                                    |
| **Custom scripts**    | **Yes â€” `modelling/ensemble.py`** (new script)                                                                                                                                                                                    |
| **Code/data changes** | New script that:                                                                                                                                                                                                                  |
|                       | 1. Loads `predictions.csv` from 2-3 selected run folders                                                                                                                                                                          |
|                       | 2. Blends them: e.g. `0.5 Ã— CatBoost + 0.3 Ã— XGBoost + 0.2 Ã— LightGBM`                                                                                                                                                            |
|                       | 3. Applies the baseline floor (same `max(blend, baseline)` logic)                                                                                                                                                                 |
|                       | 4. Saves the blended result as a new run in `run_registry.csv`                                                                                                                                                                    |
| **Expected RMSE**     | 2-5% lower than the best single model                                                                                                                                                                                             |

```bash
# Step 1: Identify the 2-3 best runs from the registry
python -c "import pandas as pd; print(pd.read_csv('modelling/artifacts/run_registry.csv').sort_values('cv_rmse_mean').head(5))"

# Step 2: Run ensemble blending
python modelling/ensemble.py \
  --runs run_20260531_0100_catboost_strategyA,run_20260531_0200_xgboost_strategyA \
  --weights 0.6,0.4 \
  --notes "CatBoost 60% + XGBoost 40% blend"
```

---

### Scenario Summary Table

| #   | Strategy                 | Algorithm | Key Difference                 | Custom Scripts   | Data Rebuild? |
| --- | ------------------------ | --------- | ------------------------------ | ---------------- | ------------- |
| 1   | `round1_baseline`        | CatBoost  | Reference (leak features kept) | None             | No            |
| 2   | `strategyA`              | CatBoost  | **Remove 4 leak features**     | None             | No            |
| 3   | `strategyA`              | XGBoost   | Algorithm comparison           | None             | No            |
| 4   | `strategyA`              | LightGBM  | Algorithm comparison           | None             | No            |
| 5   | `strategyC`              | CatBoost  | + Interaction features         | None             | No            |
| 6   | `strategyA_gravity_only` | CatBoost  | Drop flat POI counts           | None             | No            |
| 7   | `strategyA_flat_only`    | CatBoost  | Drop gravity scores            | None             | No            |
| 8   | `strategyA`              | CatBoost  | Îµ = 0.02 gravity rebuild       | None             | **Yes** âš ï¸    |
| 9   | Best from 2-7            | CatBoost  | Optuna re-tuning               | `optuna_tune.py` | No            |
| 10  | Ensemble                 | Blend     | Weighted model average         | `ensemble.py`    | No            |

### Recommended Execution Order

```
Scenario 1 â†’ 2 â†’ 3 â†’ 4 â†’ 5 â†’ 6 â†’ 7 â†’ [Compare 2-7] â†’ 9 â†’ 10
                                          â†“
                                    (Only if time permits)
                                          8
```

> [!TIP]
> Scenarios 1-7 require **zero code changes** between runs â€” just different CLI flags. Scenario 8 needs a data rebuild (revert after). Scenarios 9-10 each need one small new script.

