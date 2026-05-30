# WebApp Developer Instructions — Outlet Intelligence Dashboard

> **Your role:** Frontend developer building the React dashboard independently,
> in parallel with the backend/ML pipeline team. You do not need the backend
> running to get started. Read this document end to end before writing any code.

---

## What you are building

A 5-view React dashboard called the **Outlet Intelligence Dashboard**. It visualises
predicted sales potential, trade budget allocations, POI-driven footfall insights,
and AI-generated business explanations for ~20,000 retail outlets across Sri Lanka.

The five views:

| Route | View | Purpose |
|-------|------|---------|
| `/outlets` | Outlet Explorer | Paginated, filterable table of all outlets |
| `/map` | Map View | Leaflet map with outlet markers coloured by province |
| `/outlets/:id` | Outlet Detail | Full feature profile + SHAP chart + AI explanation |
| `/budget` | Budget Dashboard | Western Province trade spend allocation charts |
| `/pipeline` | Pipeline Health | Data quality report accordion |

---

## Spec files to read (in order)

All spec files live in the team repo under the `specs/` directory (organized into subfolders). These are your contracts —
treat them like an API spec you cannot change.

| Priority | File | What it covers |
|----------|------|---------------|
| 🔴 Must read first | `webapp/API_SPEC.md` | Every endpoint: URL, query params, exact JSON response shape, error envelopes. This is your ground truth. |
| 🔴 Must read first | `webapp/WEBAPP_COMPONENTS.md` | All 5 views: ASCII layouts, component behaviour, colour rules, chart specs, phase-by-phase build order. |
| 🟡 Read before building charts | `gold/GRAVITY_MODEL.md` | Explains what gravity scores are — helps you write good tooltips and labels for the SHAP chart. |
| 🟡 Read before building Outlet Detail | `gold/SPEC_build_sales_features.md` | Explains what each `sales_history` field means — essential for labelling them correctly in the UI. |
| ⚪ Optional / reference only | `architecture/SYSTEM_OVERVIEW.md` | Big-picture pipeline context. Not required for frontend work but useful for understanding the data. |
| ⚪ Optional / reference only | `architecture/DATA_CONTRACTS.md` | Backend parquet schemas — only relevant if you need to understand where a field comes from. |

**You do not need to read** any of the Silver layer specs (`SPEC_clean_*.md`),
Bronze specs, modelling specs, or orchestration specs. Those are purely backend.

---

## Tech stack

These are recommendations from the team. You can substitute, but the app must
run with `npm install && npm run dev` and use no paid API keys.

| Layer | Recommended | Why |
|-------|-------------|-----|
| Framework | React + Vite | Fast dev server |
| Styling | Tailwind CSS | Rapid UI, no custom CSS |
| Charts | Recharts | React-native, simple API |
| Map | React-Leaflet + OpenStreetMap | Free tiles, no API key |
| HTTP | Axios | Clean interceptors |
| State | Zustand | Lightweight global filter state |
| Table | TanStack Table v8 | Required for virtualising 20k rows |

---

## Project folder structure

Create your app under `app/` in the repo root:

```
app/
├── src/
│   ├── main.jsx
│   ├── App.jsx                     ← React Router v6 root
│   ├── api/
│   │   ├── client.js               ← Axios instance (base URL from env)
│   │   ├── outlets.js              ← GET /outlets, GET /outlets/:id
│   │   ├── explain.js              ← GET /explain/:id
│   │   ├── budget.js               ← GET /budget/summary
│   │   └── pipeline.js             ← GET /pipeline/health
│   ├── store/
│   │   └── useFilters.js           ← Zustand store (province, distributor, type)
│   ├── components/
│   │   ├── layout/
│   │   │   ├── Sidebar.jsx
│   │   │   └── TopBar.jsx
│   │   ├── shared/
│   │   │   ├── Badge.jsx           ← province / tier / outlet_type colour badges
│   │   │   ├── StatCard.jsx        ← single KPI card (label + value + delta)
│   │   │   ├── LoadingSkeleton.jsx ← pulsing placeholder, no spinners
│   │   │   └── ErrorBanner.jsx
│   │   └── charts/
│   │       ├── ShapWaterfall.jsx   ← horizontal bar chart (Recharts)
│   │       └── BudgetDonut.jsx     ← donut chart (Recharts PieChart)
│   └── views/
│       ├── OutletExplorer.jsx
│       ├── MapView.jsx
│       ├── OutletDetail.jsx
│       ├── BudgetDashboard.jsx
│       └── PipelineHealth.jsx
├── fixtures/
│   ├── mock_server.py              ← FastAPI mock (provided separately)
│   └── sample_outlets.json        ← ← THIS FILE — your mock data
├── .env.example
└── package.json
```

---

## Environment setup

```bash
# .env.example  (copy to .env)
VITE_API_BASE_URL=http://localhost:8000
VITE_API_MODE=mock        # mock | real
```

