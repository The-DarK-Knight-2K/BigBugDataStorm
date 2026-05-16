import os
import json
import time
from pathlib import Path
import yaml
import pandas as pd
from geopy.distance import geodesic
from tqdm import tqdm

from pipeline.utils.logger import setup_logger

# Set paths
PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent
CONFIG_PATH = PROJECT_ROOT / "config.yaml"
SILVER_DIR = PROJECT_ROOT / "Data" / "Silver"
GOLD_DIR = PROJECT_ROOT / "Data" / "Gold"
CACHE_DIR = GOLD_DIR / "poi_raw_cache"

log = setup_logger("build_poi_features")

# Overpass API POI Category Map
POI_CATEGORY_MAP = {
    "schools": [("amenity", "school"), ("amenity", "university")],
    "hospitals": [("amenity", "hospital"), ("amenity", "clinic")],
    "transport": [("highway", "bus_stop"), ("railway", "station")],
    "markets": [("shop", "supermarket"), ("amenity", "marketplace")],
    "worship": [("amenity", "place_of_worship")],
    "hospitality": [("tourism", "hotel"), ("amenity", "restaurant")]
}

# Footfall Weights (only applied to 500m counts)
FOOTFALL_WEIGHTS = {
    "transport": 3.0,
    "schools": 2.5,
    "markets": 2.0,
    "hospitals": 1.5,
    "worship": 1.0,
    "hospitality": 1.0
}

def load_config():
    with open(CONFIG_PATH, "r") as f:
        config = yaml.safe_load(f)
    return config["poi"]

def classify_poi(tags):
    """Returns the category string (e.g., 'schools') if tags match, else None."""
    for category, tag_list in POI_CATEGORY_MAP.items():
        for k, v in tag_list:
            if tags.get(k) == v:
                return category
    return None

