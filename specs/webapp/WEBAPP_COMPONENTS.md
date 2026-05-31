# Web App Components Spec — Outlet Intelligence Dashboard

## Tech stack recommendation

| Layer | Choice | Rationale |
|-------|--------|-----------|
| Framework | React + Vite | Fast dev server, easy local setup for judges |
| Styling | Tailwind CSS | Rapid UI without custom CSS overhead |
| Charts | Recharts | Simple API, React-native, no extra config |
| Map | React-Leaflet + OpenStreetMap | Free tiles, no API key needed |
| API calls | Axios | Clean interceptors for loading/error states |
| State | Zustand | Lightweight global state without Redux boilerplate |
| Table | TanStack Table v8 | Virtualized rows — required for 20k outlet list |

Member C is free to substitute any of these — this is a recommendation, not a
requirement. The only hard constraint is that the app runs with `npm install && npm run dev`
and needs no paid API keys to function.

---

## Running the app

```bash
# Clone and install
cd app/
npm install

# Start against the mock server (Phase 1–2)
cp .env.example .env       # set API_MODE=mock
npm run dev                # starts on http://localhost:5173

# Start against the real backend (Phase 3+)
# In one terminal:
uvicorn app.api.main:app --reload --port 8000

# In another terminal:
# set API_MODE=real in .env
npm run dev
```

---

## App structure

```
app/
├── src/
│   ├── main.jsx
│   ├── App.jsx                    ← router root (React Router v6)
│   ├── api/
│   │   ├── client.js              ← Axios instance with base URL from env
│   │   ├── outlets.js             ← GET /outlets, GET /outlets/:id
│   │   ├── explain.js             ← GET /explain/:id
│   │   ├── budget.js              ← GET /budget/summary
│   │   └── pipeline.js            ← GET /pipeline/health
│   ├── store/
│   │   └── useFilters.js          ← Zustand store for filter state
│   ├── components/
│   │   ├── layout/
│   │   │   ├── Sidebar.jsx
│   │   │   └── TopBar.jsx
│   │   ├── shared/
│   │   │   ├── Badge.jsx          ← tier/province/type badges
│   │   │   ├── StatCard.jsx       ← single KPI card
│   │   │   ├── LoadingSkeleton.jsx
│   │   │   └── ErrorBanner.jsx
│   │   └── charts/
│   │       ├── ShapWaterfall.jsx  ← horizontal bar chart for SHAP
│   │       └── BudgetDonut.jsx    ← donut for tier split
│   └── views/
│       ├── OutletExplorer.jsx     ← view 1
│       ├── MapView.jsx            ← view 2
│       ├── OutletDetail.jsx       ← view 3
│       ├── BudgetDashboard.jsx    ← view 4
│       └── PipelineHealth.jsx     ← view 5
├── fixtures/
│   ├── mock_server.py
│   └── sample_outlets.json
├── .env.example
└── package.json
```

---

## View 1 — Outlet Explorer

**Route:** `/outlets`
**API:** `GET /outlets` (paginated, filterable)

### Layout

```
┌─────────────────────────────────────────────────────────┐
│  [Province ▼]  [Distributor ▼]  [Type ▼]  [Search...]  │  ← filter bar
├────────────┬──────────────┬──────────┬────────┬─────────┤
│ Outlet ID  │ Type / Size  │ Potential│ Gap    │ Footfall│  ← sortable headers
├────────────┼──────────────┼──────────┼────────┼─────────┤
│ OUT_W_0042 │ Grocery / Md │ 1,240 L  │ 420 L  │  67.4   │  ← clickable row
│ ...        │ ...          │ ...      │ ...    │ ...     │
└────────────┴──────────────┴──────────┴────────┴─────────┘
  Showing 1–50 of 20,000    [< Prev]  Page 1 of 400  [Next >]
```

### Behaviour

- Filters are applied as query parameters on `GET /outlets`
- All filter state lives in the Zustand `useFilters` store so the map view
  reflects the same active filters
- Clicking any row navigates to `/outlets/{outlet_id}`
- Province and Distributor dropdowns are statically populated from the known
  values in `config.yaml` — do not fetch them from the API
- The table is virtualized via TanStack Table — do not render all 20k rows to DOM
- Column sorting is server-side (passed as `sort_by` + `sort_dir` query params)
- Potential and Gap values display with thousand separators and a "L" suffix

### Province badge colours

| Province | Colour |
|----------|--------|
| Western | Blue |
| Central | Teal |
| North-Western | Amber |
| Southern | Coral/Orange |

---

## View 2 — Map View

**Route:** `/map`
**API:** `GET /outlets?page_size=200` (load first 200, or all if feasible)

### Layout

Full-width Leaflet map centred on Sri Lanka (lat: 7.8731, lng: 80.7718, zoom: 8).

Each outlet is a circle marker. Marker colour encodes province (use the same
palette as View 1). Marker radius encodes `predicted_potential_litres` (scale
between 4px and 14px using min-max across loaded outlets).

