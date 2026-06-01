# SPEC: run_pipeline.py

## Purpose

End-to-end orchestrator that runs all pipeline stages in the correct order with dependency enforcement, timing, global error handling, and final validation. Running this single script should reproduce the entire pipeline from raw CSVs to the final competition submission CSVs.

## Layer
Orchestration (`pipeline/run_pipeline.py`)

## Inputs
All raw CSV files in `Data/Raw/` (via the Bronze ingest step).

## Outputs
- `outputs/bigbug_predictions.csv` (via the Predict step).
- `outputs/bigbug_budget_allocations.csv` (via the Optimization step).

---

## Execution order (strict — do not reorder)

```text
Stage 0  → Bronze: ingest
Stage 1  → Silver: clean_outlets          
Stage 2  → Silver: clean_coordinates      
Stage 3  → Silver: clean_transactions     
Stage 4  → Silver: clean_seasonality      
Stage 5  → Silver: clean_holidays         
Stage 6  → Gold:   scrape_poi_raw         (Optional, via --run-scraping)
Stage 7  → Gold:   build_poi_features   
Stage 8  → Gold:   build_sales_features   
Stage 9  → Gold:   build_gravity_features   
Stage 10 → Gold:   build_catchment_features   
Stage 11 → Gold:   build_cooler_features   
Stage 12 → Gold:   build_spatial_cluster_features   
Stage 13 → Gold:   build_master_features  
Stage 14 → Model:  baseline               
Stage 15 → Model:  train & ensemble       (Optional, via --train-models, uses round2 fallback otherwise)
Stage 16 → Model:  predict                
Stage 17 → Optimization: optimise_budget
```

---

## CLI Flags

```python
parser.add_argument("--run-scraping", action="store_true", help="Run POI Scraping (Time consuming)")
parser.add_argument("--tune-hyperparameters", action="store_true", help="Run Optuna Hyperparameter Tuning")
parser.add_argument("--train-models", action="store_true", help="Train new models instead of using pre-trained ones")
parser.add_argument("--start-from", type=int, default=0, help="Start from a specific stage number (0-17)")
```

## Example usage

```bash
# Fast Path (Default): Skips POI scraping and model training, uses cached/pre-trained models.
python pipeline/run_pipeline.py

# Full Run: Forces live POI scraping and trains fresh models
python pipeline/run_pipeline.py --run-scraping --train-models

# Resume execution from a specific stage
python pipeline/run_pipeline.py --start-from 7
```

---

## Logic Overview

1. **Preflight Checks:** If `--start-from` is 0, the script verifies all 5 raw CSV files exist in `Data/Raw/` and ensures all output directories exist.
2. **Global Error Handling:** Each stage is executed via `subprocess.run()`. If a script exits with a non-zero return code, the orchestrator logs the exact failing command to `outputs/pipeline.log`, prints instructions on how to resume using `--start-from`, and immediately halts.
3. **Dynamic Model Resolution:** If `--train-models` is provided, it iterates through XGBoost, LightGBM, and Random Forest, calling `train.py` with `--shap`. It dynamically pulls the new `run_id`s from `run_registry.csv` and passes them to `ensemble.py`. If false, it falls back to hardcoded paths for the round2 legacy models (`../round2/xgboost`, etc.).
4. **Final Validation:** After optimization, the orchestrator automatically loads both output CSVs and asserts their structural integrity (row counts, required columns, lack of nulls, and positive LKR bounds).
