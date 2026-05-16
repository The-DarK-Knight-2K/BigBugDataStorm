# Data Contracts — Exact Schema for Every Parquet File

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

### `poi_features.parquet`
| Column | Type | Nullable | Notes |
|--------|------|----------|-------|
| Outlet_ID | string | No | |
| schools_500m | int16 | No | Count within 500m |
| schools_1km | int16 | No | Count within 1km |
| schools_2km | int16 | No | Count within 2km |
| hospitals_500m | int16 | No | |
| hospitals_1km | int16 | No | |
| transport_500m | int16 | No | Bus stops + train stations |
| transport_1km | int16 | No | |
| markets_1km | int16 | No | Supermarkets + marketplaces |
| worship_500m | int16 | No | Places of worship (Poya Day traffic) |
| hotels_restaurants_500m | int16 | No | |
| poi_total_500m | int16 | No | Sum of all POI types within 500m |
| poi_total_1km | int16 | No | Sum of all POI types within 1km |
| footfall_score | float32 | No | Weighted composite, see SPEC_scrape_poi.md |
| poi_data_available | bool | No | False for the 40 zero-coord quarantined outlets |

### `sales_features.parquet`
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

### `master_features.parquet`
One row per outlet. All 20,000 outlets must be present (even the 40 with no valid
coordinates — they get median-imputed POI features).

| Column group | Source |
|-------------|--------|
| Outlet_ID | Key |
| All `outlet_master_clean` columns | Silver |
| Latitude, Longitude, coords_swapped | Silver coords |
| All `sales_features` columns | Gold sales |
| All `poi_features` columns | Gold POI |
| seasonality_jan_2026 | Silver seasonality (Jan 2026, distributor match) |
| jan_2026_holiday_count | Silver holidays (distinct holiday dates in Jan 2026) |
| jan_2026_trading_days | Computed: 31 − jan_2026_holiday_count − weekend_days |
| province | Derived from distributor_id |

---

## Output — `outputs/`

### `teamname_predictions.csv`
| Column | Type | Notes |
|--------|------|-------|
| Outlet_ID | string | All 20,000 outlets |
| Maximum_Monthly_Liters | float32 | Rounded to 2 decimal places. Must be > 0. |

### `dq_report.csv`
| Column | Type | Notes |
|--------|------|-------|
| dataset | string | Source file name |
| check_name | string | e.g. "duplicate_check" |
| records_checked | int | Total rows checked |
| records_passed | int | |
| records_quarantined | int | |
| failure_reasons | string | Comma-separated list of unique failure_reason values |
