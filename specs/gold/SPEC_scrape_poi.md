# SPEC: scrape_poi.py

## Purpose

For each of the 20,000 outlets, query OpenStreetMap's Overpass API to count
Points of Interest (POIs) within defined radius bands. These POI counts are
footfall proxies — schools, hospitals, bus stops, markets near an outlet indicate
higher potential customer traffic. Results are saved as `data/gold/poi_features.parquet`.

## Layer
Gold

## Inputs

| File | Path |
|------|------|
| outlet_coordinates_clean.parquet | `data/silver/outlet_coordinates_clean.parquet` |

## Outputs

| File | Path |
|------|------|
| poi_features.parquet | `data/gold/poi_features.parquet` |
| poi_scrape_log.json | `data/gold/poi_scrape_log.json` |

---

## Why spatial clustering (not per-outlet queries)

Querying 20,000 outlets one-by-one would take hours and likely get rate-limited.
Instead, cluster outlets into ~400 geographic groups, run one bounding-box query
per cluster that covers all outlets in the group, then for each outlet filter the
returned POIs to within the specified radius. This reduces 20,000 API calls to ~400.

---

## Step-by-step logic

### Step 1 — Load clean coordinates

```python
coords = pd.read_parquet(SILVER / "outlet_coordinates_clean.parquet")
# coords has: Outlet_ID, Latitude, Longitude, coords_swapped
log.info("Loaded %d outlet coordinates", len(coords))
```

Note: The 40 zero-coordinate outlets are absent from this file (quarantined in
Silver). They will be handled in Step 7.

### Step 2 — Spatial clustering

Use KMeans to group outlets into `n_clusters` geographic clusters (from `config.yaml`,
default 400).

```python
from sklearn.cluster import KMeans
import numpy as np

X = coords[["Latitude", "Longitude"]].values
kmeans = KMeans(n_clusters=CFG["poi"]["n_clusters"], random_state=42, n_init=10)
coords["cluster_id"] = kmeans.fit_predict(X)
log.info("Clustered %d outlets into %d spatial groups", len(coords), CFG["poi"]["n_clusters"])
```

### Step 3 — Define Overpass query builder

The Overpass API accepts a bounding box query in QL format. Build a query that
retrieves all relevant POI types within a bounding box.

```python
def build_overpass_query(lat_min: float, lon_min: float,
                         lat_max: float, lon_max: float,
                         timeout: int = 60) -> str:
    bbox = f"{lat_min},{lon_min},{lat_max},{lon_max}"
    return f"""
    [out:json][timeout:{timeout}];
    (
      node["amenity"="school"]({bbox});
      node["amenity"="university"]({bbox});
      node["amenity"="hospital"]({bbox});
      node["amenity"="clinic"]({bbox});
      node["highway"="bus_stop"]({bbox});
      node["railway"="station"]({bbox});
      node["shop"="supermarket"]({bbox});
      node["amenity"="marketplace"]({bbox});
      node["amenity"="place_of_worship"]({bbox});
      node["tourism"="hotel"]({bbox});
      node["amenity"="restaurant"]({bbox});
    );
    out center;
    """
```

### Step 4 — POI category mapping

```python
POI_CATEGORY_MAP = {
    "schools":      [("amenity", "school"), ("amenity", "university")],
    "hospitals":    [("amenity", "hospital"), ("amenity", "clinic")],
    "transport":    [("highway", "bus_stop"), ("railway", "station")],
    "markets":      [("shop", "supermarket"), ("amenity", "marketplace")],
    "worship":      [("amenity", "place_of_worship")],
    "hospitality":  [("tourism", "hotel"), ("amenity", "restaurant")],
}
```

### Step 5 — Per-cluster scraping loop

For each cluster:
1. Compute bounding box with a 500m buffer:
   ```python
   BUFFER_DEG = 0.005  # ~500m in degrees
   lat_min = cluster_outlets["Latitude"].min() - BUFFER_DEG
   lat_max = cluster_outlets["Latitude"].max() + BUFFER_DEG
   lon_min = cluster_outlets["Longitude"].min() - BUFFER_DEG
   lon_max = cluster_outlets["Longitude"].max() + BUFFER_DEG
   ```

2. Query Overpass API:
   ```python
   import requests, time

   query = build_overpass_query(lat_min, lon_min, lat_max, lon_max,
                                 timeout=CFG["poi"]["timeout_s"])
   resp = requests.post(
       CFG["poi"]["overpass_url"],
       data={"data": query},
       timeout=CFG["poi"]["timeout_s"] + 10,
   )
   resp.raise_for_status()
   elements = resp.json().get("elements", [])
   ```

