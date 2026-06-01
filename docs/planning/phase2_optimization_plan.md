# Phase 2: Budget Optimization — Detailed Implementation Plan

## Overview

This plan focuses exclusively on **Phase 2: Budget Optimization**. We will implement the script `pipeline/optimizations/optimise_budget.py`, which is responsible for distributing a strict 5,000,000 LKR trade marketing budget among traditional trade outlets in the Western Province.

The goal is to move away from historical-based flat allocations and instead use a **Potential-Based Allocation** model. By applying the Pareto Principle (80/20 rule), we will aggressively target the budget at high-ROI outlets where interventions (cooler grants, promotions) will drive the maximum incremental volume.

## 1. Input Datasets

| Dataset               | Location                                | Required Columns                                                                                     |
| --------------------- | --------------------------------------- | ---------------------------------------------------------------------------------------------------- |
| **Master Features**   | `Data/Gold/master_features.parquet`     | `Outlet_ID`, `province`, `hist_mean_monthly`, `composite_gravity_score`, `competition_density_score` |
| **Model Predictions** | `outputs/round2/bigbug_predictions.csv` | `Outlet_ID`, `Maximum_Monthly_Liters`                                                                |

## 2. Mathematical Framework & Business Logic

### A. The ROI Composite Score

To maximize volume uplift, we evaluate each outlet's Return on Investment (ROI) based on three factors. We use the **Composite Gravity Score** as our spatial driver, as it more accurately models distance-decay interactions with local POIs than a flat footfall metric.

1. **Untapped Volume:** The gap between current sales and predicted potential.
2. **Spatial Demand (Gravity):** The `composite_gravity_score` capturing distance-weighted proximity to key POIs (transit, schools, hospitals, etc.).
3. **Market Saturation:** The lack of nearby competition (less competition means interventions capture more market share).

**Formula:**

```python
uplift_gap = max(0, predicted_potential - hist_mean_monthly)

# Normalize gravity score to a 0-1 multiplier
gravity_multiplier = composite_gravity_score / 100.0

# Inverse competition multiplier (high competition reduces the score)
competition_multiplier = 1.0 / (1.0 + competition_density_score)

roi_score = uplift_gap * gravity_multiplier * competition_multiplier
```

---

## 3. Trade Marketing Investment Menu (Sri Lankan Market Prices)

The following table lists actionable trade marketing interventions available in the Sri Lankan FMCG/beverage sector, with verified market prices as of 2024–2025. These are the real-world investments the company can deploy at each outlet.

| #   | Investment Type                        | Description                                                                          | Unit Cost (LKR) | Notes                                                                            |
| --- | -------------------------------------- | ------------------------------------------------------------------------------------ | --------------- | -------------------------------------------------------------------------------- |
| 1   | **A3/A2 POS Poster**                   | Branded poster at point-of-sale (counter/wall)                                       | 240 – 1,780     | Digital print, per unit. Bulk offset printing is cheaper.                        |
| 2   | **POS Sticker / Label Set**            | Branded stickers for shelves, doors, coolers                                         | 35 – 120        | A4 sticker sheets, per unit                                                      |
| 3   | **Tent Card / Table Stand**            | A5 branded tent card with table frame                                                | 850 – 1,500     | For counter-top display                                                          |
| 4   | **Flex Banner (Small)**                | Outdoor/indoor flex banner for shop front                                            | 1,000 – 3,000   | Priced per sq ft; a small 2×3 ft banner                                          |
| 5   | **Promotional Discount Voucher**       | Volume-based discount booklet for the retailer                                       | 500 – 2,000     | Per outlet; value of the discount itself                                         |
| 6   | **Bundled Product Offer**              | Free product units bundled with a bulk order                                         | 1,500 – 5,000   | Cost of free goods provided                                                      |
| 7   | **Branded Display Rack**               | Small metal/plastic branded product rack                                             | 3,000 – 8,000   | One-time supply, placed at outlet                                                |
| 8   | **Cooler Subsidy (Partial)**           | Partial subsidy towards a mini beverage cooler (40-85L units cost Rs 40,000-120,000) | 5,000 – 15,000  | Not a full cooler grant; a contribution towards one. Full coolers are Rs 40,000+ |
| 9   | **Co-op Marketing Fund**               | Fund for retailer-led local advertising (banner, social)                             | 2,000 – 5,000   | Quarterly co-op budget per outlet                                                |
| 10  | **Sales Contest / Retailer Incentive** | Point-based reward or bonus for hitting volume targets                               | 1,000 – 3,000   | Monthly or quarterly performance incentive                                       |

> **Note:** At a 5M LKR budget across ~6,000 Western Province outlets, we **cannot** afford full cooler grants (Rs 40,000–120,000 each). Instead, the "Cooler Subsidy" in Tier 1 is a **partial contribution** (Rs 5,000–15,000) towards a cooler, combined with branded merchandising. This is realistic and commercially defensible.

---

## 4. Tier / Package Definitions

