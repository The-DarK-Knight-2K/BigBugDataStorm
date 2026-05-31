# SPEC: predict.py

> [!IMPORTANT]
> **Round 2 Architecture Upgrade:** The `predict.py` script supports Run Tracking via `--run-id`, automatic interaction feature computation, multi-algorithm decoding, and ensemble prediction loading via `--predictions-csv`. A custom output path can be specified with `--output-path`.

## Purpose

Generate the final submission CSV by blending the CatBoost model predictions with
the statistical baseline. The final prediction for every outlet is the maximum of
the two approaches, ensuring we never predict below the statistically grounded
floor. Output is `outputs/teamname_predictions.csv`.

## Layer

Modelling

## Inputs

| File                         | Path                                     |
| ---------------------------- | ---------------------------------------- |
| master_features.parquet      | `data/gold/master_features.parquet`      |
| model.pkl                    | `modelling/artifacts/model.pkl`          |
| baseline_predictions.parquet | `data/gold/baseline_predictions.parquet` |

## Outputs

| File                       | Path                                 |
| -------------------------- | ------------------------------------ |
| teamname_predictions.csv   | `outputs/teamname_predictions.csv`   |
| prediction_diagnostics.csv | `outputs/prediction_diagnostics.csv` |

---

## Step-by-step logic

### Step 1 — Load inputs

```python
import pickle

df = pd.read_parquet(GOLD / "master_features.parquet")

with open(ARTIFACTS / "model.pkl", "rb") as f:
    saved = pickle.load(f)
model       = saved["model"]
feature_cols = saved["feature_cols"]

baseline_df = pd.read_parquet(GOLD / "baseline_predictions.parquet")

log.info("Loaded master features: %d rows", len(df))
log.info("Loaded model with %d features", len(feature_cols))
log.info("Loaded baseline predictions: %d rows", len(baseline_df))
```

### Step 2 — Generate model predictions for all 20,000 outlets

```python
X_all = df[feature_cols]
df["model_prediction"] = model.predict(X_all)
log.info("Model predictions — min: %.2f  median: %.2f  max: %.2f",
         df["model_prediction"].min(),
         df["model_prediction"].median(),
         df["model_prediction"].max())
```

### Step 3 — Merge baseline predictions

```python
df = df.merge(baseline_df, on="Outlet_ID", how="left")
assert df["baseline_potential_litres"].isnull().sum() == 0, \
    "Missing baseline predictions for some outlets"
```

### Step 4 — Blend: take the maximum of baseline and model

```python
df["Maximum_Monthly_Liters"] = df[["model_prediction", "baseline_potential_litres"]].max(axis=1)
```

**Rationale:** The baseline encodes hard business logic anchored on **January-specific
historical volumes** and recency momentum — a fundamentally different signal from
the model's all-months P90 pseudo-label. The model may extrapolate higher potential
where structural signals (POI, cooler count, growth trend) justify it. Taking the
maximum of both ensures we always respect the January-grounded floor while
benefiting from the model's learned signal.

### Step 5 — Post-processing and sanity checks

**Minimum floor:** No outlet's potential can be zero or negative:

```python
floor_violations = (df["Maximum_Monthly_Liters"] <= 0).sum()
if floor_violations > 0:
    log.warning("Clamping %d predictions from ≤0 to 1.0", floor_violations)
    df["Maximum_Monthly_Liters"] = df["Maximum_Monthly_Liters"].clip(lower=1.0)
```

**Round to 2 decimal places:**

```python
df["Maximum_Monthly_Liters"] = df["Maximum_Monthly_Liters"].round(2)
```

**Distribution check:** Log decile distribution for sanity inspection:

```python
for q in [0.1, 0.25, 0.5, 0.75, 0.9, 0.95, 0.99]:
    log.info("  P%02d: %.2f litres", int(q*100),
             df["Maximum_Monthly_Liters"].quantile(q))
```

**Outlier flag:** Log any outlet predicting >5× the 99th percentile:

