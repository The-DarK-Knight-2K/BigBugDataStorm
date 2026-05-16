# SPEC: clean_coordinates.py

## Purpose

Read the raw outlet_coordinates bronze parquet, detect and fix swapped lat/lon
values, quarantine zero-coordinate ghost entries and any remaining out-of-bounds
records, and write a clean silver parquet. The clean output is used by the POI
scraping script to query OpenStreetMap.

## Layer
Silver

## Inputs

| File | Path |
|------|------|
| outlet_coordinates.parquet | `data/bronze/outlet_coordinates.parquet` |
| outlet_master_clean.parquet | `data/silver/outlet_master_clean.parquet` |

> **Dependency:** `outlet_master_clean.parquet` must exist. Orchestrator enforces order.

## Outputs

| File | Path |
|------|------|
| outlet_coordinates_clean.parquet | `data/silver/outlet_coordinates_clean.parquet` |
| rejected_outlet_coordinates.parquet | `data/quarantine/rejected_outlet_coordinates.parquet` |
| dq_report rows | Appended to `outputs/dq_report.csv` |

---

## Sri Lanka geographic bounds (from config.yaml)

```
lat_min: 5.9   lat_max: 9.9
lon_min: 79.5  lon_max: 81.9
```

---

## Known issues (from data audit)

| Issue | Count | Action |
|-------|-------|--------|
| Swapped lat/lon (Latitude ≈ 79–81, Longitude ≈ 6–9) | ~200 | Fix by swapping columns |
| Both Latitude and Longitude = 0.0 | ~40 | Quarantine |
| Remaining out-of-bounds after swap fix | 0 (expected) | Quarantine if any found |

---

## Step-by-step logic

### Step 1 — Load bronze

```python
df = pd.read_parquet(BRONZE / "outlet_coordinates.parquet")
log.info("Loaded %d rows from outlet_coordinates bronze", len(df))
```

### Step 2 — DQ checks (before fixes)

**Check 1 — Duplicate Outlet_ID**
```python
duplicate_check(df, primary_key_cols=["Outlet_ID"], dataset_name="outlet_coordinates")
```

**Check 2 — Null mandatory fields**
```python
null_check(df, mandatory_cols=["Outlet_ID", "Latitude", "Longitude"], dataset_name="outlet_coordinates")
```

**Check 3 — Referential integrity**
```python
ref_df = pd.read_parquet(SILVER / "outlet_master_clean.parquet")[["Outlet_ID"]]
ref_integrity_check(df, fk_col="Outlet_ID", ref_df=ref_df, ref_col="Outlet_ID",
                    dataset_name="outlet_coordinates")
```

Apply checks sequentially; pass survivors of each check to the next. Quarantine
failures from each check.

### Step 3 — Zero-coordinate quarantine

After DQ checks, on the surviving rows:
```python
zero_mask = (df["Latitude"] == 0.0) & (df["Longitude"] == 0.0)
```
Quarantine zero rows with reason `"zero_coordinates"`.
Log: "Quarantining {n} zero-coordinate rows (GPS never recorded)."

Work only with non-zero rows in subsequent steps.

### Step 4 — Detect and fix swapped lat/lon

**Detection logic:**
```python
swapped_mask = df["Latitude"] > 50
```
A `Latitude` value greater than 50 cannot be in Sri Lanka (max lat ≈ 9.9). These
rows have the columns swapped — what's in Latitude is actually the Longitude value
(≈79–81) and vice versa.

**Fix:**
```python
df.loc[swapped_mask, ["Latitude", "Longitude"]] = \
    df.loc[swapped_mask, ["Longitude", "Latitude"]].values
df["coords_swapped"] = swapped_mask
```

Log: "Swapped lat/lon for {n} rows."

For rows that were NOT swapped, set `coords_swapped = False`.

### Step 5 — Bounds validation (after swap fix)

```python
bounds_mask = (
    (df["Latitude"]  < CFG["sri_lanka_bounds"]["lat_min"]) |
    (df["Latitude"]  > CFG["sri_lanka_bounds"]["lat_max"]) |
    (df["Longitude"] < CFG["sri_lanka_bounds"]["lon_min"]) |
    (df["Longitude"] > CFG["sri_lanka_bounds"]["lon_max"])
)
```

Quarantine any remaining out-of-bounds rows with reason `"coordinates_out_of_sri_lanka_bounds"`.
Log count. (Expected count: 0 after swap fix — log a WARNING if any are found.)

### Step 6 — Cast types

```python
df["Latitude"]       = df["Latitude"].astype("float64")
df["Longitude"]      = df["Longitude"].astype("float64")
df["coords_swapped"] = df["coords_swapped"].astype(bool)
```

### Step 7 — Write outputs

Output columns: `[Outlet_ID, Latitude, Longitude, coords_swapped]`

Write:
1. `data/silver/outlet_coordinates_clean.parquet`
2. `data/quarantine/rejected_outlet_coordinates.parquet`
3. Append DQ report rows to `outputs/dq_report.csv`

---

## Important downstream note

The ~40 outlets with zero coordinates will be **absent** from the clean coordinates
file. The `build_master_features.py` script must handle these via a left join —
these outlets will have null POI features which will be filled with dataset medians.
Document this in the DQ report.

---

## Assertions before writing

```python
assert df_clean["Outlet_ID"].duplicated().sum() == 0
assert df_clean["Outlet_ID"].isnull().sum() == 0
assert df_clean["Latitude"].between(5.9, 9.9).all(), "Latitude out of SL bounds"
assert df_clean["Longitude"].between(79.5, 81.9).all(), "Longitude out of SL bounds"
assert (df_clean["Latitude"] == 0).sum() == 0, "Zero latitudes remain"
assert (df_clean["Longitude"] == 0).sum() == 0, "Zero longitudes remain"
# Conservation: clean + quarantined = bronze
assert len(df_clean) + total_quarantined == 20000
```

---

## Logging summary (end of script)

```
outlet_coordinates cleaning complete
  Input rows        : 20000
  Clean rows        : XXXX
  Quarantined rows  : XXXX
    zero_coordinates           : ~40
    other                      : XXXX
  Lat/Lon swaps fixed          : ~200
  coords_swapped=True in output: ~200
```

---

## CLI usage

```bash
python pipeline/silver/clean_coordinates.py
```

## Dependencies

- pandas, pyarrow, pyyaml
- `pipeline.silver.dq_checks` (local import)
