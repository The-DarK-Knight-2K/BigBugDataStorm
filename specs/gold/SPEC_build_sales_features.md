# SPEC: build_sales_features.py

## Purpose

Aggregate the cleaned transactions into outlet-level features that capture each
outlet's historical demand pattern. This is the most analytically important script
in the pipeline — it produces the features that directly inform the latent potential
estimate. Every feature must be documented with its business rationale.

## Layer
Gold

## Inputs

| File | Path |
|------|------|
| transactions_clean.parquet | `data/silver/transactions_clean.parquet` |
| outlet_master_clean.parquet | `data/silver/outlet_master_clean.parquet` |

## Outputs

| File | Path |
|------|------|
| sales_features.parquet | `data/gold/sales_features.parquet` |

---

## Step-by-step logic

### Step 1 — Load inputs

```python
txn  = pd.read_parquet(SILVER / "transactions_clean.parquet")
outlets = pd.read_parquet(SILVER / "outlet_master_clean.parquet")[["Outlet_ID"]]
log.info("Loaded %d transaction rows for %d unique outlets",
         len(txn), txn["Outlet_ID"].nunique())
```

### Step 2 — Build monthly aggregation

Create a monthly summary table — one row per (Outlet_ID, Year, Month):

```python
monthly = (
    txn
    .groupby(["Outlet_ID", "Year", "Month"], as_index=False)
    .agg(
        monthly_volume=("Volume_Litres", "sum"),
        transaction_count=("Volume_Litres", "count"),
    )
)
```

Note: Exclude `is_blackout_period = True` rows from volume calculations but keep
them in the activity timeline (so blackout months count as months in the data range).

```python
txn_valid_volume = txn[~txn["is_blackout_period"]]
monthly = txn_valid_volume.groupby(...)
```

### Step 3 — Compute the full time range of the dataset

```python
data_start = pd.Period(f"{txn['Year'].min()}-{txn['Month'].min():02d}", freq="M")
data_end   = pd.Period(f"{txn['Year'].max()}-{txn['Month'].max():02d}", freq="M")
total_months_in_data = (data_end - data_start).n + 1
log.info("Data spans %d months (%s to %s)", total_months_in_data, data_start, data_end)
```

### Step 4 — Compute per-outlet features

For each outlet, compute the following. Use `.groupby("Outlet_ID").apply(...)` or
loop with a results dict — whichever is clearer.

---

#### 4a — Historical volume statistics

| Feature | Formula | Business rationale |
|---------|---------|-------------------|
| `hist_max_monthly` | `monthly_volume.max()` | Hard ceiling observed in history |
| `hist_p90_monthly` | `monthly_volume.quantile(0.90)` | Robust ceiling (main demand proxy) |
| `hist_p75_monthly` | `monthly_volume.quantile(0.75)` | Secondary ceiling signal |
| `hist_mean_monthly` | `monthly_volume.mean()` | Average operating level |
| `hist_std_monthly` | `monthly_volume.std()` | Variability |
| `hist_cv` | `std / mean` if mean > 0 else 0 | Coefficient of variation — consistency |

---

#### 4b — January-specific features

Filter to Month == 1 rows only:
```python
jan_data = monthly[monthly["Month"] == 1]
```

| Feature | Formula |
|---------|---------|
| `jan_avg_volume` | Mean of January monthly_volumes across all years |
| `jan_max_volume` | Max of January monthly_volumes |
| `jan_count` | Number of January observations |

If an outlet has no January data (new outlet or always inactive in Jan):
`jan_avg_volume = 0, jan_max_volume = 0, jan_count = 0`

---

#### 4c — Activity and recency features

| Feature | Formula | Notes |
|---------|---------|-------|
| `active_months` | Count of months with `monthly_volume > 0` | How many months actually ordered |
| `active_months_pct` | `active_months / total_months_in_data` | Fraction of possible months active |
| `consecutive_zero_months_max` | Longest run of zero-volume months | Measures supply disruption severity |
| `months_since_last_order` | Months between last non-zero month and data end | Recency of activity |
| `total_volume` | Sum of all `Volume_Litres` for this outlet | Lifetime value |

