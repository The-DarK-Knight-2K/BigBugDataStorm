# SPEC: clean_outlets.py

## Purpose

Read the raw outlet_master bronze parquet, fix all known data quality issues
(typos, case inconsistencies, nulls), apply DQ checks, and write a clean silver
parquet and quarantine file. This file defines which outlets are valid entities
in the entire pipeline — all other scripts reference it.

## Layer
Silver

## Inputs

| File | Path |
|------|------|
| outlet_master.parquet | `Data/Bronze/outlet_master.parquet` |

## Outputs

| File | Path |
|------|------|
| outlet_master_clean.parquet | `Data/Silver/outlet_master_clean.parquet` |
| rejected_outlet_master.parquet | `Data/Quarantine/rejected_outlet_master.parquet` |
| dq_report rows | Appended to `outputs/dq_report.csv` |

---

## Known issues to fix (from data audit)

| Issue | Count | Fix |
|-------|-------|-----|
| Outlet_Size = "small" (lowercase) | ~600 | Normalise to "Small" |
| Outlet_Size = null | 196 | Impute from Cooler_Count (see Step 3) |
| Outlet_Type = "Grocry" | ~390 | Correct to "Grocery" |
| Outlet_Type = "Bakry" | ~395 | Correct to "Bakery" |
| Outlet_Type = " Eatery " (whitespace) | ~200 | Strip to "Eatery" |
| Outlet_Type = "SMMT" | ~2723 | KEEP — valid trade term (Super Mini Market Type) |

---

## Step-by-step logic

### Step 1 — Load bronze

```python
df = pd.read_parquet(BRONZE / "outlet_master.parquet")
log.info("Loaded %d rows from outlet_master bronze", len(df))
```

### Step 2 — DQ checks (before any fixes)

Run in this order. Accumulate failures in `quarantine_store`.

**Check 1 — Duplicate Outlet_ID**
```python
duplicate_check(df, primary_key_cols=["Outlet_ID"], dataset_name="outlet_master")
```
Failure reason: `"duplicate_record"`

**Check 2 — Null mandatory fields**
```python
null_check(df, mandatory_cols=["Outlet_ID", "Outlet_Type", "Cooler_Count"], dataset_name="outlet_master")
```
> `Outlet_Size` is NOT in mandatory_cols — nulls are imputed in Step 3, not quarantined.

**Check 3 — Outlet_ID format**
```python
format_check(df, col="Outlet_ID", regex_pattern=r"OUT_\d{5}", dataset_name="outlet_master")
```
Failure reason: `"format_violation:Outlet_ID"`

**Check 4 — Cooler_Count range**
```python
range_check(df, col="Cooler_Count", min_val=0, max_val=5, dataset_name="outlet_master")
```
Failure reason: `"out_of_range:Cooler_Count:value={value}"`

After these 4 checks, work only with the rows that passed all checks.

### Step 3 — Normalise Outlet_Size

Apply in this order:
1. Strip leading/trailing whitespace: `df["Outlet_Size"] = df["Outlet_Size"].str.strip()`
2. Apply title case to fix "small" → "Small":
   `df["Outlet_Size"] = df["Outlet_Size"].str.title()`
3. Validate against valid set from `config.yaml` (`valid_outlet_sizes`).
   Rows with an unrecognised (non-null) size after normalisation → quarantine with
   reason `"invalid_value:Outlet_Size:found={value}"`. Do NOT impute unrecognised
   values.
4. Impute null sizes using Cooler_Count. Create boolean flag `size_imputed`:

```python
SIZE_IMPUTATION_MAP = {0: "Small", 1: "Small", 2: "Medium", 3: "Large", 4: "Large", 5: "Extra Large"}

def impute_size(row):
    if pd.isna(row["Outlet_Size"]):
        row["size_imputed"] = True
        row["Outlet_Size"] = SIZE_IMPUTATION_MAP.get(int(row["Cooler_Count"]), "Small")
    else:
        row["size_imputed"] = False
    return row
```

Log: "Imputed Outlet_Size for {n} rows using Cooler_Count rule."

### Step 4 — Normalise Outlet_Type

1. Strip whitespace: `df["Outlet_Type"] = df["Outlet_Type"].str.strip()`
2. Apply correction mapping from `config.yaml` (`outlet_type_corrections`):
   ```python
   corrections = CFG["outlet_type_corrections"]  # {"Grocry": "Grocery", "Bakry": "Bakery"}
   df["Outlet_Type"] = df["Outlet_Type"].replace(corrections)
   ```
3. Validate against valid set from `config.yaml` (`valid_outlet_types`).
   Rows with unrecognised type after correction → quarantine with reason
   `"invalid_value:Outlet_Type:found={value}"`.

Log: "Corrected Outlet_Type typos: {n} rows updated."

### Step 5 — Cast types

```python
df["Cooler_Count"] = df["Cooler_Count"].astype("int8")
df["size_imputed"] = df["size_imputed"].astype(bool)
```

### Step 6 — Final validation

Run a final `value_set_check` on both `Outlet_Size` and `Outlet_Type` to confirm
all values are canonical. If either check fails here, it is a logic bug — raise
`RuntimeError`, do not quarantine.

### Step 7 — Write outputs

1. Write `Data/Silver/outlet_master_clean.parquet` with columns:
   `[Outlet_ID, Outlet_Size, Cooler_Count, Outlet_Type, size_imputed]`
2. Write quarantine file.
3. Append DQ report rows.

---

## Assertions before writing

```python
assert len(df_clean) > 0
assert df_clean["Outlet_ID"].duplicated().sum() == 0, "Duplicate Outlet_IDs in output"
assert df_clean["Outlet_ID"].isnull().sum() == 0
assert df_clean["Outlet_Size"].isnull().sum() == 0, "Null sizes remain after imputation"
assert set(df_clean["Outlet_Size"].unique()).issubset(set(CFG["valid_outlet_sizes"]))
assert set(df_clean["Outlet_Type"].unique()).issubset(set(CFG["valid_outlet_types"]))
assert df_clean["Cooler_Count"].between(0, 5).all()
# Total rows (clean + quarantined) must equal bronze row count
assert len(df_clean) + total_quarantined == 20000
```

---

## Logging summary (end of script)

```
outlet_master cleaning complete
  Input rows        : 20000
  Clean rows        : XXXX
  Quarantined rows  : XXXX
  Sizes imputed     : 196
  Type typos fixed  : XXXX
```

---

## CLI usage

```bash
python pipeline/silver/clean_outlets.py
```

## Dependencies

- pandas, pyarrow, pyyaml
- `silver.dq_checks` (local import)
