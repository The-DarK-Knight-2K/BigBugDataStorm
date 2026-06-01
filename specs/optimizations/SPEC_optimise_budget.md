# Specification: Budget Optimization (`pipeline/optimizations/optimise_budget.py`)

## 1. Overview
The goal of this module is to optimally allocate a fixed trade marketing budget of **5,000,000 LKR** across traditional trade outlets in the **Western Province**. The allocation uses a **Tier-Budget Capped Greedy Knapsack** framework to maximize Net Financial ROI while ensuring a wide market footprint.

## 2. Input Data
*   `Data/Gold/master_features.parquet`: Contains outlet metadata (sizes, types, transaction history, gravity scores).
*   `outputs/round2_final/bigbug_predictions.csv`: Contains the model predictions (`Outlet_ID`, `Maximum_Monthly_Liters`).

## 3. Mathematical Framework (ROI Score)
Each Western Province outlet is assigned an ROI opportunity score based on min-max normalized features:
```python
ROI = 0.40 * norm(uplift_gap) + 0.30 * norm(gravity_score) + 0.20 * norm(recent_sales) + 0.10 * norm(cooler_count)
```
*Note: `uplift_gap = max(0, predicted_potential - hist_mean_monthly)`*

## 4. Spend Packages & Tiers
The total 5M budget is strictly partitioned to ensure a broad market footprint:
*   **Tier 1 (High - Top 15%):** Cooler Subsidy / Display Rack. Budget Bucket: 2.5M. Cap: 12,000 LKR.
*   **Tier 2 (Medium - Next 35%):** Promotional Discount. Budget Bucket: 1.75M. Cap: 3,000 LKR.
*   **Tier 3 (Low - Next 15%):** Light Merchandising POS. Budget Bucket: 0.75M. Cap: 800 LKR.
*   **Tier 4 (Zero Potential):** No Allocation (0 LKR).

## 5. Knapsack Allocation Algorithm
Instead of continuous grid-search optimization, the script uses a discrete greedy approach:
1.  **Headroom Capping:** Max spend per outlet is capped based on `uplift_gap / efficiency`.
2.  **Operational Constraints:** Small outlets, Kiosks, Pharmacies, and "Cold-start" outlets (no history) are strictly capped at the Medium tier (max 3,000 LKR) regardless of ROI score.
3.  **Greedy Pass:** Outlets are sorted by ROI descending and allocated budget from their respective Tier Buckets in exact 50 LKR multiples.
4.  **Guardrails & Rebalancing:** 
    - Ensures each Western Province distributor (`DIST_W_01`, `DIST_W_02`, `DIST_W_03`) gets $\ge 25\%$ (1.25M LKR) of the budget by rebalancing from lowest-ROI to highest-ROI outlets across distributors.
    - Micro-adjusts final values (+/- 50 LKR) to precisely exhaust the 5,000,000.00 LKR limit.

## 6. Output Deliverables
1.  `outputs/bigbug_budget_allocations.csv`: Two columns (`Outlet_ID`, `Trade_Spend_Allocation_LKR`). Contains **only** Western Province outlets.
2.  `outputs/budget_diagnostics.csv`: Full diagnostics log.
3.  `data/Optimization/budget_features.parquet`: Fast load diagnostics for the Web App.
4.  `outputs/roi_distribution.png`: Histogram visualization of the ROI score distribution with tier cutoffs.