**Computing `consecutive_zero_months_max`:**
```python
def max_consecutive_zeros(monthly_volumes: pd.Series) -> int:
    max_run = 0
    current_run = 0
    for v in monthly_volumes:
        if v == 0:
            current_run += 1
            max_run = max(max_run, current_run)
        else:
            current_run = 0
    return max_run
```

---

#### 4d — Growth and trend features

| Feature | Formula | Notes |
|---------|---------|-------|
| `yoy_growth_rate` | `(avg_2025 - avg_2023) / avg_2023` | Null if <2 full years |
| `recent_3m_avg` | Average of last 3 months of data | Captures current trajectory |
| `trend_slope` | Linear regression slope on monthly volumes | Positive = growing outlet |

**Computing `trend_slope`:**
```python
from scipy.stats import linregress

def compute_trend_slope(monthly_volumes: pd.Series) -> float | None:
    if len(monthly_volumes) < 6:
        return None
    x = np.arange(len(monthly_volumes))
    slope, _, _, _, _ = linregress(x, monthly_volumes.values)
    return float(slope)
```

**Computing `yoy_growth_rate`:**
```python
def yoy_growth(monthly_df: pd.DataFrame) -> float | None:
    avg_by_year = monthly_df.groupby("Year")["monthly_volume"].mean()
    years = sorted(avg_by_year.index)
    if len(years) < 2:
        return None
    first_year_avg = avg_by_year[years[0]]
    last_year_avg  = avg_by_year[years[-1]]
    if first_year_avg == 0:
        return None
    return (last_year_avg - first_year_avg) / first_year_avg
```

---

#### 4e — Exponential Moving Averages (EMA)

| Feature | Formula | Business rationale |
|---------|---------|-------------------|
| `ema_3m` | 3-month EMA of `monthly_volume` | Captures recent momentum with exponential decay |
| `ema_6m` | 6-month EMA of `monthly_volume` | Captures medium-term trajectory |

```python
def compute_ema(monthly_volumes: pd.Series, span: int) -> float:
    if len(monthly_volumes) == 0:
        return 0.0
    return float(monthly_volumes.ewm(span=span, adjust=False).mean().iloc[-1])
```

---

#### 4f — Distributor assignment

```python
distributor_id = (
    txn[txn["Outlet_ID"] == outlet_id]["Distributor_ID"]
    .value_counts().idxmax()
)
```
(Most frequent distributor for this outlet.)

---

### Step 5 — Handle outlets with no transactions

Some outlets in `outlet_master_clean` may have zero transaction history (new or
inactive outlets). They must still appear in `sales_features.parquet`.

After computing features for outlets that have transactions, left-join back to the
full outlet list:
```python
features_df = outlets.merge(computed_features, on="Outlet_ID", how="left")
```

Fill null numeric features with 0 for inactive outlets. Fill `distributor_id` with
the global mode (most common distributor across all outlets). The province column
is derived from the distributor downstream, so it cannot be used for imputation here.

### Step 6 — Write output

```python
features_df.to_parquet(GOLD / "sales_features.parquet", index=False,
                        engine="pyarrow", compression="snappy")
log.info("Written %d rows → sales_features.parquet", len(features_df))
```

---

## Assertions before writing

```python
assert len(features_df) == 20000, f"Expected 20000 rows, got {len(features_df)}"
assert features_df["Outlet_ID"].duplicated().sum() == 0
assert features_df["Outlet_ID"].isnull().sum() == 0
assert features_df["hist_p90_monthly"].isnull().sum() == 0
assert (features_df["hist_p90_monthly"] >= 0).all()
assert (features_df["active_months_pct"].between(0, 1)).all()
```

---

## CLI usage

```bash
python pipeline/gold/build_sales_features.py
```

## Dependencies

- pandas, numpy, pyarrow, pyyaml, scipy
- Standard library: logging
