# Budget Optimization Spec — 5M LKR Trade Marketing Allocation

## Objective

Allocate a fixed budget of **LKR 5,000,000** across Western Province outlets to
maximise total projected volume uplift (litres). Only the ~6,842 outlets serviced
by `DIST_W_01`, `DIST_W_02`, and `DIST_W_03` are eligible for allocation.

The output is `outputs/teamname_budget_allocations.csv` with columns:
`Outlet_ID`, `Trade_Spend_Allocation_LKR`.

All logic lives in `modelling/optimise_budget.py`.

---

## Core intuition

Historical sales are a censored lower bound on true demand. The gap between an
outlet's `hist_p90_monthly` (demand ceiling proxy) and its `recent_3m_avg`
(current constrained performance) is the **uplift gap** — the volume we believe
is being suppressed by operational constraints (credit limits, stock, cooler
capacity). Trade marketing spend is the lever to release that suppressed demand.

Outlets with a large uplift gap AND structural drivers to sustain higher volumes
(high footfall, good cooler capacity, strong transit access) are the highest-ROI
targets. Outlets already near their ceiling should receive minimal spend — they
are constrained by market size, not operational friction.

---

## Step 1 — Filter to Western Province

```python
western_distributor_ids = {"DIST_W_01", "DIST_W_02", "DIST_W_03"}
df_west = master_features[master_features["distributor_id"].isin(western_distributor_ids)].copy()
```

All ~6,842 Western outlets receive a row in the output. Outlets that receive zero
allocation (see floor rule below) are still present with `Trade_Spend_Allocation_LKR = 0`.

---

## Step 2 — Compute the uplift gap

```python
df_west["uplift_gap_litres"] = (
    df_west["predicted_potential_litres"] - df_west["recent_3m_avg"]
).clip(lower=0)
```

- `predicted_potential_litres` comes from `outputs/teamname_predictions.csv`
- `recent_3m_avg` comes from `data/gold/sales_features.parquet`
- Clipped at 0 — we do not allocate spend to outlets already exceeding their predicted ceiling

---

## Step 3 — Compute ROI score

The ROI score ranks outlets by the expected return per rupee of trade spend.
It is a weighted composite of four signals, each normalised to [0, 1] using
min-max scaling across the Western Province cohort only.

```
roi_score = (
    0.40 × norm(uplift_gap_litres)      +   # headroom to grow
    0.30 × norm(composite_gravity_score) +   # structural footfall potential
    0.20 × norm(recent_3m_avg)           +   # proven demand — not a cold start
    0.10 × norm(cooler_count)                # physical capacity to absorb stock
)
```

Normalisation formula (applied per-column, Western cohort only):

```python
def minmax(series):
    return (series - series.min()) / (series.max() - series.min() + 1e-9)
```

ROI score is stored in `data/gold/budget_features.parquet` and served via
`GET /outlets/{outlet_id}` as `budget.roi_score`.

---

## Step 4 — Tier classification

Outlets are segmented into three spend tiers based on ROI score percentiles
within the Western Province cohort.

| Tier | ROI score percentile | Spend strategy | Per-outlet cap (LKR) |
|------|---------------------|----------------|----------------------|
| `high` | Top 10% (≥ P90) | Cooler grant + promotional stock | 12,000 |
| `medium` | P40–P90 | Discount vouchers + display material | 3,000 |
| `low` | Below P40 | Minimal promotional material only | 800 |

Outlets with `uplift_gap_litres == 0` are automatically set to `tier = "low"`
regardless of ROI score — they are at or above their ceiling.

Outlets with `has_transaction_history == False` (cold-start outlets) are capped
at `tier = "medium"` — we cannot validate their ROI score with historical evidence.

---

## Step 5 — Allocation optimisation

### Objective function

Maximise total projected volume uplift subject to the budget constraint:

```
maximise:  Σ  allocation_i × volume_per_lkr_i
subject to:
    Σ allocation_i ≤ 5,000,000          (budget constraint)
    0 ≤ allocation_i ≤ tier_cap_i       (per-outlet cap)
    allocation_i ≥ tier_floor_i  if roi_score_i ≥ threshold   (minimum meaningful spend)
```

### Volume per LKR estimate

```python
# Estimated litres of uplift per LKR spent, by tier
volume_per_lkr = {
    "high":   0.028,   # ~28 ml per rupee — high-ROI outlets convert spend efficiently
    "medium": 0.012,   # ~12 ml per rupee
    "low":    0.004,   # ~4 ml per rupee — diminishing returns
}
```

