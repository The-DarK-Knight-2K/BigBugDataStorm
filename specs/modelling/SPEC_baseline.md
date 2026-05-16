# SPEC: baseline.py

## Purpose

Compute a statistically grounded, business-logic-driven baseline estimate of
maximum monthly purchase potential for every outlet. This baseline:
1. Is used as a floor — the ML model prediction is never allowed to go below it.
2. Is independently defensible to judges without any ML.
3. Encodes the core "censored demand uncapping" logic that is central to the
   competition's methodology requirement.

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

## The uncapping logic — business rationale

Historical volume is a **censored lower bound** on true demand. An outlet that
sold 100 litres in its best month may have had customers willing to buy 150 litres
— but the delivery truck ran out. We "uncap" by:

1. Taking the 90th percentile historical monthly volume as the observed demand
   ceiling (more robust than the raw max, which may be a one-off spike).
2. Adjusting for the fact that January 2026 may be more or less active than the
   average month (seasonality multiplier).
3. Adjusting for the number of trading days in January 2026 vs the average month.
4. Adding a structural uplift for outlets with high-footfall POI environments that
   have not yet reached their demand ceiling.

---

## Step-by-step logic

### Step 1 — Load master features

```python
df = pd.read_parquet(GOLD / "master_features.parquet")
log.info("Loaded %d rows from master_features", len(df))
```

### Step 2 — Compute baseline potential

```python
AVG_TRADING_DAYS_PER_MONTH = 22.0   # standard assumption for a working month

def compute_baseline(row: pd.Series) -> float:
    """
    Baseline = P90 historical × seasonality × trading-day ratio × POI uplift
    """
    p90 = row["hist_p90_monthly"]

    # For outlets with no transaction history, use a small non-zero floor
    if p90 == 0 or not row["has_transaction_history"]:
        p90 = _estimate_cold_start_potential(row)

    # Seasonality adjustment
    season_mult = row["seasonality_multiplier_jan_2026"]   # 0.85 / 1.00 / 1.20

    # Trading-day adjustment
    trading_ratio = row["jan_2026_trading_days"] / AVG_TRADING_DAYS_PER_MONTH

    # POI uplift: outlets with high footfall scores get a small additional factor
    poi_uplift = _compute_poi_uplift(row["footfall_score"])

    baseline = p90 * season_mult * trading_ratio * poi_uplift

    # Floor: potential cannot be less than the outlet's all-time maximum
    # (avoids regressing below observed reality)
    baseline = max(baseline, row["hist_max_monthly"])

    return round(float(baseline), 2)
```

### Step 3 — Cold-start estimation for outlets with no history

```python
def _estimate_cold_start_potential(row: pd.Series) -> float:
    """
    For outlets with no transaction history, estimate using outlet structural
    characteristics — size and cooler count as proxies for capacity.
    """
    SIZE_BASE = {
        "Small":       50.0,
        "Medium":     120.0,
        "Large":      250.0,
        "Extra Large":450.0,
    }
    base = SIZE_BASE.get(row["Outlet_Size"], 80.0)
    cooler_multiplier = 1.0 + (row["Cooler_Count"] * 0.15)
    return base * cooler_multiplier
```

### Step 4 — POI uplift calculation

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

### Step 5 — Apply and validate

```python
df["baseline_potential_litres"] = df.apply(compute_baseline, axis=1)

log.info("Baseline statistics:")
log.info("  Min    : %.2f", df["baseline_potential_litres"].min())
log.info("  Median : %.2f", df["baseline_potential_litres"].median())
log.info("  Mean   : %.2f", df["baseline_potential_litres"].mean())
log.info("  P90    : %.2f", df["baseline_potential_litres"].quantile(0.90))
log.info("  Max    : %.2f", df["baseline_potential_litres"].max())
```

### Step 6 — Save and return

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
