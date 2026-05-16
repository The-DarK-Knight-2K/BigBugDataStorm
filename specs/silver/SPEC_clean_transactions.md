# SPEC: clean_transactions.py

## Purpose

Read the raw transactions bronze parquet, apply all DQ checks and cleaning rules,
write a clean silver parquet and a quarantine parquet of rejected rows. This is the
largest and most analytically critical cleaning script because the transactions file
is the primary source of demand signals.

## Layer
Silver

## Inputs

| File | Path |
|------|------|
| transactions.parquet | `data/bronze/transactions.parquet` |
| outlet_master_clean.parquet | `data/silver/outlet_master_clean.parquet` |

> **Dependency:** `outlet_master_clean.parquet` must exist before this script runs.
> The orchestrator (`run_pipeline.py`) must enforce this order.

## Outputs

| File | Path |
|------|------|
| transactions_clean.parquet | `data/silver/transactions_clean.parquet` |
| rejected_transactions.parquet | `data/quarantine/rejected_transactions.parquet` |
| dq_report rows | Appended to `outputs/dq_report.csv` |

---

## Step-by-step logic

### Step 0 — Discover column names dynamically

Because the exact column names in `transactions_history_final.csv` are not
confirmed, the script must:
1. Load the bronze parquet.
2. Print all column names and dtypes to the log at INFO level.
3. Attempt to map to expected canonical names using this fuzzy lookup table
   (case-insensitive, strip whitespace):

| Canonical name | Likely raw names |
|----------------|-----------------|
| `Outlet_ID` | outlet_id, outlet id, outletid, shop_id |
| `Date` | date, transaction_date, txn_date, order_date |
| `Distributor_ID` | distributor_id, dist_id, distributor |
| `Volume_Litres` | volume_litres, volume, litres, qty, quantity, sales_volume |

If a canonical name cannot be mapped, raise `ValueError` listing the unmapped
column and exit 1. Do not silently drop columns.

### Step 1 — Date parsing

1. Parse `Date` column with `pd.to_datetime(df["Date"], utc=True, errors="coerce")`.
2. Rows where date parsing fails (NaT result) → quarantine with reason
   `"unparseable_date"`.
3. Extract `Year` (int16) and `Month` (int8) from the parsed date.
4. Rows with date outside range 2020-01-01 to 2025-12-31 → quarantine with reason
   `"date_out_of_expected_range"`.

### Step 2 — DQ checks (call functions from dq_checks.py)

Run the following checks in order. After each check, remove failed rows from the
working DataFrame and accumulate them in `quarantine_store`.

**Check 1 — Duplicate transactions**
```python
duplicate_check(df, primary_key_cols=["Outlet_ID", "Date", "Volume_Litres"], dataset_name="transactions")
```
Failure reason: `"duplicate_record"`

**Check 2 — Null mandatory fields**
```python
null_check(df, mandatory_cols=["Outlet_ID", "Date", "Volume_Litres"], dataset_name="transactions")
```
Failure reason: `"null_in_mandatory_field:{col}"`

**Check 3 — Referential integrity (Outlet_ID must exist in outlet_master)**
```python
ref_df = pd.read_parquet(SILVER / "outlet_master_clean.parquet")[["Outlet_ID"]]
ref_integrity_check(df, fk_col="Outlet_ID", ref_df=ref_df, ref_col="Outlet_ID", dataset_name="transactions")
```
Failure reason: `"referential_integrity_violation:Outlet_ID"`

**Check 4 — Distributor_ID must be one of the 10 known distributors**
```python
valid_dists = ["DIST_W_01","DIST_W_02","DIST_W_03","DIST_C_01","DIST_C_02",
               "DIST_C_03","DIST_NW_01","DIST_NW_02","DIST_S_01","DIST_S_02"]
value_set_check(df, col="Distributor_ID", valid_values=valid_dists, dataset_name="transactions")
```
Failure reason: `"invalid_value:Distributor_ID:found={value}"`

**Check 5 — Volume range**
```python
range_check(df, col="Volume_Litres", min_val=0.01, max_val=None, dataset_name="transactions")
```
Failure reason: `"out_of_range:Volume_Litres:value={value}"`
> Zero and negative volumes are system artifacts. Max is not capped here — extreme
> outliers are flagged separately in Step 3.

### Step 3 — Outlier detection (do NOT quarantine — flag only)

After DQ checks, detect extreme volume outliers that may be data entry errors
(e.g. 1000 entered instead of 100). These rows are **kept** but flagged.

**Method:** For each Outlet_ID, compute the outlet-level IQR of `Volume_Litres`.
A single transaction is an outlier if it exceeds `Q3 + 5 × IQR` for that outlet.
If an outlet has fewer than 4 transactions, use the global dataset IQR instead.

Add boolean column: `is_volume_outlier = True/False`.
Log a WARNING with the count of flagged rows.

### Step 4 — Blackout period detection (do NOT quarantine — flag only)

A "blackout period" is a consecutive sequence of months where an outlet has zero
transactions, sandwiched between months with normal activity. This signals a real
business event (credit block, stockout), not missing data.

**Method:**
1. Create a monthly activity grid: for each (Outlet_ID, Year, Month), compute total
   volume. Missing months = 0.
2. For each outlet, find the longest consecutive run of zero-volume months.
3. If a zero-volume month is surrounded by non-zero months on both sides, mark it
   `is_blackout_period = True`.

Add boolean column: `is_blackout_period = True/False`.

### Step 5 — Construct output DataFrame

Select and rename columns to match the silver schema in DATA_CONTRACTS.md:

| Output column | Source |
|--------------|--------|
| Outlet_ID | mapped column |
| Date | parsed datetime, converted to `.dt.date` |
| Year | extracted |
| Month | extracted |
| Distributor_ID | mapped column |
| Volume_Litres | mapped column, cast to float32 |
| is_volume_outlier | from Step 3 |
| is_blackout_period | from Step 4 |
| row_source | hardcoded string `"transactions_history_final.csv"` |

### Step 6 — Write outputs

1. Write `data/silver/transactions_clean.parquet`.
2. Concatenate all `quarantine_store` entries and write
   `data/quarantine/rejected_transactions.parquet`.
3. Append DQ report rows to `outputs/dq_report.csv` (create file if not exists,
   append if exists).

---

## Error handling

- Missing bronze file → log ERROR, exit 1.
- Missing `outlet_master_clean.parquet` → log ERROR with message "Run
  clean_outlets.py first", exit 1.
- If more than 30% of rows are quarantined, log a WARNING:
  "High quarantine rate ({pct}%) — review the transactions data carefully."
  Do not exit — continue processing.

---

## Assertions before writing

```python
assert len(df_clean) > 0, "Clean transactions DataFrame is empty."
assert df_clean["Volume_Litres"].min() > 0, "Non-positive volumes in clean output."
assert df_clean["Outlet_ID"].isnull().sum() == 0, "Null Outlet_IDs in clean output."
assert "is_blackout_period" in df_clean.columns
assert "is_volume_outlier" in df_clean.columns
```

---

## CLI usage

```bash
python pipeline/silver/clean_transactions.py
```

## Dependencies

- pandas, numpy, pyarrow, scipy, pyyaml
- `pipeline.silver.dq_checks` (local import)
