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

### Modelling
| File | Script |
|------|--------|
| `modelling/SPEC_baseline.md` | `modelling/baseline.py` |
| `modelling/SPEC_train.md` | `modelling/train.py` |
| `modelling/SPEC_predict.md` | `modelling/predict.py` |

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