def main():
    start_time = time.time()
    log.info("Starting POI Feature Building (Phase 2)...")
    
    # 1. Validate Cache
    manifest_path = CACHE_DIR / "scrape_manifest.json"
    if not manifest_path.exists():
        raise FileNotFoundError("Run Phase 1 first. Scrape manifest not found.")
        
    with open(manifest_path, "r") as f:
        manifest = json.load(f)
        
    failed_clusters = set(manifest.get("failed_clusters", []))
    if failed_clusters:
        log.warning("%d clusters failed in Phase 1. They will get 0s and poi_data_available=False.", len(failed_clusters))
        
    # 2. Load Config
    cfg = load_config()
    radii_m = cfg["radii_m"] # e.g., [500, 1000, 2000]
    
    # Generate all output column names dynamically
    count_columns = []
    for cat in POI_CATEGORY_MAP.keys():
        for r in radii_m:
            count_columns.append(f"{cat}_{r}m")
            
    # 3. Load Inputs
    coords_df = pd.read_parquet(SILVER_DIR / "outlet_coordinates_clean.parquet")
    coords_dict = coords_df.set_index("Outlet_ID")[["Latitude", "Longitude"]].to_dict('index')
    
    master_df = pd.read_parquet(SILVER_DIR / "outlet_master_clean.parquet")
    all_outlet_ids = set(master_df["Outlet_ID"].unique())
    
    log.info("Loaded %d master outlets, %d with coordinates.", len(all_outlet_ids), len(coords_dict))
    
    # 4. Processing Loop
    features_list = []
    scraped_outlet_ids = set()
    
    clusters_to_process = manifest.get("completed_clusters", [])
    
    pbar = tqdm(clusters_to_process, desc="Building Features")
    
    for cluster_id in pbar:
        cache_file = CACHE_DIR / f"cluster_{cluster_id:04d}.json"
        
        if not cache_file.exists():
            continue # Should be caught by failed_clusters, but just in case
            
        with open(cache_file, "r", encoding="utf-8") as f:
            cluster_data = json.load(f)
            
        # Verify config hasn't changed
        if cluster_data["config_snapshot"]["n_clusters"] != cfg["n_clusters"]:
            log.warning("Cluster %d: Config mismatch! n_clusters changed.", cluster_id)
            
        elements = cluster_data.get("elements", [])
        cluster_outlet_ids = cluster_data.get("outlet_ids", [])
        
        # Fast path if no POIs returned
        if not elements:
            for out_id in cluster_outlet_ids:
                row = {"Outlet_ID": out_id, "poi_data_available": True}
                for col in count_columns:
                    row[col] = 0
                features_list.append(row)
                scraped_outlet_ids.add(out_id)
            continue
            
        # Pre-classify and extract coords for all POIs in this cluster
        pois = []
        for el in elements:
            cat = classify_poi(el.get("tags", {}))
            if cat:
                pois.append((cat, (el["lat"], el["lon"])))
                
        # For every outlet in this cluster
        for out_id in cluster_outlet_ids:
            if out_id not in coords_dict:
                continue # Edge case, shouldn't happen
                
            out_lat = coords_dict[out_id]["Latitude"]
            out_lon = coords_dict[out_id]["Longitude"]
            out_coords = (out_lat, out_lon)
            
            row = {"Outlet_ID": out_id, "poi_data_available": True}
            for col in count_columns:
                row[col] = 0
                
            # Compute distance to every POI
            for cat, poi_coords in pois:
                dist_m = geodesic(out_coords, poi_coords).meters
                
                for r in radii_m:
                    if dist_m <= r:
                        row[f"{cat}_{r}m"] += 1
                        
            features_list.append(row)
            scraped_outlet_ids.add(out_id)
            
    # 5. Handle missing outlets (the 40 zero-coord ones + any from failed clusters)
    missing_ids = all_outlet_ids - scraped_outlet_ids
    log.info("Found %d outlets without POI data. Assigning zeros.", len(missing_ids))
    
    for out_id in missing_ids:
        row = {"Outlet_ID": out_id, "poi_data_available": False}
        for col in count_columns:
            row[col] = 0
        features_list.append(row)
        
    df = pd.DataFrame(features_list)
    
    # Ensure all count columns are integers
    for col in count_columns:
        df[col] = df[col].astype("int32")
        
    # 6. Compute Footfall Score
    log.info("Computing Footfall Score...")
    # Calculate raw score using 500m weights
    df["raw_footfall"] = 0.0
    for cat, weight in FOOTFALL_WEIGHTS.items():
        col_500m = f"{cat}_500m"
        if col_500m in df.columns:
            df["raw_footfall"] += df[col_500m] * weight
            
    # Min-Max Normalization (0-100)
    min_score = df["raw_footfall"].min()
    max_score = df["raw_footfall"].max()
    
    if max_score > min_score:
        df["footfall_score"] = ((df["raw_footfall"] - min_score) / (max_score - min_score)) * 100.0
    else:
        df["footfall_score"] = 0.0
        
    df["footfall_score"] = df["footfall_score"].round(2).astype("float32")
    df = df.drop(columns=["raw_footfall"])
    
    # 7. Assertions
    log.info("Running Data Contract assertions...")
    assert len(df) == 20000, f"Expected 20000 rows, got {len(df)}"
    assert df["Outlet_ID"].duplicated().sum() == 0, "Duplicate Outlet_IDs found"
    assert df["Outlet_ID"].isnull().sum() == 0, "Null Outlet_IDs found"
    assert df["footfall_score"].min() >= 0.0, "Footfall score < 0"
    assert df["footfall_score"].max() <= 100.0, "Footfall score > 100"
    for col in count_columns:
        assert df[col].min() >= 0, f"Negative count in {col}"
        
    # 8. Order Columns
    final_columns = ["Outlet_ID"] + count_columns + ["footfall_score", "poi_data_available"]
    df = df[final_columns]
    
    # 9. Write Outputs
    output_path = GOLD_DIR / "poi_features.parquet"
    df.to_parquet(output_path, index=False, engine="pyarrow", compression="snappy")
    
    duration = time.time() - start_time
    
    # Audit trail
    log_dict = {
        "total_outlets": len(df),
        "outlets_with_poi_data": int(df["poi_data_available"].sum()),
        "outlets_without_poi_data": len(missing_ids),
        "clusters_queried": cfg["n_clusters"],
        "clusters_failed": len(failed_clusters),
        "radii_used_m": radii_m,
        "feature_columns": len(count_columns),
        "build_duration_seconds": round(duration, 2)
    }
    
    with open(GOLD_DIR / "poi_scrape_log.json", "w") as f:
        json.dump(log_dict, f, indent=2)
        
    log.info("Phase 2 Finished in %.2fs.", duration)
    log.info("Wrote %d rows x %d columns to %s", len(df), len(df.columns), output_path.name)
    
if __name__ == "__main__":
    main()
