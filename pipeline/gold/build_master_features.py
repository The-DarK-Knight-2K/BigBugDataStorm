"""
Build the master features table by merging all Silver-layer cleaned datasets
and Gold-layer feature tables into a single, model-ready DataFrame.
One row per outlet. All 20,000 outlets must appear in the output.

Layer  : Gold
Inputs : outlet_master_clean.parquet, outlet_coordinates_clean.parquet,
         seasonality_clean.parquet, holidays_clean.parquet,
         jan_2026_trading_days.json, sales_features.parquet, poi_features.parquet
Outputs: master_features.parquet
"""

import json
import os
import sys
import time

import numpy as np
import pandas as pd

# ---------------------------------------------------------------------------
# Path setup (matches existing Gold scripts)
# ---------------------------------------------------------------------------
CURRENT_DIR = os.path.dirname(os.path.abspath(__file__))
PIPELINE_DIR = os.path.dirname(CURRENT_DIR)
ROOT_DIR = os.path.dirname(PIPELINE_DIR)

if PIPELINE_DIR not in sys.path:
    sys.path.insert(0, PIPELINE_DIR)

from utils.logger import setup_logger

log = setup_logger("build_master_features")

SILVER_DIR = os.path.join(ROOT_DIR, "Data", "Silver")
GOLD_DIR = os.path.join(ROOT_DIR, "Data", "Gold")

# ---------------------------------------------------------------------------
# Static mappings
# ---------------------------------------------------------------------------
DIST_TO_PROVINCE = {
    "DIST_W_01": "Western",    "DIST_W_02": "Western",    "DIST_W_03": "Western",
    "DIST_C_01": "Central",    "DIST_C_02": "Central",    "DIST_C_03": "Central",
    "DIST_NW_01": "North-Western", "DIST_NW_02": "North-Western",
    "DIST_S_01": "Southern",   "DIST_S_02": "Southern",
}

SEASON_MULTIPLIER = {
    "Favorable":    1.20,
    "Moderate":     1.00,
    "Un-Favorable": 0.85,
}

PROVINCE_CENTROIDS = {
    "Western":       (6.9271, 79.8612),
    "Central":       (7.2906, 80.6337),
    "North-Western": (7.7102, 80.0078),
    "Southern":      (6.0535, 80.2210),
}


# ---------------------------------------------------------------------------
# Helper functions
# ---------------------------------------------------------------------------

def load_inputs() -> dict:
    """Step 1 — Load all input files and return them in a dict."""
    outlets = pd.read_parquet(os.path.join(SILVER_DIR, "outlet_master_clean.parquet"))
    log.info("Loaded outlet_master_clean: %d rows", len(outlets))

    coords = pd.read_parquet(os.path.join(SILVER_DIR, "outlet_coordinates_clean.parquet"))
    log.info("Loaded outlet_coordinates_clean: %d rows", len(coords))

    season = pd.read_parquet(os.path.join(SILVER_DIR, "seasonality_clean.parquet"))
    log.info("Loaded seasonality_clean: %d rows", len(season))

    sales_ft = pd.read_parquet(os.path.join(GOLD_DIR, "sales_features.parquet"))
    log.info("Loaded sales_features: %d rows", len(sales_ft))

    poi_ft = pd.read_parquet(os.path.join(GOLD_DIR, "poi_features.parquet"))
    log.info("Loaded poi_features: %d rows", len(poi_ft))

    grav_ft = pd.read_parquet(os.path.join(GOLD_DIR, "gravity_features.parquet"))
    log.info("Loaded gravity_features: %d rows", len(grav_ft))

    catch_ft = pd.read_parquet(os.path.join(GOLD_DIR, "catchment_features.parquet"))
    log.info("Loaded catchment_features: %d rows", len(catch_ft))

    json_path = os.path.join(SILVER_DIR, "jan_2026_trading_days.json")
    with open(json_path) as f:
        trading_days_info = json.load(f)
    log.info("Loaded jan_2026_trading_days.json: %s", trading_days_info)

    return {
        "outlets": outlets,
        "coords": coords,
        "season": season,
        "sales_ft": sales_ft,
        "poi_ft": poi_ft,
        "grav_ft": grav_ft,
        "catch_ft": catch_ft,
        "jan_2026_trading_days": trading_days_info["jan_2026_trading_days"],
        "jan_2026_holiday_count": trading_days_info["jan_2026_holiday_count"],
    }


