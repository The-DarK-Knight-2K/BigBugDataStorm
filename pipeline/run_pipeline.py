import argparse
import subprocess
import sys
import os
from datetime import datetime
import pandas as pd

def setup_logger():
    # Append to pipeline.log as a global orchestrator log
    base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    outputs_dir = os.path.join(base_dir, 'outputs')
    os.makedirs(outputs_dir, exist_ok=True)
    log_file = os.path.join(outputs_dir, 'pipeline.log')
    return log_file, base_dir

def preflight_checks(base_dir, log_file):
    raw_dir = os.path.join(base_dir, 'Data', 'Raw')
    raw_files = [
        'transactions.csv',
        'outlets.csv',
        'outlet_coordinates.csv',
        'seasonality.csv',
        'holidays.csv'
    ]
    for fname in raw_files:
        fpath = os.path.join(raw_dir, fname)
        if not os.path.exists(fpath):
            msg = f"\n[ERROR] Missing raw file: {fpath}\nPlace all provided CSV files in Data/Raw/ before running.\n"
            print(msg)
            with open(log_file, 'a', encoding='utf-8') as f:
                f.write(msg)
            sys.exit(1)

    directories = [
        'Data/Bronze', 'Data/Silver', 'Data/Gold', 'Data/Quarantine', 
        'outputs', 'modelling/artifacts'
    ]
    for d in directories:
        os.makedirs(os.path.join(base_dir, d.replace('/', os.sep)), exist_ok=True)

def run_cmd(cmd, env, log_file, stage_num, start_from):
    if stage_num < start_from:
        msg = f"[{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}] ORCHESTRATOR | SKIPPED Stage {stage_num}: {' '.join(cmd)}\n"
        print(msg, end='')
        return True
        
    cmd_str = ' '.join(cmd)
    msg = f"\n[{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}] ORCHESTRATOR | RUNNING Stage {stage_num}: {cmd_str}\n"
    print(msg, end='')
    
    if log_file:
        with open(log_file, 'a', encoding='utf-8') as f:
            f.write(msg)
            
    result = subprocess.run(cmd, env=env, text=True)
    
    if result.returncode != 0:
        err_msg = f"\n[{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}] ORCHESTRATOR | ERROR: Command failed with exit code {result.returncode} at Stage {stage_num}: {cmd_str}\n"
        err_msg += f"Fix the error and re-run with --start-from {stage_num}\n"
        print(err_msg, end='')
        if log_file:
            with open(log_file, 'a', encoding='utf-8') as f:
                f.write(err_msg)
        sys.exit(result.returncode)
    return True

def validate_submission(base_dir, log_file):
    # Validating Predictions
    pred_path = os.path.join(base_dir, 'outputs', 'bigbug_predictions.csv')
    if os.path.exists(pred_path):
        sub = pd.read_csv(pred_path)
        assert len(sub) == 20000, f"Expected 20000 rows in predictions, got {len(sub)}"
        assert "Outlet_ID" in sub.columns
        assert "Maximum_Monthly_Liters" in sub.columns
        assert sub["Outlet_ID"].duplicated().sum() == 0
        assert sub["Maximum_Monthly_Liters"].isnull().sum() == 0
        assert (sub["Maximum_Monthly_Liters"] > 0).all()
        msg = f"[{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}] ORCHESTRATOR | VALIDATION PASSED: bigbug_predictions.csv\n"
        print(msg, end='')
        with open(log_file, 'a', encoding='utf-8') as f:
            f.write(msg)

    # Validating Budget
    budget_path = os.path.join(base_dir, 'outputs', 'bigbug_budget_allocations.csv')
    if os.path.exists(budget_path):
        sub = pd.read_csv(budget_path)
        # Using loosely bounded threshold to account for slight variation in exact rows filtered
        assert len(sub) > 8500 and len(sub) < 10000, f"Expected ~9000 rows in budget allocations, got {len(sub)}"
        assert "Outlet_ID" in sub.columns
        assert "Trade_Spend_Allocation_LKR" in sub.columns
        msg = f"[{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}] ORCHESTRATOR | VALIDATION PASSED: bigbug_budget_allocations.csv\n"
        print(msg, end='')
        with open(log_file, 'a', encoding='utf-8') as f:
            f.write(msg)

