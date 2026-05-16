"""
Compute a January-anchored baseline estimate of maximum monthly purchase
potential for every outlet. Used as a floor — the ML model prediction is
never allowed to go below this value.

Layer  : Modelling
Inputs : master_features.parquet
Outputs: baseline_predictions.parquet
"""

import os
import sys
import time

import numpy as np
import pandas as pd

# ---------------------------------------------------------------------------
# Path setup (matches existing pipeline scripts)
# ---------------------------------------------------------------------------
CURRENT_DIR = os.path.dirname(os.path.abspath(__file__))
ROOT_DIR = os.path.dirname(CURRENT_DIR)

# Add pipeline dir to path so we can import the shared logger
PIPELINE_DIR = os.path.join(ROOT_DIR, "pipeline")
if PIPELINE_DIR not in sys.path:
    sys.path.insert(0, PIPELINE_DIR)

from utils.logger import setup_logger

log = setup_logger("baseline")

GOLD_DIR = os.path.join(ROOT_DIR, "Data", "Gold")

AVG_TRADING_DAYS_PER_MONTH = 22.0  # standard assumption for a working month


# ---------------------------------------------------------------------------
# Helper functions
# ---------------------------------------------------------------------------

def compute_size_medians(df: pd.DataFrame) -> tuple[dict, float]:
    """
    Compute the median jan_avg_volume per Outlet_Size from outlets that
    actually have January history (jan_count > 0). Returns a dict of
    size -> median and a global median fallback.
    """
    has_jan = df[df["jan_count"] > 0]
    size_medians = has_jan.groupby("Outlet_Size")["jan_avg_volume"].median().to_dict()
    global_median = has_jan["jan_avg_volume"].median() if len(has_jan) > 0 else 50.0
    return size_medians, global_median


def _estimate_cold_start_potential(
    row: pd.Series,
    size_medians: dict,
    global_median: float,
) -> float:
    """
    For outlets with no transaction history, estimate demand using the median
    January volume of outlets with the same Outlet_Size. A Cooler_Count
    multiplier is applied as a capacity proxy.
    """
    base = size_medians.get(row["Outlet_Size"], global_median)
    cooler_multiplier = 1.0 + (row["Cooler_Count"] * 0.15)
    return base * cooler_multiplier


def _compute_recency_factor(row: pd.Series) -> float:
    """
    Compare the 3-month EMA to the historical mean to detect momentum.

    - ema_3m 30% above hist_mean → factor = 1.3 (growing)
    - ema_3m equals hist_mean    → factor = 1.0 (stable)
    - ema_3m 20% below hist_mean → factor = 0.8 (declining, clamped)

    Returns 1.0 for outlets with no meaningful history.
    """
    hist_mean = row["hist_mean_monthly"]
    ema = row["ema_3m"]

    if hist_mean <= 0 or ema <= 0:
        return 1.0

    ratio = ema / hist_mean
    # Clamp between 0.8 and 1.3 to prevent extreme swings
    return max(0.8, min(ratio, 1.3))


def _compute_poi_uplift(footfall_score: float) -> float:
    """
    Footfall score is 0-100.
    Low footfall  (0-20)   -> no uplift (1.00)
    Medium        (20-60)  -> small uplift up to 1.10
    High          (60-100) -> uplift up to 1.25

    Rationale: an outlet in a high-traffic area (near a bus terminal + school)
    has more potential customers than its historical sales suggest — especially
    if it has been supply-constrained in the past.
    """
    if footfall_score <= 20:
        return 1.00
    elif footfall_score <= 60:
        return 1.00 + ((footfall_score - 20) / 40) * 0.10
    else:
        return 1.10 + ((footfall_score - 60) / 40) * 0.15


