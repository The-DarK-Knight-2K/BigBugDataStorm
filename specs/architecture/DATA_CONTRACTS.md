# Data Contracts — Exact Schema for Every Parquet File
# Round 2 Extended Version (includes all Round 1 schemas + new Round 2 additions)

Every parquet file produced by the pipeline must conform to the schema below.
Column names, types, and nullability are strict. Any script that writes a parquet
file must validate its output against this contract before saving.

---

## Bronze layer — `data/bronze/`

Bronze files are raw snapshots. Schemas match the source CSV exactly.

### `transactions.parquet`
| Column | Type | Nullable | Notes |
|--------|------|----------|-------|
| Outlet_ID | string | No | As-is from CSV |
| Date | string | Yes | Raw string, not parsed |
| Distributor_ID | string | Yes | As-is from CSV |
| Volume_Litres | float64 | Yes | As-is, may be negative |
| *(other cols)* | as-is | Yes | Preserve all columns from CSV |

> **Note:** The exact column names in `transactions_history_final.csv` are unknown
> until the file is opened. Bronze ingest must read all columns dynamically and write
> them all. Do not hardcode column names for this file.

### `outlet_master.parquet`
| Column | Type | Nullable |
|--------|------|----------|
| Outlet_ID | string | No |
| Outlet_Size | string | Yes |
| Cooler_Count | int64 | No |
| Outlet_Type | string | No |

### `outlet_coordinates.parquet`
| Column | Type | Nullable |
|--------|------|----------|
| Outlet_ID | string | No |
| Latitude | float64 | No |
| Longitude | float64 | No |

### `seasonality.parquet`
| Column | Type | Nullable |
|--------|------|----------|
| Distributor_ID | string | No |
| Year | int64 | No |
| Month | int64 | No |
| Seasonality_Index | string | No |

### `holidays.parquet`
| Column | Type | Nullable |
|--------|------|----------|
| Date | string | No |
| Holiday_Name | string | No |
| Holiday_Type | string | No |

---

## Silver layer — `data/silver/`

### `transactions_clean.parquet`
| Column | Type | Nullable | Notes |
|--------|------|----------|-------|
| Outlet_ID | string | No | Validated against outlet_master |
| Date | date | No | Parsed to Python date |
| Year | int16 | No | Extracted from Date |
| Month | int8 | No | Extracted from Date (1–12) |
| Distributor_ID | string | No | Validated against known distributor list |
| Volume_Litres | float32 | No | Positive values only |
| is_blackout_period | bool | No | True if in a connectivity gap sequence |
| row_source | string | No | Always "transactions_history_final.csv" |

### `outlet_master_clean.parquet`
| Column | Type | Nullable | Notes |
|--------|------|----------|-------|
| Outlet_ID | string | No | |
| Outlet_Size | string | No | One of: Small, Medium, Large, Extra Large |
| Cooler_Count | int8 | No | Range 0–5 |
| Outlet_Type | string | No | One of: Hotel, Grocery, SMMT, Pharmacy, Kiosk, Bakery, Eatery |
| size_imputed | bool | No | True if size was null and imputed from Cooler_Count |

### `outlet_coordinates_clean.parquet`
| Column | Type | Nullable | Notes |
|--------|------|----------|-------|
| Outlet_ID | string | No | |
| Latitude | float64 | No | Range 5.9–9.9 |
| Longitude | float64 | No | Range 79.5–81.9 |
| coords_swapped | bool | No | True if lat/lon were swapped and fixed |

### `seasonality_clean.parquet`
| Column | Type | Nullable | Notes |
|--------|------|----------|-------|
| Distributor_ID | string | No | |
| Year | int16 | No | Includes 2026 (extrapolated) |
| Month | int8 | No | 1–12 |
| Seasonality_Index | string | No | One of: Favorable, Moderate, Un-Favorable |
| is_extrapolated | bool | No | True for all 2026 rows |

### `holidays_clean.parquet`
| Column | Type | Nullable | Notes |
|--------|------|----------|-------|
| date | date | No | One row per unique calendar date |
| Holiday_Name | string | No | Name of primary holiday on that date |
| is_public | bool | No | |
| is_bank | bool | No | |
| is_mercantile | bool | No | |
| is_poya_day | bool | No | |

---

## Quarantine — `data/quarantine/`

All rejected record files share the same appended column:

| Extra Column | Type | Notes |
|-------------|------|-------|
| failure_reason | string | Snake_case code, e.g. `"zero_coordinates"` |
| original_row_index | int64 | Row number from the bronze parquet file |

### Quarantine files
- `rejected_transactions.parquet`
- `rejected_outlet_coordinates.parquet`

---

## Gold layer — `data/gold/`

