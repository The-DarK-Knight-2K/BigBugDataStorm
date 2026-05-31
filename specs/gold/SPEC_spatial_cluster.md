# DATA SPECIFICATION: Spatial Cluster Features (DBSCAN)

**Layer:** Gold
**Component:** `pipeline/gold/build_spatial_cluster_features.py`
**Output:** `Data/Gold/spatial_cluster_features.parquet`

## Overview
Applies unsupervised DBSCAN clustering on outlet coordinates to identify dense micro-markets and extract aggregated cluster-level behavioral features.

## Inputs
- `Data/Silver/outlet_coordinates_clean.parquet`
- `Data/Gold/sales_features.parquet`
- `config.yaml` (DBSCAN hyperparameters)

## Logic Highlights
1. **DBSCAN Clustering:**
   - Algorithm: Density-Based Spatial Clustering of Applications with Noise (DBSCAN).
   - Hyperparameters: Epsilon (ε) mapped to physical distance in km using haversine metric; `min_samples` = 3.
   - Outliers (Noise) are assigned cluster `-1`.
2. **Cluster Aggregation:**
   - For each valid cluster (≥ 0), calculates aggregate sales metrics (mean, p90, max) for all outlets in that cluster.
   - Computes cluster density (outlets per square km bounding box).
3. **Feature Broadcast:**
   - Joins the aggregated cluster metrics back to the individual outlets, allowing models to learn from neighboring outlet performance.

## Output Schema
| Column | Type | Description |
|--------|------|-------------|
| `Outlet_ID` | `string` | Primary Key |
| `dbscan_cluster_id` | `int32` | Assigned cluster ID (-1 for noise) |
| `cluster_mean_volume`| `float32` | Average volume for the cluster |
| `cluster_p90_volume` | `float32` | 90th percentile volume for the cluster |
| `cluster_density` | `float32` | Outlets per sq km in the cluster |
