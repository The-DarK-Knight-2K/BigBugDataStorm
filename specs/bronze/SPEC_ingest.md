# SPEC: Bronze Ingest

## Purpose

Load all 5 raw CSV files from `data/raw/` and save them as parquet snapshots in
`data/bronze/`. Zero transformations. This layer preserves the original data
exactly as provided — it is the permanent record of what we received.

## Layer
Bronze

## Inputs

| File | Path |
|------|------|
| transactions_history_final.csv | `data/raw/transactions_history_final.csv` |
| outlet_master.csv | `data/raw/outlet_master.csv` |
| outlet_coordinates.csv | `data/raw/outlet_coordinates.csv` |
| distributor_seasonality_details.csv | `data/raw/distributor_seasonality_details.csv` |
| holiday_list.csv | `data/raw/holiday_list.csv` |

All paths resolved from `config.yaml`.

## Outputs

| File | Path |
|------|------|
| transactions.parquet | `data/bronze/transactions.parquet` |
| outlet_master.parquet | `data/bronze/outlet_master.parquet` |
| outlet_coordinates.parquet | `data/bronze/outlet_coordinates.parquet` |
| seasonality.parquet | `data/bronze/seasonality.parquet` |
| holidays.parquet | `data/bronze/holidays.parquet` |

## Logic

### Step 1 — Ensure output directory exists
Create `data/bronze/` if it does not exist. Use `Path.mkdir(parents=True, exist_ok=True)`.

### Step 2 — Define ingest manifest
Create a list of dicts, each with:
- `csv_name`: filename in `data/raw/`
- `parquet_name`: filename to write in `data/bronze/`
- `read_kwargs`: any special kwargs for `pd.read_csv()` (e.g. encoding, dtype overrides)

For `transactions_history_final.csv`, add `low_memory=False` to handle mixed types
in large files. For all other files, use default read settings.

### Step 3 — For each file in the manifest

1. Log: "Ingesting {csv_name}…"
2. Read CSV: `df = pd.read_csv(raw_path, **read_kwargs)`
3. Log: "Loaded {len(df)} rows, {len(df.columns)} columns"
4. Log column names and dtypes at DEBUG level.
5. Record metadata:
   - `source_file`: csv filename
   - `row_count`: len(df)
   - `col_count`: len(df.columns)
   - `columns`: list of column names
   - `ingested_at`: `datetime.utcnow().isoformat()`
   - `file_size_mb`: file size in MB (use `Path.stat().st_size / 1e6`)
6. Write parquet: `df.to_parquet(bronze_path, index=False, engine="pyarrow", compression="snappy")`
7. Log: "Written → {parquet_name} ({len(df)} rows)"

### Step 4 — Write ingest metadata log
Save all metadata records as `data/bronze/ingest_log.json`.

```json
[
  {
    "source_file": "outlet_master.csv",
    "row_count": 20000,
    "col_count": 4,
    "columns": ["Outlet_ID", "Outlet_Size", "Cooler_Count", "Outlet_Type"],
    "ingested_at": "2025-05-15T18:30:00",
    "file_size_mb": 0.72
  }
]
```

### Step 5 — Summary log
Log total files ingested, total rows across all files.

## Error handling

- If any CSV file does not exist in `data/raw/`, log an ERROR with the missing
  filename and exit with code 1. Do not partially ingest.
- If any file fails to parse (e.g. encoding error), log the error and exit with
  code 1.
- If `data/bronze/` cannot be created (permissions), log ERROR and exit 1.

## Validation

After all files are written, assert:
```python
assert (BRONZE / "outlet_master.parquet").exists()
assert (BRONZE / "outlet_coordinates.parquet").exists()
assert (BRONZE / "seasonality.parquet").exists()
assert (BRONZE / "holidays.parquet").exists()
assert (BRONZE / "transactions.parquet").exists()

# Row count sanity
om = pd.read_parquet(BRONZE / "outlet_master.parquet")
assert len(om) == 20000, f"Expected 20000 outlet_master rows, got {len(om)}"

oc = pd.read_parquet(BRONZE / "outlet_coordinates.parquet")
assert len(oc) == 20000, f"Expected 20000 coordinate rows, got {len(oc)}"
```

## CLI usage

```bash
python pipeline/bronze/ingest.py
```

No arguments. All config from `config.yaml`.

## Dependencies

- pandas
- pyarrow
- pyyaml
- Standard library: pathlib, logging, json, datetime, sys
