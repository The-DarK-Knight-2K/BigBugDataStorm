"""
Train a gradient-boosting model to predict outlet-level maximum monthly
purchase potential. Supports multiple algorithms (CatBoost, XGBoost, LightGBM)
and multiple feature strategies via CLI flags.

Every run is saved to a timestamped folder under modelling/artifacts/runs/
with model, predictions, CV results, feature importance, and run config.
A master run_registry.csv tracks all experiments.

Layer  : Modelling
Inputs : Data/Gold/master_features.parquet
Outputs: modelling/artifacts/runs/{run_id}/model.pkl
         modelling/artifacts/runs/{run_id}/predictions.csv
         modelling/artifacts/runs/{run_id}/cv_results.json
         modelling/artifacts/runs/{run_id}/feature_importance.png
         modelling/artifacts/runs/{run_id}/run_config.json
         modelling/artifacts/run_registry.csv  (appended)
         Data/Gold/shap_values.parquet         (optional, --shap flag)
"""

import argparse
import csv
import json
import os
import pickle
import sys
import time
from datetime import datetime

import matplotlib
matplotlib.use("Agg")  # non-interactive backend (no GUI needed)
import matplotlib.pyplot as plt
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

log = setup_logger("train")

GOLD_DIR = os.path.join(ROOT_DIR, "Data", "Gold")
ARTIFACTS_DIR = os.path.join(CURRENT_DIR, "artifacts")
RUNS_DIR = os.path.join(ARTIFACTS_DIR, "runs")
REGISTRY_PATH = os.path.join(ARTIFACTS_DIR, "run_registry.csv")

# ---------------------------------------------------------------------------
# Load config
# ---------------------------------------------------------------------------
with open(os.path.join(ROOT_DIR, "config.yaml"), "r") as f:
    CFG = yaml.safe_load(f)


# ---------------------------------------------------------------------------
# Strategy definitions
# ---------------------------------------------------------------------------
# Base columns always excluded (metadata/flags/constants)
_BASE_EXCLUDE = [
    "Outlet_ID",
    "seasonality_jan_2026", "distributor_id",
    "target",
    "has_transaction_history",
    "exclude_from_training",
    "baseline_potential_litres",
    "jan_2026_holiday_count",
    "jan_2026_trading_days",
]

# Round 1 redundant columns (already excluded in R1)
_R1_REDUNDANT = [
    "hist_p75_monthly",
    "hist_mean_monthly",
    "total_volume",
    "hist_std_monthly",
    "ema_6m",
    "recent_3m_avg",
    "jan_max_volume",
]

# Target leakage columns (Strategy A additions)
_LEAK_FEATURES = [
    "hist_p90_monthly",
    "hist_max_monthly",
    "jan_avg_volume",
    "ema_3m",
]

# Flat POI count columns (18 columns)
_FLAT_POI_COLS = [
    "schools_500m", "schools_1000m", "schools_2000m",
    "hospitals_500m", "hospitals_1000m", "hospitals_2000m",
    "transport_500m", "transport_1000m", "transport_2000m",
    "markets_500m", "markets_1000m", "markets_2000m",
    "worship_500m", "worship_1000m", "worship_2000m",
    "hospitality_500m", "hospitality_1000m", "hospitality_2000m",
    "footfall_score",
]

# Gravity score columns (7 + raw composite)
_GRAVITY_COLS = [
    "school_gravity_score", "hospital_gravity_score",
    "transport_gravity_score", "market_gravity_score",
    "worship_gravity_score", "hospitality_gravity_score",
    "composite_gravity_score", "raw_composite_gravity",
]

