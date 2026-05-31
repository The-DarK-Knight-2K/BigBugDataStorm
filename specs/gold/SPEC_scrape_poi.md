# SPEC: Gold Layer POI Pipeline

## Purpose

For each of the 20,000 outlets, query OpenStreetMap's Overpass API to count Points of Interest (POIs) within defined radius bands. These POI counts act as footfall proxies — schools, hospitals, transit hubs, and markets near an outlet indicate higher potential customer traffic. 

To ensure resilience and scalability, the pipeline is split into a **Two-Phase Architecture**:
1. **Phase 1 (Network)**: Cluster outlets, fetch raw map data from Overpass API, and cache to disk.
2. **Phase 2 (Compute)**: Parse the local cache, compute geodesic distances, build the final features, and apply footfall scoring.

## Layer
Gold

## Inputs

| File | Path |
|------|------|
| outlet_coordinates_clean.parquet | `Data/Silver/outlet_coordinates_clean.parquet` |
| outlet_master_clean.parquet | `Data/Silver/outlet_master_clean.parquet` |

## Outputs

| File | Path |
|------|------|
| poi_raw_cache (Directory) | `Data/Gold/poi_raw_cache/` |
| poi_features.parquet | `Data/Gold/poi_features.parquet` |
| poi_scrape_log.json | `Data/Gold/poi_scrape_log.json` |

---

## Phase 1: `scrape_poi_raw.py` (Network / Idempotency)

Querying 20,000 outlets individually would take hours and trigger API rate limits. Instead, Phase 1 uses spatial clustering to minimize API calls and caches the raw results.

### Step 1.1 — Spatial Clustering
Use KMeans to group the 19,960 valid outlets into `n_clusters` (default 400) geographic neighborhoods based on `(Latitude, Longitude)`. This reduces 20,000 API calls down to 400 bounding-box queries.

### Step 1.2 — Bounding Box Queries
For each cluster, calculate a geographic bounding box containing all outlets in that cluster, plus a `buffer_deg` (e.g., 0.018 degrees, ~2km) to capture POIs on the edges.

Query the Overpass API using QL format to fetch specific tags (e.g., `amenity=school`, `highway=bus_stop`) inside the bounding box.

### Step 1.3 — Idempotent Caching
Save the raw JSON response for each cluster to `Data/Gold/poi_raw_cache/cluster_XXXX.json`. 
Update `scrape_manifest.json` after every successful cluster. If the script fails or the API times out, the manifest allows the script to resume exactly where it left off without re-querying completed clusters.

---

## Phase 2: `build_poi_features.py` (Compute / Feature Engineering)

Phase 2 relies entirely on the local `poi_raw_cache/` and makes zero network calls. This allows us to rapidly re-run feature extraction if we want to change radius bands or category groupings.

### Step 2.1 — Geodesic Distances
For every outlet, iterate through all POIs downloaded in its cluster. Calculate the true real-world distance in meters using `geopy.distance.geodesic` (which accounts for Earth's curvature).

### Step 2.2 — Dynamic Radius Counting
Classify each POI into one of 6 categories. If the distance falls within one of the defined radius bands (e.g., `500m`, `1000m`, `2000m`), increment the respective counter (e.g., `schools_500m`, `transport_1000m`).

### Step 2.3 — Handling Missing GPS Outlets
The 40 "quarantined" outlets lacking GPS coordinates in the Silver layer are manually injected back into the dataset. They are assigned `0` for all count columns and flagged with `poi_data_available = False` to ensure the final output contains a perfect 20,000 rows.

### Step 2.4 — Footfall Score Calculation

A weighted composite score is calculated using **only the 500m radius counts**, as immediate walkability is the strongest driver of foot traffic.

| POI Category | Weight | OSM Tags Included | Business Rationale for Weighting |
| :--- | :---: | :--- | :--- |
| **Transport** | **3.0** | `bus_stop`, `station` | **Highest Weight:** Public transit hubs drive the most intense, consistent daily volume of commuters. |
| **Schools** | **3.0** | `school`, `university` | **Highest Weight:** Generates concentrated bursts of footfall during morning drop-offs and afternoon pick-ups. |
| **Hospitality** | **2.0** | `hotel`, `restaurant` | **Medium-High Weight:** Attracts tourists and dining crowds, highly relevant for beverage sales. |
| **Markets** | **2.0** | `supermarket`, `marketplace` | **Medium-High Weight:** Shoppers are already in a commercial area with the intent to purchase. |
| **Hospitals** | **1.0** | `hospital`, `clinic` | **Medium Weight:** Provides a steady, predictable stream of staff, patients, and visitors. |
| **Worship** | **0.5** | `place_of_worship` | **Base Weight:** Generates large crowds, but highly concentrated to specific days (e.g., Poya days). |

#### Normalization
The raw weighted sum is normalized across all 20,000 outlets using Min-Max scaling to produce a clean `0.00` to `100.00` `footfall_score`.

### Step 2.5 — Write Outputs
Run strict data contract assertions (checking for 20k rows, no duplicates, non-negative scores) and write to `Data/Gold/poi_features.parquet`.

---

## Dependencies
- `pandas`, `pyyaml`, `pyarrow`
- `scikit-learn` (KMeans)
- `requests` (API scraping)
- `geopy` (Geodesic distance math)
- `tqdm` (Progress tracking)
