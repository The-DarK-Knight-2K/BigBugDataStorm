# SPEC: run_pipeline.py

## Purpose

End-to-end orchestrator that runs all pipeline stages in the correct order with
dependency enforcement, timing, and a final summary. Running this single script
should reproduce the entire pipeline from raw CSVs to the submission CSV.

## Layer
Orchestration (`pipeline/run_pipeline.py`)

## Inputs
All raw CSV files in `data/raw/` (via the Bronze ingest step).

## Outputs
`outputs/teamname_predictions.csv` (via the Predict step).

---

## Execution order (strict — do not reorder)

```
Stage 0  → Bronze: ingest
Stage 1  → Silver: clean_outlets          (no dependency on other Silver files)
Stage 2  → Silver: clean_coordinates      (depends on outlet_master_clean)
Stage 3  → Silver: clean_seasonality      (no dependency on other Silver files)
Stage 4  → Silver: clean_holidays         (no dependency on other Silver files)
Stage 5  → Silver: clean_transactions     (depends on outlet_master_clean)
Stage 6  → Gold:   scrape_poi             (depends on outlet_coordinates_clean)
Stage 7  → Gold:   build_sales_features   (depends on transactions_clean, outlet_master_clean)
Stage 8  → Gold:   build_master_features  (depends on all Silver + scrape_poi + build_sales_features)
Stage 9  → Model:  baseline               (depends on master_features)
Stage 10 → Model:  train                  (depends on master_features)
Stage 11 → Model:  predict                (depends on master_features, model.pkl, baseline)
```

---

## Step-by-step logic

### Step 1 — CLI argument parsing

```python
import argparse

parser = argparse.ArgumentParser(description="Data Storm 7.0 — Full Pipeline")
parser.add_argument(
    "--skip-poi",
    action="store_true",
    help="Skip POI scraping (use existing poi_features.parquet if present)",
)
parser.add_argument(
    "--skip-train",
    action="store_true",
    help="Skip model training (use existing model.pkl if present)",
)
parser.add_argument(
    "--start-from",
    type=int,
    default=0,
    help="Start from a specific stage number (0–11). Assumes all prior stages completed.",
)
args = parser.parse_args()
```

### Step 2 — Pre-flight checks

Before running any stage:

```python
def preflight_checks() -> None:
    """Verify all raw files exist and the environment is ready."""
    raw_files = [
        CFG["files"]["transactions"],
        CFG["files"]["outlet_master"],
        CFG["files"]["coordinates"],
        CFG["files"]["seasonality"],
        CFG["files"]["holidays"],
    ]
    for fname in raw_files:
        fpath = RAW / fname
        if not fpath.exists():
            log.error("Missing raw file: %s", fpath)
            log.error("Place all provided CSV files in data/raw/ before running.")
            sys.exit(1)

    # Create all output directories
    for d in [BRONZE, SILVER, GOLD, QUARANTINE, OUTPUTS, ARTIFACTS]:
        d.mkdir(parents=True, exist_ok=True)

    log.info("Pre-flight checks passed. All raw files found.")
```

### Step 3 — Stage runner with timing and error handling

```python
import time
import subprocess

def run_stage(stage_num: int, stage_name: str, script_path: str,
              skip: bool = False, required_output: Path | None = None) -> bool:
    """
    Run a pipeline stage as a subprocess.

    Args:
        stage_num     : Stage number for display
        stage_name    : Human-readable name
        script_path   : Relative path to the script from repo root
        skip          : If True and required_output exists, skip this stage
        required_output: If skip=True, check this file exists before skipping

    Returns:
        True if stage succeeded or was legitimately skipped, False on failure.
    """
    if skip and required_output and required_output.exists():
        log.info("[Stage %02d] SKIPPED — %s (output exists: %s)",
                 stage_num, stage_name, required_output.name)
        return True

    log.info("[Stage %02d] STARTING — %s", stage_num, stage_name)
    start = time.time()

    result = subprocess.run(
        ["python", script_path],
        capture_output=False,   # let output stream to console
        cwd=ROOT,
    )

    elapsed = time.time() - start

    if result.returncode != 0:
        log.error("[Stage %02d] FAILED — %s (%.1fs)", stage_num, stage_name, elapsed)
        log.error("Pipeline halted. Fix the error above and re-run with --start-from %d",
                  stage_num)
        return False

    log.info("[Stage %02d] COMPLETED — %s (%.1fs)", stage_num, stage_name, elapsed)
    return True
```

