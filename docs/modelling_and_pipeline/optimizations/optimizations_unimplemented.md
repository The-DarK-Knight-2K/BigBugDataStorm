# Optimizations — Unimplemented Strategies

This document outlines optimization and feature engineering strategies described in the original optimization roadmap that have **not yet been implemented** in the current pipeline.

---

## 1. Advanced Spatial & Geospatial Features — NOT IMPLEMENTED

### Distance to Distributor
- **Status**: ✗ Not Implemented
- **Proposed Logic**:
  - Estimate distributor locations as median coordinates of all outlets served by that distributor
  - Calculate Haversine distance from each outlet to its assigned distributor
- **Rationale**: Outlets closer to distribution hub might have better supply chain reliability
- **Implementation Path**: 
  - Compute distributor centroids from `outlet_coordinates_clean.parquet`
  - Use `geopy.distance.geodesic()` (already imported for POI features)
  - Add `distance_to_distributor_m` column to master features
- **Why Not Implemented**: Unclear impact; may not differentiate outlets significantly

### Location Clustering (K-Means Micro-Regions)
- **Status**: ✗ Not Implemented
- **Proposed Logic**:
  - Apply K-Means clustering on (Latitude, Longitude) to group outlets into 50–100 "micro-regions"
  - Use `Cluster_ID` as a categorical feature in training
- **Rationale**: 
  - Captures local market dynamics that individual lat/lon may not capture
  - Micro-regions could have different competitive pressures, demographics, supply constraints
- **Implementation Path**:
  ```python
  from sklearn.cluster import KMeans
  coords = master_features[["Latitude", "Longitude"]].values
  kmeans = KMeans(n_clusters=75, random_state=42)
  master_features["cluster_id"] = kmeans.fit_predict(coords)
  ```
- **Why Not Implemented**: Requires grid search to tune cluster count; adds dimensionality without clear validation

---

## 2. Advanced Target Transformations — NOT IMPLEMENTED

### Log Transformation of Target Variable
- **Status**: ✗ Not Implemented
- **Proposed Logic**:
  - The target variable `Volume_Litres` is highly right-skewed
  - During training: Apply `target_transformed = log(1 + hist_p90_monthly)` 
  - During inference: Apply inverse `exp(model_prediction) - 1` to get back to litres
- **Rationale**: 
  - Log transformation stabilizes variance and improves model fit on MSE/RMSE
  - Tree-based models optimize loss more effectively on stabilized targets
  - Reduces impact of extreme outliers on model learning
- **Current State**: Pseudo-label is not log-transformed; model trains on raw volume
- **Why Not Implemented**: 
  - CatBoost handles skewed targets reasonably well without transformation
  - CV RMSE already satisfactory (40.38)
  - Adds complexity to prediction pipeline (require inverse transformation)
  - Limited expected gain for tree-based model

---

## 3. Algorithm-Specific Adaptations — NOT IMPLEMENTED

### LightGBM Pipeline
- **Status**: ✗ Not Implemented (CatBoost selected instead)
- **Proposed Implementation**: 
  - Cast all categorical columns to `pandas.category` dtype
  - LightGBM can natively handle categorical data when declared as such
  - Minimal preprocessing required
- **Why Not Implemented**: CatBoost chosen over LightGBM based on CV performance (40.38 vs 40.96 RMSE)

### XGBoost with Encoding Pipeline
- **Status**: ✗ Not Implemented
- **Proposed Implementation**:
  - **Low Cardinality** (`Outlet_Type`, `Outlet_Size`, `Seasonality_Index`): One-Hot Encoding
  - **High Cardinality** (`Distributor_ID`, `Cluster_ID` if added): 
    - Target Encoding (smoothed average of target per category)
    - Or Frequency Encoding to avoid massive sparse matrices
- **Why Not Implemented**: CatBoost chosen as primary algorithm; XGBoost not pursued

### Random Forest (Scikit-Learn) Pipeline
- **Status**: ✗ Not Implemented
- **Proposed Implementation**:
  - **Imputation**: All missing values must be filled
    - `yoy_growth_rate` for outlets < 1 year old
    - `trend_slope` for outlets with < 6 months data
    - Use median imputation or distinct placeholder like `-999`
  - **Encoding**: Strict One-Hot or Ordinal Encoding for all string categories
- **Why Not Implemented**: 
  - Random Forest much less suitable for FMCG sales prediction than gradient boosting
  - Cannot handle categorical strings or NaNs natively (would require extensive preprocessing)
  - CatBoost offers better predictive performance with fewer constraints

---

## 4. Pluggable Preprocessor Class — NOT IMPLEMENTED

### Architectural Enhancement
- **Status**: ✗ Not Implemented (mentioned in optimizations.md as future direction)
- **Proposed Design**:
  ```python
  class Preprocessor:
      def __init__(self, algorithm: str):
          self.algorithm = algorithm
      
      def preprocess(self, df: pd.DataFrame) -> pd.DataFrame:
          if self.algorithm == "catboost":
              return df  # No preprocessing needed
          elif self.algorithm == "lightgbm":
              return df.astype({col: "category" for col in CATEGORICAL_COLS})
          elif self.algorithm == "xgboost":
              return self._encode_xgboost(df)
          elif self.algorithm == "random_forest":
              return self._impute_and_encode_rf(df)
  ```
- **Rationale**: Allows seamless algorithm swapping without modifying pipeline
- **Why Not Implemented**: 
  - CatBoost is primary algorithm; no immediate need for switching
  - Can be added later as ensemble strategy develops
  - Adds code complexity without immediate ROI

