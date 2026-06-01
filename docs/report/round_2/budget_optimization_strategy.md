# Phase 2: Budget Optimization Strategy

## 1. Executive Summary
Objective: Distribute a strict 5,000,000 LKR trade marketing budget among traditional trade outlets in the Western Province using a "Potential-Based Allocation" framework.

Through the implementation of the Tier-Budget Capped Greedy Knapsack optimization engine, we successfully achieved a **3.5x Market Footprint Boost**, increasing the total number of funded outlets from 548 (6.1%) to **1,730 outlets (19.2% market coverage)**.

## 2. Final Succeeded Strategy: Tier-Budget Capped Greedy Knapsack

We adopted the **"Balanced Portfolio" (Option A)** approach. Rather than allocating the entire 5M LKR dynamically based solely on continuous ROI limits, we partitioned the overall budget into strict tier-specific budget buckets. This ensures maximum market footprint across the Western Province.

### The ROI Allocation Engine
Each outlet in the Western Province was assigned an `roi_score` based on four critical factors to maximize volume uplift:
`ROI = 0.40 * norm(uplift_gap) + 0.30 * norm(gravity_score) + 0.20 * norm(recent_sales) + 0.10 * norm(cooler_count)`

*Note on Data Fallbacks:*
*   If `recent_3m_avg` is missing, we fall back to `hist_mean_monthly`.
*   If `composite_gravity_score` is missing, we fall back to `poi_total_1km` or default to `50.0`.

## 3. Summary of Tiers & Price Allocation (Execution Results)

The 5,000,000 LKR budget is strictly partitioned across three tiers based on predefined Trade Marketing Packages. All allocations are dynamically capped by the outlet's **Headroom** (`uplift_gap_litres / efficiency`), ensuring we don't overspend beyond an outlet's physical capability to grow.

| Tier | Tier Budget Bucket | Per-Shop Cap | Per-Shop Floor | Volume/LKR | Trade Marketing Package | Final Funded Outlets | Final Total Spend (LKR) |
| :--- | :--- | :--- | :--- | :--- | :--- | :---: | :--- |
| **High** (Top 15%) | 2,500,000 LKR (50%) | 12,000 LKR | 2,000 LKR | 0.028 | Cooler Subsidy / Display Racks | **209** | **2,500,250.00** |
| **Medium** (Next 35%)| 1,750,000 LKR (35%) | 3,000 LKR | 500 LKR | 0.012 | Promotional Discount Vouchers | **584** | **1,750,150.00** |
| **Low** (Next 15%) | 750,000 LKR (15%) | 800 LKR | 500 LKR | 0.004 | Light Merchandising (Posters) | **937** | **749,600.00** |
| **None** | 0 LKR (0%) | 0 LKR | 0 LKR | 0.000 | No Allocation | **7,270** | **0.00** |
| **Total** | **5,000,000 LKR (100%)**| — | — | — | — | **1,730** | **5,000,000.00** |

## 4. Optimization & Operational Guardrails

1.  **Dynamic Headroom Capping:** `Max Allocation = min(Tier Cap, Uplift Gap / Volume per LKR)`.
2.  **Physical Layout & Size Constraints:** Outlets classified as `Small` size, or of type `Kiosk` or `Pharmacy`, physically cannot support large commercial beverage cooler grants. Their tier is programmatically capped at the Medium tier (3,000 LKR max), even if their ROI score falls in the top 15%. This ensures every rupee allocated corresponds to an intervention they have space for.
3.  **Cold-Start Cap:** Outlets with no transaction history (`has_transaction_history == False`) are similarly capped at the Medium tier to mitigate risk.
4.  **Greedy Knapsack Loop:** We sort outlets by ROI descending, allocating up to their Headroom Cap out of their corresponding Tier's Budget Bucket, rounding to the nearest 50 LKR.
5.  **Leftover Redistribution:** Any budget remaining after the initial pass is aggressively redistributed to active High-tier outlets up to their tier caps to ensure the total allocated equals exactly 5,000,000 LKR.
6.  **Distributor Guardrail Rebalancing:** A post-pass algorithm reallocates spend from over-funded distributors to under-funded ones until all three distributors (`DIST_W_01`, `DIST_W_02`, `DIST_W_03`) receive $\ge$ 25% (1.25M LKR) of the budget. It shifts 50 LKR increments from the lowest-ROI funded outlet of the over-allocated distributor to the highest-ROI eligible outlet of the under-allocated distributor.
7.  **Final Micro-adjustments:** A final balancing pass forces the exact 5,000,000 LKR total by adjusting active allocations up or down within a strict 50 LKR tolerance (up to 100 LKR over cap).

## 5. ROI Distribution

The following chart illustrates the Pareto right-skewed distribution of ROI scores across the Western Province, highlighting why a concentrated tier-based approach is superior to a flat distribution.

![ROI Distribution Plot](file:///c:/Users/sithu/My%20Works/My%20Softwares/Competitions/DataStorm3_ML_DS/BigBugDataStorm/data/Optimizations/roi_distribution.png)

## 6. Failed Strategies & Discarded Logic

During the architectural design and iteration, several approaches were implemented but subsequently failed assertion tests or operational constraints, leading to our final refined strategy:

| Failed Strategy | Reasoning for Failure & Solution |
| :--- | :--- |
| **Continuous Variable Allocation (e.g., 1,234.50 LKR)** | Mathematically optimal but operationally impossible. A sales rep cannot purchase "1,234.50 LKR worth of marketing." **Fix:** Round all allocations to exactly 50 LKR multiples. |
| **Uncapped Maximum Spend** | The algorithm allocated nearly 1,000,000 LKR to single top-performing supermarkets, exhausting the budget instantly. **Fix:** Introduced a 12,000 LKR absolute per-shop cap (High tier). |
| **Lack of Headroom Constraints** | Early iterations allocated the full 12,000 LKR to a shop with an `uplift_gap` of only 10 Liters, wasting marketing budget. **Fix:** Introduced the `max_headroom_allocation` dynamic cap. |
| **No Minimum Spend Floor** | The algorithm distributed fractional 50 LKR amounts to thousands of shops at the tail end. 50 LKR buys nothing in Sri Lanka. **Fix:** Enforced a **500 LKR Minimum Floor**. |
| **Micro-Adjustment Loop Infinite Loops** | While forcing the final budget to exactly 5,000,000.00 LKR, the loop failed assertions because it violated the `max_headroom_allocation` by pushing extra funds into capped shops. **Fix:** We strictly enforced `min(tier_cap, headroom_cap + 100)` in the micro-adjustment loop, allowing a maximum 100 LKR tolerance for balancing. |
| **Distributor Shortfalls** | Initial Knapsack runs heavily favoured `DIST_W_01`, leaving others under the 25% minimum guardrail limit. **Fix:** Developed the Rebalancing Pass (Pass 7) to shift 50 LKR chunks from lowest-ROI over-funded shops to highest-ROI under-funded shops. |
