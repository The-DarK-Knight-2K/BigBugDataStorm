"""
Build physics-based cooler capacity ceiling features.

Models the theoretical monthly throughput based on cooler volume ×
replenishment frequency, then derives a capacity utilisation ratio
comparing historical sales to this physical ceiling.

Layer  : Gold
Inputs : Data/Silver/outlet_master_clean.parquet,
         Data/Gold/sales_features.parquet
Outputs: Data/Gold/cooler_features.parquet
"""

import time
from pathlib import Path

import numpy as np
import pandas as pd
import yaml

from pipeline.utils.logger import setup_logger

# ---------------------------------------------------------------------------
# Paths & Config
# ---------------------------------------------------------------------------
PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent
CONFIG_PATH = PROJECT_ROOT / "config.yaml"
SILVER_DIR = PROJECT_ROOT / "Data" / "Silver"
GOLD_DIR = PROJECT_ROOT / "Data" / "Gold"

with open(CONFIG_PATH) as f:
    CFG = yaml.safe_load(f)

log = setup_logger("build_cooler_features")

# Cooler constraint parameters from config
COOLER_CFG = CFG["cooler_constraints"]
LITRES_PER_COOLER = COOLER_CFG["litres_per_cooler"]          # 150 L
REPLENISHMENT_DAYS = COOLER_CFG["replenishment_cycle_days"]   # 3 days
FILLS_PER_CYCLE = COOLER_CFG["fills_per_cycle"]               # 0.85


# ---------------------------------------------------------------------------
# Core computation
# ---------------------------------------------------------------------------
def compute_cooler_features(
    outlets_df: pd.DataFrame,
    sales_df: pd.DataFrame,
) -> pd.DataFrame:
    """
    Compute physics-based cooler capacity ceiling features.

    Theoretical Monthly Ceiling = (Cooler_Count × litres_per_cooler
                                    × fills_per_cycle × 30)
                                  / replenishment_cycle_days

    capacity_utilization_ratio = hist_p90_monthly / ceiling
    """
    df = outlets_df[["Outlet_ID", "Cooler_Count"]].copy()

    # Merge historical P90 from sales features
    if "hist_p90_monthly" in sales_df.columns:
        df = df.merge(
            sales_df[["Outlet_ID", "hist_p90_monthly"]],
            on="Outlet_ID",
            how="left",
        )
        df["hist_p90_monthly"] = df["hist_p90_monthly"].fillna(0.0)
    else:
        df["hist_p90_monthly"] = 0.0

    # --- Cooler capacity (litres) ---
    df["cooler_capacity_litres"] = df["Cooler_Count"] * LITRES_PER_COOLER

    # --- Theoretical monthly ceiling ---
    # How many litres can pass through all coolers in a 30-day month
    df["theoretical_monthly_ceiling"] = (
        df["cooler_capacity_litres"]
        * FILLS_PER_CYCLE
        * (30.0 / REPLENISHMENT_DAYS)
    )

    # --- Capacity utilisation ratio ---
    # How much of the physical ceiling is actually used
    # Clip ceiling at 1 to avoid div-by-zero for 0-cooler outlets
    df["capacity_utilization_ratio"] = (
        df["hist_p90_monthly"]
        / df["theoretical_monthly_ceiling"].clip(lower=1.0)
    ).clip(upper=2.0)  # Cap at 200% to limit extreme values

    # For outlets with 0 coolers, set a special flag and ratio = 0
    zero_cooler_mask = df["Cooler_Count"] == 0
    df.loc[zero_cooler_mask, "capacity_utilization_ratio"] = 0.0

    log.info(
        "Cooler feature stats — "
        "ceiling: mean=%.1f, max=%.1f | "
        "utilization: mean=%.3f, max=%.3f",
        df["theoretical_monthly_ceiling"].mean(),
        df["theoretical_monthly_ceiling"].max(),
        df["capacity_utilization_ratio"].mean(),
        df["capacity_utilization_ratio"].max(),
    )

    # Drop the intermediate column
    df = df.drop(columns=["hist_p90_monthly"])

    return df


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------
def main() -> None:
    start = time.time()
    log.info("=" * 60)
    log.info("BUILD COOLER FEATURES  (OPT-3 — Phase 2.5)")
    log.info("=" * 60)
    log.info(
        "Config — litres/cooler=%d, replenishment=%dd, fill_rate=%.0f%%",
        LITRES_PER_COOLER, REPLENISHMENT_DAYS, FILLS_PER_CYCLE * 100,
    )

    # --- Load inputs ---
    outlets_df = pd.read_parquet(SILVER_DIR / "outlet_master_clean.parquet")
    log.info("Loaded %d outlets from Silver.", len(outlets_df))

    sales_df = pd.read_parquet(GOLD_DIR / "sales_features.parquet")
    log.info("Loaded %d rows from sales_features.", len(sales_df))

    # --- Compute features ---
    cooler_df = compute_cooler_features(outlets_df, sales_df)
    log.info("Computed cooler features for %d outlets.", len(cooler_df))

    # --- Cast types ---
    cooler_df["cooler_capacity_litres"] = cooler_df["cooler_capacity_litres"].astype("float32")
    cooler_df["theoretical_monthly_ceiling"] = cooler_df["theoretical_monthly_ceiling"].astype("float32")
    cooler_df["capacity_utilization_ratio"] = cooler_df["capacity_utilization_ratio"].astype("float32")

    # --- Order columns ---
    final_columns = [
        "Outlet_ID",
        "Cooler_Count",
        "cooler_capacity_litres",
        "theoretical_monthly_ceiling",
        "capacity_utilization_ratio",
    ]
    cooler_df = cooler_df[final_columns]

    # --- Assertions ---
    log.info("Running data contract assertions...")
    assert len(cooler_df) == 20000, f"Expected 20000 rows, got {len(cooler_df)}"
    assert cooler_df["Outlet_ID"].duplicated().sum() == 0, "Duplicate Outlet_IDs"
    assert cooler_df["Outlet_ID"].isnull().sum() == 0, "Null Outlet_IDs"
    assert cooler_df.isnull().sum().sum() == 0, "NaN values found"
    assert (cooler_df["cooler_capacity_litres"] >= 0).all(), "Negative capacity"
    assert (cooler_df["theoretical_monthly_ceiling"] >= 0).all(), "Negative ceiling"
    assert (cooler_df["capacity_utilization_ratio"] >= 0).all(), "Negative utilization"
    assert (cooler_df["capacity_utilization_ratio"] <= 2.0).all(), "Utilization > 200%"
    log.info("All assertions passed.")

    # --- Write output ---
    output_path = GOLD_DIR / "cooler_features.parquet"
    cooler_df.to_parquet(output_path, index=False, engine="pyarrow", compression="snappy")

    duration = time.time() - start
    log.info(
        "Written %d rows x %d columns -> %s (%.1fs)",
        len(cooler_df), len(cooler_df.columns), output_path.name, duration,
    )

    # --- Summary stats ---
    log.info("--- Summary ---")
    for col in ["cooler_capacity_litres", "theoretical_monthly_ceiling", "capacity_utilization_ratio"]:
        log.info(
            "  %-35s  mean=%.2f  median=%.2f  max=%.2f",
            col, cooler_df[col].mean(), cooler_df[col].median(), cooler_df[col].max(),
        )


if __name__ == "__main__":
    main()