Clicking a marker opens a popup with:
- Outlet ID
- Type and size
- Predicted potential (L)
- "View details →" link to `/outlets/{outlet_id}`

### Filter integration

The active province / distributor filters from the Zustand store are reflected
in which outlets appear on the map. When a filter is applied in View 1 and the
user navigates to View 2, the same filter is active.

### Implementation notes

- Use `react-leaflet` `<CircleMarker>` — not custom markers, not PNG pins
- Tile layer: `https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png`
  Attribution: `© OpenStreetMap contributors`
- For 20k outlets: fetch in batches of 1000 using `page` param, add markers
  progressively as each batch loads. Show a progress bar while loading.
- Do not cluster markers — the spread across Sri Lanka is large enough that
  overlap is minimal at zoom level 8

---

## View 3 — Outlet Detail

**Route:** `/outlets/:outlet_id`
**API:** `GET /outlets/:outlet_id` + `GET /explain/:outlet_id` (lazy)

### Layout

```
┌── Back to Explorer ──────────────────────────────────────┐
│  OUT_W_00042  •  Grocery  •  Medium  •  Western         │
│  DIST_W_01                                              │
├──────────────────────────┬──────────────────────────────┤
│  PREDICTION              │  SHAP WATERFALL CHART        │
│  1,240 L potential       │  (horizontal bar chart)      │
│  820 L current avg       │  transport_gravity  +182 ░░  │
│  420 L gap (51% uplift)  │  footfall_score     +134 ░░  │
│                          │  hist_p90           +98  ░░  │
│  Jan 2026: Favorable     │  hist_cv            -46  ░   │
│  20 trading days         │  zero_months        -38  ░   │
├──────────────────────────┴──────────────────────────────┤
│  AI EXPLANATION                    [Generate ▶]         │
│  ┌ loading skeleton ──────────────────────────────────┐ │
│  │ Headline...                                        │ │
│  │ ✅ Transit hub... ✅ Footfall... ✅ Peak volume... │ │
│  │ ⚠️ Order volatility...  ⚠️ Stockout gap...       │ │
│  │ Local context...                                   │ │
│  │ Recommendation...                                  │ │
│  └────────────────────────────────────────────────────┘ │
├─────────────────────────────────────────────────────────┤
│  POI CONTEXT                │  BUDGET ALLOCATION        │
│  🚌 Transport  8.75 gravity │  LKR 15,000 — High tier   │
│  🏫 Schools    3.84 gravity │  Cooler Subsidy / Display Rack │
│  🏥 Healthcare 0.41 gravity │  ROI score: 0.89 (Rank #142) │
│  🏪 Markets    2.11 gravity │                           │
│                             │  [View budget dashboard →]│
└─────────────────────────────┴───────────────────────────┘
```

### SHAP waterfall chart (`ShapWaterfall.jsx`)

Use a horizontal bar chart (Recharts `BarChart` with `layout="vertical"`).
- Positive SHAP values: blue bars extending right
- Negative SHAP values: amber bars extending left (use negative x values)
- Show the top 5 SHAP contributors only (top 3 positive + top 2 negative from API)
- X-axis label: "Contribution to predicted potential (litres)"
- Each bar shows the feature's human label and value in a tooltip

### AI Explanation panel behaviour

- **Do not auto-call** `GET /explain/:id` on page load — the LLM call takes 5–10s
  and not every user wants it
- Show a "Generate explanation ▶" button
- On click: show a loading skeleton with the text "Generating business insight…"
- On response: animate the text in (simple fade-in)
- Positive drivers render with a ✅ icon, negative with an ⚠️ icon
- Show the `headline` in a larger font weight above the driver lists
- Collapse a "Model transparency" section that shows `prompt_tokens_used` and
  `completion_tokens_used` — this satisfies the GenAI transparency requirement

### Error states

| Condition | Display |
|-----------|---------|
| Outlet ID not found | "Outlet not found" full-page message with back button |
| LLM timeout (503) | "Explanation service is temporarily unavailable. Try again." with retry button |
| Network error | Generic error banner with retry button |

---

## View 4 — Budget Dashboard

**Route:** `/budget`
**API:** `GET /budget/summary` + `GET /outlets?province=Western&sort_by=Trade_Spend_Allocation_LKR`

This view is Western Province only. Show a banner at the top confirming this scope.

### Layout

```
┌─ WESTERN PROVINCE TRADE MARKETING BUDGET ───────────────┐
│  Total: LKR 5,000,000  •  6,842 outlets  •  Jan 2026    │
├──────────┬──────────────────────┬────────────────────────┤
│ TIER     │ DISTRIBUTOR SPLIT    │ OUTLET TYPE SPLIT      │
│ (donut)  │ (horizontal bars)    │ (horizontal bars)      │
│          │                      │                        │
│ High 42% │ DIST_W_01  LKR 1.68M│ Grocery   LKR 2.10M   │
│ Med  38% │ DIST_W_02  LKR 1.62M│ Eatery    LKR 0.90M   │
│ Low  20% │ DIST_W_03  LKR 1.70M│ ...                    │
├──────────┴──────────────────────┴────────────────────────┤
│  Projected volume uplift: 128,400 L                      │
├─────────────────────────────────────────────────────────┤
│  TOP 20 OUTLETS BY ALLOCATION                           │
│  (same table as View 1, filtered to Western, sorted by  │
│   Trade_Spend_Allocation_LKR desc, showing top 20 only) │
└─────────────────────────────────────────────────────────┘
```

