"""
Build competitive catchment density features using flat outlet-to-outlet counts.

Layer  : Gold
Inputs : data/Silver/outlet_coordinates_clean.parquet,
         data/Silver/outlet_master_clean.parquet
Outputs: data/Gold/catchment_features.parquet
"""

import time
from pathlib import Path

import numpy as np
import pandas as pd
import yaml
from sklearn.neighbors import BallTree

from pipeline.utils.logger import setup_logger

# ---------------------------------------------------------------------------
# Paths & Config
# ---------------------------------------------------------------------------
PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent
CONFIG_PATH = PROJECT_ROOT / "config.yaml"
SILVER_DIR = PROJECT_ROOT / "Data" / "Silver"
GOLD_DIR = PROJECT_ROOT / "Data" / "Gold"

with open(CONFIG_PATH) as f:
    CFG = yaml.safe_load(f)

log = setup_logger("build_catchment_features")

# Radius bands for competitor counts (metres → km)
RADII_M = [500, 1000, 2000]
RADII_KM = [r / 1000.0 for r in RADII_M]

# Percentile thresholds for market saturation classification
# Based on competitors_1km distribution
SATURATION_THRESHOLDS = {
    "isolated_upper": 25,   # P25 — bottom quartile → "isolated"
    "dense_lower": 75,      # P75 — top quartile → "dense"
}


# ---------------------------------------------------------------------------
# Core computation
# ---------------------------------------------------------------------------
def compute_catchment(coords_df: pd.DataFrame) -> pd.DataFrame:
    """
    For each outlet with valid coordinates, count how many *other* outlets
    exist within each radius band using BallTree with haversine metric.

    Returns DataFrame: Outlet_ID, competitors_500m, competitors_1km,
    competitors_2km, competition_density_score, market_saturation_class.
    """
    n_outlets = len(coords_df)
    log.info("Building BallTree for %d valid-coord outlets...", n_outlets)

    # Haversine expects (lat, lon) in radians
    coords_rad = np.radians(coords_df[["Latitude", "Longitude"]].values)
    tree = BallTree(coords_rad, metric="haversine")

    # Query all radius bands at once (use the largest radius)
    max_radius_rad = max(RADII_KM) / 6371.0  # Earth radius in km
    log.info("Querying neighbours within %.0fm...", max(RADII_M))

    # query_radius returns indices of all neighbours within radius
    all_indices, all_distances = tree.query_radius(
        coords_rad, r=max_radius_rad, return_distance=True
    )

    results: list[dict] = []

    for i in range(n_outlets):
        row: dict = {"Outlet_ID": coords_df.iloc[i]["Outlet_ID"]}

        # Distances in km (haversine returns radians — multiply by Earth radius)
        dists_km = all_distances[i] * 6371.0
        indices = all_indices[i]

        # Exclude self (distance ≈ 0, same index)
        mask_not_self = indices != i
        dists_km = dists_km[mask_not_self]

        # Count competitors per radius band
        for r_m, r_km in zip(RADII_M, RADII_KM):
            col_name = f"competitors_{r_m}m" if r_m < 1000 else f"competitors_{r_m // 1000}km"
            row[col_name] = int(np.sum(dists_km <= r_km))

        results.append(row)

    df = pd.DataFrame(results)
    return df


