# SPEC: build_master_features.py

## Purpose

Merge all Silver-layer cleaned datasets and Gold-layer feature tables into a
single, model-ready DataFrame with one row per outlet. This is the final step
before modelling. Every outlet (all 20,000) must appear in the output.

## Layer
Gold

## Inputs

| File | Path |
|------|------|
| outlet_master_clean.parquet | `data/silver/outlet_master_clean.parquet` |
| outlet_coordinates_clean.parquet | `data/silver/outlet_coordinates_clean.parquet` |
| seasonality_clean.parquet | `data/silver/seasonality_clean.parquet` |
| holidays_clean.parquet | `data/silver/holidays_clean.parquet` |
| jan_2026_trading_days.json | `data/silver/jan_2026_trading_days.json` |
| sales_features.parquet | `data/gold/sales_features.parquet` |
| poi_features.parquet | `data/gold/poi_features.parquet` |

## Outputs

| File | Path |
|------|------|
| master_features.parquet | `data/gold/master_features.parquet` |

---

## Step-by-step logic

### Step 1 — Load all inputs

Load every input file. Log row counts for each.

```python
outlets   = pd.read_parquet(SILVER / "outlet_master_clean.parquet")
coords    = pd.read_parquet(SILVER / "outlet_coordinates_clean.parquet")
season    = pd.read_parquet(SILVER / "seasonality_clean.parquet")
sales_ft  = pd.read_parquet(GOLD   / "sales_features.parquet")
poi_ft    = pd.read_parquet(GOLD   / "poi_features.parquet")

with open(SILVER / "jan_2026_trading_days.json") as f:
    trading_days_info = json.load(f)

jan_2026_trading_days  = trading_days_info["jan_2026_trading_days"]
jan_2026_holiday_count = trading_days_info["jan_2026_holiday_count"]
```

### Step 2 — Build the province lookup

Derive province from Distributor_ID using the static mapping:

```python
DIST_TO_PROVINCE = {
    "DIST_W_01": "Western",   "DIST_W_02": "Western",   "DIST_W_03": "Western",
    "DIST_C_01": "Central",   "DIST_C_02": "Central",   "DIST_C_03": "Central",
    "DIST_NW_01":"North-Western", "DIST_NW_02":"North-Western",
    "DIST_S_01": "Southern",  "DIST_S_02": "Southern",
}
```

Apply to `sales_features["distributor_id"]` to add `province` column.

### Step 3 — Build January 2026 seasonality lookup

Filter seasonality to Jan 2026:
```python
jan_2026_season = season[
    (season["Year"] == 2026) & (season["Month"] == 1)
][["Distributor_ID", "Seasonality_Index"]].rename(
    columns={"Seasonality_Index": "seasonality_jan_2026"}
)
```

Convert text to numeric multiplier:
```python
SEASON_MULTIPLIER = {
    "Favorable":    1.20,
    "Moderate":     1.00,
    "Un-Favorable": 0.85,
}
jan_2026_season["seasonality_multiplier_jan_2026"] = \
    jan_2026_season["seasonality_jan_2026"].map(SEASON_MULTIPLIER)
```

### Step 4 — Merge all datasets

Start from `outlets` as the base (this guarantees all 20,000 outlets are present).
Use LEFT JOIN for every merge.

```python
df = outlets.copy()                                          # 20,000 rows

# Merge coordinates
df = df.merge(
    coords[["Outlet_ID", "Latitude", "Longitude", "coords_swapped"]],
    on="Outlet_ID", how="left"
)

# Merge sales features (drop Outlet_ID from right to avoid duplication)
df = df.merge(sales_ft, on="Outlet_ID", how="left")

# Merge POI features
df = df.merge(poi_ft, on="Outlet_ID", how="left")

# Merge seasonality: join on distributor_id from sales_features
df = df.merge(
    jan_2026_season,
    left_on="distributor_id",
    right_on="Distributor_ID",
    how="left"
).drop(columns=["Distributor_ID"])
```

### Step 5 — Add scalar features

```python
df["jan_2026_holiday_count"] = jan_2026_holiday_count       # scalar, same for all
df["jan_2026_trading_days"]  = jan_2026_trading_days        # scalar, same for all
```

### Step 6 — Derive province column

```python
df["province"] = df["distributor_id"].map(DIST_TO_PROVINCE)
```

### Step 7 — Handle nulls from left joins

