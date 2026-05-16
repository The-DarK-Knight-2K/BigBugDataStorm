"""
Generate final submission predictions by blending LightGBM model output with the statistical baseline.

Layer  : Modelling
Inputs : data/gold/master_features.parquet, modelling/artifacts/model.pkl, data/gold/baseline_predictions.parquet
Outputs: outputs/teamname_predictions.csv, outputs/prediction_diagnostics.csv
"""

import logging
import pickle
import sys
from pathlib import Path

import pandas as pd
import yaml

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
OUTPUTS = ROOT / CFG.get("paths", {}).get("outputs", Path("outputs"))
ARTIFACTS = ROOT / CFG.get("paths", {}).get("artifacts", Path("modelling") / "artifacts")
MASTER_FEATURES_PATH = GOLD / "master_features.parquet"
BASELINE_PATH = GOLD / "baseline_predictions.parquet"
MODEL_PATH = ARTIFACTS / "model.pkl"
TEAM_NAME = CFG.get("team_name", "teamname")
SUBMISSION_PATH = OUTPUTS / f"{TEAM_NAME}_predictions.csv"
DIAGNOSTICS_PATH = OUTPUTS / "prediction_diagnostics.csv"


def load_inputs() -> tuple[pd.DataFrame, object, list[str], pd.DataFrame]:
    if not MASTER_FEATURES_PATH.exists():
        log.error("Cannot proceed: missing master_features file: %s", MASTER_FEATURES_PATH)
        sys.exit(1)

    if not MODEL_PATH.exists():
        log.error("Cannot proceed: missing model artifact file: %s", MODEL_PATH)
        sys.exit(1)

    if not BASELINE_PATH.exists():
        log.error("Cannot proceed: missing baseline predictions file: %s", BASELINE_PATH)
        sys.exit(1)

    df = pd.read_parquet(MASTER_FEATURES_PATH)
    log.info("Loaded master features: %d rows", len(df))

    with open(MODEL_PATH, "rb") as f:
        saved = pickle.load(f)

    model = saved.get("model")
    feature_cols = saved.get("feature_cols")
    if model is None or feature_cols is None:
        log.error("Model artifact must contain 'model' and 'feature_cols'")
        sys.exit(1)

    log.info("Loaded model with %d features", len(feature_cols))

    baseline_df = pd.read_parquet(BASELINE_PATH)
    log.info("Loaded baseline predictions: %d rows", len(baseline_df))

    return df, model, feature_cols, baseline_df


def generate_model_predictions(df: pd.DataFrame, model: object, feature_cols: list[str]) -> pd.DataFrame:
    missing_features = [c for c in feature_cols if c not in df.columns]
    if missing_features:
        log.error("Missing feature columns in master features: %s", missing_features)
        sys.exit(1)

    X_all = df[feature_cols]
    df["model_prediction"] = model.predict(X_all)
    log.info(
        "Model predictions — min: %.2f  median: %.2f  max: %.2f",
        df["model_prediction"].min(),
        df["model_prediction"].median(),
        df["model_prediction"].max(),
    )
    return df


def blend_with_baseline(df: pd.DataFrame, baseline_df: pd.DataFrame) -> pd.DataFrame:
    df = df.merge(baseline_df, on="Outlet_ID", how="left")
    missing_baseline = df["baseline_potential_litres"].isnull().sum()
    if missing_baseline > 0:
        log.error("Missing baseline predictions for %d outlets", missing_baseline)
        sys.exit(1)
    return df


