# DATA SPECIFICATION: Catchment & Competition Features

**Layer:** Gold
**Component:** `pipeline/gold/build_catchment_features.py`
**Output:** `Data/Gold/catchment_features.parquet`

## Overview
Calculates the competitive density and market saturation metrics for each outlet using geospatial distance calculations.

## Inputs
- `Data/Silver/outlet_coordinates_clean.parquet`
- `Data/Silver/outlet_master_clean.parquet`
- `config.yaml` (competition thresholds)

## Logic Highlights
1. **BallTree Algorithm:**
   - Uses `sklearn.neighbors.BallTree` with the `haversine` metric for fast, accurate radius queries.
2. **Competition Density:**
   - Counts the total number of distinct outlets within 500m, 1km, and 2km radii for every given outlet.
3. **Market Saturation Class:**
   - Assigns a categorical saturation class based on the 1km competition count:
     - `low`: < 5 competitors
     - `medium`: 5-15 competitors
     - `high`: 16-30 competitors
     - `oversaturated`: > 30 competitors

## Output Schema
| Column | Type | Description |
|--------|------|-------------|
| `Outlet_ID` | `string` | Primary Key |
| `competition_count_500m` | `int32` | Number of outlets within 500m |
| `competition_count_1km` | `int32` | Number of outlets within 1km |
| `competition_count_2km` | `int32` | Number of outlets within 2km |
| `competition_density_score` | `float32` | Composite density score based on distance-weighted counts |
| `market_saturation_class` | `string` | Categorical label for competition density |
