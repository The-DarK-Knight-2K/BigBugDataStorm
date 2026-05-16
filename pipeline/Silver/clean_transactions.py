import pandas as pd
import numpy as np
import os
import sys

# Path setup
CURRENT_DIR = os.path.dirname(os.path.abspath(__file__))
PIPELINE_DIR = os.path.dirname(CURRENT_DIR)
ROOT_DIR = os.path.dirname(PIPELINE_DIR)

if PIPELINE_DIR not in sys.path:
    sys.path.insert(0, PIPELINE_DIR)

from utils.logger import setup_logger
from silver.dq_checks import duplicate_check, null_check, ref_integrity_check, value_set_check, range_check, run_checks

log = setup_logger("clean_transactions")

BRONZE_DIR = os.path.join(ROOT_DIR, "Data", "Bronze")
SILVER_DIR = os.path.join(ROOT_DIR, "Data", "Silver")
QUARANTINE_DIR = os.path.join(ROOT_DIR, "Data", "Quarantine")
OUTPUTS_DIR = os.path.join(ROOT_DIR, "outputs")

def get_canonical_columns(df: pd.DataFrame) -> dict:
    fuzzy_map = {
        "Outlet_ID": ["outlet_id", "outlet id", "outletid", "shop_id"],
        "Date": ["date", "transaction_date", "txn_date", "order_date"],
        "Distributor_ID": ["distributor_id", "dist_id", "distributor"],
        "Volume_Litres": ["volume_litres", "volume", "litres", "qty", "quantity", "sales_volume", "volume_liters"]
    }
    
    col_mapping = {}
    raw_cols_lower = {c.lower().strip(): c for c in df.columns}
    
    for canonical, fuzzy_list in fuzzy_map.items():
        found = False
        for fuzzy in fuzzy_list:
            if fuzzy.lower() in raw_cols_lower:
                col_mapping[raw_cols_lower[fuzzy.lower()]] = canonical
                found = True
                break
        if not found:
            raise ValueError(f"Could not find canonical column '{canonical}'. Available raw columns: {df.columns.tolist()}")
            
    return col_mapping

