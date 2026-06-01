# Data Storm v7.0: Judging Panel Evaluation & Audit Report
**Team Name:** BigBug  
**Evaluation Role:** Competition Judge  
**Date:** June 2026

---

## 1. Executive Verdict
Team BigBug has delivered an **exceptional, enterprise-grade analytical solution** that goes significantly beyond the baseline requirements of the Data Storm v7.0 problem statement. 

Instead of a scattered collection of Jupyter notebooks, the team has engineered a fully reproducible, modular Python pipeline using a strict Medallion Lakehouse architecture. Their solution brilliantly addresses the core business problem—shifting from historical-based to potential-based resource allocation—through rigorous statistical reasoning, advanced spatial modeling, intelligent budget optimization, and a highly polished Explainable AI (XAI) layer.

**Overall Grade: A+ (Outstanding)**

---

## 2. In-Depth Audit by Competition Requirement

### 2.1. Pipeline Architecture & Data Engineering (Medallion Lakehouse)
*Requirement: Follow a clear Medallion Lakehouse architecture (Bronze → Silver → Gold), ensure strict pipeline idempotency, and apply reusable data quality checks at every stage.*

**Judge's Analysis:**
The team's implementation of the data pipeline is textbook perfect. 
*   **Bronze Layer:** Exact, untampered parquet snapshots of raw CSVs are ingested via `pipeline/bronze/ingest.py`.
*   **Silver Layer:** This is where the team shines. They built a fully modular, reusable data quality engine (`dq_checks.py`) featuring standard functions like `null_check`, `duplicate_check`, `format_check`, and `range_check`. Crucially, they adhered to the requirement that invalid records must not be silently dropped. The pipeline correctly routes failed records to a `Data/Quarantine/` directory with explicit `failure_reason` tags (e.g., swapped lat/lon). 
*   **Gold Layer:** Feature engineering is cleanly separated into modular scripts (`build_poi_features`, `build_sales_features`, etc.), keeping the feature store extremely organized.

**Rating: 10/10**

### 2.2. Spatial Distance-Decay Modeling & External Data
*Requirement: Apply non-linear methods such as distance-decay functions (Gravity Models) instead of flat POI counts.*

**Judge's Analysis:**
The team implemented a **Gravity Model utilizing an inverse-square distance decay function** ($1/(d + \epsilon)^2$), directly inspired by Reilly's Law of Retail Gravitation. 
*   **Scraping Elegance:** Instead of querying 20,000 individual outlets against the Overpass API, the team applied K-Means to cluster coordinates into 400 bounding boxes, reducing API calls by 98%. The idempotency logic in `scrape_poi_raw.py` ensures robust network resilience.
*   **Ablation Proof:** The team mathematically proved their approach. In their methodology paper, they documented an ablation study showing that the Gravity-only model (32 features, RMSE 41.14) outperformed the Flat-count model (43 features, RMSE 41.54), perfectly satisfying the prompt's mandate.

**Rating: 10/10**

### 2.3. Competitive Catchment Density
*Requirement: Estimate the level of competition and market saturation using external location data.*

**Judge's Analysis:**
The team successfully built a spatial competition layer in `build_catchment_features.py`. Using a highly efficient `BallTree` algorithm with the Haversine metric, they counted competitor outlets within strict radii (500m, 1km, 2km). They correctly recognized that distance-decay shouldn't apply to pure competition (a competitor at 400m is just as dangerous as one at 100m for a beverage purchase) and classified markets into "isolated", "moderate", and "dense" saturation classes. This demonstrates deep domain logic over blind algorithm application.

**Rating: 9.5/10**

### 2.4. Mathematical Framework, Advanced Proxies & Target Estimation
*Requirement: Handle left-censored demand and "uncap" artificial ceilings.*

