# Gravity Model Spec — Distance-Weighted POI Features

## Why this replaces flat counts

Round 1 used flat POI counts: `schools_500m = 3`. This treats a school 50m away
identically to one at 490m. The Round 2 evaluation criteria explicitly calls out
**gravity/decay models** as the expected upgrade.

A gravity model weights each POI by the inverse of its distance, so a nearby POI
contributes much more than a distant one. This is the same principle as Newton's
law of gravitation — influence decays with distance.

All Round 1 flat count columns (`schools_500m`, `schools_1000m`, etc.) are
**retained in `master_features.parquet`** for backward compatibility with the
existing trained model. The gravity scores are added as new columns alongside them.

---

## The decay function

We use **inverse square decay** — the same functional form as gravitational pull
and the standard choice in retail trade area modelling:

```
gravity_contribution(poi) = 1 / (distance_km + ε)²
```

Where:
- `distance_km` is the geodesic distance from the outlet to the POI in kilometres
- `ε = 0.05` is a small constant to prevent division by zero for POIs at the exact
  outlet location (i.e. on the same GPS coordinate)

The total gravity score for a category is the sum of contributions from all POIs
in that category within the 2km radius:

```
category_gravity(outlet) = Σ  1 / (distance_km(poi) + 0.05)²
                          poi in category within 2km
```

---

## Why inverse square over exponential decay?

| Decay function | Formula | Character |
|---------------|---------|-----------|
| Inverse square | `1 / d²` | Sharp near-field drop-off, longer tail |
| Exponential | `e^(-λd)` | Smoother, tunable with λ |
| Inverse linear | `1 / d` | Gentlest decay, least discriminating |

**We chose inverse square** because:
1. It is a well-established model in retail catchment analysis (Reilly's Law of
   Retail Gravitation, 1931 — still in use)
2. It produces the sharpest discrimination between a POI at 100m vs 500m, which
   matters more for dense urban areas (Colombo) than rural ones
3. It is easy to explain to a business audience: "influence drops with the square
   of distance, just like gravity"
4. No hyperparameter to tune (exponential λ requires calibration)

---

## Per-category gravity scores

One score per category, computed across all POIs in that category within 2km:

| Column | Category | OSM tags |
|--------|----------|----------|
| `school_gravity_score` | Education | `amenity=school`, `amenity=university`, `amenity=college` |
| `hospital_gravity_score` | Healthcare | `amenity=hospital`, `amenity=clinic`, `amenity=pharmacy` |
| `transport_gravity_score` | Transit | `highway=bus_stop`, `railway=station`, `railway=halt` |
| `market_gravity_score` | Markets | `shop=supermarket`, `amenity=marketplace`, `shop=convenience` |
| `worship_gravity_score` | Community | `amenity=place_of_worship` |
| `hospitality_gravity_score` | Hospitality | `amenity=restaurant`, `amenity=hotel`, `tourism=hotel` |

---

## Composite gravity score

A single weighted composite normalised to [0, 100]:

```
raw_composite = (
    3.0 × transport_gravity_score    +
    3.0 × school_gravity_score       +
    2.0 × hospitality_gravity_score  +
    2.0 × market_gravity_score       +
    1.0 × hospital_gravity_score     +
    0.5 × worship_gravity_score
)

composite_gravity_score = minmax(raw_composite, cohort=all 19,960 outlets with valid coords) × 100
```

The weights have been optimized specifically for beverage sales potential (in litres) rather than using general footfall weights. Highly relevant beverage drivers like transit hubs, schools, and hospitality outlets (restaurants/hotels) are prioritized, while healthcare and places of worship are de-prioritized.

---

## Implementation — `pipeline/gold/build_gravity_features.py`

The script reads the POI raw cache produced by Round 1's `scrape_poi_raw.py`
(`data/gold/poi_raw_cache/`). No new API calls are needed — the cache already
contains all POI coordinates. This means the gravity upgrade is purely a
reprocessing of existing data.