STRATEGIES = {
    "round1_baseline": {
        "description": "Round 1 features on updated master_features (with gravity+catchment auto-included). Leak features KEPT.",
        "exclude": _BASE_EXCLUDE + _R1_REDUNDANT,
        "interaction_features": False,
    },
    "strategyA": {
        "description": "Remove target leakage features. Forces model to learn from structural/spatial features.",
        "exclude": _BASE_EXCLUDE + _R1_REDUNDANT + _LEAK_FEATURES,
        "interaction_features": False,
    },
    "strategyC": {
        "description": "Strategy A + auto-generated interaction features (gravity×cooler, catchment×cooler, etc.).",
        "exclude": _BASE_EXCLUDE + _R1_REDUNDANT + _LEAK_FEATURES,
        "interaction_features": True,
    },
    "strategyA_gravity_only": {
        "description": "Strategy A but drop all flat POI counts. Only gravity scores + catchment + structural.",
        "exclude": _BASE_EXCLUDE + _R1_REDUNDANT + _LEAK_FEATURES + _FLAT_POI_COLS,
        "interaction_features": False,
    },
    "strategyA_flat_only": {
        "description": "Strategy A but drop all gravity scores. Only flat POI counts + catchment + structural.",
        "exclude": _BASE_EXCLUDE + _R1_REDUNDANT + _LEAK_FEATURES + _GRAVITY_COLS,
        "interaction_features": False,
    },
}

# Categorical features handled natively by CatBoost
CAT_FEATURES = ["Outlet_Type", "Outlet_Size", "province", "market_saturation_class"]


# ---------------------------------------------------------------------------
# Interaction feature engineering
# ---------------------------------------------------------------------------
def add_interaction_features(df: pd.DataFrame) -> list[str]:
    """Create cross-features and return the list of new column names."""
    interactions = {}

    if "composite_gravity_score" in df.columns and "Cooler_Count" in df.columns:
        interactions["gravity_x_cooler"] = (
            df["composite_gravity_score"] * df["Cooler_Count"]
        )
    if "composite_gravity_score" in df.columns and "active_months_pct" in df.columns:
        interactions["gravity_x_active_months"] = (
            df["composite_gravity_score"] * df["active_months_pct"]
        )
    if "competition_density_score" in df.columns and "Cooler_Count" in df.columns:
        interactions["catchment_x_cooler"] = (
            df["competition_density_score"] * df["Cooler_Count"]
        )
    if "transport_gravity_score" in df.columns and "school_gravity_score" in df.columns:
        interactions["transport_x_school"] = (
            df["transport_gravity_score"] * df["school_gravity_score"]
        )

    for col_name, values in interactions.items():
        df[col_name] = values

    log.info("Added %d interaction features: %s", len(interactions), list(interactions.keys()))
    return list(interactions.keys())


# ---------------------------------------------------------------------------
# Model factory
# ---------------------------------------------------------------------------
def create_model(algorithm: str, params: dict):
    """Create a model instance for the specified algorithm."""
    if algorithm == "catboost":
        from catboost import CatBoostRegressor
        return CatBoostRegressor(**params)

    elif algorithm == "xgboost":
        import xgboost as xgb
        return xgb.XGBRegressor(**params)

    elif algorithm == "lightgbm":
        import lightgbm as lgb
        return lgb.LGBMRegressor(**params)

    else:
        raise ValueError(f"Unknown algorithm: {algorithm}")