---

## 5. Ensemble & Voting Strategy — NOT MENTIONED BUT RELEVANT

### Multi-Algorithm Ensemble
- **Status**: ✗ Not Implemented
- **Proposed Logic**:
  - Train CatBoost, LightGBM, XGBoost on same features
  - Final prediction = weighted average (or median) of three models
  - Combine via voting or stacking
- **Why Not Implemented**: 
  - Single CatBoost model already competitive
  - Ensemble adds deployment complexity
  - Hyperparameter tuning for each algorithm time-consuming

---

## 6. Cross-Validation Enhancements — NOT FULLY IMPLEMENTED

### Time-Series Cross-Validation
- **Status**: ✗ Not Implemented (Current: K-Fold on outlet_id)
- **Proposed Logic**:
  - Use temporal splits instead of random K-Fold
  - Train on data up to Month T, validate on Month T+1
  - Ensures model learns predictive patterns, not data leakage
- **Why Not Implemented**: 
  - Current problem is cross-sectional (predict Jan 2026 for all outlets)
  - Not time-series (predict next month for single outlet over time)
  - K-Fold on outlet_id is appropriate for this problem structure

### Nested Cross-Validation for Hyperparameter Tuning
- **Status**: ✗ Not Implemented
- **Proposed Logic**:
  - Inner CV loop for hyperparameter search (Optuna)
  - Outer CV loop for unbiased model evaluation
- **Why Not Implemented**: 
  - Optuna already used for single hyperparameter search
  - Nested CV would add significant runtime without clear benefit
  - CV RMSE already satisfactory

---

## 7. Feature Selection & Pruning — NOT IMPLEMENTED

### Automated Feature Importance Filtering
- **Status**: ✗ Not Implemented
- **Proposed Logic**:
  - Train model with all features
  - Remove features with importance < 0.1% of max importance
  - Retrain model with reduced feature set
  - Measure improvement in CV RMSE / inference speed
- **Why Not Implemented**: 
  - All ~50 features are meaningful and interpretable
  - Model already lightweight for inference
  - Risk of removing features that interact in non-linear ways

### Recursive Feature Elimination (RFE)
- **Status**: ✗ Not Implemented
- **Proposed Logic**:
  - Iteratively remove lowest-importance features and retrain
  - Stop when CV RMSE increases
- **Why Not Implemented**: Same as above; feature set is lean

---

## 8. Target Validation & Proxy Checks — NOT FULLY IMPLEMENTED

### Pseudo-Label Sanity Checks
- **Status**: ✓ Partially Implemented (basic checks in train.py)
- **Proposed Enhancements**:
  - Verify pseudo-target distribution is reasonable
  - Compare pseudo-target to baseline predictions
  - Flag outlets where pseudo-target seems anomalous (e.g., 100× historical mean)
  - Manual review of extreme targets
- **Why Not Fully Implemented**: 
  - Basic assertions exist
  - Comprehensive outlier review would be manual process

### Alternative Pseudo-Label Generation
- **Status**: ✗ Not Implemented (alternatives exist but not explored)
- **Proposed Alternatives**:
  - `hist_max_monthly` (all-time maximum, less conservative than p90)
  - `hist_mean_monthly × 1.5` (expected value with growth buffer)
  - Machine learning based target (Approach 2 or 3 from target_generation_strategies.md)

---

## 9. External Data Integration — NOT IMPLEMENTED

### Demographic Data
- **Status**: ✗ Not Implemented
- **Proposed Features**:
  - Population density around outlet (from census data)
  - Income levels / purchasing power
  - Tourism intensity (seasonal variation)

### Weather & Climate Data
- **Status**: ✗ Not Implemented
- **Proposed Features**:
  - Average temperature by region (beverage consumption ↑ in heat)
  - Monsoon season patterns
  - Holiday calendars beyond national holidays

### Competitive Intelligence
- **Status**: ✗ Not Implemented
- **Proposed Features**:
  - Distance to nearest competitor outlet
  - Competitor outlet counts by type (Kiosk vs Grocery)
  - Estimated market share by region

### Economic Indicators
- **Status**: ✗ Not Implemented
- **Proposed Features**:
  - Regional economic growth rates
  - Inflation indices
  - Employment rates

---

## Summary: What Could Be Added

| Feature | Complexity | Expected Impact | Priority |
|---------|------------|-----------------|----------|
| Distance to distributor | Low | Low | Low |
| K-Means micro-regions | Medium | Medium | Medium |
| Log transformation of target | Low | Low | Low |
| XGBoost pipeline | Medium | None (if CatBoost works) | Low |
| Random Forest pipeline | High | Low | Low |
| Pluggable Preprocessor class | Medium | High (for maintainability) | Low |
| Multi-algorithm ensemble | High | Medium | Low |
| Time-series CV | Low | None (not time-series problem) | N/A |
| Nested CV | High | Low | Low |
| Feature pruning (RFE) | Medium | Low | Low |
| External data (demographics, weather) | Very High | Very High | Low (time-limited) |

---

## Recommendation

**Focus areas for next iteration (if time permits):**
1. **K-Means micro-regions** — Medium complexity, potential high impact for capturing local market effects
2. **Alternative pseudo-labels** — Low complexity, validate robustness of current approach
3. **External demographic data** — High complexity but could significantly improve generalization
4. **Ensemble strategy** — Medium complexity, proven effective in competitions

**Skip for now:**
- Log transformation (CatBoost handles skew well)
- Random Forest pipeline (tree-based models not as suitable)
- Time-series CV (problem is cross-sectional, not temporal)
