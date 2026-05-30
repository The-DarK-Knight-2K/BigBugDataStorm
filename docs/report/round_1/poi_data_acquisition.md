# POI Data Acquisition

## Geospatial Scraping Strategy

We sourced geospatial Point of Interest (POI) data using the **OpenStreetMap Overpass API**. To circumvent aggressive rate limits and high latency associated with 20,000 individual queries, we engineered a highly scalable, two-phase scraping architecture:

**Two-Phase Implementation:**

1. **Phase 1 (Network - `scrape_poi_raw.py`):** Applied **K-Means spatial clustering** to group the 20,000 outlets into 400 geographic neighborhoods based on `(Latitude, Longitude)`. We issued a single bounding-box query (with a ~2 km buffer) per cluster and cached the raw JSON envelopes locally. This reduced API calls by 98% and achieved 100% data retrieval while ensuring idempotency.
2. **Phase 2 (Compute - `build_poi_features.py`):** A local processing script parsed the cache and calculated precise **geodesic distances** from every outlet to every nearby POI using `geopy` to correctly account for the Earth's curvature.

## POI Categories & Footfall Rationale

We extracted 6 core categories. Counts were binned into **500m, 1000m, and 2000m** radius bands. The 500m counts were heavily weighted to generate a normalized **Footfall Score (0-100)**, as immediate walkability is the strongest driver of foot traffic.

| Category | Core OSM Tags | Demand Signal Rationale | Weight |
| :--- | :--- | :--- | :---: |
| **transport** | `bus_stop`, `station` | **Highest Weight:** Public transit hubs drive the most intense, consistent daily volume of commuters. | 3.0 |
| **schools** | `school`, `university` | **High Weight:** Generates concentrated bursts of footfall during morning drop-offs and afternoon pick-ups. | 2.5 |
| **markets** | `supermarket`, `marketplace` | **Medium-High Weight:** Shoppers are already in a commercial area with the intent to purchase. | 2.0 |
| **hospitals** | `hospital`, `clinic` | **Medium Weight:** Provides a steady, predictable stream of staff, patients, and visitors. | 1.5 |
| **worship** | `place_of_worship` | **Base Weight:** Generates large crowds, but highly concentrated to specific days (e.g., Poya days). | 1.0 |
| **hospitality** | `hotel`, `restaurant` | **Base Weight:** Attracts tourists and dining crowds, but traffic is more variable. | 1.0 |

## Final Engineered Features

Each outlet received 20 newly engineered geospatial features, significantly upgrading the baseline dataset:

- **18 Dynamic Count Columns:** Specific POI counts for all 6 categories across 3 radii (e.g., `schools_500m`, `transport_1000m`, `markets_2000m`).
- **`footfall_score`:** A Min-Max normalized composite score (0.00-100.00) mathematically combining the weighted 500m metrics.
- **`poi_data_available`:** A boolean data contract flag gracefully handling the 40 quarantined outlets lacking valid GPS coordinates by safely assigning them zeroes and scoring them 0 for POI activity.
