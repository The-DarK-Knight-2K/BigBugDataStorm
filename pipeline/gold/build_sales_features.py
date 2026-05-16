import pandas as pd
import numpy as np
import os
import sys
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
# Helper functions
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


def compute_yoy_growth(monthly_df: pd.DataFrame):
    """Year-over-year growth rate from first to last year average. None if <2 years."""
    avg_by_year = monthly_df.groupby("Year")["monthly_volume"].mean()
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

    # Build a complete period range for filling zeros later
    all_periods = pd.period_range(data_start, data_end, freq="M")

    # ── Step 4: Compute per-outlet features ──────────────────────────────
    results = []
    outlets_with_txn = monthly["Outlet_ID"].unique()

    # Global mode distributor for imputation of outlets with no transactions
    global_mode_dist = txn["Distributor_ID"].value_counts().idxmax()

    for outlet_id in outlets_with_txn:
        om = monthly[monthly["Outlet_ID"] == outlet_id].copy()

        # Create a full timeline for this outlet (fill missing months with 0)
        om["period"] = pd.PeriodIndex(
            om["Year"].astype(str) + "-" + om["Month"].astype(str).str.zfill(2), freq="M"
        )
        om = om.set_index("period").reindex(all_periods, fill_value=0).reset_index()
        om.rename(columns={"index": "period"}, inplace=True)
        om["Year"] = om["period"].dt.year
        om["Month"] = om["period"].dt.month
        # Ensure monthly_volume is float for calculations
        om["monthly_volume"] = om["monthly_volume"].astype(float)

        vol = om["monthly_volume"]

        # 4a — Historical volume statistics
        hist_max = float(vol.max())
        hist_p90 = float(vol.quantile(0.90))
        hist_p75 = float(vol.quantile(0.75))
        hist_mean = float(vol.mean())
        hist_std = float(vol.std()) if len(vol) > 1 else 0.0
        hist_cv = float(hist_std / hist_mean) if hist_mean > 0 else 0.0

        # 4b — January-specific features
        jan_data = om[om["Month"] == 1]["monthly_volume"]
        jan_avg = float(jan_data.mean()) if len(jan_data) > 0 else 0.0
        jan_max = float(jan_data.max()) if len(jan_data) > 0 else 0.0
        jan_count = int((jan_data > 0).sum())

        # 4c — Activity and recency
        active_months = int((vol > 0).sum())
        active_months_pct = float(active_months / total_months_in_data) if total_months_in_data > 0 else 0.0
        consec_zero_max = max_consecutive_zeros(vol)

        # months_since_last_order: distance from last non-zero month to data_end
        non_zero_indices = vol[vol > 0].index
        if len(non_zero_indices) > 0:
            last_active_idx = non_zero_indices[-1]
            months_since_last = len(vol) - 1 - last_active_idx
        else:
            months_since_last = total_months_in_data

        total_vol = float(vol.sum())

        # 4d — Growth and trend
        yoy = compute_yoy_growth(om)
        recent_3m = float(vol.iloc[-3:].mean()) if len(vol) >= 3 else float(vol.mean())
        slope = compute_trend_slope(vol)

        # 4e — EMA
        ema_3 = compute_ema(vol, span=3)
        ema_6 = compute_ema(vol, span=6)

        # 4f — Distributor assignment (most frequent)
        outlet_txn = txn[txn["Outlet_ID"] == outlet_id]
        dist_id = outlet_txn["Distributor_ID"].value_counts().idxmax()

        results.append({
            "Outlet_ID": outlet_id,
            "hist_max_monthly": hist_max,
            "hist_p90_monthly": hist_p90,
            "hist_p75_monthly": hist_p75,
            "hist_mean_monthly": hist_mean,
            "hist_std_monthly": hist_std,
            "hist_cv": hist_cv,
            "jan_avg_volume": jan_avg,
            "jan_max_volume": jan_max,
            "jan_count": jan_count,
            "active_months": active_months,
            "active_months_pct": active_months_pct,
            "consecutive_zero_months_max": consec_zero_max,
            "yoy_growth_rate": yoy,
            "recent_3m_avg": recent_3m,
            "trend_slope": slope,
            "months_since_last_order": months_since_last,
            "total_volume": total_vol,
            "distributor_id": dist_id,
            "ema_3m": ema_3,
            "ema_6m": ema_6,
        })

    computed = pd.DataFrame(results)
    log.info("Computed features for %d outlets with transaction history.", len(computed))

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

    log.info("Written %d rows → sales_features.parquet", len(features_df))
    log.info("  Outlets with history : %d", len(features_df) - no_history_count)
    log.info("  Outlets without      : %d", no_history_count)


if __name__ == "__main__":
    main()
