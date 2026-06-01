# Phase 2: Budget Optimization — Tier-Budget Capped Greedy Knapsack Plan

This document details the mathematical framework, constraints, real-world package options, and implementation logic for our advanced **Potential-Based Tier-Budget Capped Greedy Knapsack Budget Optimization Engine** for the Western Province (5,000,000 LKR budget).

---

## 1. The "Balanced Portfolio" (Option A) Budget Allocation
We partition the total 5,000,000 LKR budget into three strict, tier-specific budget buckets based on your verified market price packages to ensure massive brand footprint and distributor satisfaction across the Western Province:
1. **High Tier (Growth Accelerator):** Capped at 50% of the total budget = **2,500,000 LKR**
2. **Medium Tier (Visibility Boost):** Capped at 35% of the total budget = **1,750,000 LKR**
3. **Low Tier (Brand Presence):** Capped at 15% of the total budget = **750,000 LKR**

### Expected Allocation Footprint & Impact:

| Tier | Tier Budget Share | Per-Shop Cap | Per-Shop Floor | Volume/LKR | Est. Funded Shops | Interventions |
| :--- | :--- | :--- | :--- | :--- | :---: | :--- |
| **High** | 50% (2,500,000 LKR) | 12,000 LKR | 2,000 LKR | 0.028 | **~208** | Cooler Subsidy / Display Racks |
| **Medium** | 35% (1,750,000 LKR) | 3,000 LKR | 500 LKR | 0.012 | **~583** | Promotional Discount Vouchers |
| **Low** | 15% (750,000 LKR) | 800 LKR | 500 LKR | 0.004 | **~937** | Table Stands & Table card POS |
| **None** | 0% | 0 LKR | 0 LKR | 0.000 | **~7,272** | None |
| **Total** | **100% (5,000,000 LKR)** | — | — | — | **~1,728 (19.2%)** | **Market Coverage increased by 3.5x!** |

---

## 2. Mathematical Framework

### A. Normalized ROI Score
To maximize volume uplift, we evaluate each outlet's Return on Investment (ROI) based on a normalized, weighted composite score across four operational and spatial signals:

`ROI = 0.40 * norm(uplift_gap) + 0.30 * norm(gravity_score) + 0.20 * norm(recent_sales) + 0.10 * norm(cooler_count)`

Where:
* `uplift_gap`: Headroom to grow, calculated as `max(0, predicted_potential - recent_3m_avg)`.
* `gravity_score`: Spatial footfall potential from the gravity/distance-decay model.
* `recent_sales`: Proven sales baseline (prevents cold-start marketing risks).
* `cooler_count`: Storage/absorption physical capacity.
* `norm()`: Min-max scaling to range `[0, 1]` across eligible Western Province outlets.

### B. The "Headroom-Cap" Spend Limit
Because the optimization objective is linear with respect to spend:

`Projected Uplift (Liters) = Spend (LKR) * Volume per LKR[tier]`

An outlet cannot grow beyond its actual physical ceiling (`uplift_gap_litres`). To prevent allocating "wasted" budget to shops with low headroom, we define a **dynamic, headroom-scaled maximum allocation cap**:

`Max Allocation = min(Tier Cap, Uplift Gap / Volume per LKR)`

We then round this dynamic allocation to the **nearest multiple of 50 LKR** for clean, professional business transactions:

`Max Allocation = round(Max Allocation / 50) * 50`

If the rounded amount falls below the minimum meaningful spend (`Tier Floor`), the allocation is set to 0.

---

## 3. Operational Spending Capacity & Activity Constraints
Before allocating any spend, we check if the outlet has the **operational capability** to utilize it:
1. **Activity Check:** If `recent_3m_avg == 0` or `uplift_gap == 0`, the allocation is immediately forced to 0 LKR.
2. **Physical Layout Caps:** Outlets classified as `Small` size, or of type `Kiosk` or `Pharmacy`, physically cannot support large commercial beverage cooler grants. Their tier is **programmatically capped at Medium tier (3,000 LKR cap)**, even if their ROI score falls in the top 15%. This ensures every rupee allocated corresponds to an intervention they have space for.

---

## 4. Optimization & Guardrails Enforcement

### A. The Greedy Knapsack Algorithm
1. Sort all Western Province outlets by `roi_score` descending.
2. Track three remaining budget variables:
   * `high_budget_remaining = 2,500,000.0`
   * `med_budget_remaining = 1,750,000.0`
   * `low_budget_remaining = 750,000.0`
3. Loop through sorted outlets. For each outlet:
   * Identify its tier (`High`, `Medium`, or `Low`).
   * Allocate `spend = min(Max Allocation, corresponding_budget_remaining)`.
   * Round to nearest 50 LKR.
   * If `spend < Tier Floor`, set `spend = 0.0`.
   * Deduct `spend` from the corresponding budget bucket.

### B. Leftover Redistribution Pass
Sum any leftover budgets from the three buckets (due to floor cuts). Distribute the sum in 50 LKR increments to the highest-ROI funded High-tier stores up to their absolute tier caps, achieving a perfect 5,000,000.00 LKR total allocation.

### C. Distributor Share Guardrail (>= 25% each)
The three distributors (`DIST_W_01`, `DIST_W_02`, `DIST_W_03`) must each receive at least 1,250,000 LKR of the budget. 
* If any distributor falls below this limit, we perform a **rebalancing pass**:
  * Shift spend from the lowest-ROI funded outlets of the over-allocated distributor to the highest-ROI unallocated outlets of the under-allocated distributor until all distributor shares are >= 25%.

---

## 5. Verification Plan & Assertions
1. **Total Budget Check:** Assert `sum(Trade_Spend_Allocation_LKR) == 5,000,000` exactly.
2. **Boundary Floor Check:** Assert no funded outlet receives less than 500 LKR.
3. **High Cap Check:** Assert no outlet gets more than 12,000 LKR.
4. **Province Check:** Assert 100% of allocations are in the Western Province.
5. **Completeness Check:** Assert that the final submission file contains all Western province outlets with exactly two columns: `Outlet_ID`, `Trade_Spend_Allocation_LKR`.
6. **Operational Cap Check:** Assert that no `Small` outlet, `Pharmacy`, or `Kiosk` has a spend > 3,000 LKR.
7. **Coverage Check:** Assert that the total number of funded outlets is $\ge 1,000$ (representing $\ge 11\%$ market coverage).
8. **Rounding Check:** Assert all allocations are clean multiples of 50 LKR.
