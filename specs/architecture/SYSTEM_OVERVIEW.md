# System Overview — Data Storm 7.0 Pipeline

## Business objective

Predict the **maximum monthly purchase potential in litres** for each of 20,000
traditional trade retail outlets across 4 Sri Lankan provinces, for **January 2026**.
The target is latent (hidden) — historical sales are a censored lower bound on true
demand, not the demand itself.

## Repository root layout

```
datastorm-teamname/
├── config.yaml                    ← all tunable values, paths, thresholds
├── requirements.txt
├── README.md
├── .gitignore
├── .env.example
│
├── data/                          ← gitignored, local only
│   ├── raw/                       ← original CSV files placed here manually
│   ├── bronze/                    ← parquet snapshots of raw files
│   ├── silver/                    ← cleaned parquet files
│   ├── quarantine/                ← rejected records with failure_reason
│   └── gold/                      ← feature-engineered, model-ready data
│
├── pipeline/
│   ├── bronze/
│   │   └── ingest.py
│   ├── silver/
│   │   ├── dq_checks.py           ← reusable DQ library (imported by all clean_*.py)
│   │   ├── clean_transactions.py
│   │   ├── clean_outlets.py
│   │   ├── clean_coordinates.py
│   │   ├── clean_seasonality.py
│   │   └── clean_holidays.py
│   ├── gold/
│   │   ├── scrape_poi.py
│   │   ├── build_sales_features.py
│   │   └── build_master_features.py
│   └── run_pipeline.py            ← end-to-end orchestrator
│
├── modelling/
│   ├── baseline.py
│   ├── train.py
│   ├── predict.py
│   └── artifacts/                 ← saved model files (gitignored)
│
├── notebooks/
│   ├── 01_eda_transactions.ipynb
│   ├── 02_eda_outlets.ipynb
│   ├── 03_feature_exploration.ipynb
│   └── 04_model_experiments.ipynb
│
├── outputs/
│   ├── teamname_predictions.csv   ← final submission file
│   └── dq_report.csv              ← DQ summary for the report
│
├── specs/                         ← this folder
└── report/
    └── teamname_report.pdf
```

## Data flow

```
data/raw/*.csv
      │
      ▼  pipeline/bronze/ingest.py
data/bronze/*.parquet              ← raw snapshots, no transforms
      │
      ▼  pipeline/silver/clean_*.py  (uses dq_checks.py)
data/silver/*_clean.parquet        ← validated, normalised
data/quarantine/rejected_*.parquet ← bad rows with failure_reason
      │
      ├──▶ pipeline/gold/scrape_poi.py  ──▶ data/gold/poi_features.parquet
      │
      ▼  pipeline/gold/build_sales_features.py
data/gold/sales_features.parquet   ← engineered from transactions
      │
      ▼  pipeline/gold/build_master_features.py
data/gold/master_features.parquet  ← one row per outlet, all features
      │
      ├──▶ modelling/baseline.py   ──▶ baseline_predictions (in memory)
      │
      ▼  modelling/train.py
modelling/artifacts/model.pkl      ← trained LightGBM model
      │
      ▼  modelling/predict.py
outputs/teamname_predictions.csv   ← SUBMISSION FILE
```

## Layer definitions

| Layer | Folder | Rule |
|-------|--------|------|
| Bronze | `data/bronze/` | Exact copy of raw CSVs as parquet. **Zero transformations.** |
| Silver | `data/silver/` | Cleaned, validated, normalised. Bad rows go to quarantine, never silently dropped. |
| Gold | `data/gold/` | Feature-engineered. All silver datasets + external POI merged. Model-ready. |

## Datasets provided

| File | Rows | Key columns |
|------|------|-------------|
| `transactions_history_final.csv` | ~millions | Outlet_ID, Date, Volume_Litres, Distributor_ID |
| `outlet_master.csv` | 20,000 | Outlet_ID, Outlet_Size, Cooler_Count, Outlet_Type |
| `outlet_coordinates.csv` | 20,000 | Outlet_ID, Latitude, Longitude |
| `distributor_seasonality_details.csv` | 360 | Distributor_ID, Year, Month, Seasonality_Index |
| `holiday_list.csv` | 349 | Date, Holiday_Name, Holiday_Type |

## Distributors and provinces

| Province | Distributor IDs |
|----------|----------------|
| Western | DIST_W_01, DIST_W_02, DIST_W_03 |
| Central | DIST_C_01, DIST_C_02, DIST_C_03 |
| North-Western | DIST_NW_01, DIST_NW_02 |
| Southern | DIST_S_01, DIST_S_02 |

## Key facts discovered during data audit

- `outlet_master`: 196 null sizes, 796 lowercase "small", 985 typos in Outlet_Type
- `outlet_coordinates`: 200 swapped lat/lon rows, 40 zero-coordinate ghost entries
- `holiday_list`: 349 rows but only 76 unique dates — same date has 4–5 rows for
  different holiday types (Public, Bank, Mercantile, Poya Day). Not true duplicates.
  Dates are also unsorted.
- `distributor_seasonality_details`: perfectly clean, but covers only 2023–2025.
  January 2026 must be extrapolated programmatically.
- `transactions_history_final`: expect duplicates, zero/negative volumes, impossible
  spikes, orphaned Outlet_IDs, connectivity blackout gaps, ghost entries.

## Prediction target

**January 2026 Maximum Monthly Purchase Potential (litres) per outlet.**

There is no ground truth. The approach is:
1. Use 90th-percentile historical monthly volume as a proxy for the demand ceiling.
2. Adjust upward using a seasonality multiplier.
3. Train a LightGBM model to predict this ceiling from structural features.
4. Final prediction = `max(statistical_baseline, model_prediction)`.
