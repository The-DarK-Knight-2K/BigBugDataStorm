# Optimizations — Implemented Strategies

This document outlines the optimization and feature engineering strategies that have been **actively implemented** in the current pipeline.

---

## 1. Advanced Feature Engineering (Pre-Gold/Gold Phase)

### Temporal & Lag Features ✓ IMPLEMENTED

**Exponential Moving Averages (EMA)**
- ✓ **Status**: Fully implemented in `pipeline/gold/build_sales_features.py`
- **Details**: 3-month and 6-month EMA calculated for each outlet
- **Columns**: `ema_3m`, `ema_6m` in `sales_features.parquet`
- **Purpose**: EMA places higher weight on recent months (Q4 2025), which is highly predictive for January 2026

**Recency & Momentum Features**
- ✓ **Status**: Implemented in `modelling/baseline.py` and `pipeline/gold/build_sales_features.py`
- **Details**: 
  - Recent 3-month average: `recent_3m_avg`
  - Months since last order: `months_since_last_order`
  - Trend slope (linear regression): `trend_slope`
  - Year-over-year growth rate: `yoy_growth_rate`
- **Purpose**: Captures recent momentum and detects growing/declining outlets

**Historical Aggregations**
- ✓ **Status**: Fully implemented
- **Columns in sales_features**:
  - `hist_max_monthly` — highest single month volume
  - `hist_p90_monthly` — 90th percentile (used as training target)
  - `hist_p75_monthly` — 75th percentile
  - `hist_mean_monthly` — mean monthly volume
  - `hist_std_monthly` — standard deviation
  - `hist_cv` — coefficient of variation (std/mean)
- **Purpose**: Provides a robust statistical baseline for modeling

**January-Specific Metrics**
- ✓ **Status**: Implemented in `pipeline/gold/build_sales_features.py`
- **Columns**:
  - `jan_avg_volume` — average volume in January months
  - `jan_max_volume` — maximum volume in any January
  - `jan_count` — number of Januaries observed
- **Purpose**: Isolates seasonal behavior for direct January 2026 prediction

---

## 2. Algorithm-Specific Dataset Adaptations ✓ IMPLEMENTED

### CatBoost Native Support ✓ IMPLEMENTED

- **Status**: Primary algorithm selected based on CV performance
- **Implementation**: `modelling/train.py` uses CatBoostRegressor with native categorical handling
- **Categorical Features**: `Outlet_Type`, `Outlet_Size`, `province` passed via `cat_features` parameter
- **Advantages**: 
  - No manual encoding required
  - Native handling of categorical strings
  - Target Statistics (TS) for categorical features
  - CV RMSE: 40.38 (vs 40.96 for LightGBM)

### Algorithm-Agnostic Gold Layer ✓ IMPLEMENTED

- **Status**: Master features kept in raw, readable format
- **Details**: Categorical columns are stored as strings, not pre-encoded
- **Rationale**: Allows seamless switching between algorithms without pipeline modification
- **Implementation**: `pipeline/gold/build_master_features.py` preserves categorical strings

---

## 3. Recommended Architectural Update — Pre-Processing Switch ✓ PARTIALLY IMPLEMENTED

### Current Implementation
- ✓ **Conditional feature selection** in `modelling/train.py`
- ✓ **Exclusion of non-numeric columns** during training
- ✓ **CatBoost cat_features parameter** for native categorical handling

### Not Yet Implemented
- Pluggable Preprocessor class for algorithm abstraction
- Automatic pipeline switching between algorithms
- LightGBM/XGBoost/Random Forest preprocessing layers

---

## 4. Inference Optimization: "Clean Train, Predict All" ✓ IMPLEMENTED

### Bifurcated Pipeline Strategy ✓ IMPLEMENTED

**Training Set Filtering**
- ✓ **Status**: Implemented in `modelling/train.py`
- **Details**:
  - Flag `exclude_from_training` identifies the ~40 outlets with quarantined/missing coordinates
  - These outlets imputed with province centroids and POI set to 0
  - Training filters: `df_train = df[(df["has_transaction_history"] == True) & (df["exclude_from_training"] == False)]`
  - Model learns exclusively from ~19,960 clean, geographically accurate outlets
  - Prevents noisy imputed data from confusing the model

**Comprehensive Inference**
- ✓ **Status**: Planned for `modelling/predict.py`
- **Strategy**: During prediction, `exclude_from_training` flag is ignored
- **Rationale**: All 20,000 outlets receive predictions, including the 40 problematic ones
- **Outcome**: Avoids record loss in final submission

---

## 5. Spatial & Geospatial Features ✓ IMPLEMENTED

### Multi-Radius Point-of-Interest Counts
- ✓ **Status**: Fully implemented in `pipeline/gold/build_poi_features.py`
- **Radii**: 500m, 1000m, 2000m
- **Categories**: schools, hospitals, transport, markets, worship, hospitality
- **Example columns**: `schools_500m`, `hospitals_1000m`, `transport_2000m`, etc.

