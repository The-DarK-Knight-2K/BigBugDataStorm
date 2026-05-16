"""
Generate the final submission CSV by blending CatBoost model predictions with
the statistical baseline floor.

The final prediction for every outlet is max(model_prediction, baseline),
ensuring we never predict below the statistically grounded floor.

Layer  : Modelling
Inputs : data/Gold/master_features.parquet
         modelling/artifacts/model.pkl
         data/Gold/baseline_predictions.parquet
Outputs: outputs/bigbug_predictions.csv
         outputs/prediction_diagnostics.csv
"""

import os
import pickle
import sys
import time

import numpy as np
import pandas as pd
import yaml

# ---------------------------------------------------------------------------
# Path setup (matches existing baseline.py conventions)
# ---------------------------------------------------------------------------
CURRENT_DIR = os.path.dirname(os.path.abspath(__file__))
ROOT_DIR = os.path.dirname(CURRENT_DIR)

# Add pipeline dir to path so we can import the shared logger
PIPELINE_DIR = os.path.join(ROOT_DIR, "pipeline")
if PIPELINE_DIR not in sys.path:
    sys.path.insert(0, PIPELINE_DIR)

from utils.logger import setup_logger

log = setup_logger("predict")

GOLD_DIR = os.path.join(ROOT_DIR, "Data", "Gold")
ARTIFACTS_DIR = os.path.join(CURRENT_DIR, "artifacts")
OUTPUTS_DIR = os.path.join(ROOT_DIR, "outputs")

# ---------------------------------------------------------------------------
# Load config
# ---------------------------------------------------------------------------
with open(os.path.join(ROOT_DIR, "config.yaml"), "r") as f:
    CFG = yaml.safe_load(f)


# ---------------------------------------------------------------------------
# Main prediction pipeline
# ---------------------------------------------------------------------------

