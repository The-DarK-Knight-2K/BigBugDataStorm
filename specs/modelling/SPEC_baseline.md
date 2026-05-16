# SPEC: baseline.py

## Purpose

Compute a statistically grounded, business-logic-driven baseline estimate of
maximum monthly purchase potential for every outlet. This baseline:
1. Is used as a floor — the ML model prediction is never allowed to go below it.
2. Is independently defensible to judges without any ML.
3. Uses **January-specific historical volumes** as the primary signal (Direct Month
   strategy — see `docs/target_generation_strategies.md` Approach 1), making it
   fundamentally different from the model's all-months P90 pseudo-label.

## Layer
Modelling

## Inputs

| File | Path |
|------|------|
| master_features.parquet | `data/gold/master_features.parquet` |

## Outputs

| Return value | Type | Description |
|-------------|------|-------------|
| `baseline_df` | pd.DataFrame | Outlet_ID + baseline_potential_litres |

The baseline is returned in-memory for use by `predict.py`. Optionally also save
to `data/gold/baseline_predictions.parquet` for inspection.

---

## Design rationale — why January-anchored?

The `train.py` pseudo-label is constructed from `hist_p90_monthly` (the 90th
percentile across **all** months). If the baseline also used `hist_p90_monthly`,
the `max(model, baseline)` blend in `predict.py` would be comparing two nearly
identical signals — defeating the purpose of having a safety floor.

Instead, the baseline anchors on **January-specific history** (`jan_avg_volume`,
`jan_max_volume`), which directly captures seasonal patterns unique to January
(post-holiday restocking, Thai Pongal effects, etc.). This ensures the baseline
and the model are genuinely independent estimators:

- **Baseline** = "What did this outlet actually do in past Januaries, adjusted
  for current momentum?"
- **Model** = "Given all structural, spatial, and temporal features, what is the
  predicted demand ceiling?"

---

## Step-by-step logic

### Step 1 — Load master features and compute data-driven cold-start lookup

```python
df = pd.read_parquet(GOLD / "master_features.parquet")
log.info("Loaded %d rows from master_features", len(df))

# Data-driven cold-start: compute median January volume per Outlet_Size
# from outlets that actually have January history (jan_count > 0).
# This replaces hardcoded SIZE_BASE constants with empirical values.
size_medians = (
    df[df["jan_count"] > 0]
    .groupby("Outlet_Size")["jan_avg_volume"]
    .median()
    .to_dict()
)
global_median = df.loc[df["jan_count"] > 0, "jan_avg_volume"].median()
log.info("Data-driven cold-start medians by size: %s", size_medians)
log.info("Global median fallback: %.2f", global_median)
```

### Step 2 — Compute baseline potential (January-anchored)

```python
AVG_TRADING_DAYS_PER_MONTH = 22.0   # standard assumption for a working month

def compute_baseline(row: pd.Series) -> float:
    """
    Baseline = jan_demand × recency_factor × seasonality × trading_ratio × POI uplift

    The primary signal is January-specific history, NOT the all-months P90
    used by train.py. This ensures genuine independence between the baseline
    floor and the model prediction.
    """
    # --- (A) January-Anchored Demand ---
    # Prefer January-specific history when available
    if row["jan_count"] > 0:
        # Take the higher of: January average, or 85% of January max
        # (the 0.85 dampening avoids anchoring on a one-off spike)
        jan_demand = max(row["jan_avg_volume"],
                         row["jan_max_volume"] * 0.85)
    elif row["has_transaction_history"]:
        # Outlet has history but never ordered in January — fall back to P90
        jan_demand = row["hist_p90_monthly"]
    else:
        # No history at all — use data-driven cold-start
        jan_demand = _estimate_cold_start_potential(row, size_medians, global_median)

    # --- (B) Recency-Weighted Momentum Adjustment ---
    # If the outlet is trending up (ema_3m > hist_mean), the floor should
    # reflect that momentum. If trending down, dampen but don't collapse.
    recency_factor = _compute_recency_factor(row)

    # Seasonality adjustment
    season_mult = row["seasonality_multiplier_jan_2026"]   # 0.85 / 1.00 / 1.20

    # Trading-day adjustment
    trading_ratio = row["jan_2026_trading_days"] / AVG_TRADING_DAYS_PER_MONTH

    # POI uplift: outlets with high footfall scores get a small additional factor
    poi_uplift = _compute_poi_uplift(row["footfall_score"])

    baseline = jan_demand * recency_factor * season_mult * trading_ratio * poi_uplift

    # Floor: potential cannot be less than the outlet's all-time maximum
    # (avoids regressing below observed reality)
    baseline = max(baseline, row["hist_max_monthly"])

    return round(float(baseline), 2)
```