During **Phases 1 and 2**, keep `VITE_API_MODE=mock`. Your `api/client.js`
should detect this and serve data from `sample_outlets.json` directly — no
network calls, no backend required.

During **Phase 3**, the backend team will hand you a running FastAPI server.
Switch `VITE_API_MODE=real` and point `VITE_API_BASE_URL` at it.

---

## API overview (summary — full detail in API_SPEC.md)

| Endpoint | Used by view | Notes |
|----------|-------------|-------|
| `GET /outlets` | Explorer, Map | Paginated list. Supports province / type / size / distributor filters as query params. |
| `GET /outlets/:id` | Outlet Detail | Full profile: prediction, sales history, POI, gravity, SHAP, budget. |
| `GET /explain/:id` | Outlet Detail | LLM-generated explanation. **Slow (5–10s).** Do not auto-call on page load. |
| `GET /budget/summary` | Budget Dashboard | Aggregated budget stats by tier / distributor / outlet type. |
| `GET /pipeline/health` | Pipeline Health | DQ report — pass/quarantine counts per dataset and check. |

**Key rules from the API contract:**

- `budget_allocation_lkr` is `null` for non-Western Province outlets — always null-check before rendering
- `GET /explain/:id` must be triggered by a user button click, not on mount
- All error responses follow a standard envelope: `{ error, detail, request_id }` — handle 404 and 503 explicitly
- Column sorting is **server-side**: pass `sort_by` and `sort_dir` as query params, do not sort client-side

---

## Key UI rules (from WEBAPP_COMPONENTS.md)

### Province colour palette — use consistently across all views

| Province | Colour |
|----------|--------|
| Western | Blue |
| Central | Teal |
| North-Western | Amber |
| Southern | Coral / Orange |

### Budget tier colours

| Tier | Hex |
|------|-----|
| High | `#2563eb` |
| Medium | `#0d9488` |
| Low | `#9ca3af` |

### SHAP waterfall chart (ShapWaterfall.jsx)

- Recharts `BarChart` with `layout="vertical"`
- Positive SHAP → blue bar extending right
- Negative SHAP → amber bar extending left (use negative x value)
- Show top 5 contributors only (top 3 positive + top 2 negative — already pre-sorted by the API)
- X-axis label: `"Contribution to predicted potential (litres)"`

### Map (MapView.jsx)

- Centre: `lat: 7.8731, lng: 80.7718`, zoom 8
- `<CircleMarker>` only — not PNG pins
- Radius encodes `predicted_potential_litres` (scale 4px–14px, min-max)
- Tile: `https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png`
- Load outlets in batches of 1000 (paginated API calls), add markers progressively

### Loading states

- Use `LoadingSkeleton.jsx` (pulsing rectangle) everywhere — not spinners
- XAI panel specifically: show skeleton + "Generating business insight…" text while waiting

### Sidebar navigation

```
╔═══════════════╗
║ 🗺 Data Storm ║
╠═══════════════╣
║ Outlet Explorer║  /outlets
║ Map View       ║  /map
║ Budget         ║  /budget
║ Pipeline Health║  /pipeline
╚═══════════════╝
```

Always visible on desktop (≥ 1024px). Collapses to hamburger on mobile.

---

## Handoff from the backend team

When the backend is ready, they will give you:
- A running FastAPI server URL (replace `VITE_API_BASE_URL`)
- Confirmation that all 5 endpoints are live

The response shapes are **identical** between mock and real — no changes needed
in your API layer. Switch the env var, smoke-test each view, and fix any
unexpected shape differences.

---

## Static values to hardcode (do not fetch from API)

These are known at build time and will not change:

```js
// Provinces
const PROVINCES = ["Western", "Central", "North-Western", "Southern"];

// Distributors
const DISTRIBUTORS = [
  "DIST_W_01", "DIST_W_02", "DIST_W_03",
  "DIST_C_01", "DIST_C_02", "DIST_C_03",
  "DIST_NW_01", "DIST_NW_02",
  "DIST_S_01", "DIST_S_02"
];

// Outlet types
const OUTLET_TYPES = ["Grocery", "Hotel", "SMMT", "Pharmacy", "Kiosk", "Bakery", "Eatery"];

// Outlet sizes
const OUTLET_SIZES = ["Small", "Medium", "Large", "Extra Large"];

// Budget tiers
const TIERS = ["high", "medium", "low"];
```

---

## Things to be careful about

1. **Never render all 20,000 rows to the DOM.** The Explorer table must use TanStack Table's virtualisation.
2. **Don't auto-call the XAI endpoint.** It's slow and expensive. Button-triggered only.
3. **Null-check `budget_allocation_lkr`** before displaying — it is `null` for 3 out of 4 provinces.
4. **Gradient markers on the map** — scale radius by potential, not a fixed size.
5. **Server-side sorting** — don't sort the fetched array locally; send params to the API.
6. **The Budget Dashboard is Western Province only** — show a clear banner stating this scope.
