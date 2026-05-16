import pandas as pd
import os
import sys
import json
from datetime import date
import calendar

# Path setup
CURRENT_DIR = os.path.dirname(os.path.abspath(__file__))
PIPELINE_DIR = os.path.dirname(CURRENT_DIR)
ROOT_DIR = os.path.dirname(PIPELINE_DIR)

if PIPELINE_DIR not in sys.path:
    sys.path.insert(0, PIPELINE_DIR)

from utils.logger import setup_logger
from silver.dq_checks import null_check, value_set_check, run_checks

log = setup_logger("clean_holidays")

BRONZE_DIR = os.path.join(ROOT_DIR, "Data", "Bronze")
SILVER_DIR = os.path.join(ROOT_DIR, "Data", "Silver")
OUTPUTS_DIR = os.path.join(ROOT_DIR, "outputs")

def pivot_holidays(df: pd.DataFrame) -> pd.DataFrame:
    """One row per unique date with boolean columns for each holiday type."""
    result = []
    for d, group in df.groupby("date"):
        types = set(group["Holiday_Type"].str.strip().tolist())
        primary_name = group["Holiday_Name"].iloc[0]
        result.append({
            "date": d,
            "Holiday_Name": primary_name,
            "is_public": "Public" in types,
            "is_bank": "Bank" in types,
            "is_mercantile": "Mercantile" in types,
            "is_poya_day": "Poya Day" in types,
        })
    return pd.DataFrame(result)

def main():
    # 1. Load bronze
    df = pd.read_parquet(os.path.join(BRONZE_DIR, "holiday_list.parquet"))
    log.info(f"Loaded {len(df)} rows from holidays bronze")
    
    # 2. Parse dates
    df["date_parsed"] = pd.to_datetime(df["Date"], utc=True, errors="coerce")
    bad_dates = df[df["date_parsed"].isnull()]
    if len(bad_dates) > 0:
        log.warning(f"Found {len(bad_dates)} unparseable dates. Dropping them.")
        df = df[~df["date_parsed"].isnull()].copy()
        
    df["date"] = df["date_parsed"].dt.date
    
    # 3. DQ Checks on raw rows
    checks = [
        (null_check, {"mandatory_cols": ["Holiday_Name", "Holiday_Type"]}),
        (value_set_check, {"col": "Holiday_Type", "valid_values": ["Public", "Bank", "Mercantile", "Poya Day"]})
    ]
    
    df_passed, failed_dfs, report_rows = run_checks(df, checks, "holidays")
    df_clean = df_passed.copy()
    
    # 4. Pivot to one row per date
    df_pivoted = pivot_holidays(df_clean)
    df_pivoted = df_pivoted.sort_values("date")
    
    # 5. Append Jan 2026 manually
    JAN_2026_HOLIDAYS = [
        {
            "date": date(2026, 1, 2),
            "Holiday_Name": "Duruthu Full Moon Poya Day",
            "is_public": True, "is_bank": True, "is_mercantile": True, "is_poya_day": True,
        },
        {
            "date": date(2026, 1, 14),
            "Holiday_Name": "Thai Pongal Day",
            "is_public": True, "is_bank": True, "is_mercantile": True, "is_poya_day": False,
        },
    ]
    df_jan2026 = pd.DataFrame(JAN_2026_HOLIDAYS)
    df_jan2026["is_manually_added"] = True
    
    df_pivoted["is_manually_added"] = False
    
    df_final = pd.concat([df_pivoted, df_jan2026], ignore_index=True)
    df_final = df_final.sort_values("date").reset_index(drop=True)
    
    log.info(f"Manually added {len(df_jan2026)} January 2026 holiday entries.")
    
    # 6. Cast types
    df_final["date"] = pd.to_datetime(df_final["date"]).dt.date
    df_final["is_public"] = df_final["is_public"].astype(bool)
    df_final["is_bank"] = df_final["is_bank"].astype(bool)
    df_final["is_mercantile"] = df_final["is_mercantile"].astype(bool)
    df_final["is_poya_day"] = df_final["is_poya_day"].astype(bool)
    df_final["is_manually_added"] = df_final["is_manually_added"].astype(bool)
    
    # 7. Compute Jan 2026 trading days
    jan_2026_days = pd.date_range("2026-01-01", "2026-01-31")
    weekdays_jan_2026 = [d for d in jan_2026_days if d.weekday() < 5]
    
    jan_2026_holidays_df = df_final[
        (pd.to_datetime(df_final["date"]).dt.year == 2026) &
        (pd.to_datetime(df_final["date"]).dt.month == 1)
    ]
    holiday_dates = set(pd.to_datetime(jan_2026_holidays_df["date"]).dt.date)
    trading_days = [d for d in weekdays_jan_2026 if d.date() not in holiday_dates]
    
    jan_2026_trading_day_count = len(trading_days)
    log.info(f"January 2026 trading days (weekdays minus holidays): {jan_2026_trading_day_count}")
    
    os.makedirs(SILVER_DIR, exist_ok=True)
    with open(os.path.join(SILVER_DIR, "jan_2026_trading_days.json"), "w") as f:
        json.dump({"jan_2026_trading_days": jan_2026_trading_day_count, "jan_2026_holiday_count": len(holiday_dates)}, f)
        
    # 8. Assertions and Write
    assert df_final["date"].duplicated().sum() == 0, "Duplicate dates in clean holidays"
    assert df_final["date"].isnull().sum() == 0
    jan_2026_count = (pd.to_datetime(df_final["date"]).dt.year == 2026).sum()
    assert jan_2026_count >= 2, f"Expected >=2 Jan 2026 holidays, got {jan_2026_count}"
    
    output_cols = ["date", "Holiday_Name", "is_public", "is_bank", "is_mercantile", "is_poya_day", "is_manually_added"]
    df_final = df_final[output_cols]
    
    df_final.to_parquet(os.path.join(SILVER_DIR, "holidays_clean.parquet"), index=False)
    
    report_df = pd.DataFrame(report_rows)
    report_path = os.path.join(OUTPUTS_DIR, "dq_report.csv")
    os.makedirs(OUTPUTS_DIR, exist_ok=True)
    report_df.to_csv(report_path, mode='a', header=not os.path.exists(report_path), index=False)
    
    log.info("holidays cleaning complete")

if __name__ == "__main__":
    main()
