Links - https://drive.google.com/drive/folders/1Uq_OTs4e2pElRrC3nFt3_EoDk2yUZdeP?usp=drive_link

# Work Summary

## Phase 1: Infrastructure & Setup

1. Created `.gitignore` to exclude datasets and environment files.
2. Initialized Lakehouse directory structure (`Data/Raw/`, `Bronze/`, `Silver/`, `Gold/`) with `.gitkeep` files.
3. Cleaned Git history by removing a large 161MB tracked `.csv` file and amending the initial commit.
4. Successfully pushed the cleaned `main` branch to GitHub.
5. Created and executed `Scripts/01_raw_to_bronze.py` to ingest raw CSV data directly into `.parquet` format in the `Data/Bronze/` directory.
6. Upgraded project to a modular pipeline structure, adding `pipeline/utils/logger.py` and refactoring `pipeline/bronze/01_raw_to_bronze.py` to use professional file logging (`outputs/pipeline.log`).
7. Initialized Silver Layer architecture by creating the `Data/Quarantine/` directory and root `config.yaml` with geographical and string-correction constants.

## Phase 2: Exploratory Data Analysis (EDA)

8. Reviewed `01_eda_transactions.ipynb` and verified coverage of missing values, distributions, and holiday/seasonality impact.
9. Finalized strategies for transactions data: netting/quarantining negative volumes and contextualizing/log-transforming outliers for the LightGBM model.
10. Successfully conducted comprehensive Exploratory Data Analysis on `outlets.csv`, identifying and rectifying data quality issues including missing Outlet_Size values, validating cooler count ranges, and standardizing outlet type categories.
11. Successfully conducted comprehensive Exploratory Data Analysis on `holidays.csv`, validating date ranges, identifying duplicate entries, and standardizing holiday categories (Public, Bank, Mercantile, Poya Day).

## Phase 3: Silver Layer (Data Quality & Cleaning)

12. Successfully wrote Phase 1 of the Silver Layer: `dq_checks.py` library and 5 specific dataset cleaning scripts packed with all business logic and anomaly detection algorithms.
13. Executed `pipeline/Silver/clean_outlets.py`, implementing business logic to impute missing outlet sizes based on cooler count heuristics and quarantining malformed records.
14. Successfully diagnosed and resolved latitude/longitude coordinate discrepancies in `outlet_coordinates.csv` using advanced geocoding validation and bounding box checks, correcting swapped values.
15. Executed `pipeline/Silver/clean_coordinates.py`, implementing business logic to correct swapped latitude/longitude values and quarantine malformed records.
16. Executed `pipeline/Silver/clean_seasonality.py`, successfully extrapolating seasonality metrics to cover January 2026 and flagging imputed rows.
17. Executed `pipeline/Silver/clean_holidays.py`, implementing business logic to map dates to specific holiday types and quarantining malformed records.

## Phase 4: Gold Layer (Feature Engineering)

18. Implemented Gold Layer POI data acquisition pipeline: `scrape_poi_raw.py` using Overpass API with K-Means clustering to optimize bounding box queries and respect API rate limits via a manifest-based caching system.
19. Developed `build_poi_features.py` to calculate outlet-specific POI density metrics across multiple radii (500m, 1km, 2km) and compute a weighted, normalized `footfall_score` for all 20,000 outlets.
20. Implemented `build_sales_features.py` to derive advanced historical metrics, including YoY growth, EMA trends, and January-specific seasonality patterns to support target variable estimation.

## Phase 5: Repository Management

21. Synchronized local repository with `origin/main`, resolving complex merge conflicts and file locks on `outputs/pipeline.log` to ensure alignment with the latest team updates.
