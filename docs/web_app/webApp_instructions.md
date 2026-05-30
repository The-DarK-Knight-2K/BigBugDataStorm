# Outlet Intelligence Web App — Implementation Plan

This document outlines the complete implementation plan for the Outlet Intelligence Web App (Deliverable 4 of the Data Storm v7.0 Final Round). The plan has been adapted to accurately reflect the **actual schemas, tables, and values** defined in the existing mock database generation script (`setup_db.py`). 

## ✅ Current Status (Completed Work)

- **Next.js Setup**: Next.js 15 is successfully initialized in the `App` root folder.
- **Styling**: Tailwind CSS and `shadcn/ui` are fully configured.
- **Folder Structure**: Integrated the Next.js `src/` directory seamlessly alongside the existing `data` and `scripts` folders.
- **Dependencies Installed**: `better-sqlite3`, `react-leaflet`, `leaflet`, `recharts`, `lucide-react`.
- **Skeleton Pages Built**: Empty placeholder files have been created for all required routes and API endpoints.
- **Backend Scaffolded**: Created empty `data_access/db.ts`, `data_access/queries.ts`, and `lib/gemini.ts`.

---

## 🚀 Next Steps

1. **Database Access (`src/lib/db.ts`)**: Implement `better-sqlite3` to query `outlets`, `budget_allocations`, `xai_contexts`, and `pipeline_health`.
2. **Dashboard (`src/app/page.tsx`)**: Build the summary stats, the Leaflet map view, and the data table.
3. **Outlet Detail Page (`src/app/outlets/[id]/page.tsx`)**: Build the UI for predicted metrics, SHAP feature impacts, and the Gemini explanation component.
4. **LLM API (`src/app/api/explain/[id]/route.ts`)**: Connect Gemini 2.0 Flash to generate the XAI explanation and cache it back to SQLite.

---

## 1. What This App Is
The Outlet Intelligence Web App is a functional business intelligence tool allowing sales managers and judges to:
- Browse all outlet predictions across Sri Lanka.
- Filter by province, distributor, and tier.
- Drill into any single outlet to see its predicted potential, recent averages, gravity scores, and SHAP-based feature impacts.
- Read an AI-generated plain-English explanation of WHY that outlet got its score, powered by Gemini 2.0 Flash.

## 2. Tech Stack Decision
| Layer              | Technology              | Reason                                      |
| ------------------ | ----------------------- | ------------------------------------------- |
| Frontend + Backend | Next.js (App Router)    | Full-stack, professional UI, API routes     |
| Database           | SQLite (local .db file) | Single file, zero setup, fast SQL queries   |
| SQLite Client      | better-sqlite3          | Synchronous, fastest SQLite option for Node |
| Maps               | React-Leaflet           | Free, no API key, handles 20k markers       |
| Charts             | Recharts                | Clean, works natively with React            |
| LLM / XAI          | Gemini 2.0 Flash (Free) | Sufficient for demo, zero cost              |
| Styling            | Tailwind + shadcn/ui    | Premium, industry-standard component library|

## 3. High Level Architecture
1. `setup_db.py` ingests mock JSON data and generates `outlets.db`.
2. `outlets.db` contains four tables: `outlets`, `budget_allocations`, `xai_contexts`, and `pipeline_health`.
3. The `xai_contexts` table pre-computes a rich `context_json` for every outlet, preparing it for the LLM.
4. When a user requests an XAI explanation, the Next.js API route reads `context_json`, checks if `xai_explanation` is NULL. If so, it calls Gemini, updates the row, and returns the result.

## 4. Database Schema (SQLite)
Based exactly on `setup_db.py`:

```sql
CREATE TABLE outlets (
    outlet_id TEXT PRIMARY KEY,
    outlet_type TEXT NOT NULL,
    outlet_size TEXT NOT NULL,
    province TEXT NOT NULL,
    distributor_id TEXT NOT NULL,
    latitude REAL NOT NULL,
    longitude REAL NOT NULL,
    cooler_count INTEGER NOT NULL,
    predicted_potential_litres REAL NOT NULL,
    recent_3m_avg REAL NOT NULL,
    hist_p90_monthly REAL NOT NULL,
    has_transaction_history INTEGER NOT NULL,
    composite_gravity_score REAL NOT NULL,
    footfall_score REAL NOT NULL
);

CREATE TABLE budget_allocations (
    outlet_id TEXT PRIMARY KEY,
    uplift_gap_litres REAL NOT NULL,
    roi_score REAL NOT NULL,
    allocation_tier TEXT NOT NULL,
    trade_spend_allocation_lkr REAL NOT NULL,
    recommended_spend_type TEXT NOT NULL,
    projected_volume_uplift_litres REAL NOT NULL,
    FOREIGN KEY (outlet_id) REFERENCES outlets(outlet_id) ON DELETE CASCADE
);

CREATE TABLE xai_contexts (
    outlet_id TEXT PRIMARY KEY,
    context_json TEXT NOT NULL,
    xai_explanation TEXT, -- NULL by default, generated on-the-fly at runtime
    FOREIGN KEY (outlet_id) REFERENCES outlets(outlet_id) ON DELETE CASCADE
);

CREATE TABLE pipeline_health (
    dataset TEXT PRIMARY KEY,
    records_checked INTEGER NOT NULL,
    records_passed INTEGER NOT NULL,
    records_quarantined INTEGER NOT NULL,
    quarantine_rate REAL NOT NULL,
    check_details_json TEXT NOT NULL
);
```

