# Section X: Enterprise Pipeline Orchestration

## 1. Introduction
To meet the stringent technical requirements outlined in the Data Storm v7.0 problem statement, the standalone analytical scripts have been unified into a production-grade, end-to-end orchestrator (`pipeline/run_pipeline.py`). This orchestration layer strictly enforces the Medallion Lakehouse architecture (Bronze → Silver → Gold → Modelling → Optimization) while delivering robust error handling, pipeline tracking, and execution efficiency.

## 2. Key Capabilities

### 2.1. Idempotency and Fault Tolerance
The orchestrator is built with strict idempotency in mind. To avoid the cascading corruption that plagues disjointed data pipelines, the script utilizes a precise `--start-from <stage_num>` resumption mechanism. If a script exits with a non-zero return code at any stage (e.g., Silver cleaning or Gold Feature Engineering), the pipeline halts immediately, logging the exact command and trace to a centralized `outputs/pipeline.log`. Data engineers can rectify the anomaly and restart the pipeline exactly where it failed, ensuring zero compute loss on previously successful stages.

### 2.2. Intelligent "Fast-Path" Execution
Recognizing that model training and OpenStreetMap Overpass API calls (POI scraping) are heavily time-consuming, the orchestrator employs a default "Fast Path". By default, it intelligently bypasses these network and compute-heavy nodes, instead seamlessly integrating the idempotent POI caches (`Data/Gold/poi_raw_cache/`) and the highest-performing serialized model artifacts from Round 2. This dynamic routing reduces end-to-end execution time from over 40 minutes to under 2 minutes. Full execution can be forced on-demand via `--run-scraping` and `--train-models` CLI flags.

### 2.3. Dynamic Model Resolution & Ensembling
When the `--train-models` flag is passed, the orchestrator triggers training runs for XGBoost, LightGBM, and Random Forest (all utilizing GPU acceleration where available), ensuring the `--shap` parameter is passed to extract critical feature importance for the Explainable AI (XAI) dashboard. Crucially, it dynamically reads the newly generated `run_id`s from the timestamped tracking registry (`modelling/artifacts/run_registry.csv`) and passes them dynamically to the inference blending engine (`ensemble.py`). 

### 2.4. Preflight and Final Validation Checks
Before any compute is expended, the orchestrator executes a `preflight_checks` algorithm, confirming the absolute presence and integrity of the `Data/Raw/` layer. Upon successful completion of the final Budget Optimization node, it programmatically asserts the structural integrity of both the volume predictions (`bigbug_predictions.csv`) and the budget allocations (`bigbug_budget_allocations.csv`), ensuring exactly 20,000 bounds-checked predictions and properly filtered Western Province trade allocations prior to dashboard hand-off.
