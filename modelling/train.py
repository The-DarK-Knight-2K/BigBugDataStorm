"""
Train LightGBM model to predict outlet-level maximum monthly purchase potential.

Layer  : Modelling
Inputs : data/gold/master_features.parquet
Outputs: modelling/artifacts/model.pkl, modelling/artifacts/feature_importance.png, modelling/artifacts/cv_results.json
"""

import json
import logging
import pickle
import sys
from pathlib import Path

import lightgbm as lgb
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
import yaml
from sklearn.model_selection import KFold

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
ARTIFACTS = Path(__file__).parent / "artifacts"
EXCLUDE_COLS = [
    "Outlet_ID", "Outlet_Size", "Outlet_Type", "province",
    "seasonality_jan_2026", "distributor_id",
    "target",
]


def load_data() -> pd.DataFrame:
    if not MASTER_FEATURES_PATH.exists():
        log.error("Cannot proceed: missing master_features file: %s", MASTER_FEATURES_PATH)
        sys.exit(1)

    df = pd.read_parquet(MASTER_FEATURES_PATH)
    log.info("Loaded %d rows from master_features", len(df))
    return df


def select_features(df: pd.DataFrame) -> list[str]:
    feature_cols = [c for c in df.columns if c not in EXCLUDE_COLS]

    non_numeric = df[feature_cols].select_dtypes(exclude=["number"]).columns.tolist()
    if non_numeric:
        log.error("Non-numeric feature columns found: %s", non_numeric)
        sys.exit(1)

    log.info("Training with %d features", len(feature_cols))
    return feature_cols


def build_training_set(df: pd.DataFrame) -> tuple[pd.DataFrame, list[str]]:
    n_no_history = (df["has_transaction_history"] == False).sum()
    df_train = df[df["has_transaction_history"] == True].copy()

    df_train["target"] = (
        df_train["hist_p90_monthly"]
        * df_train["seasonality_multiplier_jan_2026"]
        * (df_train["jan_2026_trading_days"] / 22.0)
    )

    log.info(
        "Training set: %d outlets (excluded %d with no transaction history)",
        len(df_train),
        n_no_history,
    )
    log.info(
        "Training target — min: %.2f, median: %.2f, max: %.2f",
        df_train["target"].min(),
        df_train["target"].median(),
        df_train["target"].max(),
    )
    return df_train, [c for c in df_train.columns if c not in EXCLUDE_COLS]


def cross_validation(X: pd.DataFrame, y: pd.Series) -> tuple[list[float], list[float]]:
    cv_folds = CFG.get("modelling", {}).get("cv_folds", 5)
    random_seed = CFG.get("modelling", {}).get("random_seed", 42)
    lgbm_params = CFG.get("modelling", {}).get("lgbm_params", {})

    kf = KFold(n_splits=cv_folds, shuffle=True, random_state=random_seed)
    cv_rmse_scores = []
    cv_mae_scores = []

    log.info("Starting %d-fold cross-validation", cv_folds)

    for fold, (train_idx, val_idx) in enumerate(kf.split(X), 1):
        X_tr, X_val = X.iloc[train_idx], X.iloc[val_idx]
        y_tr, y_val = y.iloc[train_idx], y.iloc[val_idx]

        model = lgb.LGBMRegressor(**lgbm_params, random_state=random_seed)
        model.fit(
            X_tr,
            y_tr,
            eval_set=[(X_val, y_val)],
            callbacks=[
                lgb.early_stopping(50, verbose=False),
                lgb.log_evaluation(100),
            ],
        )

        preds = model.predict(X_val)
        rmse = np.sqrt(np.mean((preds - y_val) ** 2))
        mae = np.mean(np.abs(preds - y_val))
        cv_rmse_scores.append(rmse)
        cv_mae_scores.append(mae)
        log.info("Fold %d — RMSE: %.2f  MAE: %.2f", fold, rmse, mae)

    log.info("CV RMSE: %.2f ± %.2f", np.mean(cv_rmse_scores), np.std(cv_rmse_scores))
    log.info("CV MAE : %.2f ± %.2f", np.mean(cv_mae_scores), np.std(cv_mae_scores))

    return cv_rmse_scores, cv_mae_scores


