"""
Compute statistically grounded baseline demand potential for every outlet.

Layer  : Modelling
Inputs : data/gold/master_features.parquet
Outputs: data/gold/baseline_predictions.parquet
"""

import logging
import sys
from pathlib import Path

import pandas as pd
import yaml

# ---------------------------------------------------------------------------
# Config
# ---------------------------------------------------------------------------
CONFIG_PATH = Path(__file__).resolve().parents[2] / "config.yaml"
with open(CONFIG_PATH) as f:
    CFG = yaml.safe_load(f)

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s | %(levelname)-8s | %(name)s | %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
)
log = logging.getLogger(Path(__file__).stem)

ROOT = Path(__file__).resolve().parents[2]
GOLD = ROOT / CFG.get("paths", {}).get("gold", Path("data") / "gold")
MASTER_FEATURES_PATH = GOLD / "master_features.parquet"
BASELINE_OUTPUT_PATH = GOLD / "baseline_predictions.parquet"
AVG_TRADING_DAYS_PER_MONTH = 22.0
SIZE_BASE = {
    "Small": 50.0,
    "Medium": 120.0,
    "Large": 250.0,
    "Extra Large": 450.0,
}


def load_master_features() -> pd.DataFrame:
    if not MASTER_FEATURES_PATH.exists():
        log.error("Cannot proceed: missing master_features file: %s", MASTER_FEATURES_PATH)
        sys.exit(1)

    df = pd.read_parquet(MASTER_FEATURES_PATH)
    log.info("Loaded %d rows from master_features", len(df))
    return df


def _estimate_cold_start_potential(row: pd.Series) -> float:
    outlet_size = row.get("Outlet_Size")
    cooler_count = row.get("Cooler_Count")

    if pd.isna(outlet_size):
        outlet_size = None
    if pd.isna(cooler_count):
        cooler_count = 0.0

    base = SIZE_BASE.get(outlet_size, 80.0)
    try:
        cooler_multiplier = 1.0 + (float(cooler_count) * 0.15)
    except (TypeError, ValueError):
        cooler_multiplier = 1.0
        log.warning("Missing or invalid Cooler_Count for Outlet_ID=%s, using 0", row.get("Outlet_ID"))

    return base * cooler_multiplier


def _compute_poi_uplift(footfall_score: float) -> float:
    if pd.isna(footfall_score):
        footfall_score = 0.0

    score = float(footfall_score)
    if score <= 20.0:
        return 1.00
    if score <= 60.0:
        return 1.00 + ((score - 20.0) / 40.0) * 0.10
    return 1.10 + ((score - 60.0) / 40.0) * 0.15


def compute_baseline(row: pd.Series) -> float:
    p90 = row.get("hist_p90_monthly", 0.0)
    if pd.isna(p90):
        p90 = 0.0

    if p90 == 0 or not row.get("has_transaction_history", False):
        p90 = _estimate_cold_start_potential(row)

    season_mult = row.get("seasonality_multiplier_jan_2026", 1.0)
    if pd.isna(season_mult):
        season_mult = 1.0
        log.warning("Missing seasonality_multiplier_jan_2026 for Outlet_ID=%s, using 1.0", row.get("Outlet_ID"))

    trading_days = row.get("jan_2026_trading_days", AVG_TRADING_DAYS_PER_MONTH)
    if pd.isna(trading_days):
        trading_days = AVG_TRADING_DAYS_PER_MONTH
        log.warning("Missing jan_2026_trading_days for Outlet_ID=%s, using %s", row.get("Outlet_ID"), AVG_TRADING_DAYS_PER_MONTH)

    trading_ratio = float(trading_days) / AVG_TRADING_DAYS_PER_MONTH
    poi_uplift = _compute_poi_uplift(row.get("footfall_score", 0.0))

    baseline = p90 * float(season_mult) * trading_ratio * poi_uplift

    hist_max = row.get("hist_max_monthly")
    if pd.notna(hist_max):
        baseline = max(baseline, float(hist_max))

    return round(float(baseline), 2)


def save_baseline_predictions(baseline_df: pd.DataFrame) -> None:
    BASELINE_OUTPUT_PATH.parent.mkdir(parents=True, exist_ok=True)
    baseline_df.to_parquet(
        BASELINE_OUTPUT_PATH,
        index=False,
        engine="pyarrow",
        compression="snappy",
    )
    log.info("Saved baseline predictions → %s", BASELINE_OUTPUT_PATH)


def validate_baseline(baseline_df: pd.DataFrame) -> None:
    try:
        assert len(baseline_df) == 20000
        assert baseline_df["baseline_potential_litres"].isnull().sum() == 0
        assert (baseline_df["baseline_potential_litres"] > 0).all(), \
            "All baseline predictions must be positive"
        assert baseline_df["Outlet_ID"].duplicated().sum() == 0
    except AssertionError as exc:
        log.error("Baseline validation failed: %s", exc)
        sys.exit(1)

    log.info("Baseline validation passed")


def main() -> pd.DataFrame:
    log.info("Starting baseline computation")
    df = load_master_features()
    log.info("Computing baseline values for %d outlets", len(df))
    df["baseline_potential_litres"] = df.apply(compute_baseline, axis=1)

    log.info("Baseline statistics:")
    log.info("  Min    : %.2f", df["baseline_potential_litres"].min())
    log.info("  Median : %.2f", df["baseline_potential_litres"].median())
    log.info("  Mean   : %.2f", df["baseline_potential_litres"].mean())
    log.info("  P90    : %.2f", df["baseline_potential_litres"].quantile(0.90))
    log.info("  Max    : %.2f", df["baseline_potential_litres"].max())

    baseline_df = df[["Outlet_ID", "baseline_potential_litres"]].copy()
    save_baseline_predictions(baseline_df)
    validate_baseline(baseline_df)
    log.info("Baseline computation complete")
    return baseline_df


if __name__ == "__main__":
    main()
