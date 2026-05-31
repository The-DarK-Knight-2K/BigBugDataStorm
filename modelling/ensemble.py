import os
import glob
import pandas as pd
import argparse
import logging

logging.basicConfig(level=logging.INFO, format="%(asctime)s | %(levelname)-8s | ensemble | %(message)s")
log = logging.getLogger(__name__)

def main():
    parser = argparse.ArgumentParser(description="Ensemble predictions from multiple models.")
    parser.add_argument("--run-ids", nargs="+", required=True, help="List of run_ids to ensemble")
    parser.add_argument("--weights", nargs="+", type=float, help="Optional weights for each model")
    parser.add_argument("--output", type=str, default="ensemble_predictions.csv", help="Output file name")
    args = parser.parse_args()

    if args.weights and len(args.weights) != len(args.run_ids):
        raise ValueError("Number of weights must match the number of run_ids.")

    weights = args.weights if args.weights else [1.0 / len(args.run_ids)] * len(args.run_ids)
    
    current_dir = os.path.dirname(os.path.abspath(__file__))
    runs_dir = os.path.join(current_dir, "artifacts", "runs")

    dfs = []
    for run_id, weight in zip(args.run_ids, weights):
        pred_path = os.path.join(runs_dir, run_id, "predictions.csv")
        if not os.path.exists(pred_path):
            # Try finding a matching run_id if it's a partial match (e.g., prefix)
            matched_dirs = [d for d in os.listdir(runs_dir) if run_id in d]
            if len(matched_dirs) == 1:
                pred_path = os.path.join(runs_dir, matched_dirs[0], "predictions.csv")
            elif len(matched_dirs) > 1:
                raise ValueError(f"Multiple directories matched for run_id {run_id}. Please be more specific.")
            else:
                raise FileNotFoundError(f"Predictions file not found for run_id: {run_id}")
        
        log.info(f"Loading predictions from {pred_path} with weight {weight:.2f}")
        df = pd.read_csv(pred_path)
        
        # Ensure 'Outlet_ID' and 'model_prediction' exist
        if 'Outlet_ID' not in df.columns or 'model_prediction' not in df.columns:
            raise ValueError(f"Required columns missing in {pred_path}")
            
        dfs.append((df, weight))

    # Base dataframe to store results
    base_df = dfs[0][0][['Outlet_ID']].copy()
    base_df['model_prediction'] = 0.0

    for df, weight in dfs:
        # Align rows by Outlet_ID (just in case they are out of order, though they shouldn't be)
        df_aligned = base_df[['Outlet_ID']].merge(df[['Outlet_ID', 'model_prediction']], on='Outlet_ID', how='left')
        base_df['model_prediction'] += df_aligned['model_prediction'] * weight

    base_df['model_prediction'] = base_df['model_prediction'].clip(lower=0).round(2)
    
    out_path = os.path.join(runs_dir, args.output)
    base_df.to_csv(out_path, index=False)
    
    log.info(f"Ensemble completed. Saved to {out_path}")
    log.info(f"Ensemble Stats - Min: {base_df['model_prediction'].min():.2f}, Median: {base_df['model_prediction'].median():.2f}, Max: {base_df['model_prediction'].max():.2f}")

if __name__ == "__main__":
    main()