```python
import pandas as pd
import numpy as np
from sklearn.neighbors import BallTree

def compute_gravity_score(outlet_lat, outlet_lon, poi_tree, poi_coords, decay_epsilon=0.05):
    """
    Returns the sum of inverse-square gravity contributions using BallTree for fast distance calculation.
    """
    pass # Implementation details omitted for brevity
```
    """
    outlets_df: DataFrame with Outlet_ID, Latitude, Longitude
    poi_cache: dict mapping cluster_id → list of POI dicts with lat/lon/category
    Returns DataFrame with Outlet_ID + 6 category gravity scores + composite
    """
    categories = [
        "school", "hospital", "transport", "market", "worship", "hospitality"
    ]
    weights = {
        "transport": 3.0, "school": 3.0, "hospitality": 2.0,
        "market": 2.0, "hospital": 1.0, "worship": 0.5
    }

    results = []
    for _, outlet in outlets_df.iterrows():
        row = {"Outlet_ID": outlet["Outlet_ID"]}
        raw_composite = 0.0

        for cat in categories:
            # Filter POIs within 2km for this outlet (pre-filtered in cache)
            pois_in_range = [
                (p["lat"], p["lon"])
                for p in poi_cache.get(outlet["cluster_id"], [])
                if p["category"] == cat
                and geodesic(
                    (outlet["Latitude"], outlet["Longitude"]),
                    (p["lat"], p["lon"])
                ).km <= 2.0
            ]
            score = compute_gravity_score(
                outlet["Latitude"], outlet["Longitude"], pois_in_range
            )
            col = f"{cat}_gravity_score"
            row[col] = score
            raw_composite += weights[cat] * score

        row["raw_composite_gravity"] = raw_composite
        results.append(row)

    df = pd.DataFrame(results)

    # Normalise composite to [0, 100]
    mn, mx = df["raw_composite_gravity"].min(), df["raw_composite_gravity"].max()
    df["composite_gravity_score"] = (
        (df["raw_composite_gravity"] - mn) / (mx - mn + 1e-9) * 100
    ).round(2)

    return df
```

---

## Output schema — `data/gold/gravity_features.parquet`

| Column | Type | Nullable | Notes |
|--------|------|----------|-------|
| Outlet_ID | string | No | Primary key |
| school_gravity_score | float32 | No | 0 if no schools within 2km |
| hospital_gravity_score | float32 | No | 0 if no hospitals within 2km |
| transport_gravity_score | float32 | No | 0 if no transit within 2km |
| market_gravity_score | float32 | No | 0 if no markets within 2km |
| worship_gravity_score | float32 | No | 0 if no worship within 2km |
| hospitality_gravity_score | float32 | No | 0 if no hospitality within 2km |
| raw_composite_gravity | float32 | No | Unnormalised weighted sum |
| composite_gravity_score | float32 | No | Normalised [0, 100] |
| gravity_data_available | bool | No | False for 40 zero-coord outlets |

---

## Integration into `master_features.parquet`

Add the 8 new gravity columns to `build_master_features.py` by left-joining
`gravity_features.parquet` on `Outlet_ID` after the existing POI join:

```python
gravity = pd.read_parquet("data/gold/gravity_features.parquet")
master = master.merge(gravity, on="Outlet_ID", how="left")

# Fill zero-coord outlets with 0 for all gravity scores
gravity_cols = [c for c in gravity.columns if c != "Outlet_ID"]
master[gravity_cols] = master[gravity_cols].fillna(0)
master["gravity_data_available"] = master["gravity_data_available"].fillna(False)
```

---

## How gravity features feed the model

In `modelling/train.py`, add the 7 gravity score columns to the feature list
alongside (not replacing) the existing flat counts:

```python
GRAVITY_FEATURES = [
    "school_gravity_score",
    "hospital_gravity_score",
    "transport_gravity_score",
    "market_gravity_score",
    "worship_gravity_score",
    "hospitality_gravity_score",
    "composite_gravity_score",
]

# Append to existing feature list
FEATURE_COLS = EXISTING_FEATURE_COLS + GRAVITY_FEATURES
```

Tree-based models handle feature selection internally — if flat counts and gravity scores
are both present, the model will weight whichever is more predictive. Expect
`composite_gravity_score` and `transport_gravity_score` to rank highly in SHAP
importance, given their physical interpretation.

---

## Validation checks for `build_gravity_features.py`

| Check | Assertion |
|-------|-----------|
| All 20,000 outlets are present | `len(df) == len(all_outlet_ids)` |
| All gravity scores are non-negative | `(df[gravity_cols] >= 0).all().all()` |
| Composite gravity score in [0, 100] | `df["composite_gravity_score"].between(0, 100).all()` |
| No NaN values | `df.isnull().sum().sum() == 0` |
| Zero-coord outlets have gravity = 0 | Cross-check against quarantine list |

---

## Tunable parameters in `config.yaml`

```yaml
gravity_model:
  decay_epsilon: 0.05          # prevents division by zero (km)
  max_radius_km: 2.0           # POIs beyond this are excluded
  decay_function: "inverse_square"   # "inverse_square" | "exponential" | "inverse_linear"
  exponential_lambda: 1.5      # only used if decay_function = "exponential"
  weights:
    transport: 3.0
    school: 3.0
    hospitality: 2.0
    market: 2.0
    hospital: 1.0
    worship: 0.5
```