def main():
    # 1. Load bronze
    df = pd.read_parquet(os.path.join(BRONZE_DIR, "transactions_history_final.parquet"))
    log.info(f"Loaded {len(df)} rows from transactions bronze")
    
    log.info(f"Raw columns: {df.columns.tolist()}")
    log.info(f"Raw dtypes: \n{df.dtypes}")
    
    # Map columns
    col_mapping = get_canonical_columns(df)
    df = df.rename(columns=col_mapping)
    log.info(f"Mapped columns: {col_mapping}")
    
    # Check dependencies
    master_path = os.path.join(SILVER_DIR, "outlet_master_clean.parquet")
    if not os.path.exists(master_path):
        log.error(f"Dependency missing: {master_path}. Run clean_outlets.py first.")
        sys.exit(1)
        
    ref_df = pd.read_parquet(master_path)[["Outlet_ID"]]
    
    failed_dfs = []
    
    # 1. Date parsing
    df["date_parsed"] = pd.to_datetime(df["Date"], utc=True, errors="coerce")
    bad_dates_mask = df["date_parsed"].isnull()
    if bad_dates_mask.any():
        bad_dates_df = df[bad_dates_mask].copy()
        bad_dates_df["failure_reason"] = "unparseable_date"
        failed_dfs.append(bad_dates_df)
        df = df[~bad_dates_mask].copy()
        
    df["Year"] = df["date_parsed"].dt.year.astype("int16")
    df["Month"] = df["date_parsed"].dt.month.astype("int8")
    
    out_of_range_date = (df["Year"] < 2020) | (df["Year"] > 2025)
    if out_of_range_date.any():
        oor_dates_df = df[out_of_range_date].copy()
        oor_dates_df["failure_reason"] = "date_out_of_expected_range"
        failed_dfs.append(oor_dates_df)
        df = df[~out_of_range_date].copy()
        
    # 2. DQ Checks
    valid_dists = ["DIST_W_01","DIST_W_02","DIST_W_03","DIST_C_01","DIST_C_02",
                   "DIST_C_03","DIST_NW_01","DIST_NW_02","DIST_S_01","DIST_S_02"]
                   
    checks = [
        (duplicate_check, {"primary_key_cols": ["Outlet_ID", "Date", "Volume_Litres"]}),
        (null_check, {"mandatory_cols": ["Outlet_ID", "Date", "Volume_Litres"]}),
        (ref_integrity_check, {"fk_col": "Outlet_ID", "ref_df": ref_df, "ref_col": "Outlet_ID"}),
        (value_set_check, {"col": "Distributor_ID", "valid_values": valid_dists}),
        (range_check, {"col": "Volume_Litres", "min_val": 0.01, "max_val": None})
    ]
    
    df_passed, run_failed_dfs, report_rows = run_checks(checks, "transactions")
    failed_dfs.extend(run_failed_dfs)
    df_clean = df_passed.copy()
    
    # 3. Outlier detection (IQR)
    log.info("Detecting volume outliers using IQR method...")
    
    def flag_outliers(group):
        if len(group) < 4:
            return pd.Series(False, index=group.index)
        q1 = group["Volume_Litres"].quantile(0.25)
        q3 = group["Volume_Litres"].quantile(0.75)
        iqr = q3 - q1
        return group["Volume_Litres"] > (q3 + 5 * iqr)
        
    df_clean["is_volume_outlier"] = df_clean.groupby("Outlet_ID", group_keys=False).apply(flag_outliers)
    
    # For outlets with <4 txns, use global IQR
    global_q1 = df_clean["Volume_Litres"].quantile(0.25)
    global_q3 = df_clean["Volume_Litres"].quantile(0.75)
    global_iqr = global_q3 - global_q1
    global_outlier_thresh = global_q3 + 5 * global_iqr
    
    # Fill any NaNs from the groupby apply (if any) with False first
    df_clean["is_volume_outlier"] = df_clean["is_volume_outlier"].fillna(False)
    
    # Then for small outlets, override with global logic
    small_outlets = df_clean.groupby("Outlet_ID").size()
    small_outlets = small_outlets[small_outlets < 4].index
    small_mask = df_clean["Outlet_ID"].isin(small_outlets)
    df_clean.loc[small_mask, "is_volume_outlier"] = df_clean.loc[small_mask, "Volume_Litres"] > global_outlier_thresh
    
    outlier_count = df_clean["is_volume_outlier"].sum()
    log.warning(f"Flagged {outlier_count} records as extreme volume outliers (NOT quarantined).")
    
    # 4. Blackout period detection
    log.info("Detecting blackout periods...")
    
    # Create monthly activity grid
    monthly_vol = df_clean.groupby(["Outlet_ID", "Year", "Month"])["Volume_Litres"].sum().reset_index()
    
    # Create a complete grid for all outlets and all months between their first and last txn
    df_clean["is_blackout_period"] = False
    
    # To do this efficiently, we pivot and detect zero sequences
    # Using pivot table
    pivot = monthly_vol.pivot_table(index="Outlet_ID", columns=["Year", "Month"], values="Volume_Litres", fill_value=0)
    
    blackout_records = []
    
    for outlet_id, row in pivot.iterrows():
        non_zeros = row[row > 0]
        if len(non_zeros) < 2:
            continue # Needs to be sandwiched
            
        first_idx = non_zeros.index[0]
        last_idx = non_zeros.index[-1]
        
        # Slicing the series between first and last non-zero
        active_period = row.loc[first_idx:last_idx]
        zero_months = active_period[active_period == 0].index
        
        for y, m in zero_months:
            blackout_records.append({"Outlet_ID": outlet_id, "Year": y, "Month": m})
            
    if blackout_records:
        blackout_df = pd.DataFrame(blackout_records)
        blackout_df["is_blackout"] = True
        
        df_clean = df_clean.merge(blackout_df, on=["Outlet_ID", "Year", "Month"], how="left")
        df_clean["is_blackout_period"] = df_clean["is_blackout"].fillna(False)
        df_clean.drop(columns=["is_blackout"], inplace=True)
        
    blackout_count = df_clean["is_blackout_period"].sum()
    log.info(f"Flagged {blackout_count} transactions as occurring during a blackout period.")
    
    # 5. Construct Output
    df_clean["Date"] = df_clean["date_parsed"].dt.date
    df_clean["Volume_Litres"] = df_clean["Volume_Litres"].astype("float32")
    df_clean["row_source"] = "transactions_history_final.csv"
    
    output_cols = ["Outlet_ID", "Date", "Year", "Month", "Distributor_ID", 
                   "Volume_Litres", "is_volume_outlier", "is_blackout_period", "row_source"]
                   
    df_clean = df_clean[output_cols]
    
    # Assertions
    assert len(df_clean) > 0, "Clean transactions DataFrame is empty."
    assert df_clean["Volume_Litres"].min() > 0, "Non-positive volumes in clean output."
    assert df_clean["Outlet_ID"].isnull().sum() == 0, "Null Outlet_IDs in clean output."
    assert "is_blackout_period" in df_clean.columns
    assert "is_volume_outlier" in df_clean.columns
    
    # Quarantine rate check
    total_quarantined = sum(len(f) for f in failed_dfs)
    total_input = len(df)
    pct_quarantined = (total_quarantined / total_input) * 100
    
    if pct_quarantined > 30:
        log.warning(f"High quarantine rate ({pct_quarantined:.1f}%) — review the transactions data carefully.")
        
    # Write outputs
    os.makedirs(SILVER_DIR, exist_ok=True)
    df_clean.to_parquet(os.path.join(SILVER_DIR, "transactions_clean.parquet"), index=False)
    
    if failed_dfs:
        df_quarantine = pd.concat(failed_dfs, ignore_index=True)
        os.makedirs(QUARANTINE_DIR, exist_ok=True)
        df_quarantine.to_parquet(os.path.join(QUARANTINE_DIR, "rejected_transactions.parquet"), index=False)
        
    report_df = pd.DataFrame(report_rows)
    report_path = os.path.join(OUTPUTS_DIR, "dq_report.csv")
    os.makedirs(OUTPUTS_DIR, exist_ok=True)
    report_df.to_csv(report_path, mode='a', header=not os.path.exists(report_path), index=False)
    
    log.info("transactions cleaning complete")
    log.info(f"  Input rows        : {total_input}")
    log.info(f"  Clean rows        : {len(df_clean)}")
    log.info(f"  Quarantined rows  : {total_quarantined}")

if __name__ == "__main__":
    main()
