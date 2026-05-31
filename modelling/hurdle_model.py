"""
Hurdle Model: Two-Stage Zero-Inflated Demand Estimator.

Stage 1 — Binary Classifier ("The Hurdle"):
    Logistic Regression predicting P(volume > 0) for each outlet.
    Separates genuinely inactive outlets from active ones.

Stage 2 — Conditional Regressor:
    XGBRegressor trained ONLY on active outlets (volume > 0).
    Estimates E[volume | volume > 0].

Final prediction: P(active) × E[volume | active]

This formally separates the "will this outlet be active?" question from the
"how much will it sell?" question — two fundamentally different statistical
processes that standard regression models can't cleanly represent.

Layer  : Modelling
Inputs : Data/Gold/master_features.parquet
Outputs: Data/Gold/hurdle_features.parquet
"""

import os
import sys
import time

import numpy as np
import pandas as pd
import yaml
from sklearn.linear_model import LogisticRegression
from sklearn.preprocessing import StandardScaler

# ---------------------------------------------------------------------------
# Path setup
# ---------------------------------------------------------------------------
CURRENT_DIR = os.path.dirname(os.path.abspath(__file__))
ROOT_DIR = os.path.dirname(CURRENT_DIR)

PIPELINE_DIR = os.path.join(ROOT_DIR, "pipeline")
if PIPELINE_DIR not in sys.path:
    sys.path.insert(0, PIPELINE_DIR)

from utils.logger import setup_logger

log = setup_logger("hurdle_model")

GOLD_DIR = os.path.join(ROOT_DIR, "Data", "Gold")

with open(os.path.join(ROOT_DIR, "config.yaml"), "r") as f:
    CFG = yaml.safe_load(f)

SEED = CFG["modelling"]["random_seed"]