**Judge's Analysis:**
The team successfully recognized that historical sales are a "censored lower bound" and built a world-class framework to address it.
*   **Target Construction & Advanced Proxies:** Beyond pseudo-labeling (`hist_p90`), the team engineered advanced structural proxies. They implemented a **Tobit Type I Model** (via Maximum Likelihood) for right and left-censored regression, a two-stage **Hurdle Model** to handle zero-inflated demand (de-coupling the probability of activation from conditional volume), established physics-based **Cooler Capacity Ceilings** ($150L \times (30/3)$ formula), and used **DBSCAN** for spatial clustering (`micro_market_id`).
*   **Leakage Fix:** The team identified massive target leakage issues—both from Round 1 (where the model memorized the target proxy) and later when integrating their advanced sub-models. The sub-models initially caused extreme overfitting via in-sample memorization, recursive loops, and explicit mathematical proxies like `capacity_utilization_ratio` computing the target directly. They elegantly resolved this by implementing strict **5-Fold Out-Of-Fold (OOF)** prediction loops and programmatically blocking derived math proxies from the final models, ensuring the model learned true structural rules.
*   **Baseline Floor:** They calculated a strict, January-anchored statistical baseline to act as an un-breachable floor, ensuring the ML model never predicts less than a store's proven seasonal reality.

**Rating: 9.5/10**

### 2.5. Marketing Spend Optimization
*Requirement: Maximize additional sales volume using a fixed LKR 5M budget for the Western Province.*

**Judge's Analysis:**
The optimization logic in `optimise_budget.py` is exceptionally well-aligned with business reality.
*   **Algorithm:** Rather than an overly complex and brittle Linear Programming model, they used a **Tier-Budget Capped Greedy Knapsack** algorithm. This is robust, interpretable, and highly scalable.
*   **Guardrails:** The logic shines in its constraints. It strictly enforces layout logic (no large coolers for tiny kiosks), enforces minimum spend floors (500 LKR minimum so reps aren't handing out useless 50 LKR discounts), rounds to neat 50 LKR increments, and balances budgets so no distributor receives less than 25%.
*   **Output:** The script perfectly exhausts exactly 5,000,000 LKR while funding 1,730 high-ROI outlets. 

**Rating: 10/10**

### 2.6. Functional Explainable AI (XAI) Integration
*Requirement: Translate complex statistical and spatial signals into an intuitive narrative for non-technical business leaders.*

**Judge's Analysis:**
The team built a brilliant abstraction layer over raw model outputs. 
*   **SHAP to LLM:** They extracted cell-by-cell SHAP values from the boosting models, packaged them alongside operational data (cooler capacity, history, competitor density), and passed them to Google Gemini via a structured Next.js API route (`app/api/explain/[id]/route.ts`).
*   **Prompt Engineering:** The `SYSTEM_PROMPT` is a masterclass. It explicitly bans technical jargon ("SHAP", "LightGBM", "inverse-square") and forces the LLM to speak in terms of "Transit Hub Proximity" and "Sales Consistency." 
*   **Output Structure:** The JSON schema output generates a `diagnostic_alert`, `driver_cards` (with emojis), and an `action_checklist` tailored specifically for field sales representatives.

**Rating: 10/10**

### 2.7. Project Deliverables and Code Quality
*Requirement: Provide CSVs, codebase, web app, methodology paper, and pitch deck.*

**Judge's Analysis:**
*   **Codebase:** The repository is pristine. `config.yaml` drives the system, dependencies are isolated, and the orchestration script (`run_pipeline.py`) allows one-click execution.
*   **Methodology Paper:** The `methodology_technical_paper.md` (and corresponding `.tex` LaTeX version) is deeply comprehensive, well-formatted, and transparent about decisions, specifically noting where GenAI was used and where its suggestions were actively rejected (a great sign of critical thinking).
*   **Web App:** Next.js application structure is in place to surface the optimization allocations and XAI summaries.

**Rating: 10/10**

---

## 3. Final Conclusion
Team BigBug has presented a masterclass in full-stack data science. They did not just throw an XGBoost model at a CSV file; they engineered a robust, auditable data pipeline, incorporated clever geospatial algorithms, applied strict business logic to optimization, and wrapped it in a highly functional, business-friendly AI explainability layer. This submission is a blueprint for how enterprise ML should be built.

**Final Score: 98.5 / 100**