def build_seasonality_lookup(season: pd.DataFrame) -> pd.DataFrame:
    """Step 3 — Filter seasonality to Jan 2026 and add numeric multiplier."""
    jan_2026 = season[
        (season["Year"] == 2026) & (season["Month"] == 1)
    ][["Distributor_ID", "Seasonality_Index"]].rename(
        columns={"Seasonality_Index": "seasonality_jan_2026"}
    )

    jan_2026["seasonality_multiplier_jan_2026"] = (
        jan_2026["seasonality_jan_2026"].map(SEASON_MULTIPLIER)
    )
    log.info("Jan 2026 seasonality lookup: %d distributors", len(jan_2026))
    return jan_2026


def merge_all_datasets(
    outlets: pd.DataFrame,
    coords: pd.DataFrame,
    sales_ft: pd.DataFrame,
    poi_ft: pd.DataFrame,
    grav_ft: pd.DataFrame,
    catch_ft: pd.DataFrame,
    jan_2026_season: pd.DataFrame,
) -> pd.DataFrame:
    """Step 4 — LEFT JOIN all datasets onto the outlet master base."""
    df = outlets.copy()
    log.info("Base outlets: %d rows", len(df))

    # Merge coordinates
    df = df.merge(
        coords[["Outlet_ID", "Latitude", "Longitude", "coords_swapped"]],
        on="Outlet_ID", how="left"
    )
    log.info("After coords merge: %d rows", len(df))

    # Merge sales features
    df = df.merge(sales_ft, on="Outlet_ID", how="left")
    log.info("After sales_features merge: %d rows", len(df))

    # Merge POI features
    df = df.merge(poi_ft, on="Outlet_ID", how="left")
    log.info("After poi_features merge: %d rows", len(df))

    # Merge gravity features
    df = df.merge(grav_ft, on="Outlet_ID", how="left")
    log.info("After gravity_features merge: %d rows", len(df))

    # Merge catchment features
    df = df.merge(catch_ft, on="Outlet_ID", how="left")
    log.info("After catchment_features merge: %d rows", len(df))

    # Merge seasonality via distributor_id from sales_features
    df = df.merge(
        jan_2026_season,
        left_on="distributor_id",
        right_on="Distributor_ID",
        how="left"
    ).drop(columns=["Distributor_ID"])
    log.info("After seasonality merge: %d rows", len(df))

    return df


def add_scalar_features(
    df: pd.DataFrame,
    jan_2026_trading_days: int,
    jan_2026_holiday_count: int,
) -> pd.DataFrame:
    """Step 5 — Add scalar features (same value for all rows)."""
    df["jan_2026_holiday_count"] = jan_2026_holiday_count
    df["jan_2026_trading_days"] = jan_2026_trading_days
    log.info("Added scalar features: trading_days=%d, holiday_count=%d",
             jan_2026_trading_days, jan_2026_holiday_count)
    return df


def derive_province(df: pd.DataFrame) -> pd.DataFrame:
    """Step 6 — Derive province from distributor_id."""
    df["province"] = df["distributor_id"].map(DIST_TO_PROVINCE)
    unmapped = df["province"].isnull().sum()
    if unmapped > 0:
        log.warning("%d outlets have no province mapping (null distributor_id)", unmapped)
    return df


