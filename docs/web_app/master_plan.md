# Outlet Intelligence Web App — Master Plan

This is the single source of truth for Deliverable 4 of the Data Storm v7.0 Final Round. All technical implementation details have been broken down into dedicated specification files to ensure accuracy and reduce clutter.

## ✅ Current Status (Completed Work)
- **Next.js Setup**: Next.js 15 is successfully initialized in the `App` root folder.
- **Styling**: Tailwind CSS and `shadcn/ui` are fully configured.
- **Folder Structure**: Integrated the Next.js `src/` directory seamlessly alongside the existing `data` and `scripts` folders.
- **Dependencies Installed**: `better-sqlite3`, `react-leaflet`, `leaflet`, `recharts`, `lucide-react`.
- **Skeleton Pages Built**: Empty placeholder files have been created for all required routes.
- **Backend Scaffolded**: Created empty `data_access/db.ts`, `data_access/queries.ts`, and `lib/gemini.ts`.

## 📖 Specifications Directory
The detailed project requirements are located in the `specs/webapp/` folder:

- **[Spec 01: Architecture & Stack](file:///c:/Users/USER/Desktop/BigBugDataStorm/specs/webapp/01_architecture.md)** — High-level overview, data flow, tech stack, and Judge Setup Instructions.
- **[Spec 02: Database Schema](file:///c:/Users/USER/Desktop/BigBugDataStorm/specs/webapp/02_database.md)** — Accurate representations of the generated `outlets`, `budget_allocations`, `xai_contexts`, and `pipeline_health` tables, plus the expected JSON Context structure.
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

## 🚀 Phase 2: Real Data Migration (Current Active Phase)

Phase 1 is now **COMPLETED and FROZEN**. AI agents and developers must exclusively focus their efforts on Phase 2.

The exhaustive implementation plan for Phase 2 has been refactored into its own dedicated specification file:
- **[Spec 05: Phase 2 Migration Plan](file:///c:/Users/USER/Desktop/BigBugDataStorm/specs/webapp/05_phase2_migration.md)** — Contains the full database architecture (including spatial POI mapping), ETL data ingestion steps, and UI upgrades.

### 📋 Phase 2 Implementation Tasks
- [x] **Data Ingestion**: Build `App/scripts/populate_real_db.py` to parse parquets, CSVs, and `poi_raw_cache` JSONs into the new SQLite schema.
- [ ] **DB Access**: Update `App/src/data_access/queries.ts` to support the new schema and the new `getOutletPOIs` spatial query.
- [ ] **UI - Dashboard**: Add the 5th KPI card, Saturation column, and Market Saturation filter in `/`.
- [ ] **UI - Details**: Add the Cooler Capacity and Market Catchment panels in `/outlets/[id]`.
- [ ] **UI - Map**: Upgrade `SingleMap.tsx` to render the 2km radius competitors and footfall POIs.
- [ ] **GenAI API**: Update the `SYSTEM_PROMPT` in `route.ts` to explain the new Tobit/Hurdle and DBSCAN features.
