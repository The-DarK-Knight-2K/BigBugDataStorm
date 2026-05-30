# API Spec — Outlet Intelligence Web App

> **NOTE (Round 2 Architecture Update):**
> We have dropped the FastAPI Python backend. All endpoints below are now served by **Next.js API Routes** directly from the web app. The Python pipeline (`export_for_webapp.py`) generates static JSON data files (`outlets.json`, `budget_summary.json`) that the Next.js routes read from disk to fulfill this contract.

Member C must code against this contract from Day 1 using Next.js. The JSON payloads defined below are exactly what the Next.js endpoints must return to the frontend components.

---

## General conventions

- All responses are `application/json`
- Dates are ISO 8601 strings: `"2026-01-01"`
- Monetary values are plain floats in LKR with 2 decimal places
- Volumes are plain floats in litres with 2 decimal places
- Pagination uses `page` (1-indexed) and `page_size` (default 50, max 200)
- All list endpoints return a `meta` block alongside `data`
- `null` is returned for optional fields with no value — never omitted
- HTTP errors follow the standard error envelope (see section 6)

---

## 1. Outlets — list and filter

### `GET /outlets`

Returns a paginated list of all 20,000 outlets with their top-level prediction.

**Query parameters**

| Parameter | Type | Required | Default | Notes |
|-----------|------|----------|---------|-------|
| `page` | int | No | 1 | 1-indexed |
| `page_size` | int | No | 50 | Max 200 |
| `province` | string | No | — | One of: `Western`, `Central`, `North-Western`, `Southern` |
| `distributor_id` | string | No | — | e.g. `DIST_W_01` |
| `outlet_type` | string | No | — | One of: `Grocery`, `Hotel`, `SMMT`, `Pharmacy`, `Kiosk`, `Bakery`, `Eatery` |
| `outlet_size` | string | No | — | One of: `Small`, `Medium`, `Large`, `Extra Large` |
| `sort_by` | string | No | `predicted_potential_litres` | Any numeric column name |
| `sort_dir` | string | No | `desc` | `asc` or `desc` |
| `search` | string | No | — | Partial match on `Outlet_ID` |

**Response `200 OK`**

```json
{
  "meta": {
    "total_records": 20000,
    "page": 1,
    "page_size": 50,
    "total_pages": 400,
    "filters_applied": {
      "province": "Western",
      "distributor_id": null,
      "outlet_type": null,
      "outlet_size": null
    }
  },
  "data": [
    {
      "outlet_id": "OUT_W_00042",
      "province": "Western",
      "distributor_id": "DIST_W_01",
      "outlet_type": "Grocery",
      "outlet_size": "Medium",
      "cooler_count": 2,
      "latitude": 6.9271,
      "longitude": 79.8612,
      "predicted_potential_litres": 1240.50,
      "current_avg_monthly_litres": 820.30,
      "uplift_gap_litres": 420.20,
      "footfall_score": 67.40,
      "has_budget_allocation": true,
      "budget_allocation_lkr": 45000.00
    }
  ]
}
```

**Notes for Member C**
- `has_budget_allocation` is `true` only for Western Province outlets
- `budget_allocation_lkr` is `null` for non-Western outlets
- Use this endpoint for the Outlet Explorer table view and the map view

---

## 2. Outlet detail

### `GET /outlets/{outlet_id}`

Returns the full feature profile for a single outlet.

**Path parameters**

| Parameter | Type | Notes |
|-----------|------|-------|
| `outlet_id` | string | Exact match, e.g. `OUT_W_00042` |

**Response `200 OK`**

