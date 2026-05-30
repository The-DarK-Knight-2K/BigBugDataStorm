# Target Value Generation Strategies — Implemented

This document outlines the target variable generation strategies that have been **actively implemented** in the current modelling pipeline.

---

## Approach 1: The "Direct January" Approach ✓ IMPLEMENTED

### Overview
Because FMCG sales are highly seasonal, January behaves very differently than other months (e.g., post-holiday restocking, Thai Pongal local festival effects). This approach isolates the modelling problem to predicting Januaries only.

### Implementation Details

**Training Target Formula** (in `modelling/train.py`):
```python
target = hist_p90_monthly 
       × seasonality_multiplier_jan_2026 
       × (jan_2026_trading_days / 22.0)
```

**Components**:
1. **`hist_p90_monthly`** — 90th percentile of historical monthly volumes (robust to outliers, more conservative than raw maximum)
2. **`seasonality_multiplier_jan_2026`** — Derived from distributor-level seasonality index:
   - "Favorable" → 1.20x
   - "Moderate" → 1.00x
   - "Un-Favorable" → 0.85x
3. **`jan_2026_trading_days / 22.0`** — Adjustment for January 2026 having a different number of working days compared to the average month (22 days)

### Training Data Generation

| Training Record | X (Features) | y (Target) |
|---|---|---|
| Record 1 | Features calculated using all data up to Dec 2024 | January 2025 volume (adjusted) |
| Record 2 | Features calculated using all data up to Dec 2024 | Target from p90 + seasonality + trading days |
| ... | ... | ... |

### Dataset Size
- Training samples: ~19,960 outlets (20,000 minus ~40 with quarantined/missing coordinates)
- For each outlet: Single training record (cross-sectional, not time-series)

### Advantages
✓ Model perfectly learns January-specific seasonal nuances
✓ Prevents confusion from other months' dynamics
✓ Direct alignment with competition target (maximize January demand)
✓ Seasonality multiplier provides regional adjustment

### Limitations
✓ Requires January-specific features (`jan_avg_volume`, `jan_count`, etc.)
✓ Relies on distributor-level seasonality being predictive of outlet behavior