def add_density_and_classification(df: pd.DataFrame) -> pd.DataFrame:
    """
    Add normalised competition_density_score [0, 100] and
    market_saturation_class (isolated / moderate / dense).
    """
    # Use competitors_1km as the primary density metric
    ref_col = "competitors_1km"

    # Min-max normalise to [0, 100]
    mn = df[ref_col].min()
    mx = df[ref_col].max()
    if mx > mn:
        df["competition_density_score"] = (
            (df[ref_col] - mn) / (mx - mn) * 100.0
        ).round(2).astype("float32")
    else:
        df["competition_density_score"] = np.float32(0.0)

    # Classify based on percentile thresholds of competitors_1km
    p_iso = np.percentile(df[ref_col], SATURATION_THRESHOLDS["isolated_upper"])
    p_dense = np.percentile(df[ref_col], SATURATION_THRESHOLDS["dense_lower"])

    conditions = [
        df[ref_col] <= p_iso,
        df[ref_col] >= p_dense,
    ]
    choices = ["isolated", "dense"]
    df["market_saturation_class"] = np.select(conditions, choices, default="moderate")

    log.info("Saturation thresholds - isolated: <=%d competitors_1km, dense: >=%d",
             int(p_iso), int(p_dense))
    log.info("  isolated : %d outlets", (df["market_saturation_class"] == "isolated").sum())
    log.info("  moderate : %d outlets", (df["market_saturation_class"] == "moderate").sum())
    log.info("  dense    : %d outlets", (df["market_saturation_class"] == "dense").sum())

    return df


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------
def main() -> None:
    start = time.time()
    log.info("=" * 60)
    log.info("BUILD CATCHMENT FEATURES  (Node 2 — Round 2)")
    log.info("=" * 60)

    # --- Load outlet coordinates (valid only) ---
    coords_df = pd.read_parquet(SILVER_DIR / "outlet_coordinates_clean.parquet")
    log.info("Loaded %d outlet coordinates from Silver.", len(coords_df))

    # --- Load all outlet IDs ---
    master_df = pd.read_parquet(SILVER_DIR / "outlet_master_clean.parquet")
    all_outlet_ids = set(master_df["Outlet_ID"].unique())
    valid_outlet_ids = set(coords_df["Outlet_ID"].unique())
    zero_coord_ids = all_outlet_ids - valid_outlet_ids
    log.info("Total outlets: %d | Valid coords: %d | Zero-coord: %d",
             len(all_outlet_ids), len(valid_outlet_ids), len(zero_coord_ids))

    # --- Compute catchment for valid-coord outlets ---
    catchment_df = compute_catchment(coords_df)
    catchment_df = add_density_and_classification(catchment_df)
    log.info("Computed catchment features for %d valid-coord outlets.", len(catchment_df))

    # --- Append zero-coord outlets with 0 competitors ---
    if zero_coord_ids:
        zero_rows: list[dict] = []
        for out_id in zero_coord_ids:
            zero_rows.append({
                "Outlet_ID": out_id,
                "competitors_500m": 0,
                "competitors_1km": 0,
                "competitors_2km": 0,
                "competition_density_score": np.float32(0.0),
                "market_saturation_class": "isolated",
            })
        zero_df = pd.DataFrame(zero_rows)
        catchment_df = pd.concat([catchment_df, zero_df], ignore_index=True)
        log.info("Appended %d zero-coord outlets with 0 competitors.", len(zero_coord_ids))

    # --- Cast types per DATA_CONTRACTS.md ---
    for col in ["competitors_500m", "competitors_1km", "competitors_2km"]:
        catchment_df[col] = catchment_df[col].astype("int32")
    catchment_df["competition_density_score"] = catchment_df["competition_density_score"].astype("float32")

    # --- Order columns per spec ---
    final_columns = [
        "Outlet_ID",
        "competitors_500m",
        "competitors_1km",
        "competitors_2km",
        "competition_density_score",
        "market_saturation_class",
    ]
    catchment_df = catchment_df[final_columns]

    # --- Assertions (DATA_CONTRACTS.md) ---
    log.info("Running data contract assertions...")
    assert len(catchment_df) == len(all_outlet_ids), (
        f"Expected {len(all_outlet_ids)} rows, got {len(catchment_df)}"
    )
    assert catchment_df["Outlet_ID"].duplicated().sum() == 0, "Duplicate Outlet_IDs"
    assert catchment_df["Outlet_ID"].isnull().sum() == 0, "Null Outlet_IDs"
    assert catchment_df.isnull().sum().sum() == 0, "NaN values found"

    for col in ["competitors_500m", "competitors_1km", "competitors_2km"]:
        assert (catchment_df[col] >= 0).all(), f"Negative values in {col}"

    assert catchment_df["competition_density_score"].between(0, 100).all(), (
        "competition_density_score out of [0, 100]"
    )
    valid_classes = {"isolated", "moderate", "dense"}
    actual_classes = set(catchment_df["market_saturation_class"].unique())
    assert actual_classes.issubset(valid_classes), (
        f"Invalid saturation classes: {actual_classes - valid_classes}"
    )

    # Monotonicity check: competitors_500m ≤ competitors_1km ≤ competitors_2km
    assert (catchment_df["competitors_500m"] <= catchment_df["competitors_1km"]).all(), (
        "500m competitors exceeds 1km — BallTree radius logic error"
    )
    assert (catchment_df["competitors_1km"] <= catchment_df["competitors_2km"]).all(), (
        "1km competitors exceeds 2km — BallTree radius logic error"
    )
    log.info("All assertions passed.")

    # --- Write output ---
    output_path = GOLD_DIR / "catchment_features.parquet"
    catchment_df.to_parquet(output_path, index=False, engine="pyarrow", compression="snappy")

    duration = time.time() - start
    log.info("Written %d rows x %d columns -> %s",
             len(catchment_df), len(catchment_df.columns), output_path.name)
    log.info("Catchment feature build completed in %.1fs.", duration)

    # --- Summary stats ---
    log.info("--- Summary (all outlets) ---")
    for col in ["competitors_500m", "competitors_1km", "competitors_2km"]:
        log.info("  %-20s  mean=%.1f  median=%.0f  max=%d",
                 col, catchment_df[col].mean(), catchment_df[col].median(), catchment_df[col].max())
    log.info("  competition_density_score  mean=%.1f  median=%.1f  max=%.1f",
             catchment_df["competition_density_score"].mean(),
             catchment_df["competition_density_score"].median(),
             catchment_df["competition_density_score"].max())


if __name__ == "__main__":
    main()
