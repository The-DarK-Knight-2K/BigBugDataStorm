"""
Tobit-style censored demand model using XGBoost's Accelerated Failure Time
(survival:aft) objective.

Rationale: Historical sales are right-censored — an outlet's observed volume
is capped by operational constraints (cooler capacity, credit limits, supply
availability). The true unconstrained demand is higher than what we observe.
XGBoost's AFT objective natively handles censored data, providing the modern
ML equivalent of classical Tobit regression.

The output `tobit_latent_estimate` is a per-outlet estimate of uncensored
latent demand, used as an additional feature for the main ensemble models.

Layer  : Modelling
Inputs : Data/Gold/master_features.parquet
Outputs: Data/Gold/tobit_features.parquet
"""

import os
import sys
import time

import numpy as np
import pandas as pd
import yaml

# ---------------------------------------------------------------------------
# Path setup
# ---------------------------------------------------------------------------
CURRENT_DIR = os.path.dirname(os.path.abspath(__file__))
ROOT_DIR = os.path.dirname(CURRENT_DIR)

PIPELINE_DIR = os.path.join(ROOT_DIR, "pipeline")
if PIPELINE_DIR not in sys.path:
    sys.path.insert(0, PIPELINE_DIR)

from utils.logger import setup_logger

log = setup_logger("tobit_model")

GOLD_DIR = os.path.join(ROOT_DIR, "Data", "Gold")

with open(os.path.join(ROOT_DIR, "config.yaml"), "r") as f:
    CFG = yaml.safe_load(f)

SEED = CFG["modelling"]["random_seed"]

# Features to exclude (metadata/flags/targets — not predictive inputs)
_EXCLUDE_COLS = [
    "Outlet_ID",
    "seasonality_jan_2026", "distributor_id",
    "has_transaction_history",
    "exclude_from_training",
    "baseline_potential_litres",
    "jan_2026_holiday_count",
    "jan_2026_trading_days",
    # Target leakage (same as strategyA)
    "hist_p90_monthly",
    "hist_max_monthly",
    "jan_avg_volume",
    "ema_3m",
    "capacity_utilization_ratio",
    "cluster_mean_volume",
    "cluster_p90_volume",
    # Prevent reading own/other sub-model outputs
    "tobit_latent_estimate",
    "tobit_censoring_ratio",
    "p_active",
    "hurdle_conditional_volume",
    "hurdle_estimate",
    # Remove flat POI counts (gravity-only strategy)
    "schools_500m", "schools_1000m", "schools_2000m",
    "hospitals_500m", "hospitals_1000m", "hospitals_2000m",
    "transport_500m", "transport_1000m", "transport_2000m",
    "markets_500m", "markets_1000m", "markets_2000m",
    "worship_500m", "worship_1000m", "worship_2000m",
    "hospitality_500m", "hospitality_1000m", "hospitality_2000m",
    "footfall_score",
    # Round 1 redundant
    "hist_p75_monthly", "hist_mean_monthly", "total_volume",
    "hist_std_monthly", "ema_6m", "recent_3m_avg", "jan_max_volume",
]

# Categorical features to encode
CAT_FEATURES = ["Outlet_Type", "Outlet_Size", "province", "market_saturation_class"]


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------
def prepare_features(df: pd.DataFrame) -> tuple[pd.DataFrame, list[str]]:
    """Prepare feature matrix, encoding categoricals and selecting columns."""
    feature_cols = [c for c in df.columns if c not in _EXCLUDE_COLS]
    X = df[feature_cols].copy()

    # Encode categoricals as integer codes (XGBoost requires numeric)
    for col in CAT_FEATURES:
        if col in X.columns:
            X[col] = X[col].astype("category").cat.codes

    return X, feature_cols


