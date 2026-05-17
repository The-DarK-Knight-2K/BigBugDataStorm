"""
Train a CatBoost gradient-boosting model to predict outlet-level maximum
monthly purchase potential.

Since there is no labelled target variable, a pseudo-label is constructed from
the 90th percentile historical monthly volume adjusted for seasonality and
January 2026 trading days.

Layer  : Modelling
Inputs : data/Gold/master_features.parquet
Outputs: modelling/artifacts/model.pkl
         modelling/artifacts/feature_importance.png
         modelling/artifacts/cv_results.json

Algorithm: CatBoost (selected over LightGBM — CV RMSE 40.38 vs 40.96)
Hyperparameters: Optuna-tuned (20 trials), loaded from config.yaml
"""

import json
import os
import pickle
import sys
import time

import matplotlib
matplotlib.use("Agg")  # non-interactive backend (no GUI needed)
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
import yaml
from catboost import CatBoostRegressor, Pool
from sklearn.model_selection import KFold

# ---------------------------------------------------------------------------
# Path setup (matches existing baseline.py conventions)
# ---------------------------------------------------------------------------
CURRENT_DIR = os.path.dirname(os.path.abspath(__file__))
ROOT_DIR = os.path.dirname(CURRENT_DIR)

# Add pipeline dir to path so we can import the shared logger
PIPELINE_DIR = os.path.join(ROOT_DIR, "pipeline")
if PIPELINE_DIR not in sys.path:
    sys.path.insert(0, PIPELINE_DIR)

from utils.logger import setup_logger

log = setup_logger("train")

GOLD_DIR = os.path.join(ROOT_DIR, "Data", "Gold")
ARTIFACTS_DIR = os.path.join(CURRENT_DIR, "artifacts")

# ---------------------------------------------------------------------------
# Load config
# ---------------------------------------------------------------------------
with open(os.path.join(ROOT_DIR, "config.yaml"), "r") as f:
    CFG = yaml.safe_load(f)

# ---------------------------------------------------------------------------
# Feature configuration
# ---------------------------------------------------------------------------

# Exclude non-feature / metadata columns
EXCLUDE_COLS = [
    "Outlet_ID",
    "seasonality_jan_2026", "distributor_id",
    "target",                        # will be added during training
    "has_transaction_history",        # filter flag, not a feature
    "exclude_from_training",          # filter flag, not a feature
    "baseline_potential_litres",      # baseline floor, not a training feature
    "jan_2026_holiday_count",         # constant across all rows (zero variance)
    "jan_2026_trading_days",          # constant across all rows (zero variance)
    # Redundant volume columns (keep hist_p90, hist_max, ema_3m, jan_avg)
    "hist_p75_monthly",
    "hist_mean_monthly",
    "total_volume",
    "hist_std_monthly",
    "ema_6m",
    "recent_3m_avg",
    "jan_max_volume",
]

# Categorical features handled natively by CatBoost
CAT_FEATURES = ["Outlet_Type", "Outlet_Size", "province"]


# ---------------------------------------------------------------------------
# Main training pipeline
# ---------------------------------------------------------------------------

