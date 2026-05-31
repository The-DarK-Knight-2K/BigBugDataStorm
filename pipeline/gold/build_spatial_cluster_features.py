"""
Build DBSCAN spatial micro-market clustering features.

Uses DBSCAN on (Latitude, Longitude) with haversine metric to discover
natural micro-market neighborhoods — dense clusters of outlets that share
a local market environment. Unlike K-Means (used for POI acquisition),
DBSCAN discovers clusters of arbitrary shape and identifies noise points
(geographically isolated outlets).

Layer  : Gold
Inputs : Data/Silver/outlet_coordinates_clean.parquet,
         Data/Silver/outlet_master_clean.parquet,
         Data/Gold/sales_features.parquet
Outputs: Data/Gold/spatial_cluster_features.parquet
"""

import time
from pathlib import Path

import numpy as np
import pandas as pd
import yaml
from sklearn.cluster import DBSCAN

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

log = setup_logger("build_spatial_cluster_features")

# DBSCAN parameters
EARTH_RADIUS_KM = 6371.0
EPS_KM = 1.0         # Outlets within 1 km are considered in the same micro-market
MIN_SAMPLES = 5      # Minimum 5 outlets to form a cluster


# ---------------------------------------------------------------------------
# Core computation
# ---------------------------------------------------------------------------
def compute_dbscan_clusters(coords_df: pd.DataFrame) -> pd.DataFrame:
    """
    Apply DBSCAN clustering on outlet coordinates using haversine distance.

    Returns DataFrame with: Outlet_ID, micro_market_id, is_spatial_outlier.
    """
    log.info(
        "Running DBSCAN: eps=%.1f km, min_samples=%d on %d outlets...",
        EPS_KM, MIN_SAMPLES, len(coords_df),
    )

    # DBSCAN with haversine expects radians
    coords_rad = np.radians(coords_df[["Latitude", "Longitude"]].values)

    clustering = DBSCAN(
        eps=EPS_KM / EARTH_RADIUS_KM,
        min_samples=MIN_SAMPLES,
        metric="haversine",
    ).fit(coords_rad)

    result = coords_df[["Outlet_ID"]].copy()
    result["micro_market_id"] = clustering.labels_    # -1 = noise
    result["is_spatial_outlier"] = (clustering.labels_ == -1)

    n_clusters = len(set(clustering.labels_)) - (1 if -1 in clustering.labels_ else 0)
    n_noise = (clustering.labels_ == -1).sum()

    log.info(
        "DBSCAN found %d clusters, %d noise points (spatial outliers).",
        n_clusters, n_noise,
    )

    return result