def handle_nulls(df: pd.DataFrame) -> pd.DataFrame:
    """Step 7 — Handle all nulls from LEFT JOINs."""

    # --- coords_swapped: NaN for quarantined outlets → False ---
    n_null_swapped = df["coords_swapped"].isnull().sum()
    df["coords_swapped"] = df["coords_swapped"].fillna(False)
    if n_null_swapped > 0:
        log.info("Filled %d null coords_swapped with False", n_null_swapped)

    # --- exclude_from_training: flag BEFORE imputing coordinates ---
    df["exclude_from_training"] = df["Latitude"].isnull()
    n_exclude = df["exclude_from_training"].sum()
    log.info("Flagged %d outlets for exclude_from_training", n_exclude)

    # --- Coordinates: fill with province centroid ---
    n_null_coords = df["Latitude"].isnull().sum()
    for province, (lat, lon) in PROVINCE_CENTROIDS.items():
        mask = df["Latitude"].isnull() & (df["province"] == province)
        df.loc[mask, "Latitude"] = lat
        df.loc[mask, "Longitude"] = lon
    remaining_null = df["Latitude"].isnull().sum()
    if remaining_null > 0:
        # Fallback: fill any remaining nulls (no province) with overall centroid
        df["Latitude"] = df["Latitude"].fillna(7.0)
        df["Longitude"] = df["Longitude"].fillna(80.0)
        log.warning("Filled %d remaining null coords with fallback centroid", remaining_null)
    log.warning("Filled %d null coordinates with province centroids", n_null_coords)

    # --- POI features: leave as-is (already 0 for unavailable outlets) ---

    # --- Numeric sales features: fill nulls with 0 for fully inactive outlets ---
    numeric_sales_cols = [
        "hist_max_monthly", "hist_p90_monthly", "hist_p75_monthly",
        "hist_mean_monthly", "hist_std_monthly", "hist_cv",
        "jan_avg_volume", "jan_max_volume", "jan_count",
        "active_months", "active_months_pct",
        "consecutive_zero_months_max", "recent_3m_avg",
        "months_since_last_order", "total_volume",
        "ema_3m", "ema_6m",
    ]
    for col in numeric_sales_cols:
        if col in df.columns:
            n_null = df[col].isnull().sum()
            if n_null > 0:
                df[col] = df[col].fillna(0)
                log.info("Filled %d nulls in %s with 0", n_null, col)

    # --- has_transaction_history: derive from active_months ---
    df["has_transaction_history"] = df["active_months"].fillna(0).gt(0)
    n_no_history = (~df["has_transaction_history"]).sum()
    log.info("%d outlets have no transaction history", n_no_history)

    # --- trend_slope, yoy_growth_rate: fill with median ---
    for col in ["trend_slope", "yoy_growth_rate"]:
        if col in df.columns:
            median_val = df[col].median()
            null_count = df[col].isnull().sum()
            if null_count > 0:
                df[col] = df[col].fillna(median_val)
                log.info("Filled %d nulls in %s with median %.4f",
                         null_count, col, median_val)

    # --- seasonality_multiplier_jan_2026: fill null with 1.00 (Moderate) ---
    n_null_season = df["seasonality_multiplier_jan_2026"].isnull().sum()
    df["seasonality_multiplier_jan_2026"] = (
        df["seasonality_multiplier_jan_2026"].fillna(1.00)
    )
    if n_null_season > 0:
        log.info("Filled %d null seasonality_multiplier with 1.00 (Moderate)",
                 n_null_season)

    # --- seasonality_jan_2026: fill null with "Moderate" ---
    n_null_season_str = df["seasonality_jan_2026"].isnull().sum()
    df["seasonality_jan_2026"] = df["seasonality_jan_2026"].fillna("Moderate")
    if n_null_season_str > 0:
        log.info("Filled %d null seasonality_jan_2026 with 'Moderate'",
                 n_null_season_str)

    return df