def train_final_model(X: pd.DataFrame, y: pd.Series) -> object:
    random_seed = CFG.get("modelling", {}).get("random_seed", 42)
    lgbm_params = CFG.get("modelling", {}).get("lgbm_params", {})

    final_model = lgb.LGBMRegressor(**lgbm_params, random_state=random_seed)
    final_model.fit(X, y)
    log.info("Final model trained on %d samples", len(X))

    return final_model


def save_model(model: object, feature_cols: list[str]) -> None:
    ARTIFACTS.mkdir(parents=True, exist_ok=True)
    model_path = ARTIFACTS / "model.pkl"

    with open(model_path, "wb") as f:
        pickle.dump({"model": model, "feature_cols": feature_cols}, f)

    log.info("Model saved → modelling/artifacts/model.pkl")


def save_feature_importance(model: object, feature_cols: list[str]) -> None:
    importance_df = pd.DataFrame({
        "feature": feature_cols,
        "importance": model.feature_importances_,
    }).sort_values("importance", ascending=False).head(30)

    fig, ax = plt.subplots(figsize=(10, 12))
    ax.barh(importance_df["feature"][::-1], importance_df["importance"][::-1])
    ax.set_xlabel("Feature Importance (gain)")
    ax.set_title("Top 30 Feature Importances — LightGBM")
    plt.tight_layout()
    plt.savefig(ARTIFACTS / "feature_importance.png", dpi=150)
    plt.close()
    log.info("Feature importance plot saved → modelling/artifacts/feature_importance.png")


def save_cv_results(cv_rmse_scores: list[float], cv_mae_scores: list[float], n_features: int, n_train: int) -> None:
    cv_folds = CFG.get("modelling", {}).get("cv_folds", 5)
    cv_results = {
        "cv_folds": cv_folds,
        "cv_rmse_mean": float(np.mean(cv_rmse_scores)),
        "cv_rmse_std": float(np.std(cv_rmse_scores)),
        "cv_mae_mean": float(np.mean(cv_mae_scores)),
        "cv_mae_std": float(np.std(cv_mae_scores)),
        "n_features": n_features,
        "n_train_samples": n_train,
    }

    with open(ARTIFACTS / "cv_results.json", "w") as f:
        json.dump(cv_results, f, indent=2)

    log.info("CV results saved → modelling/artifacts/cv_results.json")


def validate_model(model: object, X: pd.DataFrame) -> None:
    model_path = ARTIFACTS / "model.pkl"
    if not model_path.exists():
        log.error("Model file not found: %s", model_path)
        sys.exit(1)

    sample = X.head(5)
    preds = model.predict(sample)

    if len(preds) != 5:
        log.error("Expected 5 predictions, got %d", len(preds))
        sys.exit(1)

    if any(p <= 0 for p in preds):
        log.error("Model predicting non-positive values: %s", preds)
        sys.exit(1)

    log.info("Model validation passed")


def main() -> None:
    log.info("Starting model training")
    df = load_data()
    feature_cols = select_features(df)
    df_train, feature_cols = build_training_set(df)

    X = df_train[feature_cols]
    y = df_train["target"]

    cv_rmse_scores, cv_mae_scores = cross_validation(X, y)
    final_model = train_final_model(X, y)

    save_model(final_model, feature_cols)
    save_feature_importance(final_model, feature_cols)
    save_cv_results(cv_rmse_scores, cv_mae_scores, len(feature_cols), len(X))

    validate_model(final_model, X)
    log.info("Model training complete")


if __name__ == "__main__":
    main()