def get_model_params(algorithm: str, strategy: str = None, use_optuna: bool = False) -> dict:
    """Get model parameters from config, with GPU support."""
    if algorithm == "catboost":
        params = CFG["modelling"]["catboost_params"].copy()
        params.pop("cat_features", None)

    elif algorithm == "xgboost":
        params = {
            "n_estimators": 1000,
            "learning_rate": 0.05,
            "max_depth": 6,
            "subsample": 0.8,
            "colsample_bytree": 0.8,
            "reg_alpha": 0.1,
            "reg_lambda": 1.0,
            "random_state": CFG["modelling"]["random_seed"],
            "tree_method": "hist",
            "device": "cuda",
            "verbosity": 1,
        }

    elif algorithm == "lightgbm":
        lgbm_params = CFG["modelling"].get("lgbm_params", {}).copy()
        if not lgbm_params:
            lgbm_params = {
                "n_estimators": 1000,
                "learning_rate": 0.05,
                "num_leaves": 63,
                "min_child_samples": 20,
                "subsample": 0.8,
                "colsample_bytree": 0.8,
                "reg_alpha": 0.1,
                "reg_lambda": 0.1,
            }
        lgbm_params["random_state"] = CFG["modelling"]["random_seed"]
        lgbm_params["verbose"] = -1
        params = lgbm_params
    else:
        params = {}

    if use_optuna and strategy:
        import json
        optuna_file = os.path.join(ARTIFACTS_DIR, "optuna", f"best_params_{algorithm}_{strategy}.json")
        if os.path.exists(optuna_file):
            with open(optuna_file, "r") as f:
                optuna_params = json.load(f)
            params.update(optuna_params)
            log.info("Loaded Optuna tuned parameters from %s", optuna_file)
        else:
            log.warning("Optuna params requested but file not found: %s. Using defaults.", optuna_file)

    return params


def encode_categoricals_for_non_catboost(
    df: pd.DataFrame, cat_cols: list[str], algorithm: str
) -> pd.DataFrame:
    """Encode categorical columns for XGBoost/LightGBM."""
    df = df.copy()
    if algorithm == "lightgbm":
        for col in cat_cols:
            if col in df.columns:
                df[col] = df[col].astype("category")
    elif algorithm == "xgboost":
        for col in cat_cols:
            if col in df.columns:
                df[col] = df[col].astype("category").cat.codes
    return df


# ---------------------------------------------------------------------------
# Cross-validation
# ---------------------------------------------------------------------------
def run_cross_validation(
    X: pd.DataFrame,
    y: pd.Series,
    algorithm: str,
    params: dict,
    cat_feature_indices: list[int],
    n_folds: int,
    seed: int,
) -> tuple[list[float], list[float]]:
    """Run k-fold CV and return (rmse_scores, mae_scores)."""
    from sklearn.model_selection import KFold

    kf = KFold(n_splits=n_folds, shuffle=True, random_state=seed)
    cv_rmse_scores = []
    cv_mae_scores = []

    log.info("Starting %d-fold cross-validation (%s)...", n_folds, algorithm)

    for fold, (train_idx, val_idx) in enumerate(kf.split(X), 1):
        X_tr, X_val = X.iloc[train_idx], X.iloc[val_idx]
        y_tr, y_val = y.iloc[train_idx], y.iloc[val_idx]

        if algorithm == "catboost":
            from catboost import Pool
            train_pool = Pool(X_tr, y_tr, cat_features=cat_feature_indices)
            val_pool = Pool(X_val, y_val, cat_features=cat_feature_indices)
            model = create_model(algorithm, params)
            model.fit(
                train_pool,
                eval_set=val_pool,
                early_stopping_rounds=50,
                verbose=100,
            )
            preds = model.predict(X_val)
        else:
            model = create_model(algorithm, params)
            if algorithm == "xgboost":
                model.fit(
                    X_tr, y_tr,
                    eval_set=[(X_val, y_val)],
                    verbose=100,
                )
            else:  # lightgbm
                model.fit(
                    X_tr, y_tr,
                    eval_set=[(X_val, y_val)],
                )
            preds = model.predict(X_val)

        rmse = np.sqrt(np.mean((preds - y_val.values) ** 2))
        mae = np.mean(np.abs(preds - y_val.values))
        cv_rmse_scores.append(rmse)
        cv_mae_scores.append(mae)
        log.info("Fold %d -- RMSE: %.2f  MAE: %.2f", fold, rmse, mae)

    log.info(
        "CV RMSE: %.2f +/- %.2f", np.mean(cv_rmse_scores), np.std(cv_rmse_scores)
    )
    log.info(
        "CV MAE : %.2f +/- %.2f", np.mean(cv_mae_scores), np.std(cv_mae_scores)
    )
    return cv_rmse_scores, cv_mae_scores