```json
{
  "outlet_id": "OUT_W_00042",
  "province": "Western",
  "distributor_id": "DIST_W_01",
  "outlet_type": "Grocery",
  "outlet_size": "Medium",
  "cooler_count": 2,
  "latitude": 6.9271,
  "longitude": 79.8612,
  "coords_swapped": false,
  "size_imputed": false,

  "prediction": {
    "predicted_potential_litres": 1240.50,
    "current_avg_monthly_litres": 820.30,
    "uplift_gap_litres": 420.20,
    "seasonality_jan_2026": "Favorable",
    "seasonality_multiplier": 1.15,
    "jan_2026_trading_days": 20,
    "jan_2026_holiday_count": 2
  },

  "sales_history": {
    "hist_max_monthly": 1050.00,
    "hist_p90_monthly": 980.00,
    "hist_p75_monthly": 890.00,
    "hist_mean_monthly": 820.30,
    "hist_std_monthly": 112.40,
    "hist_cv": 0.137,
    "jan_avg_volume": 855.00,
    "jan_max_volume": 960.00,
    "jan_count": 3,
    "active_months": 36,
    "active_months_pct": 0.923,
    "consecutive_zero_months_max": 2,
    "yoy_growth_rate": 0.082,
    "recent_3m_avg": 841.00,
    "trend_slope": 4.20,
    "months_since_last_order": 1,
    "total_volume": 29530.80,
    "ema_3m": 838.50,
    "ema_6m": 825.10
  },

  "poi_features": {
    "schools_500m": 2,
    "schools_1000m": 5,
    "schools_2000m": 11,
    "hospitals_500m": 0,
    "hospitals_1000m": 1,
    "hospitals_2000m": 3,
    "transport_500m": 4,
    "transport_1000m": 9,
    "transport_2000m": 18,
    "markets_500m": 1,
    "markets_1000m": 3,
    "markets_2000m": 7,
    "worship_500m": 1,
    "worship_1000m": 4,
    "worship_2000m": 9,
    "hospitality_500m": 2,
    "hospitality_1000m": 6,
    "hospitality_2000m": 14,
    "footfall_score": 67.40,
    "poi_data_available": true
  },

  "gravity_features": {
    "school_gravity_score": 3.842,
    "hospital_gravity_score": 0.410,
    "transport_gravity_score": 8.750,
    "market_gravity_score": 2.110,
    "worship_gravity_score": 1.330,
    "hospitality_gravity_score": 1.980,
    "composite_gravity_score": 62.30
  },

  "shap_values": [
    { "feature": "transport_gravity_score", "shap_value": 182.40, "direction": "positive", "feature_value": 8.75 },
    { "feature": "footfall_score",          "shap_value": 134.20, "direction": "positive", "feature_value": 67.40 },
    { "feature": "hist_p90_monthly",        "shap_value": 98.10,  "direction": "positive", "feature_value": 980.00 },
    { "feature": "cooler_count",            "shap_value": 72.30,  "direction": "positive", "feature_value": 2 },
    { "feature": "hist_cv",                 "shap_value": -45.80, "direction": "negative", "feature_value": 0.137 },
    { "feature": "consecutive_zero_months_max", "shap_value": -38.10, "direction": "negative", "feature_value": 2 },
    { "feature": "months_since_last_order", "shap_value": -12.40, "direction": "negative", "feature_value": 1 }
  ],

  "budget": {
    "allocation_lkr": 45000.00,
    "allocation_tier": "high",
    "roi_score": 0.892,
    "recommended_spend_type": "cooler_grant",
    "is_western_province": true
  }
}
```

**Error `404 Not Found`**

```json
{ "error": "outlet_not_found", "detail": "No outlet with ID OUT_W_99999" }
```

---

## 3. XAI explanation

### `GET /explain/{outlet_id}`

Generates and returns an LLM-powered business explanation for the outlet's
predicted score. This call hits the LLM API on each request — do not cache
aggressively on the frontend; a 5–10 second response time is expected.

**Path parameters**

| Parameter | Type | Notes |
|-----------|------|-------|
| `outlet_id` | string | Exact match |

**Response `200 OK`**