**`coords_swapped`:** The ~40 quarantined outlets are missing from
`outlet_coordinates_clean.parquet`, so `coords_swapped` will be NaN after the
LEFT JOIN. Fill with `False` (they weren't swapped — they were absent).

```python
df["coords_swapped"] = df["coords_swapped"].fillna(False)
```

**Coordinates:** ~40 outlets with zero coordinates will have null Latitude/Longitude.
Fill with province centroid coordinates as approximations:

```python
PROVINCE_CENTROIDS = {
    "Western":       (6.9271, 79.8612),
    "Central":       (7.2906, 80.6337),
    "North-Western": (7.7102, 80.0078),
    "Southern":      (6.0535, 80.2210),
}
# Flag outlets with no valid coordinates to be excluded from training
df["exclude_from_training"] = df["Latitude"].isnull()

# Fill null coords with province centroid
n_null_coords = df["Latitude"].isnull().sum()
for province, (lat, lon) in PROVINCE_CENTROIDS.items():
    mask = df["Latitude"].isnull() & (df["province"] == province)
    df.loc[mask, "Latitude"]  = lat
    df.loc[mask, "Longitude"] = lon
log.warning("Filled %d null coordinates with province centroids", n_null_coords)
```

**POI features:** Outlets with `poi_data_available = False` have 0 counts. Leave as-is.

**Numeric sales features:** If any outlet has null sales features (fully inactive),
fill with 0.

**`has_transaction_history`:** Derive from `active_months` (from sales features).
Outlets with 0 active months have no transaction history and will be handled
separately during modelling.

```python
df["has_transaction_history"] = df["active_months"].fillna(0).gt(0)
log.info("%d outlets have no transaction history",
         (~df["has_transaction_history"]).sum())
```

**trend_slope, yoy_growth_rate:** These legitimately can be null for outlets with
insufficient history. Fill nulls with the **median** value across all outlets
(not 0, which would bias the model).

```python
for col in ["trend_slope", "yoy_growth_rate"]:
    median_val = df[col].median()
    null_count = df[col].isnull().sum()
    df[col] = df[col].fillna(median_val)
    log.info("Filled %d nulls in %s with median %.4f", null_count, col, median_val)
```

**seasonality_multiplier_jan_2026:** If null (outlet has no distributor assigned),
fill with 1.00 (Moderate/neutral).

### Step 8 — Round floating-point columns

Round all float columns to 4 decimal places to avoid spurious precision
and reduce parquet file size.

**Important:** Upcast any `float32` columns to `float64` *before* rounding.
`float32` has only ~7 significant digits, so rounding to 4 decimal places
and keeping `float32` produces trailing noise (e.g. `1941.4699707031` instead
of `1941.47`). All float columns are written as `float64` in the output.

```python
float_cols = df.select_dtypes(include=["float32", "float64"]).columns
for col in float_cols:
    if df[col].dtype == "float32":
        df[col] = df[col].astype("float64")
df[float_cols] = df[float_cols].round(4)
log.info("Rounded %d float columns to 4 decimal places (all float64)", len(float_cols))
```

> **Note:** Categorical encoding (one-hot, ordinal) is intentionally **NOT**
> performed here. `master_features.parquet` is kept algorithm-agnostic with raw
> string categories (`Outlet_Type`, `Outlet_Size`, `province`,
> `seasonality_jan_2026`). Encoding is deferred to `train.py` via a
> Preprocessor class so the same Gold table can serve LightGBM, XGBoost,
> CatBoost, and Random Forest without modification.
> See `docs/modelling_and_pipeline/optimizations/optimizations_implemented.md` Section 3 for details.

### Step 9 — Write output

```python
df.to_parquet(GOLD / "master_features.parquet", index=False,
              engine="pyarrow", compression="snappy")
log.info("Written %d rows, %d columns → master_features.parquet",
         len(df), len(df.columns))
log.info("Columns: %s", list(df.columns))
```

---

## Assertions before writing

```python
assert len(df) == 20000, f"Expected 20000 rows, got {len(df)}"
assert df["Outlet_ID"].duplicated().sum() == 0
assert df["Outlet_ID"].isnull().sum() == 0
assert df["Latitude"].isnull().sum() == 0,  "Null latitudes after centroid fill"
assert df["Longitude"].isnull().sum() == 0, "Null longitudes after centroid fill"
assert df["coords_swapped"].isnull().sum() == 0, "Null coords_swapped after fill"
assert df["seasonality_multiplier_jan_2026"].isnull().sum() == 0
assert df["hist_p90_monthly"].isnull().sum() == 0
assert df["has_transaction_history"].dtype == bool
assert df["exclude_from_training"].dtype == bool
assert "jan_2026_trading_days" in df.columns
assert df["jan_2026_trading_days"].iloc[0] > 0
```

---

## CLI usage

```bash
python pipeline/gold/build_master_features.py
```

## Dependencies

- pandas, numpy, pyarrow, pyyaml
- Standard library: json, logging