# ---------------------------------------------------------------------------
# Train final model
# ---------------------------------------------------------------------------
def train_final_model(
    X: pd.DataFrame,
    y: pd.Series,
    algorithm: str,
    params: dict,
    cat_feature_indices: list[int],
):
    """Train the final model on the full training set."""
    log.info("Training final %s model on full training set (%d samples)...", algorithm, len(X))

    if algorithm == "catboost":
        from catboost import Pool
        full_pool = Pool(X, y, cat_features=cat_feature_indices)
        model = create_model(algorithm, params)
        model.fit(full_pool, verbose=100)
    else:
        model = create_model(algorithm, params)
        model.fit(X, y)

    log.info("Final model trained on %d samples", len(X))
    return model


# ---------------------------------------------------------------------------
# SHAP extraction
# ---------------------------------------------------------------------------
def extract_shap_values(
    model,
    X_all: pd.DataFrame,
    outlet_ids: pd.Series,
    algorithm: str,
    run_dir: str,
) -> None:
    """Extract cell-by-cell SHAP values using TreeExplainer."""
    import shap

    log.info("Extracting SHAP values for %d outlets...", len(X_all))
    start = time.time()

    explainer = shap.TreeExplainer(model)
    shap_values = explainer.shap_values(X_all)

    shap_df = pd.DataFrame(shap_values, columns=X_all.columns)
    shap_df.insert(0, "Outlet_ID", outlet_ids.values)

    # Save to Gold layer
    shap_path = os.path.join(GOLD_DIR, "shap_values.parquet")
    shap_df.to_parquet(shap_path, index=False, engine="pyarrow", compression="snappy")
    log.info("SHAP values saved -> %s (%.1fs)", shap_path, time.time() - start)

    # Also save a copy in the run folder
    run_shap_path = os.path.join(run_dir, "shap_values.parquet")
    shap_df.to_parquet(run_shap_path, index=False, engine="pyarrow", compression="snappy")
    log.info("SHAP values copy saved -> %s", run_shap_path)


# ---------------------------------------------------------------------------
# Save artifacts
# ---------------------------------------------------------------------------
def save_feature_importance(
    model, feature_cols: list[str], run_dir: str, algorithm: str
) -> None:
    """Save feature importance plot and CSV."""
    if algorithm == "catboost":
        importances = model.feature_importances_
    elif algorithm == "xgboost":
        importances = model.feature_importances_
    elif algorithm == "lightgbm":
        importances = model.feature_importances_
    else:
        log.warning("Cannot extract feature importances for %s", algorithm)
        return

    importance_df = pd.DataFrame({
        "feature": feature_cols,
        "importance": importances,
    }).sort_values("importance", ascending=False)

    # Save CSV
    csv_path = os.path.join(run_dir, "feature_importance.csv")
    importance_df.to_csv(csv_path, index=False)

    # Save plot (top 30)
    top30 = importance_df.head(30)
    fig, ax = plt.subplots(figsize=(10, 12))
    ax.barh(top30["feature"][::-1], top30["importance"][::-1])
    ax.set_xlabel("Feature Importance (gain)")
    ax.set_title(f"Top 30 Feature Importances — {algorithm.upper()}")
    plt.tight_layout()

    plot_path = os.path.join(run_dir, "feature_importance.png")
    plt.savefig(plot_path, dpi=150)
    plt.close()
    log.info("Feature importance saved -> %s", run_dir)