def main() -> None:
    start_time = time.time()
    log.info("=" * 70)
    log.info("CATBOOST TRAINING PIPELINE -- START")
    log.info("=" * 70)

    # ------------------------------------------------------------------
    # Step 1 — Load data
    # ------------------------------------------------------------------
    input_path = os.path.join(GOLD_DIR, "master_features.parquet")
    df = pd.read_parquet(input_path)
    log.info("Loaded %d rows from master_features.parquet", len(df))

    # ------------------------------------------------------------------
    # Step 2 — Define feature columns
    # ------------------------------------------------------------------
    feature_cols = [c for c in df.columns if c not in EXCLUDE_COLS]

    # Identify categorical feature indices for CatBoost Pool
    cat_feature_indices = [
        feature_cols.index(c) for c in CAT_FEATURES if c in feature_cols
    ]
    log.info(
        "Training with %d features (%d categorical): %s",
        len(feature_cols), len(cat_feature_indices), feature_cols,
    )

    # ------------------------------------------------------------------
    # Step 3 — Build training set and target (pseudo-label)
    # ------------------------------------------------------------------
    df_train = df[
        (df["has_transaction_history"] == True)
        & (df["exclude_from_training"] == False)
    ].copy()

    df_train["target"] = (
        df_train["hist_p90_monthly"]
        * df_train["seasonality_multiplier_jan_2026"]
        * (df_train["jan_2026_trading_days"] / 22.0)
    )

    X = df_train[feature_cols]
    y = df_train["target"]

    log.info(
        "Training set: %d outlets (excluded %d with no history, %d with bad coords)",
        len(df_train),
        (df["has_transaction_history"] == False).sum(),
        (df["exclude_from_training"] == True).sum(),
    )
    log.info(
        "Training target — min: %.2f, median: %.2f, max: %.2f",
        y.min(), y.median(), y.max(),
    )

    # ------------------------------------------------------------------
    # Step 4 — Cross-validation (5-fold)
    # ------------------------------------------------------------------
    cb_params = CFG["modelling"]["catboost_params"].copy()
    # Remove cat_features from params dict — passed separately to Pool
    cb_params.pop("cat_features", None)

    kf = KFold(
        n_splits=CFG["modelling"]["cv_folds"],
        shuffle=True,
        random_state=CFG["modelling"]["random_seed"],
    )

    cv_rmse_scores = []
    cv_mae_scores = []

    log.info("Starting %d-fold cross-validation...", CFG["modelling"]["cv_folds"])

    for fold, (train_idx, val_idx) in enumerate(kf.split(X), 1):
        X_tr, X_val = X.iloc[train_idx], X.iloc[val_idx]
        y_tr, y_val = y.iloc[train_idx], y.iloc[val_idx]

        train_pool = Pool(X_tr, y_tr, cat_features=cat_feature_indices)
        val_pool = Pool(X_val, y_val, cat_features=cat_feature_indices)

        model = CatBoostRegressor(**cb_params)
        model.fit(
            train_pool,
            eval_set=val_pool,
            early_stopping_rounds=50,
            verbose=100,
        )

        preds = model.predict(X_val)
        rmse = np.sqrt(np.mean((preds - y_val.values) ** 2))
        mae = np.mean(np.abs(preds - y_val.values))
        cv_rmse_scores.append(rmse)
        cv_mae_scores.append(mae)
        log.info("Fold %d -- RMSE: %.2f  MAE: %.2f", fold, rmse, mae)

    log.info(
        "CV RMSE: %.2f +/- %.2f",
        np.mean(cv_rmse_scores), np.std(cv_rmse_scores),
    )
    log.info(
        "CV MAE : %.2f +/- %.2f",
        np.mean(cv_mae_scores), np.std(cv_mae_scores),
    )

    # ------------------------------------------------------------------
    # Step 5 — Train final model on full training data
    # ------------------------------------------------------------------
    log.info("Training final model on full training set (%d samples)...", len(X))
    full_pool = Pool(X, y, cat_features=cat_feature_indices)
    final_model = CatBoostRegressor(**cb_params)
    final_model.fit(full_pool, verbose=100)
    log.info("Final model trained on %d samples", len(X))

    # ------------------------------------------------------------------
    # Step 6 — Save model
    # ------------------------------------------------------------------
    os.makedirs(ARTIFACTS_DIR, exist_ok=True)

    model_path = os.path.join(ARTIFACTS_DIR, "model.pkl")
    with open(model_path, "wb") as f:
        pickle.dump({"model": final_model, "feature_cols": feature_cols}, f)
    log.info("Model saved -> %s", model_path)

    # ------------------------------------------------------------------
    # Step 7 — Feature importance plot
    # ------------------------------------------------------------------
    importance_df = pd.DataFrame({
        "feature": feature_cols,
        "importance": final_model.feature_importances_,
    }).sort_values("importance", ascending=False).head(30)

    fig, ax = plt.subplots(figsize=(10, 12))
    ax.barh(
        importance_df["feature"][::-1],
        importance_df["importance"][::-1],
    )
    ax.set_xlabel("Feature Importance (gain)")
    ax.set_title("Top 30 Feature Importances - CatBoost")
    plt.tight_layout()

    plot_path = os.path.join(ARTIFACTS_DIR, "feature_importance.png")
    plt.savefig(plot_path, dpi=150)
    plt.close()
    log.info("Feature importance plot saved -> %s", plot_path)

    # ------------------------------------------------------------------
    # Step 8 — Save CV results
    # ------------------------------------------------------------------
    cv_results = {
        "cv_folds": CFG["modelling"]["cv_folds"],
        "cv_rmse_mean": float(np.mean(cv_rmse_scores)),
        "cv_rmse_std": float(np.std(cv_rmse_scores)),
        "cv_mae_mean": float(np.mean(cv_mae_scores)),
        "cv_mae_std": float(np.std(cv_mae_scores)),
        "n_features": len(feature_cols),
        "n_train_samples": len(X),
    }
    cv_path = os.path.join(ARTIFACTS_DIR, "cv_results.json")
    with open(cv_path, "w") as f:
        json.dump(cv_results, f, indent=2)
    log.info("CV results saved -> %s", cv_path)

    # ------------------------------------------------------------------
    # Assertions
    # ------------------------------------------------------------------
    assert os.path.exists(model_path), "model.pkl was not created"

    # Spot-check: model can make predictions
    sample = X.head(5)
    preds = final_model.predict(sample)
    assert len(preds) == 5, f"Expected 5 predictions, got {len(preds)}"
    assert all(p > 0 for p in preds), "Model predicting non-positive values"
    log.info("All assertions passed.")

    # ------------------------------------------------------------------
    # Summary
    # ------------------------------------------------------------------
    duration = time.time() - start_time
    log.info("=" * 70)
    log.info("TRAINING SUMMARY")
    log.info("  Training samples     : %d", len(X))
    log.info("  Features             : %d (%d categorical)", len(feature_cols), len(cat_feature_indices))
    log.info("  CV RMSE              : %.2f +/- %.2f", np.mean(cv_rmse_scores), np.std(cv_rmse_scores))
    log.info("  CV MAE               : %.2f +/- %.2f", np.mean(cv_mae_scores), np.std(cv_mae_scores))
    log.info("  Artifacts saved to   : %s", ARTIFACTS_DIR)
    log.info("  Duration             : %.1f seconds", duration)
    log.info("=" * 70)
    log.info("CATBOOST TRAINING PIPELINE -- DONE")
    log.info("=" * 70)


if __name__ == "__main__":
    main()