def add_cluster_statistics(
    cluster_df: pd.DataFrame,
    sales_df: pd.DataFrame,
) -> pd.DataFrame:
    """
    Enrich each outlet with aggregate statistics from its micro-market cluster.

    - cluster_outlet_count: number of outlets in the same cluster
    - cluster_mean_volume: mean hist_p90_monthly of the cluster
    - cluster_p90_volume: 90th percentile of cluster volumes
    """
    df = cluster_df.copy()

    # Merge historical P90 from sales features
    if "hist_p90_monthly" in sales_df.columns:
        df = df.merge(
            sales_df[["Outlet_ID", "hist_p90_monthly"]],
            on="Outlet_ID",
            how="left",
        )
        df["hist_p90_monthly"] = df["hist_p90_monthly"].fillna(0.0)
    else:
        df["hist_p90_monthly"] = 0.0

    # Compute cluster-level aggregates (excluding noise points from stats)
    cluster_stats = (
        df[df["micro_market_id"] >= 0]
        .groupby("micro_market_id")["hist_p90_monthly"]
        .agg(
            cluster_outlet_count="count",
            cluster_mean_volume="mean",
            cluster_p90_volume=lambda x: np.percentile(x, 90),
        )
        .reset_index()
    )

    # Merge back to all outlets
    df = df.merge(cluster_stats, on="micro_market_id", how="left")

    # Fill NaN for noise points (not part of any cluster)
    df["cluster_outlet_count"] = df["cluster_outlet_count"].fillna(0).astype("int32")
    df["cluster_mean_volume"] = df["cluster_mean_volume"].fillna(0.0)
    df["cluster_p90_volume"] = df["cluster_p90_volume"].fillna(0.0)

    # Drop intermediate column
    df = df.drop(columns=["hist_p90_monthly"])

    log.info(
        "Cluster stats — outlets in clusters: %d, mean cluster size: %.1f",
        (df["cluster_outlet_count"] > 0).sum(),
        cluster_stats["cluster_outlet_count"].mean() if len(cluster_stats) > 0 else 0,
    )

    return df


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------
def main() -> None:
    start = time.time()
    log.info("=" * 60)
    log.info("BUILD SPATIAL CLUSTER FEATURES  (OPT-4 — Round 2)")
    log.info("=" * 60)

    # --- Load outlet coordinates (valid only) ---
    coords_df = pd.read_parquet(SILVER_DIR / "outlet_coordinates_clean.parquet")
    log.info("Loaded %d outlet coordinates from Silver.", len(coords_df))

    # --- Load all outlet IDs (to include zero-coord outlets) ---
    master_df = pd.read_parquet(SILVER_DIR / "outlet_master_clean.parquet")
    all_outlet_ids = set(master_df["Outlet_ID"].unique())
    valid_outlet_ids = set(coords_df["Outlet_ID"].unique())
    zero_coord_ids = all_outlet_ids - valid_outlet_ids
    log.info(
        "Total outlets: %d | Valid coords: %d | Zero-coord: %d",
        len(all_outlet_ids), len(valid_outlet_ids), len(zero_coord_ids),
    )

    # --- Load sales features for cluster volume stats ---
    sales_df = pd.read_parquet(GOLD_DIR / "sales_features.parquet")
    log.info("Loaded %d rows from sales_features.", len(sales_df))

    # --- Run DBSCAN on valid-coord outlets ---
    cluster_df = compute_dbscan_clusters(coords_df)

    # --- Add cluster-level statistics ---
    cluster_df = add_cluster_statistics(cluster_df, sales_df)

    # --- Append zero-coord outlets as spatial outliers ---
    if zero_coord_ids:
        zero_rows = pd.DataFrame({
            "Outlet_ID": list(zero_coord_ids),
            "micro_market_id": -1,
            "is_spatial_outlier": True,
            "cluster_outlet_count": 0,
            "cluster_mean_volume": 0.0,
            "cluster_p90_volume": 0.0,
        })
        cluster_df = pd.concat([cluster_df, zero_rows], ignore_index=True)
        log.info(
            "Appended %d zero-coord outlets as spatial outliers.", len(zero_coord_ids)
        )

    # --- Cast types ---
    cluster_df["micro_market_id"] = cluster_df["micro_market_id"].astype("int32")
    cluster_df["is_spatial_outlier"] = cluster_df["is_spatial_outlier"].astype(bool)
    cluster_df["cluster_outlet_count"] = cluster_df["cluster_outlet_count"].astype("int32")
    cluster_df["cluster_mean_volume"] = cluster_df["cluster_mean_volume"].astype("float32")
    cluster_df["cluster_p90_volume"] = cluster_df["cluster_p90_volume"].astype("float32")

    # --- Order columns ---
    final_columns = [
        "Outlet_ID",
        "micro_market_id",
        "is_spatial_outlier",
        "cluster_outlet_count",
        "cluster_mean_volume",
        "cluster_p90_volume",
    ]
    cluster_df = cluster_df[final_columns]

    # --- Assertions ---
    log.info("Running data contract assertions...")
    assert len(cluster_df) == len(all_outlet_ids), (
        f"Expected {len(all_outlet_ids)} rows, got {len(cluster_df)}"
    )
    assert cluster_df["Outlet_ID"].duplicated().sum() == 0, "Duplicate Outlet_IDs"
    assert cluster_df["Outlet_ID"].isnull().sum() == 0, "Null Outlet_IDs"
    assert cluster_df.isnull().sum().sum() == 0, "NaN values found"
    assert (cluster_df["cluster_outlet_count"] >= 0).all(), "Negative cluster count"
    assert (cluster_df["cluster_mean_volume"] >= 0).all(), "Negative cluster volume"

    # Spatial outliers must have micro_market_id == -1
    outlier_mask = cluster_df["is_spatial_outlier"]
    if outlier_mask.any():
        assert (cluster_df.loc[outlier_mask, "micro_market_id"] == -1).all(), (
            "Spatial outliers must have micro_market_id == -1"
        )
    log.info("All assertions passed.")

    # --- Write output ---
    output_path = GOLD_DIR / "spatial_cluster_features.parquet"
    cluster_df.to_parquet(output_path, index=False, engine="pyarrow", compression="snappy")

    duration = time.time() - start
    log.info(
        "Written %d rows x %d columns -> %s (%.1fs)",
        len(cluster_df), len(cluster_df.columns), output_path.name, duration,
    )

    # --- Summary stats ---
    log.info("--- Summary ---")
    log.info("  Total clusters          : %d", cluster_df[cluster_df["micro_market_id"] >= 0]["micro_market_id"].nunique())
    log.info("  Spatial outliers        : %d", cluster_df["is_spatial_outlier"].sum())
    log.info("  Mean cluster size       : %.1f", cluster_df[cluster_df["cluster_outlet_count"] > 0]["cluster_outlet_count"].mean())
    log.info("  Mean cluster volume     : %.1f", cluster_df[cluster_df["cluster_mean_volume"] > 0]["cluster_mean_volume"].mean())


if __name__ == "__main__":
    main()