def save_run_config(
    run_dir: str,
    run_id: str,
    algorithm: str,
    strategy: str,
    params: dict,
    feature_cols: list[str],
    exclude_cols: list[str],
    notes: str,
    n_train: int,
) -> None:
    """Save the exact configuration of this run for reproducibility."""
    config = {
        "run_id": run_id,
        "timestamp": datetime.now().isoformat(),
        "algorithm": algorithm,
        "strategy": strategy,
        "strategy_description": STRATEGIES[strategy]["description"],
        "interaction_features": STRATEGIES[strategy]["interaction_features"],
        "model_params": params,
        "feature_cols": feature_cols,
        "excluded_cols": exclude_cols,
        "n_features": len(feature_cols),
        "n_train_samples": n_train,
        "target_formula": "hist_p90_monthly × seasonality_multiplier_jan_2026 × (jan_2026_trading_days / 22.0)",
        "notes": notes,
    }
    config_path = os.path.join(run_dir, "run_config.json")
    with open(config_path, "w") as f:
        json.dump(config, f, indent=2, default=str)
    log.info("Run config saved -> %s", config_path)


def save_predictions(
    model,
    df: pd.DataFrame,
    feature_cols: list[str],
    run_dir: str,
    algorithm: str,
) -> None:
    """Generate predictions for all 20K outlets and save inside the run folder."""
    X_all = df[feature_cols]

    if algorithm != "catboost":
        X_all = encode_categoricals_for_non_catboost(X_all, CAT_FEATURES, algorithm)

    preds = model.predict(X_all)

    pred_df = df[["Outlet_ID"]].copy()
    pred_df["model_prediction"] = preds
    pred_df["model_prediction"] = pred_df["model_prediction"].clip(lower=0).round(2)

    pred_path = os.path.join(run_dir, "predictions.csv")
    pred_df.to_csv(pred_path, index=False)
    log.info(
        "Predictions saved -> %s (min: %.2f, median: %.2f, max: %.2f)",
        pred_path,
        pred_df["model_prediction"].min(),
        pred_df["model_prediction"].median(),
        pred_df["model_prediction"].max(),
    )


def append_to_registry(
    run_id: str,
    algorithm: str,
    strategy: str,
    cv_rmse_scores: list[float],
    cv_mae_scores: list[float],
    n_features: int,
    n_train: int,
    excluded_features: list[str],
    notes: str,
    gpu: bool,
    duration: float,
) -> None:
    """Append a row to the master run_registry.csv."""
    os.makedirs(ARTIFACTS_DIR, exist_ok=True)

    row = {
        "run_id": run_id,
        "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        "algorithm": algorithm,
        "strategy": strategy,
        "cv_rmse_mean": f"{np.mean(cv_rmse_scores):.4f}",
        "cv_rmse_std": f"{np.std(cv_rmse_scores):.4f}",
        "cv_mae_mean": f"{np.mean(cv_mae_scores):.4f}",
        "cv_mae_std": f"{np.std(cv_mae_scores):.4f}",
        "n_features": n_features,
        "n_train_samples": n_train,
        "excluded_features": "|".join(excluded_features),
        "notes": notes,
        "gpu": gpu,
        "duration_s": f"{duration:.1f}",
    }

    file_exists = os.path.exists(REGISTRY_PATH)
    with open(REGISTRY_PATH, "a", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=row.keys())
        if not file_exists:
            writer.writeheader()
        writer.writerow(row)

    log.info("Run registered -> %s", REGISTRY_PATH)


# ---------------------------------------------------------------------------
# CLI argument parsing
# ---------------------------------------------------------------------------
def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Train a model with configurable strategy and algorithm."
    )
    parser.add_argument(
        "--strategy",
        type=str,
        default="strategyA",
        choices=list(STRATEGIES.keys()),
        help="Feature exclusion strategy (default: strategyA)",
    )
    parser.add_argument(
        "--algorithm",
        type=str,
        default="catboost",
        choices=["catboost", "xgboost", "lightgbm"],
        help="Training algorithm (default: catboost)",
    )
    parser.add_argument(
        "--notes",
        type=str,
        default="",
        help="Free-text notes for this run (logged in registry)",
    )
    parser.add_argument(
        "--shap",
        action="store_true",
        help="Extract SHAP values after training (saves to Data/Gold/shap_values.parquet)",
    )
    parser.add_argument(
        "--use-optuna-params",
        action="store_true",
        help="Use tuned parameters from Optuna run",
    )
    return parser.parse_args()


