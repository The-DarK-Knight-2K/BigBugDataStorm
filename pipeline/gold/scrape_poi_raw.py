import os
import json
import time
import datetime
from pathlib import Path
import yaml
import requests
import pandas as pd
from sklearn.cluster import KMeans
from tqdm import tqdm

from pipeline.utils.logger import setup_logger

# Set paths
PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent
CONFIG_PATH = PROJECT_ROOT / "config.yaml"
SILVER_DIR = PROJECT_ROOT / "Data" / "Silver"
CACHE_DIR = PROJECT_ROOT / "Data" / "Gold" / "poi_raw_cache"

log = setup_logger("scrape_poi_raw")

# Overpass API POI Category Map
# We request these specific node/way/relation tags
POI_CATEGORY_MAP = {
    "schools": [("amenity", "school"), ("amenity", "university")],
    "hospitals": [("amenity", "hospital"), ("amenity", "clinic")],
    "transport": [("highway", "bus_stop"), ("railway", "station")],
    "markets": [("shop", "supermarket"), ("amenity", "marketplace")],
    "worship": [("amenity", "place_of_worship")],
    "hospitality": [("tourism", "hotel"), ("amenity", "restaurant")]
}

def load_config():
    with open(CONFIG_PATH, "r") as f:
        config = yaml.safe_load(f)
    if "poi" not in config:
        raise ValueError("Missing 'poi' configuration block in config.yaml")
    return config["poi"]

def build_overpass_query(lat_min, lat_max, lon_min, lon_max, timeout):
    """
    Builds the Overpass QL query to fetch all relevant POIs inside the bounding box.
    """
    bbox = f"{lat_min},{lon_min},{lat_max},{lon_max}"
    
    # We want nodes, ways, and relations that match our tags.
    # Out center ensures ways and relations return a center lat/lon point.
    query_parts = [f"[out:json][timeout:{timeout}];", "("]
    
    for category, tag_list in POI_CATEGORY_MAP.items():
        for k, v in tag_list:
            query_parts.append(f'  node["{k}"="{v}"]({bbox});')
            query_parts.append(f'  way["{k}"="{v}"]({bbox});')
            query_parts.append(f'  relation["{k}"="{v}"]({bbox});')
            
    query_parts.append(");")
    query_parts.append("out center;")
    
    return "\n".join(query_parts)

def get_manifest():
    manifest_path = CACHE_DIR / "scrape_manifest.json"
    if manifest_path.exists():
        with open(manifest_path, "r") as f:
            return json.load(f)
    
    return {
        "completed_clusters": [],
        "failed_clusters": [],
        "total_clusters": 0,
        "started_at": datetime.datetime.now().isoformat()
    }

def save_manifest(manifest):
    manifest_path = CACHE_DIR / "scrape_manifest.json"
    with open(manifest_path, "w") as f:
        json.dump(manifest, f, indent=2)