Each tier represents a curated **package** of interventions, designed around realistic Sri Lankan pricing and the minimum spend needed to create measurable impact.

### Tier 1: "Growth Accelerator" Package — High Priority Outlets

| Attribute                 | Details                                                                                                                                                                                                                                                                                                     |
| ------------------------- | ----------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| **Selection Criteria**    | Top 15% of Western Province outlets by `roi_score`                                                                                                                                                                                                                                                          |
| **Expected Outlet Count** | ~1,000 outlets                                                                                                                                                                                                                                                                                              |
| **Budget Share**          | 50% of 5M = **2,500,000 LKR**                                                                                                                                                                                                                                                                               |
| **Avg. Spend Per Outlet** | ~2,500 LKR (range: 1,500 – 15,000 LKR)                                                                                                                                                                                                                                                                      |
| **Package Contents**      | Cooler Subsidy (Rs 5,000–15,000) OR Branded Display Rack (Rs 3,000–8,000) + A2 POS Poster (Rs 1,780) + Sticker Set (Rs 120)                                                                                                                                                                                 |
| **Use Case**              | High-potential outlets in high-footfall areas with low competition. These outlets have large uplift gaps — they are significantly underperforming relative to their location advantage. A cooler subsidy or branded rack directly removes physical storage/visibility constraints, unlocking latent demand. |
| **Expected Impact**       | 15–25% volume uplift per outlet due to improved product visibility and cold availability                                                                                                                                                                                                                    |

### Tier 2: "Visibility Boost" Package — Medium Priority Outlets

| Attribute                 | Details                                                                                                                                                                                                                                                      |
| ------------------------- | ------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------ |
| **Selection Criteria**    | Next 25% of Western Province outlets by `roi_score` (percentile 60–85)                                                                                                                                                                                       |
| **Expected Outlet Count** | ~1,500 outlets                                                                                                                                                                                                                                               |
| **Budget Share**          | 35% of 5M = **1,750,000 LKR**                                                                                                                                                                                                                                |
| **Avg. Spend Per Outlet** | ~1,167 LKR (range: 500 – 2,000 LKR)                                                                                                                                                                                                                          |
| **Package Contents**      | Promotional Discount Voucher (Rs 500–2,000) + A3 POS Poster (Rs 240–500) + Sticker Set (Rs 120)                                                                                                                                                              |
| **Use Case**              | Outlets with moderate uplift potential. They have decent gravity scores but may face more local competition. A promotional discount incentivises the retailer to push volume, while POS materials improve brand visibility without heavy capital investment. |
| **Expected Impact**       | 8–15% volume uplift per outlet through promotional pull and improved shelf presence                                                                                                                                                                          |

### Tier 3: "Brand Presence" Package — Low Priority Outlets

| Attribute                 | Details                                                                                                                                                                                                                                                   |
| ------------------------- | --------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| **Selection Criteria**    | Next 25% of Western Province outlets by `roi_score` (percentile 35–60)                                                                                                                                                                                    |
| **Expected Outlet Count** | ~1,500 outlets                                                                                                                                                                                                                                            |
| **Budget Share**          | 15% of 5M = **750,000 LKR**                                                                                                                                                                                                                               |
| **Avg. Spend Per Outlet** | ~500 LKR (fixed at minimum actionable spend)                                                                                                                                                                                                              |
| **Package Contents**      | A3 POS Poster (Rs 240) + Sticker Set (Rs 120) + Tent Card (Rs 140 — basic variant)                                                                                                                                                                        |
| **Use Case**              | Outlets with small but positive uplift. These are typically smaller kades or shops in moderately trafficked areas. They don't justify heavy investment, but light branding materials maintain brand awareness and ensure minimum distribution visibility. |
| **Expected Impact**       | 3–5% volume uplift; primarily a brand awareness play                                                                                                                                                                                                      |

### Tier 4: "No Allocation" — Zero Priority Outlets

| Attribute                 | Details                                                                                                                                                                                                                                                                                                        |
| ------------------------- | -------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| **Selection Criteria**    | Bottom 35% of Western Province outlets by `roi_score`                                                                                                                                                                                                                                                          |
| **Expected Outlet Count** | ~2,000 outlets                                                                                                                                                                                                                                                                                                 |
| **Budget Share**          | 0%                                                                                                                                                                                                                                                                                                             |
| **Avg. Spend Per Outlet** | Rs 0                                                                                                                                                                                                                                                                                                           |
| **Package Contents**      | None                                                                                                                                                                                                                                                                                                           |
| **Use Case**              | Outlets that are already operating near their ceiling (minimal uplift gap), are in extremely saturated competitive zones, or have very low gravity scores (isolated locations with negligible foot traffic). Any investment here yields near-zero incremental volume — the Rs 500 minimum cannot be justified. |

### Budget Allocation Summary Table