### Step 4 — Main pipeline execution

```python
def main():
    log.info("=" * 60)
    log.info("Data Storm 7.0 — Full Pipeline Starting")
    log.info("=" * 60)

    preflight_checks()
    start_from = args.start_from
    pipeline_start = time.time()

    stages = [
        (0,  "Bronze Ingest",            "pipeline/bronze/ingest.py",                       False, None),
        (1,  "Silver: Clean Outlets",    "pipeline/silver/clean_outlets.py",                False, None),
        (2,  "Silver: Clean Coords",     "pipeline/silver/clean_coordinates.py",            False, None),
        (3,  "Silver: Clean Seasonality","pipeline/silver/clean_seasonality.py",            False, None),
        (4,  "Silver: Clean Holidays",   "pipeline/silver/clean_holidays.py",               False, None),
        (5,  "Silver: Clean Transactions","pipeline/silver/clean_transactions.py",          False, None),
        (6,  "Gold: Scrape POI",         "pipeline/gold/scrape_poi.py",
             args.skip_poi, GOLD / "poi_features.parquet"),
        (7,  "Gold: Sales Features",     "pipeline/gold/build_sales_features.py",           False, None),
        (8,  "Gold: Master Features",    "pipeline/gold/build_master_features.py",          False, None),
        (9,  "Model: Baseline",          "modelling/baseline.py",                           False, None),
        (10, "Model: Train",             "modelling/train.py",
             args.skip_train, ARTIFACTS / "model.pkl"),
        (11, "Model: Predict",           "modelling/predict.py",                            False, None),
    ]

    for stage_num, stage_name, script_path, skip, required_output in stages:
        if stage_num < start_from:
            log.info("[Stage %02d] SKIPPED — %s (--start-from %d)",
                     stage_num, stage_name, start_from)
            continue

        success = run_stage(stage_num, stage_name, script_path, skip, required_output)
        if not success:
            sys.exit(1)

    total_elapsed = time.time() - pipeline_start
    log.info("=" * 60)
    log.info("Pipeline complete in %.1f minutes", total_elapsed / 60)
    log.info("Submission file: outputs/%s_predictions.csv", CFG["team_name"])
    log.info("=" * 60)


if __name__ == "__main__":
    main()
```

---

## Example usage

```bash
# Full pipeline end to end
python pipeline/run_pipeline.py

# Skip POI scraping (if poi_features.parquet already exists from a previous run)
python pipeline/run_pipeline.py --skip-poi

# Skip POI and model training (re-run only the predict step)
python pipeline/run_pipeline.py --skip-poi --skip-train --start-from 11

# Resume from Gold layer after fixing a Silver script
python pipeline/run_pipeline.py --start-from 6
```

---

## Final output validation

After all stages complete, validate the submission file:

```python
def validate_submission() -> None:
    team_name   = CFG["team_name"]
    output_path = OUTPUTS / f"{team_name}_predictions.csv"

    assert output_path.exists(), f"Submission file not found: {output_path}"
    sub = pd.read_csv(output_path)

    assert len(sub) == 20000,          f"Expected 20000 rows, got {len(sub)}"
    assert "Outlet_ID" in sub.columns, "Missing Outlet_ID column"
    assert "Maximum_Monthly_Liters" in sub.columns, "Missing Maximum_Monthly_Liters column"
    assert sub["Outlet_ID"].duplicated().sum() == 0, "Duplicate Outlet_IDs in submission"
    assert (sub["Maximum_Monthly_Liters"] > 0).all(), "Non-positive predictions found"
    assert sub["Maximum_Monthly_Liters"].isnull().sum() == 0, "Null predictions found"

    log.info("Submission file validation PASSED — ready to submit.")
```

---

## Dependencies

- Standard library: argparse, subprocess, sys, time, logging, pathlib
- pandas (for validation step)
- pyyaml