```python
p99 = df["Maximum_Monthly_Liters"].quantile(0.99)
extreme = df[df["Maximum_Monthly_Liters"] > 5 * p99]
if len(extreme) > 0:
    log.warning("Found %d extreme predictions (>5×P99=%.2f):", len(extreme), p99)
    log.warning(extreme[["Outlet_ID", "Maximum_Monthly_Liters"]].to_string())
```

### Step 6 — Write submission CSV

```python
team_name = CFG["team_name"]
output_path = OUTPUTS / f"{team_name}_predictions.csv"

submission = df[["Outlet_ID", "Maximum_Monthly_Liters"]]
submission.to_csv(output_path, index=False)
log.info("Written %d rows → %s", len(submission), output_path)
```

### Step 7 — Write diagnostics CSV

Save an expanded diagnostics file for internal analysis and the PDF report:

```python
diag_cols = [
    "Outlet_ID", "Outlet_Size", "Outlet_Type", "province",
    "Cooler_Count", "hist_p90_monthly", "hist_max_monthly",
    "jan_avg_volume", "has_transaction_history",
    "seasonality_jan_2026", "seasonality_multiplier_jan_2026",
    "footfall_score", "poi_total_1km",
    "model_prediction", "baseline_potential_litres",
    "Maximum_Monthly_Liters",
]
# Only include columns that exist
diag_cols = [c for c in diag_cols if c in df.columns]
df[diag_cols].to_csv(OUTPUTS / "prediction_diagnostics.csv", index=False)
log.info("Written diagnostics → outputs/prediction_diagnostics.csv")
```

---

## Final summary log

```python
log.info("=" * 50)
log.info("PREDICTION SUMMARY")
log.info("  Total outlets predicted : %d", len(submission))
log.info("  Min prediction          : %.2f L", submission["Maximum_Monthly_Liters"].min())
log.info("  Median prediction       : %.2f L", submission["Maximum_Monthly_Liters"].median())
log.info("  Mean prediction         : %.2f L", submission["Maximum_Monthly_Liters"].mean())
log.info("  Max prediction          : %.2f L", submission["Maximum_Monthly_Liters"].max())
log.info("  Baseline-capped (model < baseline): %d outlets",
         (df["baseline_potential_litres"] >= df["model_prediction"]).sum())
log.info("  Model won (model > baseline)      : %d outlets",
         (df["model_prediction"] > df["baseline_potential_litres"]).sum())
log.info("=" * 50)
```

---

## Assertions before writing

```python
assert len(submission) == 20000, f"Expected 20000 rows, got {len(submission)}"
assert list(submission.columns) == ["Outlet_ID", "Maximum_Monthly_Liters"], \
    "Submission columns must be exactly [Outlet_ID, Maximum_Monthly_Liters]"
assert submission["Outlet_ID"].duplicated().sum() == 0, "Duplicate Outlet_IDs"
assert submission["Outlet_ID"].isnull().sum() == 0
assert submission["Maximum_Monthly_Liters"].isnull().sum() == 0
assert (submission["Maximum_Monthly_Liters"] > 0).all(), \
    "All predictions must be positive"
```

---

## CLI usage

```bash
# Single model inference (legacy)
python modelling/predict.py

# Single model from a specific run
python modelling/predict.py --run-id run_20260531_062548_xgboost_strategyA_gravity_only

# Ensemble: load pre-blended predictions CSV and write to a custom path
python modelling/predict.py --predictions-csv modelling/artifacts/runs/ensemble_predictions.csv --output-path outputs/round2/bigbug_predictions.csv
```

### Arguments

| Flag | Type | Default | Description |
|------|------|---------|-------------|
| `--run-id` | str | None | Load model from a specific run folder |
| `--predictions-csv` | str | None | Path to existing CSV with `Outlet_ID` and `model_prediction` columns (bypasses model loading/inference) |
| `--output-path` | str | None | Custom output path for the submission CSV (default: `outputs/{team_name}_predictions.csv`) |

## Dependencies

- pandas, numpy, pyarrow, pyyaml
- Standard library: pickle, logging, argparse
