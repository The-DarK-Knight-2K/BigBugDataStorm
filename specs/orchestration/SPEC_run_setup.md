# Round 2: Model Run Setup

The pipeline's modelling architecture has been significantly upgraded for Round 2 to support organized experimentation, multiple algorithms, GPU acceleration, and dynamic feature engineering.

## Execution

The scripts are located in the `modelling/` directory. The primary entry points are `train.py` and `predict.py`.

### 1. Training a Model
The `train.py` script now accepts flags to select the modeling strategy and algorithm.

```bash
python modelling/train.py --strategy <STRATEGY> --algorithm <ALGORITHM> [--shap] [--notes "text"]
```

**Available Strategies:**
- `round1_baseline`: Keeps all features, including historical target leakages (replicates Round 1 logic on the new feature set).
- `strategyA`: Removes target leakages (`hist_max_monthly`, `jan_avg_volume`, etc.) forcing the model to rely on structural and spatial features.
- `strategyC`: Same as `strategyA` but automatically generates interaction features (e.g., `gravity_x_cooler`).
- `strategyA_gravity_only`: Strategy A minus all flat POI counts.
- `strategyA_flat_only`: Strategy A minus all gravity scores.

**Available Algorithms:**
- `lightgbm` (Default for SHAP, highly recommended, handles categorical natively)
- `xgboost`
- `lightgbm`

**Example:**
```bash
python modelling/train.py --strategy strategyA --algorithm lightgbm --shap --notes "LightGBM with Strategy A to extract SHAP values"
```

### 2. Run Tracking
Every time you execute `train.py`, a new run ID is generated (e.g., `run_20260531_143000_lightgbm_strategyA`).
All artifacts for that run are saved into `modelling/artifacts/runs/<run_id>/`:
- `model.pkl`: The serialized model.
- `cv_results.json`: Cross-validation scores (RMSE, MAE).
- `feature_importance.png` / `feature_importance.csv`: Top driving features.
- `run_config.json`: A complete record of hyperparameters and feature exclusions for reproducibility.
- `predictions.csv`: The raw model predictions.

A summary of every run is appended to the master registry at `modelling/artifacts/run_registry.csv`.

### 3. Making Final Predictions
To generate the final blended submission CSV (`outputs/teamname_predictions.csv`), you must specify which run to use:

```bash
python modelling/predict.py --run-id <RUN_ID>
```

**Example:**
```bash
python modelling/predict.py --run-id run_20260531_143000_lightgbm_strategyA
```
*(If `--run-id` is omitted, the script attempts to load a legacy `model.pkl` from the root of the `artifacts/` folder, which is not recommended for Round 2).*

> **Note:** The recommended way to run inference is now via `pipeline/run_pipeline.py`. By default, the orchestrator bypasses individual `predict.py` calls and uses an ensemble of the `round2` models automatically.

---

## Setup Details

### GPU Enablement
If using LightGBM or XGBoost, GPU training is configured by default via `config.yaml`.
For LightGBM, ensure `device_type: "gpu"` is present under `modelling.lightgbm_params`.

### SHAP Values
The XAI pipeline in Phase 3 requires SHAP values. By passing `--shap` to `train.py`, a `TreeExplainer` will compute cell-by-cell drivers for all 20,000 outlets and export them to `Data/Gold/shap_values.parquet`.

### Baseline Independence
The baseline logic (`modelling/baseline.py`) now computes POI uplift using the new `composite_gravity_score` instead of `footfall_score`, ensuring parity with the gravity model feature logic developed in Round 2 Phase 1.