| Tier  | Package Name       | Outlets    | % of Western Outlets | Budget (LKR)  | Avg/Outlet (LKR) | Recommended Spend Type        |
| ----- | ------------------ | ---------- | -------------------- | ------------- | ---------------- | ----------------------------- |
| **1** | Growth Accelerator | ~1,000     | 15%                  | 2,500,000     | ~2,500           | Cooler Subsidy / Display Rack |
| **2** | Visibility Boost   | ~1,500     | 25%                  | 1,750,000     | ~1,167           | Promotional Discount          |
| **3** | Brand Presence     | ~1,500     | 25%                  | 750,000       | ~500             | Light Merchandising           |
| **4** | No Allocation      | ~2,000     | 35%                  | 0             | 0                | None                          |
|       | **TOTAL**          | **~6,000** | **100%**             | **5,000,000** |                  |                               |

---

## 5. ROI Score Distribution — Expected Shape

> **"Should the `roi_distribution.png` contain a bell curve?"**

**No, it will almost certainly NOT be a bell curve.** The ROI score distribution is expected to be **right-skewed (positively skewed)**. Here's why:

- The ROI score is a product of three non-negative values (`uplift_gap × gravity_multiplier × competition_multiplier`).
- Most outlets will have a modest uplift gap and moderate gravity, producing small-to-medium ROI scores.
- A small number of outlets will have an extremely high combination of all three factors, creating a long right tail.
- Many outlets will cluster near zero (especially those with near-zero uplift gap, i.e., already at potential).

**Expected shape:**

```
Frequency
│ ██
│ ████
│ ██████
│ █████████
│ █████████████
│ ████████████████████                ← Most outlets here (low-medium ROI)
│ █████████████████████████████░░░░░░░░░  ← Long right tail (few high-ROI outlets)
└─────────────────────────────────────────── ROI Score
  [  None  ][   Low   ][  Medium  ][ High ]
```

The plot will use **colored bands** to show where the tier cutoffs fall on this distribution. The "High" tier will capture the outlets in that thin right tail — exactly the Pareto minority that delivers the majority of the return.

---

## 6. Proposed Code Structure

### `pipeline/optimizations/optimise_budget.py`

1. **Load Data:** Read `master_features.parquet` and `bigbug_predictions.csv`. Merge on `Outlet_ID`.
2. **Filter Province:** Isolate outlets where `province == 'Western'`.
3. **Calculate ROI:** Compute `uplift_gap_litres` and `roi_score` using `composite_gravity_score`.
4. **Rank & Tier:** Sort descending by `roi_score`. Assign `roi_rank` (1 = best). Compute percentile cutoffs and assign `allocation_tier`.
5. **Base Allocation & Budget Balancing:** Assign base monetary values per tier. Run a correction loop to exactly hit 5,000,000 LKR.
6. **Assign Spend Type:** Map tier to `recommended_spend_type` ("Cooler Subsidy / Display Rack", "Promotional Discount", "Light Merchandising", "None").
7. **Re-combine:** Merge Western outlets back with non-Western outlets (allocation = 0).
8. **Generate Plot:** `matplotlib`/`seaborn` histogram of Frequency vs ROI Score with colored tier bands. Save to `data/optimizations/roi_distribution.png`.
9. **Export Files:** Write all output artifacts.

---

## 7. Required Output Artifacts

Outputs are saved to the following directories:

### Saved in `outputs/`

| #   | File                            | Description                                                                                                                                                                                                                    |
| --- | ------------------------------- | ------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------ |
| 1   | `bigbug_budget_allocations.csv` | Competition submission. **Two columns only:** `Outlet_ID`, `Trade_Spend_Allocation_LKR`. Contains strictly Western province outlets.                                                                                           |
| 2   | `budget_diagnostics.csv`        | Full diagnostics with `Outlet_ID`, `province`, `uplift_gap_litres`, `composite_gravity_score`, `competition_density_score`, `roi_score`, `roi_rank`, `allocation_tier`, `recommended_spend_type`, `Trade_Spend_Allocation_LKR` |
| 4   | `roi_distribution.png`          | Histogram of Frequency vs ROI Score with color-banded tier cutoffs                                                                                                                                                             |

### Saved in `data/Optimization/`

| #   | File                      | Description                                                                 |
| --- | ------------------------- | --------------------------------------------------------------------------- |
| 3   | `budget_features.parquet` | Same as `budget_diagnostics.csv` in Parquet format for pipeline consumption |

---

## 8. Verification Plan

1. **Total Budget Check:** Assert that `sum(Trade_Spend_Allocation_LKR) == 5,000,000` exactly.
2. **Boundary Check:** Assert that no outlet is assigned an amount between `1` and `499` LKR (minimum actionable limit is Rs 500).
3. **Cap Check:** Assert that no outlet is assigned more than `15,000` LKR.
4. **Province Check:** Assert that all `Trade_Spend_Allocation_LKR > 0` are strictly bound to Western province.
5. **Completeness Check:** Assert the final `bigbug_budget_allocations.csv` contains ~9,000 unique `Outlet_ID`s from the Western Province with exactly two columns.
6. **Tier Integrity Check:** Assert that every outlet with `allocation_tier == "None"` has `Trade_Spend_Allocation_LKR == 0` and vice versa.
