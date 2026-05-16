import pandas as pd
import numpy as np
import os
import sys
import time
from scipy.stats import linregress

# Path setup
CURRENT_DIR = os.path.dirname(os.path.abspath(__file__))
PIPELINE_DIR = os.path.dirname(CURRENT_DIR)
ROOT_DIR = os.path.dirname(PIPELINE_DIR)

if PIPELINE_DIR not in sys.path:
    sys.path.insert(0, PIPELINE_DIR)

from utils.logger import setup_logger

log = setup_logger("build_sales_features")

SILVER_DIR = os.path.join(ROOT_DIR, "Data", "Silver")
GOLD_DIR = os.path.join(ROOT_DIR, "Data", "Gold")


# ---------------------------------------------------------------------------
# Helper functions (unchanged logic)
# ---------------------------------------------------------------------------

def max_consecutive_zeros(monthly_volumes: pd.Series) -> int:
    """Longest run of zero-volume months in the series."""
    max_run = 0
    current_run = 0
    for v in monthly_volumes:
        if v == 0:
            current_run += 1
            max_run = max(max_run, current_run)
        else:
            current_run = 0
    return max_run


def compute_trend_slope(monthly_volumes: pd.Series):
    """Linear regression slope over the monthly volume series. None if <6 pts."""
    if len(monthly_volumes) < 6:
        return None
    x = np.arange(len(monthly_volumes))
    slope, _, _, _, _ = linregress(x, monthly_volumes.values)
    return float(slope)


def compute_yoy_growth(group_df: pd.DataFrame):
    """Year-over-year growth rate from first to last year average. None if <2 years."""
    avg_by_year = group_df.groupby("Year")["monthly_volume"].mean()
    years = sorted(avg_by_year.index)
    if len(years) < 2:
        return None
    first_year_avg = avg_by_year[years[0]]
    last_year_avg = avg_by_year[years[-1]]
    if first_year_avg == 0:
        return None
    return float((last_year_avg - first_year_avg) / first_year_avg)