```json
{
  "outlet_id": "OUT_W_00042",
  "explanation": {
    "headline": "Strong transit access and consistent order history drive a high ceiling for this outlet.",
    "drivers_up": [
      "Located near 4 bus stops within 500m, generating high daily commuter footfall.",
      "Consistent ordering history across 36 active months with an 8.2% year-on-year growth trend.",
      "90th-percentile historical volume of 980 L indicates the outlet has repeatedly approached its ceiling."
    ],
    "drivers_down": [
      "Moderate demand variability (CV: 0.14) suggests some volatility in ordering behaviour.",
      "Two consecutive zero-volume months in the history point to short-term stock or credit disruptions."
    ],
    "local_context": "This outlet operates in a high-footfall Western Province corridor served by DIST_W_01. The Favorable January 2026 seasonality index for this distributor adds a further 15% uplift to the baseline estimate.",
    "recommendation": "With a predicted gap of 420 L above current average, this outlet is a strong candidate for cooler grant investment to remove physical storage constraints."
  },
  "model_version": "catboost_r2_v1",
  "generated_at": "2026-01-15T08:42:11Z",
  "prompt_tokens_used": 410,
  "completion_tokens_used": 187
}
```

**Error `404 Not Found`**

```json
{ "error": "outlet_not_found", "detail": "No outlet with ID OUT_W_99999" }
```

**Error `503 Service Unavailable`** (LLM API timeout)

```json
{ "error": "llm_unavailable", "detail": "XAI service timed out. Retry in 10 seconds." }
```

**Notes for Member C**
- Show a loading skeleton while awaiting the response — 5–10s is normal
- Display `drivers_up` as green-coded bullets and `drivers_down` as amber-coded bullets
- The `headline` is the primary display element — render it prominently above the lists
- Display `prompt_tokens_used` + `completion_tokens_used` in a collapsed "AI debug" section for transparency

---

## 4. Budget allocation summary

### `GET /budget/summary`

Returns aggregate budget allocation statistics for the Western Province.

**Query parameters**

| Parameter | Type | Required | Notes |
|-----------|------|----------|-------|
| `distributor_id` | string | No | Filter to a single distributor |
| `outlet_type` | string | No | Filter to a single outlet type |
| `tier` | string | No | One of: `high`, `medium`, `low` |

**Response `200 OK`**

```json
{
  "meta": {
    "total_budget_lkr": 5000000.00,
    "total_outlets_allocated": 6842,
    "total_outlets_western": 6842,
    "filters_applied": { "distributor_id": null, "outlet_type": null, "tier": null }
  },
  "summary_by_tier": [
    { "tier": "high",   "outlet_count": 812,  "total_allocated_lkr": 2100000.00, "avg_allocation_lkr": 2586.21, "avg_roi_score": 0.88 },
    { "tier": "medium", "outlet_count": 2430, "total_allocated_lkr": 1900000.00, "avg_allocation_lkr": 782.30,  "avg_roi_score": 0.61 },
    { "tier": "low",    "outlet_count": 3600, "total_allocated_lkr": 1000000.00, "avg_allocation_lkr": 277.78,  "avg_roi_score": 0.29 }
  ],
  "summary_by_distributor": [
    { "distributor_id": "DIST_W_01", "outlet_count": 2290, "total_allocated_lkr": 1680000.00, "pct_of_budget": 33.60 },
    { "distributor_id": "DIST_W_02", "outlet_count": 2180, "total_allocated_lkr": 1620000.00, "pct_of_budget": 32.40 },
    { "distributor_id": "DIST_W_03", "outlet_count": 2372, "total_allocated_lkr": 1700000.00, "pct_of_budget": 34.00 }
  ],
  "summary_by_outlet_type": [
    { "outlet_type": "Grocery",  "outlet_count": 2840, "total_allocated_lkr": 2100000.00, "pct_of_budget": 42.00 },
    { "outlet_type": "Eatery",   "outlet_count": 1200, "total_allocated_lkr": 900000.00,  "pct_of_budget": 18.00 },
    { "outlet_type": "Kiosk",    "outlet_count": 980,  "total_allocated_lkr": 640000.00,  "pct_of_budget": 12.80 },
    { "outlet_type": "Bakery",   "outlet_count": 710,  "total_allocated_lkr": 490000.00,  "pct_of_budget": 9.80 },
    { "outlet_type": "Hotel",    "outlet_count": 420,  "total_allocated_lkr": 380000.00,  "pct_of_budget": 7.60 },
    { "outlet_type": "Pharmacy", "outlet_count": 380,  "total_allocated_lkr": 260000.00,  "pct_of_budget": 5.20 },
    { "outlet_type": "SMMT",     "outlet_count": 312,  "total_allocated_lkr": 230000.00,  "pct_of_budget": 4.60 }
  ],
  "projected_volume_uplift_litres": 128400.00
}
```

