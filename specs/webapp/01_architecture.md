# Spec 01: Architecture & Stack

## Overview

The Outlet Intelligence Web App (Deliverable 4) is a local business intelligence tool allowing users to:

- Browse outlet predictions across Sri Lanka.
- Filter by province, distributor, and potential tier.
- View predicted potential and AI-generated explanations per outlet.

## Tech Stack

- **Framework**: Next.js (App Router)
- **Database**: SQLite (`better-sqlite3` - synchronous, extremely fast)
- **UI/Styling**: Tailwind CSS v4, shadcn/ui, Lucide React
- **Maps**: React-Leaflet
- **Charts**: Recharts
- **LLM**: Gemini 2.0 Flash

## Project Structure

```text
/App
  /data/outlets.db              ← Local SQLite Database
  /scripts/populate_real_db.py  ← Generation ETL script for outlets.db (Phase 2)
  /src/app                      ← Next.js Pages & API
  /src/components               ← UI Components (shadcn, Map)
  /src/data_access              ← SQLite Queries & Connection
  /src/lib                      ← Utilities & LLM Clients
```

## Data Flow

1. **Python Pipeline**: Outputs ML predictions, budget allocations, SHAP values, and spatial POI caches.
2. **Database Generation**: Run `populate_real_db.py` to ingest the parquets/CSVs and generate `outlets.db` locally.
3. **Next.js Data Access**: Server Components access SQLite directly via `better-sqlite3`. No external backend service is needed.
4. **On-Demand XAI**: API routes invoke Gemini 2.0 Flash for on-demand XAI explanations. The output is cached in SQLite immediately.

## Git Strategy

- **Commits**: The Next.js app, `/scripts/populate_real_db.py`, and the CSVs (if under 100MB) are committed.
- **Gitignore**: `/data/outlets.db` (generated locally), `.env.local` (API keys), `node_modules/`, and `.next/` must NOT be committed.
