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

**Coordinates:** ~40 outlets with zero coordinates will have null Latitude/Longitude.
Fill with province centroid coordinates as approximations:

```python
PROVINCE_CENTROIDS = {
    "Western":       (6.9271, 79.8612),
    "Central":       (7.2906, 80.6337),
    "North-Western": (7.7102, 80.0078),
    "Southern":      (6.0535, 80.2210),
}
# Fill null coords with province centroid
for province, (lat, lon) in PROVINCE_CENTROIDS.items():
    mask = df["Latitude"].isnull() & (df["province"] == province)
    df.loc[mask, "Latitude"]  = lat
    df.loc[mask, "Longitude"] = lon
log.warning("Filled %d null coordinates with province centroids", n_null_coords)
```

**POI features:** Outlets with `poi_data_available = False` have 0 counts. Leave as-is.

**Numeric sales features:** If any outlet has null sales features (fully inactive),
fill with 0.

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

### Step 8 — Encode categorical features

**Outlet_Size:**
```python
SIZE_ORDER = {"Small": 1, "Medium": 2, "Large": 3, "Extra Large": 4}
df["outlet_size_encoded"] = df["Outlet_Size"].map(SIZE_ORDER)
```

**Outlet_Type** (one-hot encode):
```python
type_dummies = pd.get_dummies(df["Outlet_Type"], prefix="type")
df = pd.concat([df, type_dummies], axis=1)
```

**Province** (one-hot encode):
```python
province_dummies = pd.get_dummies(df["province"], prefix="province")
df = pd.concat([df, province_dummies], axis=1)
```

**Seasonality_Index:**
```python
SEASON_ENCODE = {"Un-Favorable": 0, "Moderate": 1, "Favorable": 2}
df["seasonality_encoded"] = df["seasonality_jan_2026"].map(SEASON_ENCODE).fillna(1)
```

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
assert df["seasonality_multiplier_jan_2026"].isnull().sum() == 0
assert df["hist_p90_monthly"].isnull().sum() == 0
assert df["outlet_size_encoded"].isnull().sum() == 0
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
