import argparse
import subprocess
import sys
import os
from datetime import datetime

def setup_logger():
    # Append to pipeline.log as a global orchestrator log
    # The individual scripts will also log to this file via utils.logger
    base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    outputs_dir = os.path.join(base_dir, 'outputs')
    os.makedirs(outputs_dir, exist_ok=True)
    log_file = os.path.join(outputs_dir, 'pipeline.log')
    return log_file

def run_cmd(cmd, env=None, log_file=None):
    cmd_str = ' '.join(cmd)
    msg = f"\n[{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}] ORCHESTRATOR | RUNNING: {cmd_str}\n"
    print(msg, end='')
    
    if log_file:
        with open(log_file, 'a', encoding='utf-8') as f:
            f.write(msg)
            
    result = subprocess.run(cmd, env=env, text=True)
    
    if result.returncode != 0:
        err_msg = f"\n[{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}] ORCHESTRATOR | ERROR: Command failed with exit code {result.returncode}: {cmd_str}\n"
        print(err_msg, end='')
        if log_file:
            with open(log_file, 'a', encoding='utf-8') as f:
                f.write(err_msg)
        sys.exit(result.returncode)

def main():
    parser = argparse.ArgumentParser(description="End-to-End Pipeline Orchestrator")
    parser.add_argument("--run-scraping", action="store_true", help="Run POI Scraping (Time consuming)")
    parser.add_argument("--tune-hyperparameters", action="store_true", help="Run Optuna Hyperparameter Tuning")
    parser.add_argument("--train-models", action="store_true", help="Train new models instead of using pre-trained ones")
    args = parser.parse_args()

    log_file = setup_logger()
    
    # Ensure PYTHONPATH is set to the project root
    env = os.environ.copy()
    project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
    env["PYTHONPATH"] = project_root

    with open(log_file, 'a', encoding='utf-8') as f:
        f.write("\n" + "="*80 + "\n")
        f.write(f"PIPELINE ORCHESTRATION STARTED AT {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")
        f.write(f"Flags: scraping={args.run_scraping}, tune={args.tune_hyperparameters}, train={args.train_models}\n")
        f.write("="*80 + "\n")

    # 1. Bronze Layer
    run_cmd([sys.executable, "pipeline/bronze/ingest.py"], env=env, log_file=log_file)

    # 2. Silver Layer
    silver_scripts = [
        "clean_outlets.py", "clean_coordinates.py", "clean_transactions.py", 
        "clean_seasonality.py", "clean_holidays.py"
    ]
    for script in silver_scripts:
        run_cmd([sys.executable, f"pipeline/silver/{script}"], env=env, log_file=log_file)

    # 3. Gold Layer
    if args.run_scraping:
        run_cmd([sys.executable, "pipeline/gold/scrape_poi_raw.py"], env=env, log_file=log_file)
    else:
        msg = f"[{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}] ORCHESTRATOR | SKIPPING: POI Scraping (using cached data).\n"
        print(msg, end='')
        with open(log_file, 'a', encoding='utf-8') as f:
            f.write(msg)

    gold_scripts = [
        "build_poi_features.py", "build_sales_features.py", "build_gravity_features.py",
        "build_catchment_features.py", "build_cooler_features.py",
        "build_spatial_cluster_features.py", "build_master_features.py"
    ]
    for script in gold_scripts:
        run_cmd([sys.executable, f"pipeline/gold/{script}"], env=env, log_file=log_file)

    # 4. Modelling Baseline
    run_cmd([sys.executable, "modelling/baseline.py"], env=env, log_file=log_file)

    # 5. Modelling (Training or using pre-trained)
    run_ids = ["../round2/xgboost", "../round2/lightGBM", "../round2/random_forest"]

    if args.train_models:
        if args.tune_hyperparameters:
            run_cmd([sys.executable, "modelling/optuna_tune.py"], env=env, log_file=log_file)
        
        import pandas as pd
        registry_path = os.path.join(project_root, "modelling", "artifacts", "run_registry.csv")
        
        algorithms = ["xgboost", "lightgbm", "randomforest"]
        new_run_ids = []
        for algo in algorithms:
            cmd = [sys.executable, "modelling/train.py", "--algorithm", algo, "--strategy", "strategyA_gravity_only"]
            run_cmd(cmd, env=env, log_file=log_file)
            
            # Read last row of registry to get the run ID
            df_reg = pd.read_csv(registry_path)
            new_run_id = df_reg.iloc[-1]['run_id']
            new_run_ids.append(new_run_id)
            
        run_ids = new_run_ids
    else:
        msg = f"[{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}] ORCHESTRATOR | SKIPPING: Model Training (using pre-trained Round 2 models).\n"
        print(msg, end='')
        with open(log_file, 'a', encoding='utf-8') as f:
            f.write(msg)

    # 6. Ensemble
    # We pass the resolved run_ids (either new runs or existing round2 models)
    ensemble_cmd = [sys.executable, "modelling/ensemble.py", "--run-ids"] + run_ids + ["--weights", "0.4", "0.4", "0.2"]
    run_cmd(ensemble_cmd, env=env, log_file=log_file)

    # 7. Predict
    predict_cmd = [sys.executable, "modelling/predict.py", "--predictions-csv", "modelling/artifacts/runs/ensemble_predictions.csv"]
    run_cmd(predict_cmd, env=env, log_file=log_file)

    # 8. Budget Optimization
    run_cmd([sys.executable, "pipeline/optimizations/optimise_budget.py"], env=env, log_file=log_file)

    success_msg = f"\n[{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}] ORCHESTRATOR | SUCCESS: Pipeline execution completed.\n"
    print(success_msg, end='')
    with open(log_file, 'a', encoding='utf-8') as f:
        f.write(success_msg)
        f.write("="*80 + "\n\n")

if __name__ == "__main__":
    main()