def postprocess_predictions(df: pd.DataFrame) -> pd.DataFrame:
    df["Maximum_Monthly_Liters"] = df[["model_prediction", "baseline_potential_litres"]].max(axis=1)

    floor_violations = (df["Maximum_Monthly_Liters"] <= 0).sum()
    if floor_violations > 0:
        log.warning("Clamping %d predictions from ≤0 to 1.0", floor_violations)
        df["Maximum_Monthly_Liters"] = df["Maximum_Monthly_Liters"].clip(lower=1.0)

    df["Maximum_Monthly_Liters"] = df["Maximum_Monthly_Liters"].round(2)

    for q in [0.1, 0.25, 0.5, 0.75, 0.9, 0.95, 0.99]:
        log.info(
            "  P%02d: %.2f litres",
            int(q * 100),
            df["Maximum_Monthly_Liters"].quantile(q),
        )

    p99 = df["Maximum_Monthly_Liters"].quantile(0.99)
    extreme = df[df["Maximum_Monthly_Liters"] > 5 * p99]
    if len(extreme) > 0:
        log.warning("Found %d extreme predictions (>5×P99=%.2f):", len(extreme), p99)
        log.warning(extreme[["Outlet_ID", "Maximum_Monthly_Liters"]].to_string(index=False))

    return df


def write_submission(df: pd.DataFrame) -> pd.DataFrame:
    OUTPUTS.mkdir(parents=True, exist_ok=True)
    submission = df[["Outlet_ID", "Maximum_Monthly_Liters"]].copy()

    assert len(submission) == 20000, f"Expected 20000 rows, got {len(submission)}"
    assert list(submission.columns) == ["Outlet_ID", "Maximum_Monthly_Liters"], \
        "Submission columns must be exactly [Outlet_ID, Maximum_Monthly_Liters]"
    assert submission["Outlet_ID"].duplicated().sum() == 0, "Duplicate Outlet_IDs"
    assert submission["Outlet_ID"].isnull().sum() == 0
    assert submission["Maximum_Monthly_Liters"].isnull().sum() == 0
    assert (submission["Maximum_Monthly_Liters"] > 0).all(), "All predictions must be positive"

    submission.to_csv(SUBMISSION_PATH, index=False)
    log.info("Written %d rows → %s", len(submission), SUBMISSION_PATH)
    return submission


def write_diagnostics(df: pd.DataFrame) -> None:
    diag_cols = [
        "Outlet_ID", "Outlet_Size", "Outlet_Type", "province",
        "Cooler_Count", "hist_p90_monthly", "hist_max_monthly",
        "jan_avg_volume", "has_transaction_history",
        "seasonality_jan_2026", "seasonality_multiplier_jan_2026",
        "footfall_score", "poi_total_1km",
        "model_prediction", "baseline_potential_litres",
        "Maximum_Monthly_Liters",
    ]
    diag_cols = [c for c in diag_cols if c in df.columns]
    df[diag_cols].to_csv(DIAGNOSTICS_PATH, index=False)
    log.info("Written diagnostics → %s", DIAGNOSTICS_PATH)


def log_summary(submission: pd.DataFrame, df: pd.DataFrame) -> None:
    log.info("%s", "=" * 50)
    log.info("PREDICTION SUMMARY")
    log.info("  Total outlets predicted : %d", len(submission))
    log.info("  Min prediction          : %.2f L", submission["Maximum_Monthly_Liters"].min())
    log.info("  Median prediction       : %.2f L", submission["Maximum_Monthly_Liters"].median())
    log.info("  Mean prediction         : %.2f L", submission["Maximum_Monthly_Liters"].mean())
    log.info("  Max prediction          : %.2f L", submission["Maximum_Monthly_Liters"].max())
    log.info(
        "  Baseline-capped (model < baseline): %d outlets",
        (df["baseline_potential_litres"] >= df["model_prediction"]).sum(),
    )
    log.info(
        "  Model won (model > baseline)      : %d outlets",
        (df["model_prediction"] > df["baseline_potential_litres"]).sum(),
    )
    log.info("%s", "=" * 50)


def main() -> pd.DataFrame:
    log.info("Starting prediction generation")
    df, model, feature_cols, baseline_df = load_inputs()
    df = generate_model_predictions(df, model, feature_cols)
    df = blend_with_baseline(df, baseline_df)
    df = postprocess_predictions(df)
    submission = write_submission(df)
    write_diagnostics(df)
    log_summary(submission, df)
    log.info("Prediction generation complete")
    return submission


if __name__ == "__main__":
    main()