3. Rate limit: sleep `CFG["poi"]["request_delay_s"]` between requests.

4. On failure (timeout, HTTP error, JSON parse error):
   - Log WARNING: "Cluster {cluster_id} failed: {error}. Retrying once."
   - Retry once after 5 seconds.
   - If retry also fails: log WARNING and record all outlets in this cluster as
     `poi_data_available = False`. Continue to next cluster — do not abort.

5. For each POI element returned, extract `lat`, `lon`, and tag dict.

### Step 6 — Compute per-outlet POI counts

For each outlet in the cluster:

```python
from geopy.distance import geodesic

def count_pois_within_radius(
    outlet_lat: float, outlet_lon: float,
    poi_elements: list[dict],
    radius_m: float,
    category_tags: list[tuple],
) -> int:
    count = 0
    for el in poi_elements:
        poi_lat = el.get("lat") or el.get("center", {}).get("lat")
        poi_lon = el.get("lon") or el.get("center", {}).get("lon")
        if poi_lat is None or poi_lon is None:
            continue
        dist = geodesic((outlet_lat, outlet_lon), (poi_lat, poi_lon)).meters
        if dist <= radius_m:
            tags = el.get("tags", {})
            for tag_key, tag_val in category_tags:
                if tags.get(tag_key) == tag_val:
                    count += 1
                    break
    return count
```

For each outlet, compute counts for all combinations of category × radius:
- Radii: 500m, 1000m, 2000m (from `config.yaml`)
- Categories: schools, hospitals, transport, markets, worship, hospitality

### Step 7 — Handle outlets with no coordinate data

The 40 zero-coord outlets are not in `outlet_coordinates_clean`. For these,
create rows with all count columns = 0 and `poi_data_available = False`:

```python
all_outlet_ids = pd.read_parquet(SILVER / "outlet_master_clean.parquet")["Outlet_ID"]
scraped_ids    = set(poi_df["Outlet_ID"])
missing_ids    = set(all_outlet_ids) - scraped_ids

for oid in missing_ids:
    poi_df = pd.concat([poi_df, pd.DataFrame([{
        "Outlet_ID": oid,
        **{col: 0 for col in count_cols},
        "footfall_score": 0.0,
        "poi_data_available": False,
    }])], ignore_index=True)
```

### Step 8 — Compute footfall_score

A weighted composite of POI counts within 500m:

```python
FOOTFALL_WEIGHTS = {
    "transport_500m":    3.0,   # Highest weight — direct footfall driver
    "schools_500m":      2.5,
    "markets_500m":      2.0,
    "hospitals_500m":    1.5,
    "worship_500m":      1.0,
    "hospitality_500m":  1.0,
}

poi_df["footfall_score"] = sum(
    poi_df[col] * weight
    for col, weight in FOOTFALL_WEIGHTS.items()
)
```

Normalise to 0–100 scale using min-max normalisation:
```python
fs_min = poi_df["footfall_score"].min()
fs_max = poi_df["footfall_score"].max()
poi_df["footfall_score"] = (
    (poi_df["footfall_score"] - fs_min) / (fs_max - fs_min) * 100
).round(2)
```

### Step 9 — Write outputs

Write `data/gold/poi_features.parquet` with all columns per DATA_CONTRACTS.md.

Write `data/gold/poi_scrape_log.json`:
```json
{
  "total_outlets": 20000,
  "outlets_with_poi_data": 19960,
  "outlets_without_poi_data": 40,
  "clusters_queried": 400,
  "clusters_failed": 0,
  "scrape_duration_seconds": 1234
}
```

---

## Progress tracking

Use `tqdm` to show a progress bar over clusters:
```python
from tqdm import tqdm
for cluster_id in tqdm(coords["cluster_id"].unique(), desc="Scraping POI clusters"):
```

---

## Assertions before writing

```python
assert len(poi_df) == 20000, f"Expected 20000 rows, got {len(poi_df)}"
assert poi_df["Outlet_ID"].duplicated().sum() == 0
assert poi_df["Outlet_ID"].isnull().sum() == 0
assert poi_df["footfall_score"].between(0, 100).all()
count_cols = [c for c in poi_df.columns if c.endswith(("_500m","_1km","_2km"))]
assert (poi_df[count_cols] >= 0).all().all(), "Negative POI counts found"
```

---

## CLI usage

```bash
python pipeline/gold/scrape_poi.py
```

Expected runtime: 20–60 minutes depending on network speed and cluster count.

## Dependencies

- pandas, numpy, pyarrow, pyyaml
- scikit-learn (KMeans)
- requests
- geopy
- tqdm
