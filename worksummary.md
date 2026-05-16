# Work Summary

1. Created `.gitignore` to exclude datasets and environment files.
2. Initialized Lakehouse directory structure (`Data/Raw/`, `Bronze/`, `Silver/`, `Gold/`) with `.gitkeep` files.
3. Cleaned Git history by removing a large 161MB tracked `.csv` file and amending the initial commit.
4. Successfully pushed the cleaned `main` branch to GitHub.
5. Created and executed `Scripts/01_raw_to_bronze.py` to ingest raw CSV data directly into `.parquet` format in the `Data/Bronze/` directory.
