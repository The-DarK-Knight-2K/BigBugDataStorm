import os
import json
import logging
import argparse
import numpy as np
import pandas as pd
import optuna
import sys

# Add root directory to path to allow absolute imports
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

# Import needed functions and constants from our train script
from modelling.train import (
    STRATEGIES,
    CAT_FEATURES,
    GOLD_DIR,
    ARTIFACTS_DIR,
    add_interaction_features,
    run_cross_validation,
    get_model_params,
)

logging.basicConfig(level=logging.INFO, format="%(asctime)s | %(levelname)-8s | optuna_tune | %(message)s")
log = logging.getLogger(__name__)

# Suppress verbose info logs from train.py during trials
logging.getLogger("modelling.train").setLevel(logging.WARNING)
# Suppress XGBoost warnings
import warnings
warnings.filterwarnings("ignore")

def load_data(strategy_name: str, algorithm: str):
    strategy = STRATEGIES[strategy_name]
    input_path = os.path.join(GOLD_DIR, "master_features.parquet")
    df = pd.read_parquet(input_path)

    interaction_cols = []
    if strategy["interaction_features"]:
        interaction_cols = add_interaction_features(df)

    exclude_cols = strategy["exclude"]
    feature_cols = [c for c in df.columns if c not in exclude_cols]

    for col in interaction_cols:
        if col not in feature_cols:
            feature_cols.append(col)

    cat_in_features = [c for c in CAT_FEATURES if c in feature_cols]
    cat_feature_indices = [feature_cols.index(c) for c in cat_in_features]

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

    cat_cols = [c for c in CAT_FEATURES if c in X.columns]
    if algorithm in ["lightgbm", "catboost"]:
        for col in cat_cols:
            if col in X.columns:
                X[col] = X[col].astype("category")
    elif algorithm == "xgboost":
        for col in cat_cols:
            if col in X.columns:
                X[col] = X[col].astype("category").cat.codes

    return X, y, cat_feature_indices

def objective(trial, X, y, cat_feature_indices, algorithm):
    base_params = get_model_params(algorithm)
    
    if algorithm == "xgboost":
        params = base_params.copy()
        # Suppress verbose terminal output for xgboost within CV
        params["verbosity"] = 0 
        params.update({
            "learning_rate": trial.suggest_float("learning_rate", 0.01, 0.2, log=True),
            "max_depth": trial.suggest_int("max_depth", 3, 10),
            "subsample": trial.suggest_float("subsample", 0.5, 1.0),
            "colsample_bytree": trial.suggest_float("colsample_bytree", 0.5, 1.0),
            "reg_alpha": trial.suggest_float("reg_alpha", 1e-3, 10.0, log=True),
            "reg_lambda": trial.suggest_float("reg_lambda", 1e-3, 10.0, log=True),
            "n_estimators": trial.suggest_int("n_estimators", 500, 1500, step=100),
        })
    elif algorithm == "catboost":
        params = base_params.copy()
        params.update({
            "learning_rate": trial.suggest_float("learning_rate", 0.01, 0.2, log=True),
            "depth": trial.suggest_int("depth", 3, 10),
            "l2_leaf_reg": trial.suggest_float("l2_leaf_reg", 1e-3, 10.0, log=True),
            "subsample": trial.suggest_float("subsample", 0.5, 1.0),
        })
    else:
        raise ValueError(f"Algorithm {algorithm} not supported for tuning yet.")
        
    cv_rmse, cv_mae = run_cross_validation(
        X, y, algorithm, params, cat_feature_indices, n_folds=5, seed=42
    )
    
    mean_rmse = np.mean(cv_rmse)
    return mean_rmse

def parse_args():
    parser = argparse.ArgumentParser()
    parser.add_argument("--strategy", type=str, default="strategyC", choices=list(STRATEGIES.keys()))
    parser.add_argument("--algorithm", type=str, default="xgboost", choices=["catboost", "xgboost", "lightgbm"])
    parser.add_argument("--n-trials", type=int, default=50)
    return parser.parse_args()

if __name__ == "__main__":
    args = parse_args()
    log.info(f"Starting Optuna tuning for {args.algorithm} using {args.strategy} for {args.n_trials} trials.")
    
    X, y, cat_feature_indices = load_data(args.strategy, args.algorithm)
    
    study = optuna.create_study(direction="minimize")
    study.optimize(lambda trial: objective(trial, X, y, cat_feature_indices, args.algorithm), n_trials=args.n_trials)
    
    log.info(f"Best RMSE: {study.best_value}")
    log.info(f"Best Params: {study.best_params}")
    
    optuna_dir = os.path.join(ARTIFACTS_DIR, "optuna")
    os.makedirs(optuna_dir, exist_ok=True)
    
    out_path = os.path.join(optuna_dir, f"best_params_{args.algorithm}_{args.strategy}.json")
    with open(out_path, "w") as f:
        json.dump(study.best_params, f, indent=4)
        
    log.info(f"Saved best params to {out_path}")
