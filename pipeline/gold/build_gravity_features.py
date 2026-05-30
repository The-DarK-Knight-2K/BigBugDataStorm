"""
Build gravity-based POI features using inverse-square distance decay.

Layer  : Gold
Inputs : data/Gold/poi_raw_cache/*.json, data/Silver/outlet_coordinates_clean.parquet,
         data/Silver/outlet_master_clean.parquet
Outputs: data/Gold/gravity_features.parquet
"""

import json
import time
from pathlib import Path

import numpy as np
import pandas as pd
import yaml
from sklearn.neighbors import BallTree
from tqdm import tqdm

from pipeline.utils.logger import setup_logger

# ---------------------------------------------------------------------------
# Paths & Config
# ---------------------------------------------------------------------------
PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent
CONFIG_PATH = PROJECT_ROOT / "config.yaml"
SILVER_DIR = PROJECT_ROOT / "Data" / "Silver"
GOLD_DIR = PROJECT_ROOT / "Data" / "Gold"
CACHE_DIR = GOLD_DIR / "poi_raw_cache"

with open(CONFIG_PATH) as f:
    CFG = yaml.safe_load(f)

log = setup_logger("build_gravity_features")

# ---------------------------------------------------------------------------
# POI category map (matches build_poi_features.py + GRAVITY_MODEL.md tags)
# ---------------------------------------------------------------------------
POI_CATEGORY_MAP: dict[str, list[tuple[str, str]]] = {
    "school":      [("amenity", "school"), ("amenity", "university"), ("amenity", "college")],
    "hospital":    [("amenity", "hospital"), ("amenity", "clinic"), ("amenity", "pharmacy")],
    "transport":   [("highway", "bus_stop"), ("railway", "station"), ("railway", "halt")],
    "market":      [("shop", "supermarket"), ("amenity", "marketplace"), ("shop", "convenience")],
    "worship":     [("amenity", "place_of_worship")],
    "hospitality": [("amenity", "restaurant"), ("amenity", "hotel"), ("tourism", "hotel")],
}

CATEGORIES = list(POI_CATEGORY_MAP.keys())


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------
def classify_poi(tags: dict) -> str | None:
    """Return category string if tags match any rule, else None."""
    for category, tag_list in POI_CATEGORY_MAP.items():
        for k, v in tag_list:
            if tags.get(k) == v:
                return category
    return None


def load_all_pois() -> pd.DataFrame:
    """
    Parse every cluster JSON from the POI raw cache.
    Returns a DataFrame with columns: [lat, lon, category].
    """
    manifest_path = CACHE_DIR / "scrape_manifest.json"
    if not manifest_path.exists():
        raise FileNotFoundError(
            "POI cache not found. Run pipeline/gold/scrape_poi_raw.py first."
        )

    with open(manifest_path) as f:
        manifest = json.load(f)

    completed = manifest.get("completed_clusters", [])
    failed = set(manifest.get("failed_clusters", []))
    if failed:
        log.warning("%d clusters failed during scraping — their POIs are missing.", len(failed))

    rows: list[dict] = []
    seen: set[tuple[float, float, str]] = set()  # deduplicate POIs across clusters

    for cluster_id in tqdm(completed, desc="Loading POI cache"):
        cache_file = CACHE_DIR / f"cluster_{cluster_id:04d}.json"
        if not cache_file.exists():
            continue

        with open(cache_file, "r", encoding="utf-8") as f:
            cluster_data = json.load(f)

        for el in cluster_data.get("elements", []):
            cat = classify_poi(el.get("tags", {}))
            if cat is None:
                continue
            key = (el["lat"], el["lon"], cat)
            if key in seen:
                continue
            seen.add(key)
            rows.append({"lat": el["lat"], "lon": el["lon"], "category": cat})

    poi_df = pd.DataFrame(rows)
    log.info("Loaded %d unique POIs across %d clusters.", len(poi_df), len(completed))
    for cat in CATEGORIES:
        n = (poi_df["category"] == cat).sum()
        log.info("  %-15s: %d POIs", cat, n)

    return poi_df