### Code Location
- **Target construction**: [`modelling/train.py`](modelling/train.py#L145-L156)
- **Pseudo-label formula**:
  ```python
  df_train["target"] = (
      df_train["hist_p90_monthly"]
      * df_train["seasonality_multiplier_jan_2026"]
      * (df_train["jan_2026_trading_days"] / 22.0)
  )
  ```

---

## Baseline Heuristic: January-Anchored Estimation ✓ IMPLEMENTED

### Overview
The baseline serves as a **floor** for model predictions — the trained model prediction is never allowed to go below this value. It uses a multi-path January-anchored estimation strategy.

### Implementation Details

**File**: `modelling/baseline.py`

**Baseline Formula**:
```
baseline = jan_demand 
         × recency_factor 
         × seasonality_multiplier_jan_2026 
         × (jan_2026_trading_days / 22.0) 
         × poi_uplift

Final baseline = max(estimated_baseline, hist_max_monthly)
```

### Three Estimation Paths

#### Path 1: January-Anchored (Outlets with Jan History)
**Condition**: `jan_count > 0` (outlet has ordered in January before)

**Logic**:
```
jan_demand = max(jan_avg_volume, jan_max_volume × 0.85)
```

**Rationale**: 
- Take the higher of: January average or 85% of January max
- The 0.85 dampening avoids anchoring on a one-off spike
- Most reliable path, uses actual historical January data

#### Path 2: P90 Fallback (Outlets with History but No Jan Orders)
**Condition**: `has_transaction_history == True` AND `jan_count == 0`

**Logic**:
```
jan_demand = hist_p90_monthly
```

**Rationale**: 
- Outlet has never ordered in January despite having history
- Fall back to all-months P90 as conservative estimate
- Prevents underestimation for outlets that never ordered Jan

#### Path 3: Cold-Start (Outlets with No Transaction History)
**Condition**: `has_transaction_history == False`

**Logic**:
```
base = size_medians[Outlet_Size]  # or global_median fallback
jan_demand = base × (1.0 + Cooler_Count × 0.15)
```

**Rationale**: 
- Use median January volume of outlets with same `Outlet_Size`
- Apply `Cooler_Count` multiplier (cooler count ≈ capacity proxy)
- 0.15 per cooler = 15% uplift per cooler unit (tunable)

### Momentum & Recency Adjustment

**Recency Factor Calculation** (in `baseline.py`):
```python
ratio = ema_3m / hist_mean_monthly
recency_factor = max(0.8, min(ratio, 1.3))
```

**Interpretation**:
- EMA 30% above mean → factor = 1.3 (growing outlet)
- EMA equals mean → factor = 1.0 (stable outlet)
- EMA 20% below mean → factor = 0.8 (declining outlet, clamped)

**Rationale**: Captures recent momentum without extreme swings

### POI Uplift Factor

**Footfall Score Logic** (0–100):
- **Low** (0–20): `uplift = 1.00` (no additional potential)
- **Medium** (20–60): `uplift = 1.00 + (footfall - 20) / 40 × 0.10` (linear to 1.10x)
- **High** (60–100): `uplift = 1.10 + (footfall - 60) / 40 × 0.15` (linear to 1.25x)

**Rationale**: 
- Outlets in high-traffic areas have more potential customers
- Especially true for supply-constrained outlets
- Footfall score already accounts for nearby schools, hospitals, transit, markets

### Floor Constraint

```python
baseline = max(baseline, hist_max_monthly)
```

**Rationale**: Never regress below observed reality — if an outlet has ever sold this much, it could potentially sell that much again

### Advantages
✓ January-specific (direct match to competition target)
✓ Three fallback paths handle cold-start and inactive outlets
✓ Incorporates recent momentum via EMA
✓ POI uplift captures untapped potential
✓ Floor constraint prevents underestimation

### Code Location
- **Main function**: [`modelling/baseline.py` - `compute_baseline()`](modelling/baseline.py)
- **Path 1 (Jan)**: Lines ~110–115
- **Path 2 (P90)**: Lines ~116–118
- **Path 3 (Cold-start)**: Lines ~119–120
- **Recency factor**: `_compute_recency_factor()` function
- **POI uplift**: `_compute_poi_uplift()` function

---

## Why Approach 1 Was Chosen

### Comparison with Alternatives

| Aspect | Direct January (Chosen) | Sliding Window | Lagged Growth |
|--------|------------------------|---|---|
| Data points per outlet | 1 | 60+ | 60+ |
| Seasonal specificity | Very High | Medium | Medium |
| Seasonal control | Explicit multiplier | Implicit in features | Implicit in features |
| Interpretability | High | Medium | Low |
| Training complexity | Simple | Medium | Medium |
| CV Performance | 40.38 RMSE | Not tested | Not tested |

**Decision Rationale**:
1. **Direct alignment with target** — Predicting January 2026 using a January-trained model is intuitive
2. **Seasonal control** — Explicit seasonality multiplier allows regional tuning
3. **Feature engineering** — January-specific features already built (`jan_avg_volume`, `jan_count`)
4. **Proven performance** — CatBoost with this approach: CV RMSE 40.38 (vs 40.96 for LightGBM)

---

## Integration with Master Features

### Required Columns in `master_features.parquet`
For Approach 1 to function, the following columns are required:

| Column | Source | Purpose |
|--------|--------|---------|
| `hist_p90_monthly` | `sales_features` | Base target before adjustments |
| `jan_avg_volume` | `sales_features` | January-specific baseline (Path 1) |
| `jan_max_volume` | `sales_features` | Jan spike dampening (Path 1) |
| `jan_count` | `sales_features` | Count of Jan orders (Path selector) |
| `hist_max_monthly` | `sales_features` | Floor constraint |
| `seasonality_multiplier_jan_2026` | Derived in `build_master_features.py` | Regional seasonal adjustment |
| `jan_2026_trading_days` | From `jan_2026_trading_days.json` | Trading day adjustment |
| `has_transaction_history` | Derived in `build_master_features.py` | Cold-start detector |
| `exclude_from_training` | Derived in `build_master_features.py` | Filter for model training |

---

## Summary

**Approach 1: Direct January** has been fully implemented across:

1. ✓ **Training target construction** — `modelling/train.py`
2. ✓ **Baseline floor estimation** — `modelling/baseline.py`
3. ✓ **Feature engineering** — `pipeline/gold/build_sales_features.py`
4. ✓ **Master table integration** — `pipeline/gold/build_master_features.py`
5. ✓ **Data contracts** — `specs/architecture/DATA_CONTRACTS.md`

**Performance**:
- CV RMSE: 40.38 ± 0.XX litres
- CV MAE: ~32.XX litres
- Baseline coverage: Three fallback paths for all 20,000 outlets