def round_floats(df: pd.DataFrame, decimals: int = 4) -> pd.DataFrame:
    """Step 8 — Round all float columns to reduce spurious precision."""
    float_cols = df.select_dtypes(include=["float32", "float64"]).columns.tolist()
    # Upcast float32 → float64 so that rounding to 4 dp is exact
    # (float32 has only ~7 significant digits, causing trailing noise)
    for col in float_cols:
        if df[col].dtype == "float32":
            df[col] = df[col].astype("float64")
    df[float_cols] = df[float_cols].round(decimals)
    log.info("Rounded %d float columns to %d decimal places (all float64)",
             len(float_cols), decimals)
    return df


def run_assertions(df: pd.DataFrame) -> None:
    """Validate the output DataFrame before writing."""
    assert len(df) == 20000, f"Expected 20000 rows, got {len(df)}"
    assert df["Outlet_ID"].duplicated().sum() == 0, "Duplicate Outlet_IDs found"
    assert df["Outlet_ID"].isnull().sum() == 0, "Null Outlet_IDs found"
    assert df["Latitude"].isnull().sum() == 0, "Null latitudes after centroid fill"
    assert df["Longitude"].isnull().sum() == 0, "Null longitudes after centroid fill"
    assert df["coords_swapped"].isnull().sum() == 0, "Null coords_swapped after fill"
    assert df["seasonality_multiplier_jan_2026"].isnull().sum() == 0, \
        "Null seasonality_multiplier after fill"
    assert df["hist_p90_monthly"].isnull().sum() == 0, "Null hist_p90_monthly"
    assert df["has_transaction_history"].dtype == bool, \
        f"has_transaction_history is {df['has_transaction_history'].dtype}, expected bool"
    assert df["exclude_from_training"].dtype == bool, \
        f"exclude_from_training is {df['exclude_from_training'].dtype}, expected bool"
    assert "jan_2026_trading_days" in df.columns, "jan_2026_trading_days column missing"
    assert df["jan_2026_trading_days"].iloc[0] > 0, "jan_2026_trading_days must be > 0"
    log.info("All assertions passed.")


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def main():
    start_time = time.time()
    log.info("=" * 70)
    log.info("BUILD MASTER FEATURES — START")
    log.info("=" * 70)

    # Step 1 — Load all inputs
    inputs = load_inputs()

    # Step 3 — Build January 2026 seasonality lookup
    jan_2026_season = build_seasonality_lookup(inputs["season"])

    # Step 4 — Merge all datasets
    df = merge_all_datasets(
        outlets=inputs["outlets"],
        coords=inputs["coords"],
        sales_ft=inputs["sales_ft"],
        poi_ft=inputs["poi_ft"],
        grav_ft=inputs["grav_ft"],
        catch_ft=inputs["catch_ft"],
        jan_2026_season=jan_2026_season,
    )

    # Step 5 — Add scalar features
    df = add_scalar_features(
        df,
        jan_2026_trading_days=inputs["jan_2026_trading_days"],
        jan_2026_holiday_count=inputs["jan_2026_holiday_count"],
    )

    # Step 6 — Derive province column
    df = derive_province(df)

    # Step 7 — Handle nulls from left joins
    df = handle_nulls(df)

    # Step 8 — Round floating-point columns
    df = round_floats(df, decimals=4)

    # Step 9 — Assertions and write output
    run_assertions(df)

    os.makedirs(GOLD_DIR, exist_ok=True)
    output_path = os.path.join(GOLD_DIR, "master_features.parquet")
    df.to_parquet(output_path, index=False, engine="pyarrow", compression="snappy")

    duration = time.time() - start_time
    log.info("Written %d rows, %d columns -> master_features.parquet (%.1fs)",
             len(df), len(df.columns), duration)
    log.info("Columns: %s", list(df.columns))
    log.info("=" * 70)
    log.info("BUILD MASTER FEATURES — DONE")
    log.info("=" * 70)


if __name__ == "__main__":
    main()