### `poi_features.parquet` *(Round 1 — retained)*
| Column | Type | Nullable | Notes |
|--------|------|----------|-------|
| Outlet_ID | string | No | Primary key |
| schools_500m | int32 | No | Count within 500m |
| schools_1000m | int32 | No | Count within 1000m |
| schools_2000m | int32 | No | Count within 2000m |
| hospitals_500m | int32 | No | Count within 500m |
| hospitals_1000m | int32 | No | Count within 1000m |
| hospitals_2000m | int32 | No | Count within 2000m |
| transport_500m | int32 | No | Bus stops + train stations within 500m |
| transport_1000m | int32 | No | Bus stops + train stations within 1000m |
| transport_2000m | int32 | No | Bus stops + train stations within 2000m |
| markets_500m | int32 | No | Supermarkets + marketplaces within 500m |
| markets_1000m | int32 | No | Supermarkets + marketplaces within 1000m |
| markets_2000m | int32 | No | Supermarkets + marketplaces within 2000m |
| worship_500m | int32 | No | Places of worship within 500m |
| worship_1000m | int32 | No | Places of worship within 1000m |
| worship_2000m | int32 | No | Places of worship within 2000m |
| hospitality_500m | int32 | No | Hotels + restaurants within 500m |
| hospitality_1000m | int32 | No | Hotels + restaurants within 1000m |
| hospitality_2000m | int32 | No | Hotels + restaurants within 2000m |
| footfall_score | float32 | No | Weighted composite (0-100), based only on 500m |
| poi_data_available | bool | No | False for the 40 zero-coord quarantined outlets |

### `gravity_features.parquet` *(Round 2 — NEW)*
| Column | Type | Nullable | Notes |
|--------|------|----------|-------|
| Outlet_ID | string | No | Primary key |
| school_gravity_score | float32 | No | Σ 1/(d+ε)² for schools within 2km |
| hospital_gravity_score | float32 | No | Σ 1/(d+ε)² for hospitals within 2km |
| transport_gravity_score | float32 | No | Σ 1/(d+ε)² for transit within 2km |
| market_gravity_score | float32 | No | Σ 1/(d+ε)² for markets within 2km |
| worship_gravity_score | float32 | No | Σ 1/(d+ε)² for worship within 2km |
| hospitality_gravity_score | float32 | No | Σ 1/(d+ε)² for hospitality within 2km |
| raw_composite_gravity | float32 | No | Unnormalised weighted sum |
| composite_gravity_score | float32 | No | Normalised [0, 100] across all valid outlets |
| gravity_data_available | bool | No | False for the 40 zero-coord quarantined outlets |

> See `specs/gold/GRAVITY_MODEL.md` for full decay function specification and implementation.

### `catchment_features.parquet` *(Round 2 — NEW)*
| Column | Type | Nullable | Notes |
|--------|------|----------|-------|
| Outlet_ID | string | No | Primary key |
| competitors_500m | int32 | No | Count of other outlets within 500m |
| competitors_1km | int32 | No | Count of other outlets within 1km |
| competitors_2km | int32 | No | Count of other outlets within 2km |
| competition_density_score | float32 | No | Normalised [0, 100] |
| market_saturation_class | string | No | One of: isolated, moderate, dense |

### `sales_features.parquet` *(Round 1 — retained)*
| Column | Type | Nullable | Notes |
|--------|------|----------|-------|
| Outlet_ID | string | No | |
| hist_max_monthly | float32 | No | Highest single month volume ever |
| hist_p90_monthly | float32 | No | 90th percentile monthly volume |
| hist_p75_monthly | float32 | No | 75th percentile monthly volume |
| hist_mean_monthly | float32 | No | Mean monthly volume |
| hist_std_monthly | float32 | No | Std dev of monthly volume |
| hist_cv | float32 | No | Coefficient of variation (std/mean) |
| jan_avg_volume | float32 | No | Average volume in January months only |
| jan_max_volume | float32 | No | Max volume in any January |
| jan_count | int8 | No | Number of Januaries observed |
| active_months | int16 | No | Total months with at least one transaction |
| active_months_pct | float32 | No | active_months / total_months_in_data |
| consecutive_zero_months_max | int8 | No | Longest gap with no orders |
| yoy_growth_rate | float32 | Yes | Null if fewer than 2 years of data |
| recent_3m_avg | float32 | No | Average of last 3 months |
| trend_slope | float32 | Yes | Linear regression slope; null if <6 data points |
| months_since_last_order | int16 | No | Recency indicator |
| total_volume | float32 | No | Lifetime volume sum |
| distributor_id | string | No | Most frequent distributor for this outlet |
| ema_3m | float32 | No | 3-month exponential moving average of monthly volume |
| ema_6m | float32 | No | 6-month exponential moving average of monthly volume |

### `shap_values.parquet` *(Round 2 — NEW)*
One row per outlet. One column per model feature (signed float). Outlet_ID is the index key.

| Column | Type | Nullable | Notes |
|--------|------|----------|-------|
| Outlet_ID | string | No | Primary key |
| *(one column per feature)* | float32 | No | Signed SHAP contribution in litres |

> Columns are dynamic — one per feature in `FEATURE_COLS` from `modelling/train.py`.
> Must be extracted immediately after training in `modelling/train.py` before
> writing `modelling/artifacts/model.pkl`.
> See `specs/modelling/XAI_SPEC.md` Step 1 for extraction code.