These rates are calibrated from FMCG trade marketing benchmarks and are stored
in `config.yaml` under `budget_optimization.volume_per_lkr` so they can be tuned.

### Implementation approach

Use `scipy.optimize.linprog` for linear programming, or a greedy knapsack
as a simpler-to-explain fallback:

**Greedy knapsack (preferred for explainability):**

1. Sort all Western outlets by `roi_score` descending
2. Iterate through the sorted list
3. Assign each outlet its tier maximum allocation if budget remains
4. If remaining budget < tier maximum, assign the remaining budget to that outlet
5. Stop when budget is exhausted

The greedy approach is near-optimal for this problem structure (all items are
divisible) and is far easier to justify to a business audience than LP output.

```python
df_west = df_west.sort_values("roi_score", ascending=False)
budget_remaining = 5_000_000
allocations = []

for _, row in df_west.iterrows():
    cap = TIER_CAPS[row["allocation_tier"]]
    floor = TIER_FLOORS[row["allocation_tier"]]
    spend = min(cap, budget_remaining)
    if spend < floor:
        spend = 0   # don't allocate below minimum meaningful spend
    allocations.append(spend)
    budget_remaining -= spend
    if budget_remaining <= 0:
        break

# Remaining outlets get 0
```

---

## Step 6 — Constraints and guardrails

The following hard rules are applied as post-processing after the greedy allocation:

| Rule | Implementation |
|------|---------------|
| Budget must not exceed 5,000,000 LKR | Assert `sum(allocations) <= 5_000_000` |
| No outlet receives a negative allocation | `clip(lower=0)` |
| No allocation below the tier floor unless it is zero | Floor enforcement in loop |
| All 3 distributors must receive at least 25% of budget | Minimum distributor share guard |
| Min 60% of budget must go to `high` and `medium` tiers | Tier share assertion |
| Cold-start outlets (no history) receive at most `medium` tier spend | `has_transaction_history` guard |

The minimum distributor share guard prevents the optimizer from concentrating all
spend on a single distributor's top performers. If after the greedy pass any
distributor holds less than 25% of the total allocation, top-up their lowest-ROI
outlets until the constraint is satisfied, redistributing from the lowest-ROI
outlets of the over-allocated distributor.

---

## Step 7 — Output

```python
budget_output = df_west[["Outlet_ID"]].copy()
budget_output["Trade_Spend_Allocation_LKR"] = allocations
budget_output["Trade_Spend_Allocation_LKR"] = budget_output[
    "Trade_Spend_Allocation_LKR"
].round(2)
budget_output.to_csv("outputs/teamname_budget_allocations.csv", index=False)
```

Additionally, write `data/gold/budget_features.parquet` with the full intermediate
columns for the API and the web app to consume:

| Column | Type | Notes |
|--------|------|-------|
| Outlet_ID | string | Primary key |
| uplift_gap_litres | float32 | Predicted potential − recent 3m avg |
| roi_score | float32 | Weighted composite [0, 1] |
| allocation_tier | string | `high`, `medium`, or `low` |
| trade_spend_allocation_lkr | float32 | Final allocation |
| recommended_spend_type | string | `cooler_grant`, `discount_voucher`, `display_material` |
| projected_volume_uplift_litres | float32 | `allocation × volume_per_lkr[tier]` |
| is_western_province | bool | Always True for rows in this table |

---

## Tunable parameters in `config.yaml`

```yaml
budget_optimization:
  total_budget_lkr: 5_000_000
  tier_thresholds:
    high_percentile: 90        # top 10% → high tier
    medium_percentile: 40      # P40–P90 → medium tier
  tier_caps_lkr:
    high: 12000
    medium: 3000
    low: 800
  tier_floors_lkr:
    high: 2000
    medium: 500
    low: 0                     # low-tier outlets can receive zero
  volume_per_lkr:
    high: 0.028
    medium: 0.012
    low: 0.004
  roi_weights:
    uplift_gap: 0.40
    gravity_score: 0.30
    recent_volume: 0.20
    cooler_count: 0.10
  distributor_min_share: 0.25  # each distributor gets at least 25% of budget
  tier_min_combined_share: 0.60  # high + medium tiers get at least 60% of budget
```