### Donut chart (`BudgetDonut.jsx`)

Use Recharts `PieChart` with `innerRadius` set to 60% of outer radius.
Display the tier percentages as a legend below the donut, not as labels on slices
(slice labels overlap at small sizes).

Colour coding for tiers:
- High: Blue (`#2563eb`)
- Medium: Teal (`#0d9488`)
- Low: Gray (`#9ca3af`)

### Filter interaction

Province, distributor, and tier filter dropdowns at the top of this view filter
both the summary cards and the top outlets table. Filtering updates the
`GET /budget/summary` query params and re-renders the charts.

---

## View 5 — Pipeline Health

**Route:** `/pipeline`
**API:** `GET /pipeline/health`

### Layout

```
┌─ DATA QUALITY REPORT ──────────────────────────────────┐
│  Overall pass rate: 99.3%  •  Generated: 2026-01-15    │
├─────────────────────────────────────────────────────────┤
│  DATASET          CHECKED   PASSED   QUARANTINED  RATE  │
│  transactions     2,376,389 2,359,769 16,620      0.70% │
│  coordinates         20,000    19,960     40       0.20% │
│  outlet_master       20,000    20,000      0       0.00% │
├─────────────────────────────────────────────────────────┤
│  CHECKS — transactions_history_final.csv                │
│  [expand/collapse per dataset]                          │
│                                                         │
│  ✅ duplicate_check     2,375,800 passed  589 quarantined│
│  ✅ null_check          2,376,200 passed  189 quarantined│
│  ⚠️ range_check_volume  2,374,612 passed  1,777 quarant. │
│  ...                                                    │
└─────────────────────────────────────────────────────────┘
```

### Behaviour

- The dataset rows are always visible; the per-check breakdown is collapsed by default
  and expands on click (accordion pattern)
- A pass rate ≥ 99% shows a ✅ icon; 95–99% shows ⚠️; below 95% shows ❌
- The `corrected` field (for swap corrections and imputations) shows as a separate
  "corrected (not quarantined)" column if non-zero
- This view is read-only — no filters or interactions beyond accordion expand/collapse

---

## Shared components

### `Badge.jsx`

```jsx
// Usage: <Badge variant="province" value="Western" />
// Usage: <Badge variant="tier" value="high" />
// Usage: <Badge variant="outlet_type" value="Grocery" />
```

Variants and their colours are defined in a static config within the component.

### `StatCard.jsx`

```jsx
// Usage:
<StatCard
  label="Predicted potential"
  value="1,240"
  unit="L"
  delta="+51%"
  deltaDirection="up"
/>
```

### `LoadingSkeleton.jsx`

A pulsing gray rectangle of configurable width and height. Used everywhere
data is loading. Do not show a spinner — skeletons give a better sense of
the incoming layout.

---

## Navigation sidebar

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

The sidebar is always visible on desktop (≥ 1024px). On mobile it collapses to
a hamburger menu. Active route is highlighted with a left border accent.

---

## Environment variables

```bash
# .env.example
VITE_API_BASE_URL=http://localhost:8000
VITE_API_MODE=mock          # mock | real
```

When `VITE_API_MODE=mock`, the API client imports and calls `mock_server.py`'s
static data directly (via a mock adapter) instead of hitting the network.
This means Member C can develop with no running backend at all during Phase 1.

---

## Phase-by-phase frontend build order

### Phase 1 (Member C alone, mock data)
1. Scaffold Vite + React project with routing
2. Implement sidebar layout and top bar
3. Build `OutletExplorer` with static mock data (no API calls)
4. Build `MapView` with hardcoded markers from `sample_outlets.json`
5. Build `OutletDetail` shell with all sections laid out, all values hardcoded

### Phase 2 (wire up real API shapes, mock server running)
6. Implement `api/client.js` and all API modules
7. Replace hardcoded data with `GET /outlets` calls in `OutletExplorer`
8. Replace hardcoded data with `GET /outlets/:id` in `OutletDetail`
9. Build `BudgetDashboard` against `GET /budget/summary` mock
10. Build `PipelineHealth` against `GET /pipeline/health` mock

### Phase 3 (real backend running, XAI endpoint live)
11. Wire `GET /explain/:id` into the `OutletDetail` AI Explanation panel
12. Implement `ShapWaterfall` chart with real SHAP data
13. Switch `VITE_API_MODE=real`, verify all views against real backend
14. Fix any shape mismatches between mock and real response

### Phase 4 (polish)
15. Loading skeletons on all async sections
16. Error states for all API calls
17. Responsive layout pass (sidebar → hamburger at < 1024px)
18. README setup instructions
19. End-to-end walkthrough with final predictions CSV loaded