# Features to exclude (metadata/flags/targets — same as strategyA_gravity_only)
_EXCLUDE_COLS = [
    "Outlet_ID",
    "seasonality_jan_2026", "distributor_id",
    "has_transaction_history",
    "exclude_from_training",
    "baseline_potential_litres",
    "jan_2026_holiday_count",
    "jan_2026_trading_days",
    # Target leakage
    "hist_p90_monthly",
    "hist_max_monthly",
    "jan_avg_volume",
    "ema_3m",
    # Flat POI (gravity-only)
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

CAT_FEATURES = ["Outlet_Type", "Outlet_Size", "province", "market_saturation_class"]


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------
def prepare_features(df: pd.DataFrame) -> tuple[pd.DataFrame, list[str]]:
    """Prepare feature matrix, encoding categoricals."""
    feature_cols = [c for c in df.columns if c not in _EXCLUDE_COLS]
    X = df[feature_cols].copy()

    for col in CAT_FEATURES:
        if col in X.columns:
            X[col] = X[col].astype("category").cat.codes

    return X, feature_cols


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------
def main() -> None:
    import xgboost as xgb

    start_time = time.time()
    log.info("=" * 70)
    log.info("HURDLE MODEL (Two-Stage) — START")
    log.info("=" * 70)

    # --- Load master features ---
    input_path = os.path.join(GOLD_DIR, "master_features.parquet")
    df = pd.read_parquet(input_path)
    log.info("Loaded %d rows from master_features.parquet", len(df))

    # --- Filter training set ---
    df_train = df[
        (df["has_transaction_history"] == True)
        & (df["exclude_from_training"] == False)
    ].copy()
    log.info("Training set: %d outlets", len(df_train))

    # --- Prepare features ---
    X_train, feature_cols = prepare_features(df_train)
    X_all, _ = prepare_features(df)

    # --- Build target: P90 monthly volume (same as main pipeline) ---
    y_volume = (
        df_train["hist_p90_monthly"]
        * df_train["seasonality_multiplier_jan_2026"]
        * (df_train["jan_2026_trading_days"] / 22.0)
    )
    y_binary = (y_volume > 0).astype(int)

    n_active = y_binary.sum()
    n_inactive = len(y_binary) - n_active
    log.info(
        "Binary target — active: %d (%.1f%%), inactive: %d (%.1f%%)",
        n_active, 100 * n_active / len(y_binary),
        n_inactive, 100 * n_inactive / len(y_binary),
    )

    # ======================================================================
    # STAGE 1: Logistic Regression — P(active)
    # ======================================================================
    log.info("--- Stage 1: Logistic Regression (binary classifier) ---")

    # Scale features for logistic regression
    scaler = StandardScaler()
    X_train_scaled = scaler.fit_transform(X_train)
    X_all_scaled = scaler.transform(X_all)

    if len(np.unique(y_binary)) < 2:
        log.info("Only one class detected in y_binary. Skipping Logistic Regression and setting p_active = has_transaction_history.")
        p_active_train = np.ones(len(df_train))
        p_active_all = df["has_transaction_history"].astype(float).values
        acc = 1.0
        f1 = 1.0
    else:
        clf = LogisticRegression(
            max_iter=2000,
            random_state=SEED,
            class_weight="balanced",   # Handle imbalanced classes
            solver="lbfgs",
            C=1.0,
        )
        clf.fit(X_train_scaled, y_binary)

        # Predict P(active) for ALL outlets
        p_active_train = clf.predict_proba(X_train_scaled)[:, 1]
        p_active_all = clf.predict_proba(X_all_scaled)[:, 1]

    log.info(
        "P(active) — min: %.4f, median: %.4f, mean: %.4f, max: %.4f",
        np.min(p_active_all),
        np.median(p_active_all),
        np.mean(p_active_all),
        np.max(p_active_all),
    )

    # Evaluate Stage 1 accuracy
    from sklearn.metrics import accuracy_score, f1_score
    y_pred_binary = (p_active_train >= 0.5).astype(int)
    acc = accuracy_score(y_binary, y_pred_binary)
    f1 = f1_score(y_binary, y_pred_binary, zero_division=0)
    log.info("Stage 1 — Accuracy: %.4f, F1: %.4f", acc, f1)

    # ======================================================================
    # STAGE 2: XGBRegressor — E[volume | active]
    # ======================================================================
    log.info("--- Stage 2: XGBRegressor (conditional volume) ---")

    active_mask = y_volume > 0
    X_active = X_train[active_mask]
    y_active = y_volume[active_mask]

    log.info("Active outlets for Stage 2 training: %d", len(X_active))

    reg = xgb.XGBRegressor(
        n_estimators=500,
        max_depth=6,
        learning_rate=0.05,
        subsample=0.8,
        colsample_bytree=0.8,
        reg_alpha=0.1,
        reg_lambda=1.0,
        random_state=SEED,
        tree_method="hist",
        device="cuda",
        verbosity=1,
    )
    reg.fit(X_active, y_active)

    # Predict conditional volume for ALL outlets
    conditional_volume_all = reg.predict(X_all)
    conditional_volume_all = np.clip(conditional_volume_all, 0.0, None)

    log.info(
        "Conditional volume — min: %.2f, median: %.2f, mean: %.2f, max: %.2f",
        np.min(conditional_volume_all),
        np.median(conditional_volume_all),
        np.mean(conditional_volume_all),
        np.max(conditional_volume_all),
    )

    # ======================================================================
    # COMBINE: hurdle_estimate = P(active) × E[volume | active]
    # ======================================================================
    hurdle_estimate = p_active_all * conditional_volume_all

    log.info(
        "Hurdle estimate — min: %.2f, median: %.2f, mean: %.2f, max: %.2f",
        np.min(hurdle_estimate),
        np.median(hurdle_estimate),
        np.mean(hurdle_estimate),
        np.max(hurdle_estimate),
    )

    # --- Build output DataFrame ---
    df_out = df[["Outlet_ID"]].copy()
    df_out["p_active"] = p_active_all.round(4)
    df_out["hurdle_conditional_volume"] = conditional_volume_all.round(4)
    df_out["hurdle_estimate"] = hurdle_estimate.round(4)

    # --- Cast types ---
    df_out["p_active"] = df_out["p_active"].astype("float32")
    df_out["hurdle_conditional_volume"] = df_out["hurdle_conditional_volume"].astype("float32")
    df_out["hurdle_estimate"] = df_out["hurdle_estimate"].astype("float32")

    # --- Assertions ---
    assert len(df_out) == 20000, f"Expected 20000 rows, got {len(df_out)}"
    assert df_out["Outlet_ID"].duplicated().sum() == 0, "Duplicate Outlet_IDs"
    assert df_out.isnull().sum().sum() == 0, "NaN values found"
    assert (df_out["p_active"] >= 0).all() and (df_out["p_active"] <= 1).all(), (
        "p_active must be in [0, 1]"
    )
    assert (df_out["hurdle_estimate"] >= 0).all(), "Negative hurdle estimates"
    log.info("All assertions passed.")

    # --- Save output ---
    output_path = os.path.join(GOLD_DIR, "hurdle_features.parquet")
    df_out.to_parquet(output_path, index=False, engine="pyarrow", compression="snappy")

    duration = time.time() - start_time
    log.info(
        "Written %d rows x %d columns -> hurdle_features.parquet (%.1fs)",
        len(df_out), len(df_out.columns), duration,
    )
    log.info("=" * 70)
    log.info("HURDLE MODEL — DONE")
    log.info("=" * 70)


if __name__ == "__main__":
    main()