---

## 5. Pipeline health / DQ report

### `GET /pipeline/health`

Returns the data quality report for display in the Pipeline Health dashboard view.

**Response `200 OK`**

```json
{
  "generated_at": "2026-01-15T06:00:00Z",
  "overall_pass_rate": 0.9930,
  "datasets": [
    {
      "dataset": "transactions_history_final.csv",
      "records_checked": 2376389,
      "records_passed": 2359769,
      "records_quarantined": 16620,
      "quarantine_rate": 0.0070,
      "checks": [
        { "check_name": "duplicate_check",          "passed": 2375800, "quarantined": 589,   "failure_reason": "duplicate_primary_key" },
        { "check_name": "null_check",               "passed": 2376200, "quarantined": 189,   "failure_reason": "null_mandatory_field" },
        { "check_name": "range_check_volume",       "passed": 2374612, "quarantined": 1777,  "failure_reason": "negative_volume" },
        { "check_name": "referential_integrity",    "passed": 2370120, "quarantined": 6249,  "failure_reason": "orphaned_outlet_id" },
        { "check_name": "format_check_date",        "passed": 2375983, "quarantined": 406,   "failure_reason": "unparseable_date" },
        { "check_name": "referential_distributor",  "passed": 2376203, "quarantined": 186,   "failure_reason": "unknown_distributor_id" }
      ]
    },
    {
      "dataset": "outlet_coordinates.csv",
      "records_checked": 20000,
      "records_passed": 19960,
      "records_quarantined": 40,
      "quarantine_rate": 0.0020,
      "checks": [
        { "check_name": "zero_coordinate_check",   "passed": 19960,  "quarantined": 40,    "failure_reason": "zero_coordinates" },
        { "check_name": "swap_correction",         "passed": 19800,  "quarantined": 0,     "failure_reason": null, "corrected": 200 }
      ]
    },
    {
      "dataset": "outlet_master.csv",
      "records_checked": 20000,
      "records_passed": 20000,
      "records_quarantined": 0,
      "quarantine_rate": 0.0000,
      "checks": [
        { "check_name": "null_size_imputation",    "passed": 20000,  "quarantined": 0,     "failure_reason": null, "corrected": 196 },
        { "check_name": "typo_canonicalization",   "passed": 20000,  "quarantined": 0,     "failure_reason": null, "corrected": 785 }
      ]
    }
  ]
}
```

---

## 6. Standard error envelope

All error responses use this shape:

```json
{
  "error": "snake_case_error_code",
  "detail": "Human-readable description of what went wrong.",
  "request_id": "req_8f3a2c"
}
```

| HTTP Status | `error` code | When used |
|-------------|-------------|-----------|
| 400 | `invalid_parameter` | Bad query param type or value |
| 404 | `outlet_not_found` | Outlet ID does not exist |
| 422 | `validation_error` | Request body fails schema validation |
| 503 | `llm_unavailable` | XAI LLM API timed out or returned an error |
| 500 | `internal_error` | Unhandled server exception |

---

## 7. Mock server

Member C can mock these Next.js API Routes by having them return static JSON fixtures from `app/data/mock_outlets.json` during early development.

Once Phase 3 is complete and `export_for_webapp.py` has generated the real data files, swap the API routes to read from the real `app/data/outlets.json` instead of the mock fixtures.
