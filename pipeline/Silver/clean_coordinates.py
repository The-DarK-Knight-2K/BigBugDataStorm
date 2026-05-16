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
from silver.dq_checks import duplicate_check, null_check, ref_integrity_check, run_checks

log = setup_logger("clean_coordinates")

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
    df = pd.read_parquet(os.path.join(BRONZE_DIR, "outlet_coordinates.parquet"))
    log.info(f"Loaded {len(df)} rows from outlet_coordinates bronze")
    
    # Check dependencies
    master_path = os.path.join(SILVER_DIR, "outlet_master_clean.parquet")
    if not os.path.exists(master_path):
        log.error(f"Dependency missing: {master_path}. Run clean_outlets.py first.")
        sys.exit(1)
        
    ref_df = pd.read_parquet(master_path)[["Outlet_ID"]]
    
    # 2. DQ Checks
    checks = [
        (duplicate_check, {"primary_key_cols": ["Outlet_ID"]}),
        (null_check, {"mandatory_cols": ["Outlet_ID", "Latitude", "Longitude"]}),
        (ref_integrity_check, {"fk_col": "Outlet_ID", "ref_df": ref_df, "ref_col": "Outlet_ID"})
    ]
    
    df_passed, failed_dfs, report_rows = run_checks(df, checks, "outlet_coordinates")
    df_clean = df_passed.copy()
    
    # 3. Zero-coordinate quarantine
    zero_mask = (df_clean["Latitude"] == 0.0) & (df_clean["Longitude"] == 0.0)
    zero_count = zero_mask.sum()
    if zero_count > 0:
        zero_df = df_clean[zero_mask].copy()
        zero_df["failure_reason"] = "zero_coordinates"
        failed_dfs.append(zero_df)
        df_clean = df_clean[~zero_mask].copy()
        log.info(f"Quarantining {zero_count} zero-coordinate rows (GPS never recorded).")
        
    # 4. Detect and fix swapped lat/lon
    swapped_mask = df_clean["Latitude"] > 50
    swapped_count = swapped_mask.sum()
    
    # Do the swap
    df_clean.loc[swapped_mask, ["Latitude", "Longitude"]] = df_clean.loc[swapped_mask, ["Longitude", "Latitude"]].values
    df_clean["coords_swapped"] = swapped_mask
    log.info(f"Swapped lat/lon for {swapped_count} rows.")
    
    # 5. Bounds validation
    bounds = CFG["sri_lanka_bounds"]
    out_of_bounds_mask = (
        (df_clean["Latitude"] < bounds["lat_min"]) |
        (df_clean["Latitude"] > bounds["lat_max"]) |
        (df_clean["Longitude"] < bounds["lon_min"]) |
        (df_clean["Longitude"] > bounds["lon_max"])
    )
    oob_count = out_of_bounds_mask.sum()
    if oob_count > 0:
        oob_df = df_clean[out_of_bounds_mask].copy()
        oob_df["failure_reason"] = "coordinates_out_of_sri_lanka_bounds"
        failed_dfs.append(oob_df)
        df_clean = df_clean[~out_of_bounds_mask].copy()
        log.warning(f"Quarantining {oob_count} out-of-bounds rows after swap fix.")
        
    # 6. Cast types
    df_clean["Latitude"] = df_clean["Latitude"].astype("float64")
    df_clean["Longitude"] = df_clean["Longitude"].astype("float64")
    df_clean["coords_swapped"] = df_clean["coords_swapped"].astype(bool)
    
    # Assertions
    assert df_clean["Outlet_ID"].duplicated().sum() == 0
    assert df_clean["Outlet_ID"].isnull().sum() == 0
    assert df_clean["Latitude"].between(bounds["lat_min"], bounds["lat_max"]).all()
    assert df_clean["Longitude"].between(bounds["lon_min"], bounds["lon_max"]).all()
    assert (df_clean["Latitude"] == 0).sum() == 0
    assert (df_clean["Longitude"] == 0).sum() == 0
    
    total_quarantined = sum(len(f) for f in failed_dfs)
    assert len(df_clean) + total_quarantined == len(df)
    
    # 7. Write outputs
    output_cols = ["Outlet_ID", "Latitude", "Longitude", "coords_swapped"]
    df_clean = df_clean[output_cols]
    
    os.makedirs(SILVER_DIR, exist_ok=True)
    df_clean.to_parquet(os.path.join(SILVER_DIR, "outlet_coordinates_clean.parquet"), index=False)
    
    if failed_dfs:
        df_quarantine = pd.concat(failed_dfs, ignore_index=True)
        os.makedirs(QUARANTINE_DIR, exist_ok=True)
        df_quarantine.to_parquet(os.path.join(QUARANTINE_DIR, "rejected_outlet_coordinates.parquet"), index=False)
        
    report_df = pd.DataFrame(report_rows)
    report_path = os.path.join(OUTPUTS_DIR, "dq_report.csv")
    os.makedirs(OUTPUTS_DIR, exist_ok=True)
    report_df.to_csv(report_path, mode='a', header=not os.path.exists(report_path), index=False)
    
    log.info("outlet_coordinates cleaning complete")
    log.info(f"  Input rows        : {len(df)}")
    log.info(f"  Clean rows        : {len(df_clean)}")
    log.info(f"  Quarantined rows  : {total_quarantined}")
    log.info(f"    zero_coordinates: {zero_count}")
    log.info(f"    other           : {total_quarantined - zero_count}")
    log.info(f"  Lat/Lon swaps     : {swapped_count}")

if __name__ == "__main__":
    main()