# ---------------------------------------------------------------------------
# Main training pipeline
# ---------------------------------------------------------------------------
def main() -> None:
    args = parse_args()
    start_time = time.time()

    strategy_name = args.strategy
    algorithm = args.algorithm
    strategy = STRATEGIES[strategy_name]

    # Generate run ID
    timestamp_str = datetime.now().strftime("%Y%m%d_%H%M%S")
    run_id = f"run_{timestamp_str}_{algorithm}_{strategy_name}"

    log.info("=" * 70)
    log.info("TRAINING PIPELINE -- START")
    log.info("  Run ID    : %s", run_id)
    log.info("  Algorithm : %s", algorithm)
    log.info("  Strategy  : %s", strategy_name)
    log.info("  Notes     : %s", args.notes or "(none)")
    log.info("=" * 70)

    # ------------------------------------------------------------------
    # Step 1 — Load data
    # ------------------------------------------------------------------
    input_path = os.path.join(GOLD_DIR, "master_features.parquet")
    df = pd.read_parquet(input_path)
    log.info("Loaded %d rows from master_features.parquet", len(df))

    # ------------------------------------------------------------------
    # Step 2 — Add interaction features (if strategy requires it)
    # ------------------------------------------------------------------
    interaction_cols = []
    if strategy["interaction_features"]:
        interaction_cols = add_interaction_features(df)

    # ------------------------------------------------------------------
    # Step 3 — Define feature columns
    # ------------------------------------------------------------------
    exclude_cols = strategy["exclude"]
    feature_cols = [c for c in df.columns if c not in exclude_cols]

    # Also add interaction columns to feature_cols if they exist
    for col in interaction_cols:
        if col not in feature_cols:
            feature_cols.append(col)

    # Identify categorical feature indices for CatBoost
    cat_in_features = [c for c in CAT_FEATURES if c in feature_cols]
    cat_feature_indices = [feature_cols.index(c) for c in cat_in_features]

    log.info(
        "Training with %d features (%d categorical): %s",
        len(feature_cols), len(cat_feature_indices), feature_cols,
    )

    # ------------------------------------------------------------------
    # Step 4 — Build training set and target (pseudo-label)
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

    X = df_train[feature_cols].copy()
    y = df_train["target"]

    # Encode categoricals for non-CatBoost algorithms
    if algorithm != "catboost":
        X = encode_categoricals_for_non_catboost(X, CAT_FEATURES, algorithm)

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
    # Step 5 — Train / Cross-validate
    # ------------------------------------------------------------------
    params = get_model_params(algorithm, strategy_name, args.use_optuna_params)
    gpu_used = "task_type" in params and params.get("task_type") == "GPU"
    if algorithm == "xgboost":
        gpu_used = params.get("device") == "cuda"

    cv_rmse_scores, cv_mae_scores = run_cross_validation(
        X, y, algorithm, params, cat_feature_indices,
        n_folds=CFG["modelling"]["cv_folds"],
        seed=CFG["modelling"]["random_seed"],
    )

    # ------------------------------------------------------------------
    # Step 6 — Train final model on full training data
    # ------------------------------------------------------------------
    final_model = train_final_model(X, y, algorithm, params, cat_feature_indices)

    # ------------------------------------------------------------------
    # Step 7 — Create run directory and save all artifacts
    # ------------------------------------------------------------------
    run_dir = os.path.join(RUNS_DIR, run_id)
    os.makedirs(run_dir, exist_ok=True)

    # Save model
    model_path = os.path.join(run_dir, "model.pkl")
    with open(model_path, "wb") as f:
        pickle.dump({"model": final_model, "feature_cols": feature_cols, "algorithm": algorithm}, f)
    log.info("Model saved -> %s", model_path)

    # Save CV results
    cv_results = {
        "cv_folds": CFG["modelling"]["cv_folds"],
        "cv_rmse_per_fold": [float(s) for s in cv_rmse_scores],
        "cv_mae_per_fold": [float(s) for s in cv_mae_scores],
        "cv_rmse_mean": float(np.mean(cv_rmse_scores)),
        "cv_rmse_std": float(np.std(cv_rmse_scores)),
        "cv_mae_mean": float(np.mean(cv_mae_scores)),
        "cv_mae_std": float(np.std(cv_mae_scores)),
        "n_features": len(feature_cols),
        "n_train_samples": len(X),
    }
    cv_path = os.path.join(run_dir, "cv_results.json")
    with open(cv_path, "w") as f:
        json.dump(cv_results, f, indent=2)
    log.info("CV results saved -> %s", cv_path)

    # Feature importance
    save_feature_importance(final_model, feature_cols, run_dir, algorithm)

    # Run config
    save_run_config(
        run_dir, run_id, algorithm, strategy_name, params,
        feature_cols, exclude_cols, args.notes, len(X),
    )

    # Per-run predictions
    # For non-catboost, we need to encode the full df's categoricals too
    df_for_pred = df.copy()
    if strategy["interaction_features"]:
        add_interaction_features(df_for_pred)
    save_predictions(final_model, df_for_pred, feature_cols, run_dir, algorithm)

    # ------------------------------------------------------------------
    # Step 8 — SHAP extraction (optional)
    # ------------------------------------------------------------------
    if args.shap:
        X_all = df_for_pred[feature_cols].copy()
        if algorithm != "catboost":
            X_all = encode_categoricals_for_non_catboost(X_all, CAT_FEATURES, algorithm)
        extract_shap_values(
            final_model, X_all, df["Outlet_ID"], algorithm, run_dir
        )

    # ------------------------------------------------------------------
    # Step 9 — Append to run registry
    # ------------------------------------------------------------------
    duration = time.time() - start_time

    append_to_registry(
        run_id=run_id,
        algorithm=algorithm,
        strategy=strategy_name,
        cv_rmse_scores=cv_rmse_scores,
        cv_mae_scores=cv_mae_scores,
        n_features=len(feature_cols),
        n_train=len(X),
        excluded_features=exclude_cols,
        notes=args.notes,
        gpu=gpu_used,
        duration=duration,
    )

    # ------------------------------------------------------------------
    # Assertions
    # ------------------------------------------------------------------
    assert os.path.exists(model_path), "model.pkl was not created"

    sample = X.head(5)
    preds = final_model.predict(sample)
    assert len(preds) == 5, f"Expected 5 predictions, got {len(preds)}"
    log.info("All assertions passed.")

    # ------------------------------------------------------------------
    # Summary
    # ------------------------------------------------------------------
    log.info("=" * 70)
    log.info("TRAINING SUMMARY")
    log.info("  Run ID               : %s", run_id)
    log.info("  Algorithm            : %s", algorithm)
    log.info("  Strategy             : %s", strategy_name)
    log.info("  Training samples     : %d", len(X))
    log.info("  Features             : %d (%d categorical)", len(feature_cols), len(cat_feature_indices))
    log.info("  CV RMSE              : %.2f +/- %.2f", np.mean(cv_rmse_scores), np.std(cv_rmse_scores))
    log.info("  CV MAE               : %.2f +/- %.2f", np.mean(cv_mae_scores), np.std(cv_mae_scores))
    log.info("  GPU used             : %s", gpu_used)
    log.info("  Artifacts saved to   : %s", run_dir)
    log.info("  Duration             : %.1f seconds", duration)
    log.info("=" * 70)
    log.info("TRAINING PIPELINE -- DONE")
    log.info("=" * 70)


if __name__ == "__main__":
    main()
