# Specification: Budget Optimization (`pipeline/optimizations/optimise_budget.py`)

## 1. Overview
The goal of this module is to optimally allocate a fixed trade marketing budget of **5,000,000 LKR** across traditional trade outlets in the **Western Province**. The allocation is based on a "Potential-Based Allocation" framework to maximize Net Financial ROI.

## 2. Input Data
*   `Data/Gold/master_features.parquet`: Contains outlet metadata (`province`, `hist_mean_monthly`, `composite_gravity_score`, `competition_density_score`).
*   `outputs/round2/bigbug_predictions.csv`: Contains the model predictions (`Outlet_ID`, `Maximum_Monthly_Liters`).

## 3. Mathematical Framework (ROI Score)
Each Western Province outlet is assigned an ROI opportunity score:
```python
uplift_gap = max(0, predicted_potential - hist_mean_monthly)
gravity_multiplier = composite_gravity_score / 100.0 
competition_multiplier = 1.0 / (1.0 + competition_density_score)
roi_score = uplift_gap * gravity_multiplier * competition_multiplier
```

## 4. Spend Packages & Tiers
*   **Tier 1 (High Potential):** Cooler Subsidy / Display Rack (~2,500 LKR base up to 15,000 LKR max). Expected uplift conversion: 20%.
*   **Tier 2 (Medium Potential):** Promotional Discount (~1,167 LKR base). Expected uplift conversion: 10%.
*   **Tier 3 (Low Potential):** Merchandising POS (~500 LKR fixed). Expected uplift conversion: 3%.
*   **Tier 4 (Zero Potential):** No Allocation (0 LKR).

*Financial Assumption:* Gross profit per liter is estimated at **50 LKR**.

## 5. Automated Optimization (Grid Search)
The script will perform hyperparameter tuning using a grid search to find the optimal percentage cutoffs for each tier (e.g., Top X% gets Tier 1, Next Y% gets Tier 2).
*   **Objective Function:** Maximize `Total Net Profit = (Expected Incremental Liters * 50) - Total Spend`
*   **Constraints:** `Sum of Spend == 5,000,000 LKR`. Spend per outlet must be either 0, or between 500 and 15,000 LKR. Only outlets with `province == 'Western'` can receive budget.

## 6. Budget Balancing
After the optimal tier boundaries are found, the script will execute a balancing loop on Tier 1 and Tier 2 allocations to ensure the exact sum equals 5,000,000 LKR, accounting for rounding differences.

## 7. Outputs
All outputs are saved to `data/optimizations/`:
1.  `bigbug_budget_allocations.csv`: Two columns (`Outlet_ID`, `Trade_Spend_Allocation_LKR`).
2.  `budget_diagnostics.csv`: Full diagnostics including calculated ROI, tier assignment, and projected profit.
3.  `budget_features.parquet`: Parquet version of diagnostics.
4.  `roi_distribution.png`: Histogram visualization of the ROI score distribution with overlaid tier cutoffs.