def build_censoring_labels(
    df: pd.DataFrame,
) -> tuple[np.ndarray, np.ndarray]:
    """
    Build the upper/lower bound arrays for XGBoost AFT.

    AFT expects:
      - y_lower: the observed value (lower bound)
      - y_upper: the upper bound (inf for right-censored, same as lower for exact)

    Strategy:
      - Outlets with high capacity utilization (>= 0.8) are right-censored:
        their observed sales are likely constrained by cooler capacity.
        y_upper = +inf (we don't know the true demand).
      - All other outlets: exact observations.
        y_upper = y_lower = observed volume.
    """
    # Use hist_p90_monthly as the observed volume
    observed = df["hist_p90_monthly"].values.copy()
    observed = np.clip(observed, 1e-3, None)  # AFT requires strictly positive values

    y_lower = observed.copy()
    y_upper = observed.copy()

    # Mark right-censored outlets: those where capacity utilization >= threshold
    if "capacity_utilization_ratio" in df.columns:
        censored_mask = df["capacity_utilization_ratio"].values >= 0.8
        y_upper[censored_mask] = np.inf
        n_censored = censored_mask.sum()
        log.info(
            "Censoring: %d outlets marked as right-censored (utilization >= 0.8), "
            "%d exact observations.",
            n_censored, len(df) - n_censored,
        )
    else:
        # Fallback: use a simple heuristic — if P90 > 80% of hist_max,
        # the outlet is likely constrained
        if "hist_max_monthly" in df.columns:
            hist_max = df["hist_max_monthly"].values
            censored_mask = (hist_max > 0) & (observed / np.clip(hist_max, 1e-3, None) > 0.85)
            y_upper[censored_mask] = np.inf
            n_censored = censored_mask.sum()
            log.info(
                "Censoring (fallback): %d outlets right-censored (P90/max > 0.85).",
                n_censored,
            )

    return y_lower, y_upper


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------
def main() -> None:
    import xgboost as xgb

    start_time = time.time()
    log.info("=" * 70)
    log.info("TOBIT MODEL (XGBoost AFT) — START")
    log.info("=" * 70)

    # --- Load master features ---
    input_path = os.path.join(GOLD_DIR, "master_features.parquet")
    df = pd.read_parquet(input_path)
    log.info("Loaded %d rows from master_features.parquet", len(df))

    # --- Filter training set (same criteria as train.py) ---
    df_train = df[
        (df["has_transaction_history"] == True)
        & (df["exclude_from_training"] == False)
    ].copy()
    log.info("Training set: %d outlets", len(df_train))

    # --- Prepare features ---
    X_train, feature_cols = prepare_features(df_train)
    X_all, _ = prepare_features(df)

    from sklearn.model_selection import KFold

    # --- Build censoring labels ---
    y_lower, y_upper = build_censoring_labels(df_train)

    # --- Train AFT model with OOF ---
    params = {
        "objective": "survival:aft",
        "eval_metric": "aft-nloglik",
        "aft_loss_distribution": "normal",
        "aft_loss_distribution_scale": 1.0,
        "learning_rate": 0.05,
        "max_depth": 6,
        "subsample": 0.8,
        "colsample_bytree": 0.8,
        "seed": SEED,
        "tree_method": "hist",
        "verbosity": 0,
    }

    log.info("Training XGBoost AFT model with 5-fold OOF predictions...")
    log.info("Params: %s", params)

    kf = KFold(n_splits=5, shuffle=True, random_state=SEED)
    
    oof_predictions = np.zeros(len(X_train))
    test_predictions = np.zeros(len(X_all))
    dall = xgb.DMatrix(X_all)
    
    X_train_np = X_train.values

    for fold, (train_idx, val_idx) in enumerate(kf.split(X_train_np)):
        X_tr, X_val = X_train_np[train_idx], X_train_np[val_idx]
        y_lower_tr, y_lower_val = y_lower[train_idx], y_lower[val_idx]
        y_upper_tr, y_upper_val = y_upper[train_idx], y_upper[val_idx]
        
        dtrain_fold = xgb.DMatrix(X_tr)
        dtrain_fold.set_float_info("label_lower_bound", y_lower_tr)
        dtrain_fold.set_float_info("label_upper_bound", y_upper_tr)
        
        dval_fold = xgb.DMatrix(X_val)
        dval_fold.set_float_info("label_lower_bound", y_lower_val)
        dval_fold.set_float_info("label_upper_bound", y_upper_val)
        
        model = xgb.train(
            params,
            dtrain_fold,
            num_boost_round=500,
            evals=[(dtrain_fold, "train"), (dval_fold, "val")],
            verbose_eval=False,
        )
        
        oof_predictions[val_idx] = model.predict(dval_fold)
        test_predictions += model.predict(dall) / 5.0
        log.info(f"Fold {fold+1} complete.")

    # --- Generate predictions for ALL outlets ---
    train_outlet_ids = df_train["Outlet_ID"].values
    all_outlet_ids = df["Outlet_ID"].values
    
    tobit_predictions = test_predictions.copy()
    oof_map = dict(zip(train_outlet_ids, oof_predictions))
    
    for i, oid in enumerate(all_outlet_ids):
        if oid in oof_map:
            tobit_predictions[i] = oof_map[oid]

    # Clip to ensure positive predictions
    tobit_predictions = np.clip(tobit_predictions, 0.0, None)

    log.info(
        "Tobit predictions — min: %.2f, median: %.2f, mean: %.2f, max: %.2f",
        np.min(tobit_predictions),
        np.median(tobit_predictions),
        np.mean(tobit_predictions),
        np.max(tobit_predictions),
    )

    # --- Compute censoring probability (fraction of samples in each outlet's
    # neighborhood that are censored) ---
    # Simplified: use the ratio of prediction to observed as a censoring indicator
    df_out = df[["Outlet_ID"]].copy()
    df_out["tobit_latent_estimate"] = tobit_predictions.round(4)

    # Censoring ratio: how much higher the Tobit estimate is vs observed P90
    observed_p90 = df["hist_p90_monthly"].values.copy()
    observed_p90 = np.clip(observed_p90, 1e-3, None)
    df_out["tobit_censoring_ratio"] = np.clip(
        (tobit_predictions / observed_p90) - 1.0, 0.0, None
    ).round(4)

    log.info(
        "Censoring ratio — mean: %.3f, P50: %.3f, P90: %.3f, max: %.3f",
        df_out["tobit_censoring_ratio"].mean(),
        df_out["tobit_censoring_ratio"].median(),
        df_out["tobit_censoring_ratio"].quantile(0.90),
        df_out["tobit_censoring_ratio"].max(),
    )

    # --- Cast types ---
    df_out["tobit_latent_estimate"] = df_out["tobit_latent_estimate"].astype("float32")
    df_out["tobit_censoring_ratio"] = df_out["tobit_censoring_ratio"].astype("float32")

    # --- Assertions ---
    assert len(df_out) == 20000, f"Expected 20000 rows, got {len(df_out)}"
    assert df_out["Outlet_ID"].duplicated().sum() == 0, "Duplicate Outlet_IDs"
    assert df_out.isnull().sum().sum() == 0, "NaN values found"
    assert (df_out["tobit_latent_estimate"] >= 0).all(), "Negative Tobit estimates"
    log.info("All assertions passed.")

    # --- Save output ---
    output_path = os.path.join(GOLD_DIR, "tobit_features.parquet")
    df_out.to_parquet(output_path, index=False, engine="pyarrow", compression="snappy")

    duration = time.time() - start_time
    log.info(
        "Written %d rows x %d columns -> tobit_features.parquet (%.1fs)",
        len(df_out), len(df_out.columns), duration,
    )
    log.info("=" * 70)
    log.info("TOBIT MODEL — DONE")
    log.info("=" * 70)


if __name__ == "__main__":
    main()