def main():
    parser = argparse.ArgumentParser(description="End-to-End Pipeline Orchestrator")
    parser.add_argument("--run-scraping", action="store_true", help="Run POI Scraping (Time consuming)")
    parser.add_argument("--tune-hyperparameters", action="store_true", help="Run Optuna Hyperparameter Tuning")
    parser.add_argument("--train-models", action="store_true", help="Train new models instead of using pre-trained ones")
    parser.add_argument("--start-from", type=int, default=0, help="Start from a specific stage number (0-15)")
    args = parser.parse_args()

    log_file, base_dir = setup_logger()
    
    # Pre-flight
    if args.start_from == 0:
        preflight_checks(base_dir, log_file)
    
    env = os.environ.copy()
    env["PYTHONPATH"] = base_dir

    with open(log_file, 'a', encoding='utf-8') as f:
        f.write("\n" + "="*80 + "\n")
        f.write(f"PIPELINE ORCHESTRATION STARTED AT {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")
        f.write(f"Flags: scraping={args.run_scraping}, tune={args.tune_hyperparameters}, train={args.train_models}, start_from={args.start_from}\n")
        f.write("="*80 + "\n")

    stage = 0

    # Stage 0: Bronze Layer
    run_cmd([sys.executable, "pipeline/bronze/ingest.py"], env, log_file, stage, args.start_from)
    stage += 1

    # Stage 1-5: Silver Layer
    silver_scripts = [
        "clean_outlets.py", "clean_coordinates.py", "clean_transactions.py", 
        "clean_seasonality.py", "clean_holidays.py"
    ]
    for script in silver_scripts:
        run_cmd([sys.executable, f"pipeline/silver/{script}"], env, log_file, stage, args.start_from)
        stage += 1

    # Stage 6: POI Scraping
    if args.run_scraping:
        run_cmd([sys.executable, "pipeline/gold/scrape_poi_raw.py"], env, log_file, stage, args.start_from)
    else:
        if stage >= args.start_from:
            msg = f"[{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}] ORCHESTRATOR | SKIPPING Stage {stage}: POI Scraping (using cached data).\n"
            print(msg, end='')
            with open(log_file, 'a', encoding='utf-8') as f:
                f.write(msg)
    stage += 1

    # Stage 7-13: Gold Layer
    gold_scripts = [
        "build_poi_features.py", "build_sales_features.py", "build_gravity_features.py",
        "build_catchment_features.py", "build_cooler_features.py",
        "build_spatial_cluster_features.py", "build_master_features.py"
    ]
    for script in gold_scripts:
        run_cmd([sys.executable, f"pipeline/gold/{script}"], env, log_file, stage, args.start_from)
        stage += 1

    # Stage 14: Modelling Baseline
    run_cmd([sys.executable, "modelling/baseline.py"], env, log_file, stage, args.start_from)
    stage += 1

    # Stage 15: Modelling Train & Ensemble
    run_ids = ["../round2/xgboost", "../round2/lightGBM", "../round2/random_forest"]
    
    if stage >= args.start_from:
        if args.train_models:
            if args.tune_hyperparameters:
                run_cmd([sys.executable, "modelling/optuna_tune.py"], env, log_file, stage, args.start_from)
            
            registry_path = os.path.join(base_dir, "modelling", "artifacts", "run_registry.csv")
            algorithms = ["xgboost", "lightgbm", "randomforest"]
            new_run_ids = []
            
            for algo in algorithms:
                cmd = [sys.executable, "modelling/train.py", "--algorithm", algo, "--strategy", "strategyA_gravity_only", "--shap"]
                run_cmd(cmd, env, log_file, stage, args.start_from)
                df_reg = pd.read_csv(registry_path)
                new_run_ids.append(df_reg.iloc[-1]['run_id'])
                
            run_ids = new_run_ids
        else:
            msg = f"[{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}] ORCHESTRATOR | SKIPPING: Model Training (using pre-trained Round 2 models).\n"
            print(msg, end='')
            with open(log_file, 'a', encoding='utf-8') as f:
                f.write(msg)
                
        # Ensemble predictions using the resolved run_ids
        ensemble_cmd = [sys.executable, "modelling/ensemble.py", "--run-ids"] + run_ids + ["--weights", "0.4", "0.4", "0.2"]
        run_cmd(ensemble_cmd, env, log_file, stage, args.start_from)
    stage += 1

    # Stage 16: Predict
    predict_cmd = [sys.executable, "modelling/predict.py", "--predictions-csv", "modelling/artifacts/runs/ensemble_predictions.csv"]
    run_cmd(predict_cmd, env, log_file, stage, args.start_from)
    stage += 1

    # Stage 17: Budget Optimization
    run_cmd([sys.executable, "pipeline/optimizations/optimise_budget.py"], env, log_file, stage, args.start_from)
    stage += 1

    # Final Validation
    if args.start_from <= stage:
        validate_submission(base_dir, log_file)

    success_msg = f"\n[{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}] ORCHESTRATOR | SUCCESS: Pipeline execution completed.\n"
    print(success_msg, end='')
    with open(log_file, 'a', encoding='utf-8') as f:
        f.write(success_msg)
        f.write("="*80 + "\n\n")

if __name__ == "__main__":
    main()