def compute_gravity_scores(
    outlets_df: pd.DataFrame,
    poi_df: pd.DataFrame,
    epsilon: float,
    max_radius_km: float,
    weights: dict[str, float],
) -> pd.DataFrame:
    """
    For each outlet, compute per-category inverse-square gravity scores
    using BallTree for fast neighbour queries.

    Returns DataFrame: Outlet_ID + 6 category scores + raw_composite + composite + flag.
    """
    max_radius_rad = max_radius_km / 6371.0  # Earth radius in km

    # Build per-category BallTrees (haversine expects radians)
    trees: dict[str, tuple[BallTree, np.ndarray]] = {}
    for cat in CATEGORIES:
        cat_pois = poi_df[poi_df["category"] == cat]
        if cat_pois.empty:
            trees[cat] = (None, np.empty((0, 2)))
            continue
        coords_rad = np.radians(cat_pois[["lat", "lon"]].values)
        tree = BallTree(coords_rad, metric="haversine")
        trees[cat] = (tree, coords_rad)

    # Outlet coordinates in radians
    outlet_coords_rad = np.radians(outlets_df[["Latitude", "Longitude"]].values)

    results: list[dict] = []

    for i in tqdm(range(len(outlets_df)), desc="Computing gravity scores"):
        outlet = outlets_df.iloc[i]
        row: dict = {"Outlet_ID": outlet["Outlet_ID"]}
        raw_composite = 0.0
        point = outlet_coords_rad[i].reshape(1, -1)

        for cat in CATEGORIES:
            tree, _ = trees[cat]
            if tree is None:
                score = 0.0
            else:
                # Query all POIs within max_radius
                indices, distances = tree.query_radius(
                    point, r=max_radius_rad, return_distance=True
                )
                dists_km = distances[0] * 6371.0  # radians → km

                # Inverse-square decay: Σ 1/(d_km + ε)²
                score = float(np.sum(1.0 / (dists_km + epsilon) ** 2))

            col = f"{cat}_gravity_score"
            row[col] = round(score, 4)
            raw_composite += weights.get(cat, 1.0) * score

        row["raw_composite_gravity"] = round(raw_composite, 4)
        results.append(row)

    df = pd.DataFrame(results)

    # Min-max normalise composite to [0, 100]
    mn = df["raw_composite_gravity"].min()
    mx = df["raw_composite_gravity"].max()
    if mx > mn:
        df["composite_gravity_score"] = (
            (df["raw_composite_gravity"] - mn) / (mx - mn) * 100.0
        ).round(2)
    else:
        df["composite_gravity_score"] = 0.0

    df["gravity_data_available"] = True
    return df


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------
def main() -> None:
    start = time.time()
    log.info("=" * 60)
    log.info("BUILD GRAVITY FEATURES  (Node 1 - Round 2)")
    log.info("=" * 60)

    # --- Config ---
    grav_cfg = CFG["gravity_model"]
    epsilon = grav_cfg["decay_epsilon"]
    max_radius_km = grav_cfg["max_radius_km"]
    weights = grav_cfg["weights"]
    log.info("Decay function : %s", grav_cfg["decay_function"])
    log.info("Epsilon (km)   : %s", epsilon)
    log.info("Max radius (km): %s", max_radius_km)
    log.info("Weights        : %s", weights)

    # --- Load outlet coordinates (valid only) ---
    coords_df = pd.read_parquet(SILVER_DIR / "outlet_coordinates_clean.parquet")
    log.info("Loaded %d outlet coordinates from Silver.", len(coords_df))

    # --- Load all outlet IDs (to include zero-coord outlets) ---
    master_df = pd.read_parquet(SILVER_DIR / "outlet_master_clean.parquet")
    all_outlet_ids = set(master_df["Outlet_ID"].unique())
    valid_outlet_ids = set(coords_df["Outlet_ID"].unique())
    zero_coord_ids = all_outlet_ids - valid_outlet_ids
    log.info("Total outlets: %d | Valid coords: %d | Zero-coord: %d",
             len(all_outlet_ids), len(valid_outlet_ids), len(zero_coord_ids))

    # --- Load POIs ---
    poi_df = load_all_pois()

    # --- Compute gravity scores for valid-coord outlets ---
    gravity_df = compute_gravity_scores(
        coords_df, poi_df, epsilon, max_radius_km, weights
    )
    log.info("Computed gravity scores for %d valid-coord outlets.", len(gravity_df))

    # --- Append zero-coord outlets with all-zero scores ---
    if zero_coord_ids:
        zero_rows: list[dict] = []
        for out_id in zero_coord_ids:
            row: dict = {"Outlet_ID": out_id}
            for cat in CATEGORIES:
                row[f"{cat}_gravity_score"] = 0.0
            row["raw_composite_gravity"] = 0.0
            row["composite_gravity_score"] = 0.0
            row["gravity_data_available"] = False
            zero_rows.append(row)
        zero_df = pd.DataFrame(zero_rows)
        gravity_df = pd.concat([gravity_df, zero_df], ignore_index=True)
        log.info("Appended %d zero-coord outlets with gravity_data_available=False.", len(zero_coord_ids))

    # --- Cast types per DATA_CONTRACTS.md ---
    gravity_score_cols = [f"{cat}_gravity_score" for cat in CATEGORIES]
    for col in gravity_score_cols + ["raw_composite_gravity", "composite_gravity_score"]:
        gravity_df[col] = gravity_df[col].astype("float32")
    gravity_df["gravity_data_available"] = gravity_df["gravity_data_available"].astype(bool)

    # --- Order columns per spec ---
    final_columns = (
        ["Outlet_ID"]
        + gravity_score_cols
        + ["raw_composite_gravity", "composite_gravity_score", "gravity_data_available"]
    )
    gravity_df = gravity_df[final_columns]

    # --- Assertions (DATA_CONTRACTS.md) ---
    log.info("Running data contract assertions...")
    assert len(gravity_df) == len(all_outlet_ids), (
        f"Expected {len(all_outlet_ids)} rows, got {len(gravity_df)}"
    )
    assert gravity_df["Outlet_ID"].duplicated().sum() == 0, "Duplicate Outlet_IDs"
    assert gravity_df["Outlet_ID"].isnull().sum() == 0, "Null Outlet_IDs"
    assert gravity_df.isnull().sum().sum() == 0, "NaN values found"
    for col in gravity_score_cols + ["raw_composite_gravity"]:
        assert (gravity_df[col] >= 0).all(), f"Negative values in {col}"
    assert gravity_df["composite_gravity_score"].between(0, 100).all(), (
        "composite_gravity_score out of [0, 100]"
    )
    # Zero-coord outlets must have all-zero scores
    zero_mask = ~gravity_df["gravity_data_available"]
    if zero_mask.any():
        for col in gravity_score_cols:
            assert (gravity_df.loc[zero_mask, col] == 0).all(), (
                f"Zero-coord outlet has non-zero {col}"
            )
    log.info("All assertions passed.")

    # --- Write output ---
    output_path = GOLD_DIR / "gravity_features.parquet"
    gravity_df.to_parquet(output_path, index=False, engine="pyarrow", compression="snappy")

    duration = time.time() - start
    log.info("Written %d rows x %d columns -> %s", len(gravity_df), len(gravity_df.columns), output_path.name)
    log.info("Gravity feature build completed in %.1fs.", duration)

    # --- Summary stats ---
    valid = gravity_df[gravity_df["gravity_data_available"]]
    log.info("--- Summary (valid-coord outlets only) ---")
    for col in gravity_score_cols + ["composite_gravity_score"]:
        log.info("  %-30s  mean=%.2f  median=%.2f  max=%.2f",
                 col, valid[col].mean(), valid[col].median(), valid[col].max())


if __name__ == "__main__":
    main()