def main():
    log.info("Starting POI Raw Scraping (Phase 1)...")
    
    # 1. Load config
    cfg = load_config()
    n_clusters = cfg["n_clusters"]
    buffer_deg = cfg["buffer_deg"]
    overpass_url = cfg["overpass_url"]
    timeout_s = cfg["timeout_s"]
    request_delay_s = cfg["request_delay_s"]
    
    log.info("Loaded config: %d clusters, %f deg buffer", n_clusters, buffer_deg)
    
    # Ensure cache directory exists
    CACHE_DIR.mkdir(parents=True, exist_ok=True)
    
    # 2. Load Coordinates & Cluster
    coords_path = SILVER_DIR / "outlet_coordinates_clean.parquet"
    if not coords_path.exists():
        raise FileNotFoundError(f"Missing {coords_path}. Run Silver pipeline first.")
        
    df_coords = pd.read_parquet(coords_path)
    log.info("Loaded %d outlets with valid GPS coordinates.", len(df_coords))
    
    log.info("Running KMeans to create %d clusters...", n_clusters)
    kmeans = KMeans(n_clusters=n_clusters, random_state=42, n_init=10)
    df_coords["cluster_id"] = kmeans.fit_predict(df_coords[["Latitude", "Longitude"]])
    log.info("Clustering complete.")
    
    # 3. Load Manifest
    manifest = get_manifest()
    manifest["total_clusters"] = n_clusters
    save_manifest(manifest)
    
    completed = set(manifest["completed_clusters"])
    
    # 4. Scraping Loop
    clusters_to_process = [c for c in range(n_clusters) if c not in completed]
    log.info("%d clusters already completed. %d clusters left to process.", 
             len(completed), len(clusters_to_process))
    
    if not clusters_to_process:
        log.info("All clusters completed successfully! Phase 1 is done.")
        return

    # Use tqdm for progress tracking
    pbar = tqdm(clusters_to_process, desc="Scraping Clusters")
    
    session = requests.Session()
    
    for cluster_id in pbar:
        # Get outlets in this cluster
        cluster_mask = df_coords["cluster_id"] == cluster_id
        cluster_df = df_coords[cluster_mask]
        outlet_ids = cluster_df["Outlet_ID"].tolist()
        
        # Compute Bounding Box with Buffer
        lat_min = cluster_df["Latitude"].min() - buffer_deg
        lat_max = cluster_df["Latitude"].max() + buffer_deg
        lon_min = cluster_df["Longitude"].min() - buffer_deg
        lon_max = cluster_df["Longitude"].max() + buffer_deg
        
        query = build_overpass_query(lat_min, lat_max, lon_min, lon_max, timeout_s)
        
        success = False
        retries = 1
        
        for attempt in range(retries + 1):
            try:
                # Add delay before request to respect rate limits
                if attempt > 0 or cluster_id != clusters_to_process[0]:
                    time.sleep(request_delay_s)
                    
                response = session.post(
                    overpass_url, 
                    data=query.encode('utf-8'),
                    headers={'User-Agent': 'DataStormPOI/1.0'},
                    timeout=timeout_s + 10
                )
                
                # Overpass API can return 429 Too Many Requests
                if response.status_code == 429:
                    log.warning("Cluster %04d: Rate limited (429). Waiting 15s...", cluster_id)
                    time.sleep(15)
                    continue
                    
                response.raise_for_status()
                data = response.json()
                
                # Successful response!
                elements = []
                for el in data.get("elements", []):
                    # For nodes, lat/lon are direct. For ways/relations, they are in 'center'
                    if "lat" in el and "lon" in el:
                        lat, lon = el["lat"], el["lon"]
                    elif "center" in el:
                        lat, lon = el["center"]["lat"], el["center"]["lon"]
                    else:
                        continue # Skip elements without coordinates
                        
                    elements.append({
                        "lat": lat,
                        "lon": lon,
                        "tags": el.get("tags", {})
                    })
                
                # Build Rich Envelope
                envelope = {
                    "cluster_id": cluster_id,
                    "config_snapshot": {
                        "n_clusters": n_clusters,
                        "buffer_deg": buffer_deg
                    },
                    "bounding_box": {
                        "lat_min": float(lat_min),
                        "lat_max": float(lat_max),
                        "lon_min": float(lon_min),
                        "lon_max": float(lon_max)
                    },
                    "outlet_ids": outlet_ids,
                    "n_outlets": len(outlet_ids),
                    "n_pois_returned": len(elements),
                    "scraped_at": datetime.datetime.now().isoformat(),
                    "elements": elements
                }
                
                # Save cache file
                cache_file = CACHE_DIR / f"cluster_{cluster_id:04d}.json"
                with open(cache_file, "w") as f:
                    json.dump(envelope, f, indent=2)
                
                # Update manifest
                manifest["completed_clusters"].append(cluster_id)
                if cluster_id in manifest["failed_clusters"]:
                    manifest["failed_clusters"].remove(cluster_id)
                save_manifest(manifest)
                
                success = True
                break # Exit retry loop
                
            except requests.exceptions.RequestException as e:
                log.warning("Cluster %04d: Request failed (attempt %d): %s", cluster_id, attempt+1, str(e))
                if attempt < retries:
                    time.sleep(5)
            except json.JSONDecodeError:
                log.warning("Cluster %04d: Invalid JSON response (attempt %d).", cluster_id, attempt+1)
                if attempt < retries:
                    time.sleep(5)
                    
        if not success:
            log.error("Cluster %04d failed permanently.", cluster_id)
            if cluster_id not in manifest["failed_clusters"]:
                manifest["failed_clusters"].append(cluster_id)
            save_manifest(manifest)
            
    # Final Summary
    log.info("Phase 1 Finished.")
    log.info("Total clusters: %d", n_clusters)
    log.info("Completed: %d", len(manifest["completed_clusters"]))
    log.info("Failed: %d", len(manifest["failed_clusters"]))
    
    if len(manifest["failed_clusters"]) > 0:
        log.warning("There were %d failed clusters. Phase 2 will handle them gracefully.", len(manifest["failed_clusters"]))

if __name__ == "__main__":
    main()