## 5. The Outlet JSON Structure (LLM Context)
The JSON structure already generated by `setup_db.py` inside `xai_contexts` will be passed directly to Gemini. An example structure:

```json
{
  "outlet_id": "W_001",
  "province": "Western",
  "distributor_id": "DIST_W_01",
  "outlet_type": "Grocery",
  "outlet_size": "Medium",
  "cooler_count": 2,
  "prediction": {
    "uplift_gap_litres": 2150.0,
    "Maximum_Monthly_Liters": 4250.0,
    "recent_3m_avg": 2100.0,
    "seasonality_multiplier_jan_2026": 1.18
  },
  "sales_history": {
    "hist_p90_monthly": 2415.0,
    "active_months": 24,
    "consecutive_zero_months_max": 1,
    "hist_cv": 0.10
  },
  "poi_features": {
    "footfall_score": 85.4
  },
  "gravity_features": {
    "composite_gravity_score": 7.8,
    "transport_gravity_score": 3.5
  },
  "shap_values": [
    {"feature": "transport_gravity_score", "shap_value": 1075.0, "direction": "positive", "feature_value": 3.5},
    {"feature": "footfall_score", "shap_value": 645.0, "direction": "positive", "feature_value": 85.4}
  ],
  "budget": {
    "allocation_tier": "high",
    "roi_score": 0.85,
    "recommended_spend_type": "cooler_grant",
    "trade_spend_allocation_lkr": 45000.0
  }
}
```

## 6. LLM Integration & Prompts
The LLM integration will rely on reading the above JSON. 

**System Prompt Adjustments:**
- Instead of generic POI counts, mention **Gravity Scores** and **Footfall Scores**.
- Explain that **SHAP values** dictate feature importance.
- Reference **Uplift Gap** and **Recent 3M Avg**.
- Emphasize interpreting the `budget` recommendations if available.

**Caching Strategy:**
```sql
-- Read
SELECT context_json, xai_explanation FROM xai_contexts WHERE outlet_id = ?;

-- Write
UPDATE xai_contexts SET xai_explanation = ? WHERE outlet_id = ?;
```

## 7. Web App Pages

**Page 1 — Dashboard / Home (`/`)**
- Summary Stats: Total Outlets, Total Predicted Volume, High Potential Outlets.
- Filters: Province, Distributor, Tier.
- **Map View:** 20k markers (React-Leaflet) colored by potential tier.
- **Table View:** `outlet_id`, `outlet_type`, `predicted_potential_litres`, `recent_3m_avg`, `composite_gravity_score`.

**Page 2 — Outlet Detail Page (`/outlets/[id]`)**
- Header: Name, Province, Distributor, Size, Type.
- Metrics Cards: Predicted Maximum, Recent 3M Avg, Uplift Gap, Composite Gravity Score.
- **SHAP Feature Impact Chart:** Horizontal bar chart mapping `shap_values` array (Positive = Green, Negative = Red).
- Budget Allocation constraints (if available).
- **AI Business Insight:** Calls the `/api/explain/[id]` route, triggers spinner, and caches response.

**Page 3 — Budget Allocation Dashboard (`/budget`)**
- Focuses on outlets where `budget_allocations` exist.
- Summary Stats: Total Allocated Spend, Total Projected Uplift.
- Charts: Budget split by distributor, ROI scores.
- Table: Filterable budget allocation list.

**Page 4 — Pipeline Health Dashboard (`/health`)**
- Validates the `pipeline_health` data and tracks recent runs.

## 8. Actual Project Structure
```text
/App                            ← Project Root
  /data
    outlets.db                  ← Existing SQLite Database
  /scripts                      ← Existing Python scripts
    setup_db.py
    verify_db.py
  /src                          ← Next.js Source Folder
    /app
      /api/explain/[id]/route.ts
      /budget/page.tsx
      /health/page.tsx          
      /outlets/[id]/page.tsx
      globals.css
      layout.tsx
      page.tsx
    /components
      /ui                       ← shadcn/ui components
      Map.tsx                   
    /data_access
      db.ts                     ← SQLite Connection
      queries.ts                ← SQL Queries
    /lib                        
      gemini.ts                 ← Gemini API Client
      utils.ts                  ← shadcn utilities
  package.json                  
  tailwind.config.ts            
```
