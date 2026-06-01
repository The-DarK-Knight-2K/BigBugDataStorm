# XAI Pipeline: Current State & Handoff Document

This document serves as a bridge for the next chat session. It outlines exactly where we left off with the Data Storm v7.0 pipeline, what the current state of the Explainable AI (XAI) feature is, and what key design decisions need to be resolved before coding begins.

## 1. Current Pipeline State (What is already built)
- **The Orchestrator:** We have a fully functional `pipeline/run_pipeline.py` script. It handles Bronze to Optimization steps idempotently.
- **SHAP Value Generation:** When the orchestrator is run with the `--train-models` flag, it successfully passes the `--shap` flag to the training models. `TreeExplainer` calculates cell-by-cell drivers and saves them to `Data/Gold/shap_values.parquet`.
- **Optimization Outputs:** The budget optimization layer successfully generates `bigbug_budget_allocations.csv` specifically for the Western Province.

## 2. The Planned XAI Scripts (To be built)
According to the `project_task_list.md`, the XAI phase consists of the following components:
1. **`context_packager.py`**: Merges structural data, SHAP values, prediction volumes, and budget allocations into a single context payload per outlet.
2. **`prompt_builder.py`**: Converts the raw data payload into a heavily engineered, contextualized prompt for the Gemini LLM.
3. **`pregenerate_western.py`**: A runner script that iterates through Western Province outlets, queries the Gemini API, and caches the textual business insights to `xai_pregenerated.parquet`.
4. **`export_for_webapp.py`**: Transforms the final parquet files into flat JSON files (`outlets.json`, `budget_summary.json`) meant to be ingested by the Next.js frontend.

## 3. Critical Discussion Points for the Next Session

Before writing the Python scripts above, the following questions **must be resolved** in the new chat session:

### A. Frontend Schema Requirements
Your teammate has already built the Next.js frontend on the `app` branch. What exact JSON schema/keys does the frontend expect? 
*(e.g., Does it expect an array of objects? Does the XAI string need to be nested under a specific `insight` key? How are the SHAP values formatted for the `ShapWaterfall.jsx` component?)*

### B. LLM Prompt Design & Tone
What is the desired tone for the GenAI output? Should the explanation be highly technical (citing standard deviations and specific POI counts), or should it be a prescriptive business narrative intended for a Sales Manager?

### C. Rate Limiting and Batching
The Gemini API will need to generate explanations for roughly ~9,000 Western Province outlets. How should we handle rate limiting? Should we implement batching, asynchronous calls (`asyncio`), or simple sequential loops with `time.sleep()`?

### D. Integration with Orchestrator
Should `pregenerate_western.py` be automatically executed at the end of `run_pipeline.py`? Given the heavy latency of 9,000 API calls, it might be safer to keep the LLM generation as an independent, manually triggered script.

---
**Next Steps for New Chat:** Share the Next.js API payload expectations, decide on the LLM prompt style, and kick off the implementation plan for the scripts listed in Section 2.