def main() -> None:
    start_time = time.time()
    log.info("=" * 70)
    log.info("PREDICTION PIPELINE — START")
    log.info("=" * 70)

    # ------------------------------------------------------------------
    # Step 1 — Load inputs
    # ------------------------------------------------------------------
    df = pd.read_parquet(os.path.join(GOLD_DIR, "master_features.parquet"))
    log.info("Loaded master features: %d rows", len(df))

    model_path = os.path.join(ARTIFACTS_DIR, "model.pkl")
    with open(model_path, "rb") as f:
        saved = pickle.load(f)
    model = saved["model"]
    feature_cols = saved["feature_cols"]
    log.info("Loaded model with %d features", len(feature_cols))

    baseline_df = pd.read_parquet(
        os.path.join(GOLD_DIR, "baseline_predictions.parquet")
    )
    log.info("Loaded baseline predictions: %d rows", len(baseline_df))

    # ------------------------------------------------------------------
    # Step 2 — Generate model predictions for all 20,000 outlets
    # ------------------------------------------------------------------
    X_all = df[feature_cols]
    df["model_prediction"] = model.predict(X_all)
    log.info(
        "Model predictions — min: %.2f  median: %.2f  max: %.2f",
        df["model_prediction"].min(),
        df["model_prediction"].median(),
        df["model_prediction"].max(),
    )

    # ------------------------------------------------------------------
    # Step 3 — Merge baseline predictions
    # ------------------------------------------------------------------
    df = df.merge(baseline_df, on="Outlet_ID", how="left")
    assert df["baseline_potential_litres"].isnull().sum() == 0, \
        "Missing baseline predictions for some outlets"

    # ------------------------------------------------------------------
    # Step 4 — Blend: take the maximum of baseline and model
    # ------------------------------------------------------------------
    df["Maximum_Monthly_Liters"] = df[
        ["model_prediction", "baseline_potential_litres"]
    ].max(axis=1)

    # ------------------------------------------------------------------
    # Step 5 — Post-processing and sanity checks
    # ------------------------------------------------------------------

    # Minimum floor: no outlet's potential can be zero or negative
    floor_violations = (df["Maximum_Monthly_Liters"] <= 0).sum()
    if floor_violations > 0:
        log.warning(
            "Clamping %d predictions from ≤0 to 1.0", floor_violations
        )
        df["Maximum_Monthly_Liters"] = df["Maximum_Monthly_Liters"].clip(
            lower=1.0
        )

    # Round to 2 decimal places
    df["Maximum_Monthly_Liters"] = df["Maximum_Monthly_Liters"].round(2)

    # Distribution check: log decile distribution for sanity inspection
    for q in [0.1, 0.25, 0.5, 0.75, 0.9, 0.95, 0.99]:
        log.info(
            "  P%02d: %.2f litres",
            int(q * 100),
            df["Maximum_Monthly_Liters"].quantile(q),
        )

    # Outlier flag: log any outlet predicting >5x the 99th percentile
    p99 = df["Maximum_Monthly_Liters"].quantile(0.99)
    extreme = df[df["Maximum_Monthly_Liters"] > 5 * p99]
    if len(extreme) > 0:
        log.warning(
            "Found %d extreme predictions (>5×P99=%.2f):", len(extreme), p99
        )
        log.warning(
            extreme[["Outlet_ID", "Maximum_Monthly_Liters"]].to_string()
        )

    # ------------------------------------------------------------------
    # Assertions before writing
    # ------------------------------------------------------------------
    submission = df[["Outlet_ID", "Maximum_Monthly_Liters"]]

    assert len(submission) == 20000, \
        f"Expected 20000 rows, got {len(submission)}"
    assert list(submission.columns) == ["Outlet_ID", "Maximum_Monthly_Liters"], \
        "Submission columns must be exactly [Outlet_ID, Maximum_Monthly_Liters]"
    assert submission["Outlet_ID"].duplicated().sum() == 0, \
        "Duplicate Outlet_IDs"
    assert submission["Outlet_ID"].isnull().sum() == 0
    assert submission["Maximum_Monthly_Liters"].isnull().sum() == 0
    assert (submission["Maximum_Monthly_Liters"] > 0).all(), \
        "All predictions must be positive"
    log.info("All assertions passed.")

    # ------------------------------------------------------------------
    # Step 6 — Write submission CSV
    # ------------------------------------------------------------------
    os.makedirs(OUTPUTS_DIR, exist_ok=True)

    team_name = CFG["team_name"]
    output_path = os.path.join(OUTPUTS_DIR, f"{team_name}_predictions.csv")
    submission.to_csv(output_path, index=False)
    log.info("Written %d rows → %s", len(submission), output_path)

    # ------------------------------------------------------------------
    # Step 7 — Write diagnostics CSV
    # ------------------------------------------------------------------
    diag_cols = [
        "Outlet_ID", "Outlet_Size", "Outlet_Type", "province",
        "Cooler_Count", "hist_p90_monthly", "hist_max_monthly",
        "jan_avg_volume", "has_transaction_history",
        "seasonality_jan_2026", "seasonality_multiplier_jan_2026",
        "footfall_score", "poi_total_1km",
        "model_prediction", "baseline_potential_litres",
        "Maximum_Monthly_Liters",
    ]
    # Only include columns that actually exist in the DataFrame
    diag_cols = [c for c in diag_cols if c in df.columns]

    diag_path = os.path.join(OUTPUTS_DIR, "prediction_diagnostics.csv")
    df[diag_cols].to_csv(diag_path, index=False)
    log.info("Written diagnostics → %s", diag_path)

    # ------------------------------------------------------------------
    # Final summary log
    # ------------------------------------------------------------------
    duration = time.time() - start_time
    log.info("=" * 50)
    log.info("PREDICTION SUMMARY")
    log.info("  Total outlets predicted : %d", len(submission))
    log.info(
        "  Min prediction          : %.2f L",
        submission["Maximum_Monthly_Liters"].min(),
    )
    log.info(
        "  Median prediction       : %.2f L",
        submission["Maximum_Monthly_Liters"].median(),
    )
    log.info(
        "  Mean prediction         : %.2f L",
        submission["Maximum_Monthly_Liters"].mean(),
    )
    log.info(
        "  Max prediction          : %.2f L",
        submission["Maximum_Monthly_Liters"].max(),
    )
    log.info(
        "  Baseline-capped (model < baseline): %d outlets",
        (df["baseline_potential_litres"] >= df["model_prediction"]).sum(),
    )
    log.info(
        "  Model won (model > baseline)      : %d outlets",
        (df["model_prediction"] > df["baseline_potential_litres"]).sum(),
    )
    log.info("  Duration                : %.1f seconds", duration)
    log.info("=" * 50)
    log.info("PREDICTION PIPELINE — DONE")
    log.info("=" * 50)


if __name__ == "__main__":
    main()