### `xai_context.parquet` *(Round 2 — NEW)*
| Column | Type | Nullable | Notes |
|--------|------|----------|-------|
| Outlet_ID | string | No | Primary key |
| context_json | string | No | JSON-serialised context dict per specs/modelling/XAI_SPEC.md Step 2 |

> The `context_json` column stores the full context payload as a JSON string.
> Parse with `json.loads(row["context_json"])` before passing to the prompt builder.


### `master_features.parquet` *(Round 1 base + Round 2 additions)*
One row per outlet. All 20,000 outlets must be present.

| Column group | Source | Round |
|-------------|--------|-------|
| Outlet_ID | Key | R1 |
| All `outlet_master_clean` columns | Silver | R1 |
| Latitude, Longitude, coords_swapped | Silver coords | R1 |
| All `sales_features` columns | Gold sales | R1 |
| All `poi_features` columns | Gold POI | R1 |
| All `gravity_features` columns | Gold gravity | **R2** |
| All `catchment_features` columns | Gold catchment | **R2** |
| seasonality_jan_2026 | Silver seasonality | R1 |
| seasonality_multiplier_jan_2026 | Derived from seasonality | R1 |
| jan_2026_holiday_count | Silver holidays | R1 |
| jan_2026_trading_days | `jan_2026_trading_days.json` | R1 |
| province | Derived from distributor_id | R1 |
| has_transaction_history | bool — True if `active_months > 0` | R1 |
| exclude_from_training | bool — True for ~40 zero-coord outlets | R1 |

> All float columns are upcast to `float64` and rounded to 4 decimal places.
> Categorical columns (`Outlet_Type`, `Outlet_Size`, `province`, `seasonality_jan_2026`)
> are stored as raw strings. Encoding is deferred to `train.py`.

---

## Optimization layer — `data/Optimizations/`

### `budget_features.parquet` *(Round 2 — NEW, Western Province only)*
| Column | Type | Nullable | Notes |
|--------|------|----------|-------|
| Outlet_ID | string | No | Primary key — Western Province outlets only (~6,842 rows) |
| uplift_gap_litres | float32 | No | predicted_potential − recent_3m_avg, clipped at 0 |
| roi_score | float32 | No | Weighted composite [0, 1] — see specs/modelling/BUDGET_OPTIMIZATION.md |
| allocation_tier | string | No | One of: `high`, `medium`, `low` |
| trade_spend_allocation_lkr | float32 | No | Final LKR allocation (0 if below floor) |
| recommended_spend_type | string | No | One of: `cooler_grant`, `discount_voucher`, `display_material` |
| projected_volume_uplift_litres | float32 | No | allocation × volume_per_lkr[tier] |
| is_western_province | bool | No | Always True for rows in this table |

---

## Output — `outputs/`

### `teamname_predictions.csv` *(Round 1 — format unchanged)*
| Column | Type | Notes |
|--------|------|-------|
| Outlet_ID | string | All 20,000 outlets |
| Maximum_Monthly_Liters | float32 | Rounded to 2 decimal places. Must be > 0. |

### `teamname_budget_allocations.csv` *(Round 2 — NEW)*
| Column | Type | Notes |
|--------|------|-------|
| Outlet_ID | string | Western Province outlets only (~6,842 rows) |
| Trade_Spend_Allocation_LKR | float32 | Rounded to 2 decimal places. Must be ≥ 0. Sum ≤ 5,000,000. |

> Non-Western Province outlets must NOT appear in this file.
> Outlets receiving zero allocation ARE included with `Trade_Spend_Allocation_LKR = 0.00`.
> See `specs/modelling/BUDGET_OPTIMIZATION.md` for full allocation logic.

### `dq_report.csv` *(Round 1 — format unchanged)*
| Column | Type | Notes |
|--------|------|-------|
| dataset | string | Source file name |
| check_name | string | e.g. "duplicate_check" |
| records_checked | int | Total rows checked |
| records_passed | int | |
| records_quarantined | int | |
| failure_reasons | string | Comma-separated list of unique failure_reason values |

---

## Cross-file referential integrity rules

| Child file | Foreign key | Must exist in |
|-----------|------------|---------------|
| `transactions_clean` | `Outlet_ID` | `outlet_master_clean` |
| `transactions_clean` | `Distributor_ID` | known distributor list in `config.yaml` |
| `gravity_features` | `Outlet_ID` | `outlet_coordinates_clean` (valid coords only) |
| `catchment_features` | `Outlet_ID` | `outlet_coordinates_clean` (valid coords only) |
| `shap_values` | `Outlet_ID` | `master_features` |
| `xai_context` | `Outlet_ID` | `master_features` |
| `budget_features` | `Outlet_ID` | `master_features` WHERE `province = "Western"` |
| `teamname_budget_allocations.csv` | `Outlet_ID` | `budget_features` |
| `teamname_predictions.csv` | `Outlet_ID` | `outlet_master_clean` (must be exactly 20,000) |
