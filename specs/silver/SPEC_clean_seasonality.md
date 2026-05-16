# SPEC: clean_seasonality.py

## Purpose

Read the raw distributor_seasonality_details bronze parquet, validate it, and
programmatically append extrapolated January 2026 rows for all 10 distributors.
The January 2026 seasonality values are essential for the final prediction step.

## Layer
Silver

## Inputs

| File | Path |
|------|------|
| seasonality.parquet | `data/bronze/seasonality.parquet` |

## Outputs

| File | Path |
|------|------|
| seasonality_clean.parquet | `data/silver/seasonality_clean.parquet` |
| dq_report rows | Appended to `outputs/dq_report.csv` |

> No quarantine file for this dataset — the source data is clean. If DQ checks
> find unexpected failures, raise an ERROR and exit (this would indicate a
> fundamental data problem requiring human review).

---

## Known facts from data audit

- 360 rows: exactly 10 distributors × 3 years × 12 months — perfectly complete.
- Zero nulls, zero duplicates.
- Seasonality values: "Favorable", "Moderate", "Un-Favorable" (note the hyphen).
- January seasonality is consistent across years:
  - Western, Central, North-Western distributors → "Moderate" in Jan 2023, 2024, 2025
  - Southern distributors → "Favorable" in Jan 2023, 2024, 2025
- No 2026 data exists — must be extrapolated.

---

## Step-by-step logic

### Step 1 — Load bronze

```python
df = pd.read_parquet(BRONZE / "seasonality.parquet")
log.info("Loaded %d rows from seasonality bronze", len(df))
```

### Step 2 — DQ checks

**Check 1 — Duplicate (Distributor_ID, Year, Month) composite key**
```python
duplicate_check(df, primary_key_cols=["Distributor_ID", "Year", "Month"],
                dataset_name="seasonality")
```
If any failures: raise `RuntimeError("Duplicate seasonality rows — data integrity issue")`

**Check 2 — Null mandatory fields**
```python
null_check(df, mandatory_cols=["Distributor_ID", "Year", "Month", "Seasonality_Index"],
           dataset_name="seasonality")
```
If any failures: raise `RuntimeError`

**Check 3 — Valid Seasonality_Index values**
```python
value_set_check(df, col="Seasonality_Index",
                valid_values=["Favorable", "Moderate", "Un-Favorable"],
                dataset_name="seasonality")
```
If any failures: raise `RuntimeError`

**Check 4 — Year range**
```python
range_check(df, col="Year", min_val=2023, max_val=2025, dataset_name="seasonality")
```

**Check 5 — Month range**
```python
range_check(df, col="Month", min_val=1, max_val=12, dataset_name="seasonality")
```

**Check 6 — Completeness check**
Verify all 360 distributor-year-month combinations are present:
```python
from itertools import product
expected_combos = pd.DataFrame(
    list(product(KNOWN_DISTRIBUTORS, [2023, 2024, 2025], range(1, 13))),
    columns=["Distributor_ID", "Year", "Month"]
)
merged = expected_combos.merge(df, on=["Distributor_ID", "Year", "Month"], how="left")
missing = merged[merged["Seasonality_Index"].isnull()]
if len(missing) > 0:
    log.warning("Missing %d distributor-year-month combinations", len(missing))
    log.warning(missing.to_string())
```

Where:
```python
KNOWN_DISTRIBUTORS = [
    "DIST_W_01", "DIST_W_02", "DIST_W_03",
    "DIST_C_01", "DIST_C_02", "DIST_C_03",
    "DIST_NW_01", "DIST_NW_02",
    "DIST_S_01", "DIST_S_02"
]
```

### Step 3 — Extrapolate January 2026

**Logic:** Use each distributor's January 2025 value as the January 2026 value.
(Most recent year is the best predictor for next year. The data shows this value
has been stable across 2023–2024–2025.)

```python
jan_2025 = df[(df["Year"] == 2025) & (df["Month"] == 1)].copy()
jan_2026 = jan_2025.copy()
jan_2026["Year"] = 2026
jan_2026["is_extrapolated"] = True
```

Add `is_extrapolated = False` to all original rows:
```python
df["is_extrapolated"] = False
```

Append:
```python
df_clean = pd.concat([df, jan_2026], ignore_index=True)
```

Log: "Extrapolated January 2026 seasonality for 10 distributors using Jan 2025 values."
Log each distributor's extrapolated value:
```
DIST_W_01  → Jan 2026: Moderate (extrapolated from Jan 2025)
DIST_S_01  → Jan 2026: Favorable (extrapolated from Jan 2025)
...
```

### Step 4 — Cast types

```python
df_clean["Year"]  = df_clean["Year"].astype("int16")
df_clean["Month"] = df_clean["Month"].astype("int8")
df_clean["is_extrapolated"] = df_clean["is_extrapolated"].astype(bool)
```

### Step 5 — Write output

Output columns: `[Distributor_ID, Year, Month, Seasonality_Index, is_extrapolated]`

Write `data/silver/seasonality_clean.parquet`.

---

## Assertions before writing

```python
assert len(df_clean) == 370, f"Expected 370 rows (360 + 10 Jan 2026), got {len(df_clean)}"
jan_2026_rows = df_clean[(df_clean["Year"] == 2026) & (df_clean["Month"] == 1)]
assert len(jan_2026_rows) == 10, "Expected 10 Jan 2026 rows"
assert jan_2026_rows["is_extrapolated"].all(), "Jan 2026 rows must be flagged as extrapolated"
assert set(jan_2026_rows["Distributor_ID"]) == set(KNOWN_DISTRIBUTORS)
assert df_clean["Seasonality_Index"].isnull().sum() == 0
valid_vals = {"Favorable", "Moderate", "Un-Favorable"}
assert set(df_clean["Seasonality_Index"].unique()).issubset(valid_vals)
```

---

## CLI usage

```bash
python pipeline/silver/clean_seasonality.py
```

## Dependencies

- pandas, pyarrow, pyyaml
- `pipeline.silver.dq_checks` (local import)
- Standard library: itertools, logging
