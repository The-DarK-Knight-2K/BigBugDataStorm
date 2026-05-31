# SPEC: Bronze Ingest

## Purpose

Load all 5 raw CSV files from `Data/Raw/` and save them as parquet snapshots in
`Data/Bronze/`. Zero transformations. This layer preserves the original data
exactly as provided — it is the permanent record of what we received.

## Layer
Bronze

## Inputs

| File | Path |
|------|------|
| transactions_history_final.csv | `Data/Raw/transactions_history_final.csv` |
| outlet_master.csv | `Data/Raw/outlet_master.csv` |
| outlet_coordinates.csv | `Data/Raw/outlet_coordinates.csv` |
| distributor_seasonality_details.csv | `Data/Raw/distributor_seasonality_details.csv` |
| holiday_list.csv | `Data/Raw/holiday_list.csv` |

All paths resolved from `config.yaml`.

## Outputs

| File | Path |
|------|------|
| transactions_history_final.parquet | `Data/Bronze/transactions_history_final.parquet` |
| outlet_master.parquet | `Data/Bronze/outlet_master.parquet` |
| outlet_coordinates.parquet | `Data/Bronze/outlet_coordinates.parquet` |
| distributor_seasonality_details.parquet | `Data/Bronze/distributor_seasonality_details.parquet` |
| holiday_list.parquet | `Data/Bronze/holiday_list.parquet` |

## Logic

### Step 1 — Ensure output directory exists
Create `Data/Bronze/` if it does not exist. Use `os.makedirs()`.

### Step 2 — Define ingest manifest
Create a list of dicts, each with:
- `csv_name`: filename in `Data/Raw/`
- `parquet_name`: filename to write in `Data/Bronze/`

For all files, use default read settings in pandas (`pd.read_csv`).

### Step 3 — For each file in the manifest

1. Log: "Ingesting {csv_name}…"
2. Read CSV: `df = pd.read_csv(raw_path)`
3. Log: "Loaded {len(df)} rows, {len(df.columns)} columns"
4. Log column names and dtypes at DEBUG level.
5. Write parquet: `df.to_parquet(bronze_path, index=False, engine="pyarrow", compression="snappy")`
6. Log: "Written → {parquet_name} ({len(df)} rows)"

### Step 4 — Summary log
Log total files ingested, total rows across all files.

## Error handling

- If any CSV file does not exist in `Data/Raw/`, log an ERROR with the missing
  filename and exit with code 1. Do not partially ingest.
- If any file fails to parse (e.g. encoding error), log the error and exit with
  code 1.
- If `Data/Bronze/` cannot be created (permissions), log ERROR and exit 1.

## Validation

After all files are written, assert:
```python
assert (BRONZE / "outlet_master.parquet").exists()
assert (BRONZE / "outlet_coordinates.parquet").exists()
assert (BRONZE / "distributor_seasonality_details.parquet").exists()
assert (BRONZE / "holiday_list.parquet").exists()
assert (BRONZE / "transactions_history_final.parquet").exists()

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
