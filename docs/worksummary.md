Links - https://drive.google.com/drive/folders/1Uq_OTs4e2pElRrC3nFt3_EoDk2yUZdeP?usp=drive_link

# Work Summary

1. Created `.gitignore` to exclude datasets and environment files.
2. Initialized Lakehouse directory structure (`Data/Raw/`, `Bronze/`, `Silver/`, `Gold/`) with `.gitkeep` files.
3. Cleaned Git history by removing a large 161MB tracked `.csv` file and amending the initial commit.
4. Successfully pushed the cleaned `main` branch to GitHub.
5. Created and executed `Scripts/01_raw_to_bronze.py` to ingest raw CSV data directly into `.parquet` format in the `Data/Bronze/` directory.
6. Upgraded project to a modular pipeline structure, adding `pipeline/utils/logger.py` and refactoring `pipeline/bronze/01_raw_to_bronze.py` to use professional file logging (`outputs/pipeline.log`).
7. Initialized Silver Layer architecture by creating the `Data/Quarantine/` directory and root `config.yaml` with geographical and string-correction constants.
8. Successfully wrote Phase 1 of the Silver Layer: `dq_checks.py` library and 5 specific dataset cleaning scripts packed with all business logic and anomaly detection algorithms.

## Exploratory Data Analysis (EDA) Phase
9. Reviewed `01_eda_transactions.ipynb` and verified coverage of missing values, distributions, and holiday/seasonality impact.
10. Finalized strategies for transactions data: netting/quarantining negative volumes and contextualizing/log-transforming outliers for the LightGBM model.
11. Successfully conducted comprehensive Exploratory Data Analysis on `outlets.csv`, identifying and rectifying data quality issues including missing Outlet_Size values, validating cooler count ranges, and Standardizing outlet type categories.
12. Executed `pipeline/Silver/clean_outlets.py`, implementing business logic to impute missing outlet sizes based on cooler count heuristics and quarantining malformed records to maintain data integrity.
13. Successfully diagnosed and resolved latitude/longitude coordinate discrepancies in `outlet_coordinates.csv` using advanced geocoding validation and bounding box checks, correcting swapped values and quarantining invalid records in `pipeline/Silver/clean_coordinates.py`.
14. Executed `pipeline/Silver/clean_coordinates.py`, implementing business logic to correct swapped latitude/longitude values and quarantine malformed records to maintain data integrity.
15. Executed `pipeline/Silver/clean_seasonality.py`, successfully extrapolating seasonality metrics to cover January 2026 and flagging imputed rows to maintain data integrity.
16. Successfully conducted comprehensive Exploratory Data Analysis on `holidays.csv`, identifying and rectifying data quality issues including missing Outlet_Size values, validating cooler count ranges, and Standardizing outlet type categories.
17. Executed `pipeline/Silver/clean_holidays.py`, implementing business logic to map dates to specific holiday types and quarantining malformed records to maintain data integrity.