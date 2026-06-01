# Modelling Artifacts Directory

This directory stores the configurations and models produced by the machine learning training and optimization pipelines.

## Structure

### Runs and Tracking

- `runs/`: Contains time-stamped subdirectories for each execution of `train.py`.
  - Each run folder contains:
    - `model.pkl`: The trained model artifact and its feature list.
    - `feature_importance.png`: Visual plot of feature importances.
    - `cv_results.json`: Cross-validation scores and metrics.
    - `run_config.json`: The hyperparameter config and strategy parameters used.
- `run_registry.csv`: A centralized log tracking hyperparameters, features used, and cross-validation performance of every run.

### Final Selected Models

- `round1/`: Contains the final selected model for Round 1.
  - `catboost/`: CatBoost model run files.
- `round2/`: Contains the final selected models for Round 2.
  - `lightGBM/`: LightGBM model run files.
  - `random_forest/`: Random Forest model run files.
  - `xgboost/`: XGBoost model run files.

### Hyperparameter Tuning

- `optuna/`: Stores optimized hyperparameter configuration JSON files from Optuna study searches for various models and strategies.