### Step 3 — Recency-weighted momentum factor

```python
def _compute_recency_factor(row: pd.Series) -> float:
    """
    Compares the 3-month EMA to the historical mean to detect momentum.

    - If ema_3m is 30% above hist_mean → factor = 1.3 (outlet is growing)
    - If ema_3m equals hist_mean       → factor = 1.0 (stable)
    - If ema_3m is 20% below hist_mean → factor = 0.8 (declining, but clamped)

    For outlets with no meaningful history (hist_mean ≈ 0), returns 1.0.
    """
    hist_mean = row["hist_mean_monthly"]
    ema = row["ema_3m"]

    if hist_mean <= 0 or ema <= 0:
        return 1.0

    ratio = ema / hist_mean
    # Clamp between 0.8 and 1.3 to prevent extreme swings
    return max(0.8, min(ratio, 1.3))
```

### Step 4 — Data-driven cold-start estimation

```python
def _estimate_cold_start_potential(row: pd.Series, size_medians: dict,
                                    global_median: float) -> float:
    """
    For outlets with no transaction history, estimate demand using the median
    January volume of outlets with the same Outlet_Size. This is empirically
    grounded (derived from actual data) rather than using hardcoded constants.

    A Cooler_Count multiplier is applied as a capacity proxy:
    more coolers → higher storage → higher potential throughput.
    """
    base = size_medians.get(row["Outlet_Size"], global_median)
    cooler_multiplier = 1.0 + (row["Cooler_Count"] * 0.15)
    return base * cooler_multiplier
```

### Step 5 — POI uplift calculation

```python
def _compute_poi_uplift(footfall_score: float) -> float:
    """
    Footfall score is 0–100.
    Low footfall  (0–20)   → no uplift (1.00)
    Medium        (20–60)  → small uplift up to 1.10
    High          (60–100) → uplift up to 1.25

    Rationale: an outlet in a high-traffic area (near a bus terminal + school)
    has more potential customers than its historical sales suggest — especially
    if it has been supply-constrained in the past.
    """
    if footfall_score <= 20:
        return 1.00
    elif footfall_score <= 60:
        return 1.00 + ((footfall_score - 20) / 40) * 0.10
    else:
        return 1.10 + ((footfall_score - 60) / 40) * 0.15
```

### Step 6 — Apply and validate

```python
df["baseline_potential_litres"] = df.apply(compute_baseline, axis=1)

log.info("Baseline statistics:")
log.info("  Min    : %.2f", df["baseline_potential_litres"].min())
log.info("  Median : %.2f", df["baseline_potential_litres"].median())
log.info("  Mean   : %.2f", df["baseline_potential_litres"].mean())
log.info("  P90    : %.2f", df["baseline_potential_litres"].quantile(0.90))
log.info("  Max    : %.2f", df["baseline_potential_litres"].max())

# Log how many outlets used each estimation path
jan_path   = (df["jan_count"] > 0) & df["has_transaction_history"]
p90_path   = (df["jan_count"] == 0) & df["has_transaction_history"]
cold_path  = ~df["has_transaction_history"]
log.info("Estimation paths — January-anchored: %d, P90 fallback: %d, Cold-start: %d",
         jan_path.sum(), p90_path.sum(), cold_path.sum())
```

### Step 7 — Save and return

```python
baseline_df = df[["Outlet_ID", "baseline_potential_litres"]]
baseline_df.to_parquet(GOLD / "baseline_predictions.parquet", index=False,
                        engine="pyarrow", compression="snappy")
log.info("Saved baseline predictions → baseline_predictions.parquet")
return baseline_df
```

---

## Assertions

```python
assert len(baseline_df) == 20000
assert baseline_df["baseline_potential_litres"].isnull().sum() == 0
assert (baseline_df["baseline_potential_litres"] > 0).all(), \
    "All baseline predictions must be positive"
assert baseline_df["Outlet_ID"].duplicated().sum() == 0
```

---

## CLI usage

```bash
python modelling/baseline.py
```

(Can also be called as a module from `predict.py`.)

## Dependencies

- pandas, numpy, pyarrow, pyyaml
- Standard library: logging
