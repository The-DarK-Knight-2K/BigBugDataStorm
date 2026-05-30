# Spec Files — Big Bug Data Storm

This folder contains the full specification for every script in the pipeline.
Each spec is a contract: read it, then have an AI agent (or a teammate) implement
the corresponding script in `pipeline/` or `modelling/`.

## How to use these specs

1. Open the spec for the script you are implementing.
2. Paste the entire spec into your AI coding assistant (Claude, Copilot, etc.).
3. Prefix with: *"Implement this script in Python 3.11 exactly as specified. Do not add
   features not listed. Follow the error handling and quarantine rules exactly."*
4. Review the generated code against the spec line-by-line before committing.
5. Run the validation assertions listed at the bottom of each spec.

## Spec index

### Architecture (read these first)
| File | Purpose |
|------|---------|
| `architecture/SYSTEM_OVERVIEW.md` | Full pipeline, data flow, layer definitions |
| `architecture/DATA_CONTRACTS.md` | Exact schema for every parquet file |
| `architecture/CONVENTIONS.md` | Coding style, logging, error handling rules |

### Bronze layer
| File | Script |
|------|--------|
| `bronze/SPEC_ingest.md` | `pipeline/bronze/ingest.py` |

### EDA (Jupyter Notebooks)
| File | Notebook |
|------|--------|
| `eda/01_transactions_spec.md` | `notebooks/01_eda_transactions.ipynb` |
| `eda/02_outlets_spec.md` | `notebooks/02_eda_outlets.ipynb` |
| `eda/03_features_spec.md` | `notebooks/03_feature_exploration.ipynb` |

### Silver layer
| File | Script |
|------|--------|
| `silver/SPEC_dq_checks.md` | `pipeline/silver/dq_checks.py` |
| `silver/SPEC_clean_transactions.md` | `pipeline/silver/clean_transactions.py` |
| `silver/SPEC_clean_outlets.md` | `pipeline/silver/clean_outlets.py` |
| `silver/SPEC_clean_coordinates.md` | `pipeline/silver/clean_coordinates.py` |
| `silver/SPEC_clean_seasonality.md` | `pipeline/silver/clean_seasonality.py` |
| `silver/SPEC_clean_holidays.md` | `pipeline/silver/clean_holidays.py` |

### Gold layer
| File | Script |
|------|--------|
| `gold/SPEC_scrape_poi.md` | `pipeline/gold/scrape_poi.py` |
| `gold/SPEC_build_sales_features.md` | `pipeline/gold/build_sales_features.py` |
| `gold/SPEC_build_master_features.md` | `pipeline/gold/build_master_features.py` |
| `gold/GRAVITY_MODEL.md` | `pipeline/gold/build_gravity_features.py` |

### Modelling
| File | Script |
|------|--------|
| `modelling/SPEC_baseline.md` | `modelling/baseline.py` |
| `modelling/SPEC_train.md` | `modelling/train.py` |
| `modelling/SPEC_predict.md` | `modelling/predict.py` |
| `modelling/BUDGET_OPTIMIZATION.md` | `modelling/optimise_budget.py` |
| `modelling/XAI_SPEC.md` | `pipeline/xai/` (context packager/prompt builder) & `app/api/xai_api.py` |

### Web App & API
| File | Description / Component |
|------|-------------------------|
| `webapp/API_SPEC.md` | `app/api/main.py` (FastAPI backend endpoints & contract) |
| `webapp/WEBAPP_COMPONENTS.md` | `app/src/` (Vite + React frontend component dashboard views) |

### Orchestration
| File | Script |
|------|--------|
| `orchestration/SPEC_run_pipeline.md` | `pipeline/run_pipeline.py` |

## Progress tracking

1. Record each implemented step concisely.
2. Save the summary to the `docs/worksummary.md` file.
3. Keep the content brief and focused on key actions.
4. Don't make it too long, write just the summary.
5. Check off completed items in `docs/task_list.md`.
