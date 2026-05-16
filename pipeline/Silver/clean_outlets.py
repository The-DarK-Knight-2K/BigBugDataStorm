import pandas as pd
import os
import sys
import yaml

# Path setup
CURRENT_DIR = os.path.dirname(os.path.abspath(__file__))
PIPELINE_DIR = os.path.dirname(CURRENT_DIR)
ROOT_DIR = os.path.dirname(PIPELINE_DIR)

if PIPELINE_DIR not in sys.path:
    sys.path.insert(0, PIPELINE_DIR)

from utils.logger import setup_logger
from silver.dq_checks import duplicate_check, null_check, format_check, range_check, value_set_check, run_checks

log = setup_logger("clean_outlets")

BRONZE_DIR = os.path.join(ROOT_DIR, "Data", "Bronze")
SILVER_DIR = os.path.join(ROOT_DIR, "Data", "Silver")
QUARANTINE_DIR = os.path.join(ROOT_DIR, "Data", "Quarantine")
OUTPUTS_DIR = os.path.join(ROOT_DIR, "outputs")
CONFIG_PATH = os.path.join(ROOT_DIR, "config.yaml")

def load_config():
    with open(CONFIG_PATH, 'r') as file:
        return yaml.safe_load(file)

def main():
    CFG = load_config()
    
    # 1. Load bronze
    df = pd.read_parquet(os.path.join(BRONZE_DIR, "outlet_master.parquet"))
    log.info(f"Loaded {len(df)} rows from outlet_master bronze")
    
    # 2. DQ Checks (before any fixes)
    checks = [
        (duplicate_check, {"primary_key_cols": ["Outlet_ID"]}),
        (null_check, {"mandatory_cols": ["Outlet_ID", "Outlet_Type", "Cooler_Count"]}),
        (format_check, {"col": "Outlet_ID", "regex_pattern": r"OUT_\d{5}"}),
        (range_check, {"col": "Cooler_Count", "min_val": 0, "max_val": 5})
    ]
    
    df_passed, failed_dfs, report_rows = run_checks(checks, "outlet_master")
    
    if df_passed.empty:
        log.error("All rows failed DQ checks!")
        sys.exit(1)
        
    df_clean = df_passed.copy()
    
    # 3. Normalise Outlet_Size
    df_clean["Outlet_Size"] = df_clean["Outlet_Size"].astype(str).str.strip().str.title()
    # Replace "Nan" or "None" strings resulting from casting nulls to string
    df_clean.loc[df_clean["Outlet_Size"].isin(["Nan", "None", ""]), "Outlet_Size"] = None
    
    SIZE_IMPUTATION_MAP = {0: "Small", 1: "Small", 2: "Medium", 3: "Large", 4: "Large", 5: "Extra Large"}
    
    def impute_size(row):
        if pd.isna(row["Outlet_Size"]):
            row["size_imputed"] = True
            row["Outlet_Size"] = SIZE_IMPUTATION_MAP.get(int(row["Cooler_Count"]), "Small")
        else:
            row["size_imputed"] = False
        return row
        
    df_clean = df_clean.apply(impute_size, axis=1)
    imputed_count = df_clean["size_imputed"].sum()
    log.info(f"Imputed Outlet_Size for {imputed_count} rows using Cooler_Count rule.")
    
    # Validation against valid sizes
    valid_sizes = CFG["valid_outlet_sizes"]
    invalid_size_mask = ~df_clean["Outlet_Size"].isin(valid_sizes)
    if invalid_size_mask.any():
        invalid_size_df = df_clean[invalid_size_mask].copy()
        invalid_size_df["failure_reason"] = "invalid_value:Outlet_Size:found=" + invalid_size_df["Outlet_Size"]
        failed_dfs.append(invalid_size_df)
        df_clean = df_clean[~invalid_size_mask].copy()
    
    # 4. Normalise Outlet_Type
    df_clean["Outlet_Type"] = df_clean["Outlet_Type"].astype(str).str.strip()
    corrections = CFG["outlet_type_corrections"]
    
    mask_to_correct = df_clean["Outlet_Type"].isin(corrections.keys())
    corrected_count = mask_to_correct.sum()
    df_clean["Outlet_Type"] = df_clean["Outlet_Type"].replace(corrections)
    log.info(f"Corrected Outlet_Type typos: {corrected_count} rows updated.")
    
    # Validation against valid types
    valid_types = CFG["valid_outlet_types"]
    invalid_type_mask = ~df_clean["Outlet_Type"].isin(valid_types)
    if invalid_type_mask.any():
        invalid_type_df = df_clean[invalid_type_mask].copy()
        invalid_type_df["failure_reason"] = "invalid_value:Outlet_Type:found=" + invalid_type_df["Outlet_Type"]
        failed_dfs.append(invalid_type_df)
        df_clean = df_clean[~invalid_type_mask].copy()

    # 5. Cast Types
    df_clean["Cooler_Count"] = df_clean["Cooler_Count"].astype("int8")
    df_clean["size_imputed"] = df_clean["size_imputed"].astype(bool)
    
    # 6. Final Validation (Internal Logic Check)
    assert set(df_clean["Outlet_Size"].unique()).issubset(set(valid_sizes))
    assert set(df_clean["Outlet_Type"].unique()).issubset(set(valid_types))
    
    # 7. Write Outputs
    output_cols = ["Outlet_ID", "Outlet_Size", "Cooler_Count", "Outlet_Type", "size_imputed"]
    df_clean = df_clean[output_cols]
    
    os.makedirs(SILVER_DIR, exist_ok=True)
    df_clean.to_parquet(os.path.join(SILVER_DIR, "outlet_master_clean.parquet"), index=False)
    
    total_quarantined = 0
    if failed_dfs:
        df_quarantine = pd.concat(failed_dfs, ignore_index=True)
        total_quarantined = len(df_quarantine)
        os.makedirs(QUARANTINE_DIR, exist_ok=True)
        df_quarantine.to_parquet(os.path.join(QUARANTINE_DIR, "rejected_outlet_master.parquet"), index=False)
        
    report_df = pd.DataFrame(report_rows)
    report_path = os.path.join(OUTPUTS_DIR, "dq_report.csv")
    os.makedirs(OUTPUTS_DIR, exist_ok=True)
    report_df.to_csv(report_path, mode='a', header=not os.path.exists(report_path), index=False)

    log.info("outlet_master cleaning complete")
    log.info(f"  Input rows        : {len(df)}")
    log.info(f"  Clean rows        : {len(df_clean)}")
    log.info(f"  Quarantined rows  : {total_quarantined}")
    log.info(f"  Sizes imputed     : {imputed_count}")
    log.info(f"  Type typos fixed  : {corrected_count}")
    
    assert len(df_clean) + total_quarantined == 20000

if __name__ == "__main__":
    main()