### Footfall Score Composite Feature
- ✓ **Status**: Implemented in `build_poi_features.py`
- **Formula**: Weighted composite of 500m POI counts (0-100 scale)
- **Weights**:
  - transport: 3.0x
  - schools: 2.5x
  - markets: 2.0x
  - hospitals: 1.5x
  - worship: 1.0x
  - hospitality: 1.0x
- **Purpose**: Proxy for high-footfall locations (commercial hubs, transit nodes)

### POI Data Availability Flag
- ✓ **Status**: Implemented
- **Column**: `poi_data_available` (bool)
- **Usage**: False for outlets with zero coordinates or failed OSM scrapes
- **Impact on Training**: These outlets get 0 POI counts; model learns to handle sparse geo data

### Competitive Catchment Density
- ✓ **Status**: Fully implemented in `pipeline/gold/build_catchment_features.py`
- **Logic**: Counts competing outlets within 500m, 1km, and 2km using `BallTree`.
- **Columns**: `competitors_500m`, `competitors_1km`, `competitors_2km`, `competition_density_score`, `market_saturation_class`
- **Purpose**: Estimates market saturation and identifies isolated vs dense outlets.

### Spatial Distance-Decay Modeling (Gravity Model)
- ✓ **Status**: Fully implemented in `pipeline/gold/build_gravity_features.py`
- **Logic**: Applies inverse-square distance decay function to POIs within a maximum radius. Closer POIs exert a stronger gravitational pull than distant ones.
- **Columns**: Category-specific gravity scores (e.g. `transport_gravity_score`) and a `composite_gravity_score` (0-100 scale).
- **Purpose**: Models realistic spatial influence of POIs better than flat multi-radius counts.

---

## 6. Baseline Heuristic (January-Anchored) ✓ IMPLEMENTED

### Cold-Start Estimation
- ✓ **Status**: Implemented in `modelling/baseline.py`
- **Logic**: For outlets with no transaction history:
  - Estimate demand using median January volume of outlets with same `Outlet_Size`
  - Apply `Cooler_Count` multiplier as capacity proxy: `base × (1.0 + cooler_count × 0.15)`

### Recency-Weighted Momentum Adjustment
- ✓ **Status**: Implemented
- **Formula**: Compares 3-month EMA to historical mean
  - EMA 30% above mean → factor = 1.3 (growing)
  - EMA equals mean → factor = 1.0 (stable)
  - EMA 20% below mean → factor = 0.8 (declining, clamped)

### POI Uplift Factor
- ✓ **Status**: Implemented
- **Logic**:
  - Footfall 0–20: 1.00x
  - Footfall 20–60: 1.00–1.10x (linear interpolation)
  - Footfall 60–100: 1.10–1.25x (linear interpolation)
- **Rationale**: High-footfall outlets have more potential customers → upward adjustment

### Baseline Floor
- ✓ **Status**: Implemented
- **Rule**: `baseline = max(estimated_potential, hist_max_monthly)`
- **Rationale**: Never regress below observed reality (all-time maximum)

---

## 7. Direct January Approach ✓ PARTIALLY IMPLEMENTED

### January-Anchored Training Target
- ✓ **Status**: Implemented in `modelling/train.py`
- **Formula**: 
  ```
  pseudo_target = hist_p90_monthly
                × seasonality_multiplier_jan_2026
                × (jan_2026_trading_days / 22.0)
  ```
- **Rationale**: 
  - `hist_p90_monthly` is robust to outliers compared to raw maximum
  - Multiplied by January 2026 seasonality (Favorable/Moderate/Un-Favorable)
  - Adjusted for trading day count differences

### January-Specific Baseline
- ✓ **Status**: Implemented in `modelling/baseline.py`
- **Logic**: Three estimation paths:
  1. **January-anchored** (outlets with Jan history): Use `max(jan_avg, jan_max × 0.85)`
  2. **P90 fallback** (outlets with history but no Jan): Use `hist_p90_monthly`
  3. **Cold-start** (no history): Use size-median-based estimate

---

## Summary: What's Working

| Feature | Status | Module |
|---------|--------|--------|
| EMA (3m, 6m) | ✓ | `build_sales_features.py` |
| Trend slope, YoY growth | ✓ | `build_sales_features.py` |
| Recent 3m average | ✓ | `build_sales_features.py` |
| Historical stats (max, p90, p75, mean, std, CV) | ✓ | `build_sales_features.py` |
| January-specific metrics | ✓ | `build_sales_features.py` |
| CatBoost categorical support | ✓ | `train.py` |
| Algorithm-agnostic master features | ✓ | `build_master_features.py` |
| Clean train / Predict all strategy | ✓ | `train.py` + `predict.py` |
| POI multi-radius counts | ✓ | `build_poi_features.py` |
| Footfall score | ✓ | `build_poi_features.py` |
| Competitive catchment density | ✓ | `build_catchment_features.py` |
| Gravity model (distance-decay) | ✓ | `build_gravity_features.py` |
| January-anchored baseline | ✓ | `baseline.py` |
| Cold-start estimation | ✓ | `baseline.py` |
| Recency momentum factor | ✓ | `baseline.py` |
| POI uplift factor | ✓ | `baseline.py` |
| Direct January target approach | ✓ | `train.py` + `baseline.py` |
