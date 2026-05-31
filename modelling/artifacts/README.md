# Modelling Artifacts Directory

This directory stores the output of the machine learning training pipeline.

## Structure
- `runs/`: Directory containing time-stamped subdirectories for each execution of `train.py` (Run Tracking).
  - Each run folder contains:
    - `model.pkl`: The trained model artifact and feature list.
    - `feature_importance.png`: Visual plot of feature importances.
    - `cv_results.json`: Cross-validation scores and metrics.
    - `run_config.json`: The hyperparameter config and strategy parameters used.
- `run_registry.csv`: A centralized log tracking the hyperparameters, features used, and cross-validation performance of every run.
