# Optimizations and Feature Engineering Strategy

This document outlines additional optimizations, advanced feature engineering strategies, and dataset adaptations required to support various tree-based machine learning algorithms (LightGBM, XGBoost, CatBoost, and Random Forest) as we move from the Silver to the Gold and Modelling phases.

## 1. Advanced Feature Engineering (Pre-Gold/Gold Phase)

Before feeding the data into the models, we can extract significantly more signal from our cleaned Silver tables:

### Temporal & Lag Features
*   **Rolling Aggregations**: Moving beyond basic history, we should calculate 3-month, 6-month, and 12-month rolling averages, minimums, maximums, and standard deviations for `Volume_Litres`.
*   **Exponential Moving Averages (EMA)**: EMA places higher weight on recent months (e.g., Q4 2025) which is highly predictive for January 2026.
*   **Target Lags**: Explicitly map $t-1, t-2, t-3$ and seasonal lags like $t-12$ (January 2025 volume) as distinct columns.

### Spatial & Geospatial Features
*   **Outlet Density**: Using the cleaned coordinates, calculate the count of competing outlets within a 1km, 5km, and 10km radius for each `Outlet_ID`. High density might mean higher competition, or it might indicate a major commercial hub.
*   **Distance to Distributor**: If we can estimate distributor locations (e.g., median coordinates of all outlets served by a distributor), we can calculate the Haversine distance from the outlet to the distributor.
*   **Location Clustering**: Apply K-Means clustering on Latitude/Longitude to group outlets into "micro-regions" (e.g., 50-100 clusters) and use the `Cluster_ID` as a categorical feature.

### Advanced Target Transformations
*   **Log Transformation**: The target variable `Volume_Litres` is highly right-skewed. Taking $\log(1 + \text{Volume})$ during training and applying $\exp()$ during prediction will help tree-based models optimize MSE/RMSE much more effectively.

---

## 2. Algorithm-Specific Dataset Adaptations (Silver -> Gold Phase)

We plan to use **LightGBM** as the primary algorithm. LightGBM is highly forgiving and handles raw data well. However, if we pivot to **XGBoost, CatBoost, or Random Forest (Scikit-Learn)**, we must adjust our data preparation pipelines.

Here is how the dataset requirements differ and the changes needed in the pipeline:

### LightGBM (Current Main)
*   **Categoricals**: Handles categorical data natively if pandas columns are cast to the `category` dtype.
*   **Missing Values**: Natively handles NaNs by learning which side of the tree split maximizes the objective. No strict imputation is required.
*   **Action for Pipeline**: Minimal. Just ensure string columns like `Outlet_Type`, `Outlet_Size`, and `Distributor_ID` are cast to `category`.

### CatBoost
*   **Categoricals**: The absolute best at handling categorical variables. It can take raw string columns directly via the `cat_features` parameter and uses advanced Target Statistics (TS) under the hood.
*   **Missing Values**: Highly robust to missing values.
*   **Action for Pipeline**: None. CatBoost can consume the Silver/Gold parquet files exactly as they are currently designed.

### XGBoost
*   **Categoricals**: While newer versions (1.6+) have experimental categorical support, XGBoost traditionally requires all features to be strictly numerical. 
*   **Missing Values**: Handles NaNs well, similar to LightGBM.
*   **Action for Pipeline**: We would need to add an Encoding step.
    *   *Low Cardinality* (`Outlet_Type`, `Outlet_Size`, `Seasonality_Index`): Apply **One-Hot Encoding** or Ordinal Encoding.
    *   *High Cardinality* (`Distributor_ID`, `Cluster_ID`): Apply **Target Encoding** (smoothed average of the target variable per category) or Frequency Encoding to avoid massive sparse matrices.

### Random Forest (Scikit-Learn)
*   **Categoricals**: Cannot handle categorical strings natively.
*   **Missing Values**: **Cannot handle NaNs at all.** It will throw an error if `NaN` or `Inf` is passed.
*   **Action for Pipeline**: Significant changes required in the Gold/Modelling layer:
    *   **Imputation**: All missing values (e.g., `yoy_growth_rate` for outlets < 1 year old, or `trend_slope`) MUST be imputed. We should use a distinct placeholder like `-999` or median imputation depending on the feature's distribution.
    *   **Encoding**: Strict One-Hot Encoding or Ordinal Encoding for all string categories.

---

## 3. Recommended Architectural Update

To support seamless model swapping (Ensembling) down the line without breaking the pipeline, we should implement a **"Pre-Processing Switch"** in the Modelling phase (`train.py`):

1. Keep the Silver and Gold parquet files as "Raw & Readable" as possible (leave strings as strings, leave NaNs as NaNs).
2. Inside the modelling orchestrator, inject a `Preprocessor` class that takes the algorithm type as an argument:
   * If `algo == "lightgbm"`, apply `pandas.astype("category")`.
   * If `algo == "random_forest"`, trigger a `SimpleImputer` pipeline followed by an `OrdinalEncoder` pipeline.

This prevents the Silver/Gold tables from being bloated by one-hot encoded columns (which are unreadable for humans and take up unnecessary disk space).

---

## 4. Inference Optimization: "Clean Train, Predict All"

To maximize the generalization capability of our model while strictly adhering to the submission requirement of predicting for all 20,000 outlets, we use a bifurcated pipeline strategy:

1. **Filtering the Training Set**: The 40 outlets with quarantined/missing coordinates will have their coordinates imputed with the province centroid and POI features set to 0. While necessary for prediction, this imputed data acts as noise during training. Thus, we create an `exclude_from_training` flag in `master_features.parquet` and filter these records out before calling `model.fit()`. The model learns exclusively from the ~19,960 clean, geographically accurate outlets.
2. **Comprehensive Inference**: During `predict.py`, the `exclude_from_training` flag is ignored. The trained model infers the target for all 20,000 outlets. The 40 problematic outlets receive a prediction based on their actual sales history and their best-guess (imputed) geographic features, avoiding any loss of records in the final submission.