def compute_ema(monthly_volumes: pd.Series, span: int) -> float:
    """Exponential moving average with given span. Returns 0.0 if series is empty."""
    if len(monthly_volumes) == 0:
        return 0.0
    return float(monthly_volumes.ewm(span=span, adjust=False).mean().iloc[-1])


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def main():
    start_time = time.time()

    # ── Step 1: Load inputs ──────────────────────────────────────────────
    txn = pd.read_parquet(os.path.join(SILVER_DIR, "transactions_clean.parquet"))
    outlets = pd.read_parquet(os.path.join(SILVER_DIR, "outlet_master_clean.parquet"))[["Outlet_ID"]]
    log.info("Loaded %d transaction rows for %d unique outlets", len(txn), txn["Outlet_ID"].nunique())

    # ── Step 2: Build monthly aggregation ────────────────────────────────
    # Exclude blackout-period rows from volume calcs (but keep in timeline)
    txn_valid = txn[~txn["is_blackout_period"]].copy()

    monthly = (
        txn_valid
        .groupby(["Outlet_ID", "Year", "Month"], as_index=False)
        .agg(
            monthly_volume=("Volume_Litres", "sum"),
            transaction_count=("Volume_Litres", "count"),
        )
    )

    # ── Step 3: Compute the full time range ──────────────────────────────
    data_start = pd.Period(f"{int(txn['Year'].min())}-{int(txn['Month'].min()):02d}", freq="M")
    data_end = pd.Period(f"{int(txn['Year'].max())}-{int(txn['Month'].max()):02d}", freq="M")
    total_months_in_data = (data_end - data_start).n + 1
    log.info("Data spans %d months (%s to %s)", total_months_in_data, data_start, data_end)

    all_periods = pd.period_range(data_start, data_end, freq="M")

    # ── Step 4: Build the complete outlet × period grid (VECTORIZED) ─────
    # Instead of reindexing per outlet in a loop, build one massive grid
    outlet_ids = monthly["Outlet_ID"].unique()
    log.info("Building complete grid for %d outlets × %d months...", len(outlet_ids), len(all_periods))

    grid = pd.MultiIndex.from_product([outlet_ids, all_periods], names=["Outlet_ID", "period"])
    full = grid.to_frame(index=False)
    full["Year"] = full["period"].dt.year
    full["Month"] = full["period"].dt.month

    # Attach a period column to monthly for merging
    monthly["period"] = pd.PeriodIndex(
        monthly["Year"].astype(str) + "-" + monthly["Month"].astype(str).str.zfill(2), freq="M"
    )

    # Merge actual data onto grid — missing months become 0
    full = full.merge(
        monthly[["Outlet_ID", "period", "monthly_volume"]],
        on=["Outlet_ID", "period"],
        how="left"
    )
    full["monthly_volume"] = full["monthly_volume"].fillna(0.0).astype(float)

    log.info("Grid built: %d rows. Computing features...", len(full))

    # ── Step 4a: Vectorized basic stats via groupby().agg() ──────────────
    grouped = full.groupby("Outlet_ID")["monthly_volume"]

    stats = grouped.agg(
        hist_max_monthly="max",
        hist_mean_monthly="mean",
        hist_std_monthly="std",
        total_volume="sum",
    ).reset_index()

    # Quantiles need separate calls
    stats["hist_p90_monthly"] = grouped.quantile(0.90).values
    stats["hist_p75_monthly"] = grouped.quantile(0.75).values

    # Fill NaN std (outlets with only 1 month of data)
    stats["hist_std_monthly"] = stats["hist_std_monthly"].fillna(0.0)

    # Coefficient of variation
    stats["hist_cv"] = np.where(
        stats["hist_mean_monthly"] > 0,
        stats["hist_std_monthly"] / stats["hist_mean_monthly"],
        0.0
    )

    # Active months
    stats["active_months"] = grouped.apply(lambda x: int((x > 0).sum())).values
    stats["active_months_pct"] = stats["active_months"] / total_months_in_data

    log.info("Basic stats computed.")

    # ── Step 4b: January features via filtered groupby ───────────────────
    jan = full[full["Month"] == 1]
    jan_grouped = jan.groupby("Outlet_ID")["monthly_volume"]

    jan_stats = jan_grouped.agg(
        jan_avg_volume="mean",
        jan_max_volume="max",
    ).reset_index()

    jan_stats["jan_count"] = jan_grouped.apply(lambda x: int((x > 0).sum())).values

    log.info("January features computed.")

    # ── Step 4c: Sequential features via groupby().apply() ───────────────
    # These genuinely need per-group sequential logic
    def compute_sequential(group):
        vol = group["monthly_volume"]

        # Consecutive zero months
        czm = max_consecutive_zeros(vol)

        # Months since last order
        non_zero_mask = vol > 0
        if non_zero_mask.any():
            last_active_pos = non_zero_mask.values[::-1].argmax()
            months_since = last_active_pos
        else:
            months_since = total_months_in_data

        # Recent 3-month average
        recent_3m = float(vol.iloc[-3:].mean()) if len(vol) >= 3 else float(vol.mean())

        # Trend slope
        slope = compute_trend_slope(vol)

        # YoY growth
        yoy = compute_yoy_growth(group)

        # EMA
        ema_3 = compute_ema(vol, span=3)
        ema_6 = compute_ema(vol, span=6)

        return pd.Series({
            "consecutive_zero_months_max": czm,
            "months_since_last_order": months_since,
            "recent_3m_avg": recent_3m,
            "trend_slope": slope,
            "yoy_growth_rate": yoy,
            "ema_3m": ema_3,
            "ema_6m": ema_6,
        })

    seq = full.groupby("Outlet_ID").apply(compute_sequential).reset_index()

    log.info("Sequential features computed.")

    # ── Step 4d: Distributor assignment via groupby ───────────────────────
    dist = (
        txn.groupby("Outlet_ID")["Distributor_ID"]
        .agg(lambda x: x.value_counts().idxmax())
        .reset_index()
        .rename(columns={"Distributor_ID": "distributor_id"})
    )

    # Global mode distributor for imputation of outlets with no transactions
    global_mode_dist = txn["Distributor_ID"].value_counts().idxmax()

    log.info("Distributor assignments computed.")

    # ── Step 4e: Merge all feature groups ────────────────────────────────
    computed = (
        stats
        .merge(jan_stats, on="Outlet_ID", how="left")
        .merge(seq, on="Outlet_ID", how="left")
        .merge(dist, on="Outlet_ID", how="left")
    )

    # Fill jan stats for outlets that had no January data
    computed["jan_avg_volume"] = computed["jan_avg_volume"].fillna(0.0)
    computed["jan_max_volume"] = computed["jan_max_volume"].fillna(0.0)
    computed["jan_count"] = computed["jan_count"].fillna(0)

    log.info("Merged all feature groups: %d outlets with transaction history.", len(computed))

    # ── Step 5: Handle outlets with no transactions ──────────────────────
    features_df = outlets.merge(computed, on="Outlet_ID", how="left")

    no_history_count = features_df["hist_max_monthly"].isnull().sum()
    log.info("Outlets with no transaction history: %d", no_history_count)

    # Fill numeric NaNs with 0 for inactive outlets
    numeric_cols = [
        "hist_max_monthly", "hist_p90_monthly", "hist_p75_monthly",
        "hist_mean_monthly", "hist_std_monthly", "hist_cv",
        "jan_avg_volume", "jan_max_volume", "jan_count",
        "active_months", "active_months_pct",
        "consecutive_zero_months_max", "recent_3m_avg",
        "months_since_last_order", "total_volume",
        "ema_3m", "ema_6m",
    ]
    for col in numeric_cols:
        features_df[col] = features_df[col].fillna(0)

    # For outlets with no history, set months_since_last_order to total_months_in_data
    features_df.loc[features_df["active_months"] == 0, "months_since_last_order"] = total_months_in_data

    # Fill missing distributor with global mode
    features_df["distributor_id"] = features_df["distributor_id"].fillna(global_mode_dist)

    # yoy_growth_rate and trend_slope remain NaN where not computable (contract allows null)

    # ── Cast types ───────────────────────────────────────────────────────
    float32_cols = [
        "hist_max_monthly", "hist_p90_monthly", "hist_p75_monthly",
        "hist_mean_monthly", "hist_std_monthly", "hist_cv",
        "jan_avg_volume", "jan_max_volume",
        "active_months_pct", "recent_3m_avg", "total_volume",
        "ema_3m", "ema_6m",
    ]
    for col in float32_cols:
        features_df[col] = features_df[col].astype("float32")

    # Nullable float32 columns
    features_df["yoy_growth_rate"] = features_df["yoy_growth_rate"].astype("float32") if features_df["yoy_growth_rate"].notna().any() else features_df["yoy_growth_rate"]
    features_df["trend_slope"] = features_df["trend_slope"].astype("float32") if features_df["trend_slope"].notna().any() else features_df["trend_slope"]

    features_df["jan_count"] = features_df["jan_count"].astype("int8")
    features_df["active_months"] = features_df["active_months"].astype("int16")
    features_df["consecutive_zero_months_max"] = features_df["consecutive_zero_months_max"].astype("int8")
    features_df["months_since_last_order"] = features_df["months_since_last_order"].astype("int16")

    # ── Assertions ───────────────────────────────────────────────────────
    assert len(features_df) == 20000, f"Expected 20000 rows, got {len(features_df)}"
    assert features_df["Outlet_ID"].duplicated().sum() == 0
    assert features_df["Outlet_ID"].isnull().sum() == 0
    assert features_df["hist_p90_monthly"].isnull().sum() == 0
    assert (features_df["hist_p90_monthly"] >= 0).all()
    assert (features_df["active_months_pct"].between(0, 1)).all()

    # ── Step 6: Write output ─────────────────────────────────────────────
    output_cols = [
        "Outlet_ID",
        "hist_max_monthly", "hist_p90_monthly", "hist_p75_monthly",
        "hist_mean_monthly", "hist_std_monthly", "hist_cv",
        "jan_avg_volume", "jan_max_volume", "jan_count",
        "active_months", "active_months_pct",
        "consecutive_zero_months_max",
        "yoy_growth_rate", "recent_3m_avg", "trend_slope",
        "months_since_last_order", "total_volume",
        "distributor_id",
        "ema_3m", "ema_6m",
    ]
    features_df = features_df[output_cols]

    os.makedirs(GOLD_DIR, exist_ok=True)
    features_df.to_parquet(
        os.path.join(GOLD_DIR, "sales_features.parquet"),
        index=False, engine="pyarrow", compression="snappy"
    )

    duration = time.time() - start_time
    log.info("Written %d rows → sales_features.parquet (%.1fs)", len(features_df), duration)
    log.info("  Outlets with history : %d", len(features_df) - no_history_count)
    log.info("  Outlets without      : %d", no_history_count)


if __name__ == "__main__":
    main()
