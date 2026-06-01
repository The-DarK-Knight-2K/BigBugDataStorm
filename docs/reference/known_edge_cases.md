# Known Edge Cases & Pipeline Limitations

This document serves as a reference for potential failure points, unhandled exceptions, and environmental edge cases that may occur when running the pipeline on client or judge machines.

## 1. Hardware & Environment Failures

### 1.1 CPU-Only Machines (No GPU)
- **Issue:** In `modelling/train.py`, we explicitly set parameters like `"device": "cuda"` (XGBoost) or `"device": "gpu"` (LightGBM) to accelerate training. 
- **Impact:** If the pipeline is executed with the `--train-models` flag on a machine without a compatible GPU (or without CUDA installed), the script will crash immediately with an error similar to `XGBoostError: No visible GPU is found`.
- **Future Fix:** Implement a dynamic hardware check (e.g., trying to detect CUDA availability) before training, and automatically fall back to `"device": "cpu"` if a GPU isn't found.

### 1.2 Out of Memory (OOM) Errors on Low-Spec Machines
- **Issue:** Generating cell-by-cell SHAP values using `TreeExplainer` for 20,000 rows across 69 features requires significant RAM. Building spatial `BallTree` instances for distance calculations is also memory-intensive.
- **Impact:** If executed on older machines with limited RAM (e.g., 4GB - 8GB), the OS might kill the Python process due to memory exhaustion (OOM kill), causing the pipeline to freeze or crash silently.
- **Future Fix:** Batch the SHAP value generation into smaller chunks (e.g., 5,000 rows at a time) or utilize `dask` / `modin` for out-of-core computation.

### 1.3 Missing Python Dependencies
- **Issue:** Users may attempt to run `pipeline/run_pipeline.py` before installing the required packages from `requirements.txt`.
- **Impact:** The orchestrator will fail immediately on the first `import pandas` or `import yaml` statement with a raw `ModuleNotFoundError`.
- **Future Fix:** Wrap top-level imports in a `try/except` block inside the orchestrator to print a friendly, actionable error message (e.g., "Please run pip install -r requirements.txt first").

## 2. External Service & API Failures

### 2.1 Missing or Invalid Gemini API Key
- **Issue:** Phase 2 (Explainable AI Pipeline) relies on querying the Gemini LLM to generate natural language explanations for the outlets.
- **Impact:** If the user’s environment does not contain a valid `GEMINI_API_KEY`, the script will throw an authentication error and break the extraction process.
- **Future Fix:** Add robust `try/except` fallback logic to output a generic placeholder string (e.g., "AI Insight currently unavailable") instead of breaking the entire execution loop.

### 2.2 OpenStreetMap (Overpass API) Rate Limiting or Drops
- **Issue:** The `--run-scraping` flag triggers live data extraction from OSM. While we have K-Means clustering and idempotency built-in, a complete network blackout or IP ban from Overpass will stall the process.
- **Impact:** The script will correctly retry and eventually save its state to the `scrape_manifest.json` before exiting, but the POI cache will be incomplete. Downstream Gold scripts will impute missing POI values with 0s, potentially degrading model accuracy.
- **Future Fix:** Pre-package a fully completed `poi_raw_cache` within the final submission so users never have to run `--run-scraping` unless actively developing.

## 3. Operating System Variances

### 3.1 Cross-Platform Pathing (`\` vs `/`)
- **Issue:** Windows uses backslashes (`\`), while Linux/macOS uses forward slashes (`/`).
- **Impact:** While the orchestrator safely utilizes `os.path.join`, some underlying scripts might inadvertently hardcode paths. In strict Linux environments, this can cause unexpected `FileNotFoundError`s.
- **Future Fix:** Audit all scripts to strictly use `pathlib.Path` or `os.path.join` for all file I/O operations.
