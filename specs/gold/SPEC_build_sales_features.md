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
| transactions_clean.parquet | `Data/Silver/transactions_clean.parquet` |
| outlet_master_clean.parquet | `Data/Silver/outlet_master_clean.parquet` |

## Outputs

| File | Path |
|------|------|
| sales_features.parquet | `Data/Gold/sales_features.parquet` |

---

## Performance Architecture

The script uses **vectorized pandas operations** instead of per-outlet Python loops.
The key optimization is building a single **outlet × period grid** (a cross-join of
all outlet IDs with all months in the data range), then merging actual transaction
data onto it and filling gaps with zeros. This allows all statistical aggregations
to run as bulk `groupby().agg()` calls, reducing runtime from ~15–30 minutes to
~30–60 seconds (~20–30× speedup).

---

## Step-by-step logic

### Step 1 — Load inputs

```python
txn  = pd.read_parquet(SILVER / "transactions_clean.parquet")
outlets = pd.read_parquet(SILVER / "outlet_master_clean.parquet")[["Outlet_ID"]]
```

### Step 2 — Build monthly aggregation

Create a monthly summary table — one row per (Outlet_ID, Year, Month).
Exclude `is_blackout_period = True` rows from volume calculations but keep
them in the activity timeline (so blackout months count as months in the data range).

```python
txn_valid = txn[~txn["is_blackout_period"]]
monthly = txn_valid.groupby(["Outlet_ID", "Year", "Month"], as_index=False).agg(
    monthly_volume=("Volume_Litres", "sum"),
    transaction_count=("Volume_Litres", "count"),
)
```

### Step 3 — Compute the full time range

```python
data_start = pd.Period(f"{txn['Year'].min()}-{txn['Month'].min():02d}", freq="M")
data_end   = pd.Period(f"{txn['Year'].max()}-{txn['Month'].max():02d}", freq="M")
total_months_in_data = (data_end - data_start).n + 1
```

### Step 4 — Build the complete outlet × period grid (Vectorized)

Instead of reindexing per outlet in a loop, build a single cross-join DataFrame
with every `(Outlet_ID, period)` combination, then left-merge actual monthly data
onto it and fill missing volumes with 0:

```python
grid = pd.MultiIndex.from_product([outlet_ids, all_periods], names=["Outlet_ID", "period"])
full = grid.to_frame(index=False)
full = full.merge(monthly[["Outlet_ID", "period", "monthly_volume"]], ...)
full["monthly_volume"] = full["monthly_volume"].fillna(0.0)
```

This eliminates 20,000 individual DataFrame filter + reindex operations.

### Step 4a — Vectorized basic stats via groupby().agg()

A single `groupby("Outlet_ID").agg(...)` computes all simple statistics at once:

| Feature | Formula | Business rationale |
|---------|---------|-------------------|
| `hist_max_monthly` | `max()` | Hard ceiling observed in history |
| `hist_p90_monthly` | `quantile(0.90)` | Robust ceiling (main demand proxy) |
| `hist_p75_monthly` | `quantile(0.75)` | Secondary ceiling signal |
| `hist_mean_monthly` | `mean()` | Average operating level |
| `hist_std_monthly` | `std()` | Variability |
| `hist_cv` | `std / mean` if mean > 0 else 0 | Coefficient of variation — consistency |
| `active_months` | Count of months with volume > 0 | How many months actually ordered |
| `active_months_pct` | `active_months / total_months_in_data` | Fraction of possible months active |
| `total_volume` | `sum()` | Lifetime value |

### Step 4b — January features via filtered groupby

Filter the full grid to `Month == 1` once, then groupby:

| Feature | Formula |
|---------|---------|
| `jan_avg_volume` | Mean of January monthly_volumes across all years |
| `jan_max_volume` | Max of January monthly_volumes |
| `jan_count` | Number of January observations with volume > 0 |

### Step 4c — Sequential features via groupby().apply()

These genuinely need per-group sequential logic and use a single
`groupby().apply()` that returns all features at once:

| Feature | Formula | Notes |
|---------|---------|-------|
| `consecutive_zero_months_max` | Longest run of zero-volume months | Measures supply disruption severity |
| `months_since_last_order` | Distance from last non-zero month to data end | Recency of activity |
| `recent_3m_avg` | Average of last 3 months of data | Current trajectory |
| `trend_slope` | Linear regression slope on monthly volumes | Null if <6 data points |
| `yoy_growth_rate` | `(avg_last_year - avg_first_year) / avg_first_year` | Null if <2 full years |
| `ema_3m` | 3-month exponential moving average | Recent momentum with exponential decay |
| `ema_6m` | 6-month exponential moving average | Medium-term trajectory |

### Step 4d — Distributor assignment via groupby

```python
dist = txn.groupby("Outlet_ID")["Distributor_ID"].agg(lambda x: x.value_counts().idxmax())
```

Most frequent distributor for each outlet. Missing distributors (outlets with no
transactions) are filled with the global mode distributor.

### Step 5 — Handle outlets with no transactions

Left-join computed features back to the full 20,000-outlet list:
```python
features_df = outlets.merge(computed, on="Outlet_ID", how="left")
```

Fill null numeric features with 0 for inactive outlets. Fill `distributor_id` with
the global mode (most common distributor across all outlets).

`yoy_growth_rate` and `trend_slope` remain null where not computable (contract allows null).

### Step 6 — Write output

```python
features_df.to_parquet(GOLD / "sales_features.parquet", index=False,
                        engine="pyarrow", compression="snappy")
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

Expected runtime: ~30–60 seconds (vectorized implementation).

## Dependencies

- pandas, numpy, pyarrow, pyyaml, scipy
- Standard library: logging, time