def compute_baseline(
    row: pd.Series,
    size_medians: dict,
    global_median: float,
) -> float:
    """
    Baseline = jan_demand x recency_factor x seasonality x trading_ratio x POI uplift

    The primary signal is January-specific history, NOT the all-months P90
    used by train.py. This ensures genuine independence between the baseline
    floor and the model prediction.
    """
    # --- (A) January-Anchored Demand ---
    if row["jan_count"] > 0:
        # Take the higher of: January average, or 85% of January max
        # (the 0.85 dampening avoids anchoring on a one-off spike)
        jan_demand = max(row["jan_avg_volume"],
                         row["jan_max_volume"] * 0.85)
    elif row["has_transaction_history"]:
        # Outlet has history but never ordered in January — fall back to P90
        jan_demand = row["hist_p90_monthly"]
    else:
        # No history at all — use data-driven cold-start
        jan_demand = _estimate_cold_start_potential(row, size_medians, global_median)

    # --- (B) Recency-Weighted Momentum Adjustment ---
    recency_factor = _compute_recency_factor(row)

    # Seasonality adjustment
    season_mult = row["seasonality_multiplier_jan_2026"]  # 0.85 / 1.00 / 1.20

    # Trading-day adjustment
    trading_ratio = row["jan_2026_trading_days"] / AVG_TRADING_DAYS_PER_MONTH

    # POI uplift
    poi_uplift = _compute_poi_uplift(row["footfall_score"])

    baseline = jan_demand * recency_factor * season_mult * trading_ratio * poi_uplift

    # Floor: potential cannot be less than the outlet's all-time maximum
    # (avoids regressing below observed reality)
    baseline = max(baseline, row["hist_max_monthly"])

    return round(float(baseline), 2)


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def main() -> pd.DataFrame:
    start_time = time.time()
    log.info("=" * 70)
    log.info("BASELINE ESTIMATION — START")
    log.info("=" * 70)

    # Step 1 — Load master features
    input_path = os.path.join(GOLD_DIR, "master_features.parquet")
    df = pd.read_parquet(input_path)
    log.info("Loaded %d rows from master_features.parquet", len(df))

    # Step 1b — Compute data-driven cold-start lookup
    size_medians, global_median = compute_size_medians(df)
    log.info("Data-driven cold-start medians by size: %s", size_medians)
    log.info("Global median fallback: %.2f", global_median)

    # Step 2 — Apply baseline computation
    df["baseline_potential_litres"] = df.apply(
        compute_baseline, axis=1,
        size_medians=size_medians,
        global_median=global_median,
    )

    # Step 3 — Log statistics
    log.info("Baseline statistics:")
    log.info("  Min    : %.2f", df["baseline_potential_litres"].min())
    log.info("  Median : %.2f", df["baseline_potential_litres"].median())
    log.info("  Mean   : %.2f", df["baseline_potential_litres"].mean())
    log.info("  P90    : %.2f", df["baseline_potential_litres"].quantile(0.90))
    log.info("  Max    : %.2f", df["baseline_potential_litres"].max())

    # Log estimation path counts
    jan_path = (df["jan_count"] > 0) & df["has_transaction_history"]
    p90_path = (df["jan_count"] == 0) & df["has_transaction_history"]
    cold_path = ~df["has_transaction_history"]
    log.info("Estimation paths — January-anchored: %d, P90 fallback: %d, Cold-start: %d",
             jan_path.sum(), p90_path.sum(), cold_path.sum())

    # Step 4 — Assertions
    baseline_df = df[["Outlet_ID", "baseline_potential_litres"]].copy()

    assert len(baseline_df) == 20000, \
        f"Expected 20000 rows, got {len(baseline_df)}"
    assert baseline_df["baseline_potential_litres"].isnull().sum() == 0, \
        "Null baseline predictions found"
    assert (baseline_df["baseline_potential_litres"] > 0).all(), \
        "All baseline predictions must be positive"
    assert baseline_df["Outlet_ID"].duplicated().sum() == 0, \
        "Duplicate Outlet_IDs found"
    log.info("All assertions passed.")

    # Step 5 — Save
    os.makedirs(GOLD_DIR, exist_ok=True)
    output_path = os.path.join(GOLD_DIR, "baseline_predictions.parquet")
    baseline_df.to_parquet(output_path, index=False,
                           engine="pyarrow", compression="snappy")

    duration = time.time() - start_time
    log.info("Saved %d rows -> baseline_predictions.parquet (%.1fs)", len(baseline_df), duration)
    log.info("=" * 70)
    log.info("BASELINE ESTIMATION — DONE")
    log.info("=" * 70)

    return baseline_df


if __name__ == "__main__":
    main()
