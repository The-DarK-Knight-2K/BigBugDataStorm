# Outlet Intelligence Web App — Master Plan

This is the single source of truth for Deliverable 4 of the Data Storm v7.0 Final Round. All technical implementation details have been broken down into dedicated specification files to ensure accuracy and reduce clutter.

## ✅ Current Status (Completed Work)
- **Next.js Setup**: Next.js 15 is successfully initialized in the `App` root folder.
- **Styling**: Tailwind CSS and `shadcn/ui` are fully configured.
- **Folder Structure**: Integrated the Next.js `src/` directory seamlessly alongside the existing `data` and `scripts` folders.
- **Dependencies Installed**: `better-sqlite3`, `react-leaflet`, `leaflet`, `recharts`, `lucide-react`, `@google/genai`.
- **All Pages Implemented**: Dashboard, Outlet Detail, Budget, and Pipeline Health pages are fully functional.
- **Backend Complete**: `data_access/db.ts`, `data_access/queries.ts`, and all API routes are production-ready.
- **Real Data Populated**: `populate_real_db.py` ingests 20,000 outlets, 9,000 budget allocations, 20,000 XAI contexts, ~20,000 cluster links, and ~38,000 POIs from parquet/CSV/JSON sources.

## 📖 Specifications Directory
The detailed project requirements are located in the `specs/webapp/` folder:

- **[Spec 01: Architecture & Stack](file:///c:/Users/USER/Desktop/BigBugDataStorm/specs/webapp/01_architecture.md)** — High-level overview, data flow, tech stack, and Judge Setup Instructions.
- **[Spec 02: Database Schema](file:///c:/Users/USER/Desktop/BigBugDataStorm/specs/webapp/02_database.md)** — Accurate representations of all 6 tables (`outlets`, `budget_allocations`, `xai_contexts`, `pipeline_health`, `outlet_clusters`, `cluster_pois`), the expanded `outlets` schema with spatial gravity scores, and the expected JSON structures.
- **[Spec 03: LLM & XAI Integration](file:///c:/Users/USER/Desktop/BigBugDataStorm/specs/webapp/03_llm_integration.md)** — The exact System Prompts, User Prompts, and caching strategies for Gemini 2.0 Flash.
- **[Spec 04: UI & Pages](file:///c:/Users/USER/Desktop/BigBugDataStorm/specs/webapp/04_ui_pages.md)** — Precise layouts and visualizations required for Dashboard, Outlet Detail, Budget, and Pipeline Health pages.

---

## ✅ Phase 1: Implementation Tasks (Completed)
- [x] **Architecture**: Review `01_architecture.md` and start dev server.
- [x] **Database**: Build `src/data_access/db.ts` and SQL queries according to `02_database.md`.
- [x] **GenAI API**: Connect Gemini and implement caching in `xai_contexts` according to `03_llm_integration.md`.
- [x] **UI - Dashboard**: Build map and tables in `/` based on `04_ui_pages.md`.
- [x] **UI - Details**: Build SHAP charts and XAI component in `/outlets/[id]` based on `04_ui_pages.md`.
- [x] **UI - Budget**: Build allocation charts in `/budget` based on `04_ui_pages.md`.
- [x] **UI - Health**: Display validation states in `/health` based on `04_ui_pages.md`.

---

## ✅ Phase 2: Real Data Migration (Completed)

Phase 1 is now **COMPLETED and FROZEN**. The exhaustive implementation plan for Phase 2 has been refactored into its own dedicated specification file:
- **[Spec 05: Phase 2 Migration Plan](file:///c:/Users/USER/Desktop/BigBugDataStorm/specs/webapp/05_phase2_migration.md)** — Contains the full database architecture (including spatial POI mapping), ETL data ingestion steps, and UI upgrades.

### 📋 Phase 2 Implementation Tasks
- [x] **Data Ingestion**: Build `App/scripts/populate_real_db.py` to parse parquets, CSVs, and `poi_raw_cache` JSONs into the new SQLite schema. *(Completed & patched for case-sensitive data mapping)*
- [x] **DB Access & Performance**: Update `App/src/data_access/queries.ts` to support the new schema. *(Completed, alongside a massive Canvas-native rewrite of `Map.tsx` to render 20,000 points instantly)*
- [x] **UI - Bug Fixes**: Patched `OutletDetailClient.tsx` to securely handle the new flat SHAP dataset structure without crashing, and implemented a Business Glossary dictionary to map raw ML features to C-Suite friendly labels.
- [x] **UI - Dashboard**: Add the 5th KPI card, Saturation column, and Market Saturation filter in `/`. *(Completed)*
- [x] **UI - Details**: Add the Cooler Capacity and Market Catchment panels in `/outlets/[id]`. *(Completed, and refactored ML jargon to C-Suite friendly business terms like 'True Demand Est.' and 'Footfall Impact')*
- [x] **UI - Map**: Upgrade `SingleMap.tsx` to render the 2km radius competitors and footfall POIs.
- [x] **GenAI API**: Update the `SYSTEM_PROMPT` in `route.ts` to explain the new Tobit/Hurdle and DBSCAN features. *(Completed: enriched context pipeline + C-Suite SYSTEM_PROMPT rewrite)*

---

## 🔧 Phase 2 Audit & Fixes (Completed)

A comprehensive system audit was conducted across the full data pipeline (Python ETL → SQLite → TypeScript API → React UI). Four critical bugs were identified and fixed:

### 📋 Audit Fix Tasks
- [x] **Data Loss — Spatial Gravity Scores**: `populate_real_db.py` was not extracting `school_gravity_score`, `transport_gravity_score`, `worship_gravity_score`, `hospitality_gravity_score`, `active_months`, or `seasonality_multiplier_jan_2026` from `master_features.parquet`. The `outlets` table schema was expanded and the ETL script was patched to populate all 6 missing columns.
- [x] **UI Context Mismatch — SHAP vs Business Metrics**: `OutletDetailClient.tsx` was reading spatial scores from the SHAP `context_json` dictionary (which contains model impact values), instead of from the `outlet` database record (which contains the real-world business metrics). Refactored to read directly from the `outlet` prop.
- [x] **Pipeline Health Schema Mismatch**: `populate_real_db.py` was generating `check_details_json` with `{"check": ..., "failed": ...}` but `health/page.tsx` expected `{"check_name": ..., "passed": ..., "quarantined": ..., "failure_reason": ...}`. Fixed the Python script to match the React component's expected schema.
- [x] **Missing POI Markers — Transport & Hospitality**: The POI parser only extracted `amenity`, `shop`, and `leisure` OSM tags, causing bus stops (`highway: bus_stop`) and hotels (`tourism: hotel`) to be classified as `unknown`. Extended the parser to also extract `tourism`, `highway`, and `public_transport` tags. Updated `SingleMap.tsx` icon mappings to handle `bus_stop`, `station`, `platform`, `hotel`, `guest_house`, and `hostel`.
