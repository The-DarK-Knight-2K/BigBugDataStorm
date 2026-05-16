import pandas as pd
import os
import sys
from itertools import product

# Path setup
CURRENT_DIR = os.path.dirname(os.path.abspath(__file__))
PIPELINE_DIR = os.path.dirname(CURRENT_DIR)
ROOT_DIR = os.path.dirname(PIPELINE_DIR)

if PIPELINE_DIR not in sys.path:
    sys.path.insert(0, PIPELINE_DIR)

from utils.logger import setup_logger
from silver.dq_checks import duplicate_check, null_check, value_set_check, range_check, run_checks

log = setup_logger("clean_seasonality")

BRONZE_DIR = os.path.join(ROOT_DIR, "Data", "Bronze")
SILVER_DIR = os.path.join(ROOT_DIR, "Data", "Silver")
OUTPUTS_DIR = os.path.join(ROOT_DIR, "outputs")

KNOWN_DISTRIBUTORS = [
    "DIST_W_01", "DIST_W_02", "DIST_W_03",
    "DIST_C_01", "DIST_C_02", "DIST_C_03",
    "DIST_NW_01", "DIST_NW_02",
    "DIST_S_01", "DIST_S_02"
]

def main():
    # 1. Load bronze
    df = pd.read_parquet(os.path.join(BRONZE_DIR, "distributor_seasonality_details.parquet"))
    log.info(f"Loaded {len(df)} rows from seasonality bronze")
    
    # 2. DQ Checks
    checks = [
        (duplicate_check, {"primary_key_cols": ["Distributor_ID", "Year", "Month"]}),
        (null_check, {"mandatory_cols": ["Distributor_ID", "Year", "Month", "Seasonality_Index"]}),
        (value_set_check, {"col": "Seasonality_Index", "valid_values": ["Favorable", "Moderate", "Un-Favorable"]}),
        (range_check, {"col": "Year", "min_val": 2023, "max_val": 2025}),
        (range_check, {"col": "Month", "min_val": 1, "max_val": 12})
    ]
    
    df_passed, failed_dfs, report_rows = run_checks(df, checks, "seasonality")
    
    if failed_dfs:
        log.error("DQ failures detected in seasonality! Source data should be clean.")
        sys.exit(1)
        
    df_clean = df_passed.copy()
    
    # Completeness check
    expected_combos = pd.DataFrame(
        list(product(KNOWN_DISTRIBUTORS, [2023, 2024, 2025], range(1, 13))),
        columns=["Distributor_ID", "Year", "Month"]
    )
    merged = expected_combos.merge(df_clean, on=["Distributor_ID", "Year", "Month"], how="left")
    missing = merged[merged["Seasonality_Index"].isnull()]
    if len(missing) > 0:
        log.warning(f"Missing {len(missing)} distributor-year-month combinations")
        log.warning(missing.to_string())
        
    # 3. Extrapolate January 2026
    jan_2025 = df_clean[(df_clean["Year"] == 2025) & (df_clean["Month"] == 1)].copy()
    jan_2026 = jan_2025.copy()
    jan_2026["Year"] = 2026
    jan_2026["is_extrapolated"] = True
    
    df_clean["is_extrapolated"] = False
    
    df_clean = pd.concat([df_clean, jan_2026], ignore_index=True)
    
    log.info("Extrapolated January 2026 seasonality for 10 distributors using Jan 2025 values.")
    for _, row in jan_2026.iterrows():
        log.info(f"{row['Distributor_ID']} -> Jan 2026: {row['Seasonality_Index']} (extrapolated from Jan 2025)")
        
    # 4. Cast types
    df_clean["Year"] = df_clean["Year"].astype("int16")
    df_clean["Month"] = df_clean["Month"].astype("int8")
    df_clean["is_extrapolated"] = df_clean["is_extrapolated"].astype(bool)
    
    # Assertions
    assert len(df_clean) == 370
    jan_2026_rows = df_clean[(df_clean["Year"] == 2026) & (df_clean["Month"] == 1)]
    assert len(jan_2026_rows) == 10
    assert jan_2026_rows["is_extrapolated"].all()
    assert set(jan_2026_rows["Distributor_ID"]) == set(KNOWN_DISTRIBUTORS)
    assert df_clean["Seasonality_Index"].isnull().sum() == 0
    assert set(df_clean["Seasonality_Index"].unique()).issubset({"Favorable", "Moderate", "Un-Favorable"})
    
    # 5. Write outputs
    output_cols = ["Distributor_ID", "Year", "Month", "Seasonality_Index", "is_extrapolated"]
    df_clean = df_clean[output_cols]
    
    os.makedirs(SILVER_DIR, exist_ok=True)
    df_clean.to_parquet(os.path.join(SILVER_DIR, "seasonality_clean.parquet"), index=False)
    
    report_df = pd.DataFrame(report_rows)
    report_path = os.path.join(OUTPUTS_DIR, "dq_report.csv")
    os.makedirs(OUTPUTS_DIR, exist_ok=True)
    report_df.to_csv(report_path, mode='a', header=not os.path.exists(report_path), index=False)
    
    log.info("seasonality cleaning complete")

if __name__ == "__main__":
    main()
