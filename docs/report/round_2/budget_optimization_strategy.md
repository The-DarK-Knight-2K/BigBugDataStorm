# Phase 2: Budget Optimization Strategy

This document outlines the methodology, strategic decisions, and discarded options for the **Phase 2 Budget Optimization** module (`pipeline/optimizations/optimise_budget.py`). Our core objective was to distribute a strict **5,000,000 LKR** trade marketing budget among traditional trade outlets in the Western Province using a "Potential-Based Allocation" framework.

---

## 1. Core Methodology

Our approach bridges the gap between theoretical data science and practical business execution. Rather than blindly allocating funds based on historical sales, we calculate an "Opportunity Score" (ROI Score) for every outlet and algorithmically allocate the budget to maximize **Net Financial Profit**.

### The ROI Allocation Engine
Each outlet in the Western Province was assigned an `roi_score` based on three critical factors:
1. **Untapped Volume Gap:** The difference between the model's predicted potential and the outlet's historical average.
2. **Spatial Demand (Gravity):** Distance-weighted proximity to key POIs (transit, schools, hospitals) using the `composite_gravity_score`. Close, high-traffic POIs act as a multiplier.
3. **Market Saturation (Competition):** The lack of nearby competition. Outlets in highly saturated areas are penalized, as interventions there often result in cannibalization rather than true market expansion.

---

## 2. Strategic Decisions & The Pareto Principle

### The Pareto Principle (80/20 Rule)
A critical business decision was to avoid spreading the 5,000,000 LKR budget thinly across all 20,000 outlets. The generated `roi_distribution` revealed a heavy right-skew: the vast majority of outlets have very low opportunity potential, while a small minority possess massive untapped potential. 

We applied the **Pareto Principle**, aggressively targeting the budget strictly at the high-ROI outlets (the long right-tail). By concentrating the spend on the top ~35% of eligible outlets, we maximize the incremental volume yield per Rupee spent.

### Tier-Based "Packages" over Continuous Allocation
We replaced abstract mathematical allocations with actionable, real-world **Trade Marketing Packages**:
*   **Tier 1 (High Priority):** Cooler Subsidies & Display Racks (Max 15,000 LKR). Target: Outlets with massive volume gaps and spatial dominance.
*   **Tier 2 (Medium Priority):** Promotional Discount Vouchers (~1,000 - 2,000 LKR). Target: Outlets needing a volume pull mechanism.
*   **Tier 3 (Low Priority):** Light Merchandising (Posters/Stickers, ~500 LKR). Target: Brand presence maintenance.
*   **Tier 4 (Zero Priority):** No Allocation. Target: Outlets already operating at their ceiling or in hyper-competitive zones.

### Automated Hyperparameter Tuning (Grid Search)
Instead of manually guessing the tier boundaries (e.g., "Top 15% gets Tier 1"), we implemented an **Automated Grid Search**. The algorithm iterates through hundreds of percentile configurations, calculating the projected Net Profit for each scenario. It automatically selects the configuration that maximizes profit while adhering to the 5M budget constraint.

### Financial Viability Tracking
To ensure the optimization makes commercial sense, we introduced a dummy **Gross Profit Margin of 50 LKR per Liter**. By projecting the expected volume lift from the assigned tiers and subtracting the cost of the intervention, the algorithm explicitly optimizes for **Net Profit**, proving business viability to leadership.

---

## 3. Discarded Options & Reasoning

During the architectural design, several approaches were discarded to preserve real-world operational feasibility:

| Discarded Option | Reasoning |
| :--- | :--- |
| **Continuous Variable Allocation (e.g., 1,234.50 LKR)** | Mathematically optimal but operationally impossible. A sales rep cannot purchase "1,234.50 LKR worth of marketing." Allocations must map to physical goods or standard discount booklets. We adopted Tiered Packages instead. |
| **Strict 5,000,000.00 LKR exact matching** | Forcing the algorithm to spend exactly down to the last cent results in fractional allocations. We opted for a `<=` 5,000,000 LKR constraint, allowing the algorithm to stop once it maximizes profit, which is standard financial practice. |
| **Uncapped Maximum Spend** | Without caps, the algorithm might allocate 1,000,000 LKR to a single high-potential supermarket. We introduced a **15,000 LKR Maximum Cap** because a traditional trade shop physically cannot absorb infinite marketing or cooler space. |
| **No Minimum Spend Floor** | The algorithm might allocate 50 LKR to thousands of shops. 50 LKR buys nothing in Sri Lanka. We enforced a **500 LKR Minimum Floor**—the exact cost of the cheapest physical intervention (an A3 Poster + Sticker Set). |
| **Full Cooler Grants (40,000+ LKR)** | A full cooler is too expensive for a 5M total budget; it would drain the budget on just ~100 shops. We reduced Tier 1 to a **Partial Cooler Subsidy** (up to 15,000 LKR), requiring retailer co-investment, which is standard industry practice. |
| **Exact Penny Rounding** | We instituted a rule that all allocated spend must be a **multiple of 50 LKR** rounded up. This makes cash/voucher accounting dramatically easier for the regional distributors and sales teams on the ground. |
