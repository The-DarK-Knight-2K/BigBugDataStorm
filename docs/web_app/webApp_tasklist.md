# WebApp Task List — Outlet Intelligence Dashboard

Track progress here. Check off each item as it is completed.
Work through phases in order — later phases depend on earlier ones.

---

## Pre-work (before writing any code)

- [ ] Read `webapp/API_SPEC.md` end to end
- [ ] Read `webapp/WEBAPP_COMPONENTS.md` end to end
- [ ] Skim `gold/GRAVITY_MODEL.md` (understand gravity scores for labels/tooltips)
- [ ] Skim `gold/SPEC_build_sales_features.md` (understand sales_history field meanings)
- [ ] Copy `sample_outlets.json` into `app/fixtures/`
- [ ] Set up `.env` from `.env.example` with `VITE_API_MODE=mock`

---

## Phase 1 — Scaffold & Static Layout (mock data, no API calls)

### Project setup
- [ ] Initialise Vite + React project under `app/`
- [ ] Install dependencies: Tailwind CSS, React Router v6, Recharts, React-Leaflet, Axios, Zustand, TanStack Table v8
- [ ] Configure Tailwind
- [ ] Set up React Router v6 with routes for `/outlets`, `/map`, `/outlets/:id`, `/budget`, `/pipeline`
- [ ] Confirm `npm run dev` starts cleanly on `http://localhost:5173`

### Layout shell
- [ ] Build `Sidebar.jsx` with navigation links to all 5 routes
- [ ] Build `TopBar.jsx`
- [ ] Active route highlighted with left border accent in sidebar
- [ ] Sidebar collapses to hamburger on < 1024px

### Shared components
- [ ] `Badge.jsx` — province (blue/teal/amber/coral), tier (blue/teal/gray), outlet_type
- [ ] `StatCard.jsx` — label, value, unit, delta, deltaDirection
- [ ] `LoadingSkeleton.jsx` — pulsing rectangle, configurable width/height
- [ ] `ErrorBanner.jsx` — generic error message with optional retry button

### View 1 — Outlet Explorer (static)
- [ ] Filter bar: Province, Distributor, Type dropdowns + Search input (hardcoded options, no API)
- [ ] Table with columns: Outlet ID, Type/Size, Potential (L), Gap (L), Footfall Score
- [ ] Populate table rows from `sample_outlets.json` (hardcoded, no API call yet)
- [ ] Clicking a row navigates to `/outlets/:id`
- [ ] Pagination controls rendered (static, no logic yet)
- [ ] Potential and Gap values formatted with thousand separators + "L" suffix

### View 2 — Map View (static)
- [ ] Leaflet map centred on Sri Lanka (`lat: 7.8731, lng: 80.7718`, zoom 8)
- [ ] `<CircleMarker>` for each outlet from `sample_outlets.json`
- [ ] Marker colour encodes province (matches badge palette)
- [ ] Marker radius encodes `predicted_potential_litres` (4px–14px scaled)
- [ ] Popup on click: Outlet ID, Type, Size, Predicted Potential, "View details →" link

### View 3 — Outlet Detail (static shell)
- [ ] Header: Outlet ID, type, size, province, distributor
- [ ] Prediction section: potential, current avg, gap, seasonality, trading days
- [ ] `ShapWaterfall.jsx` — horizontal bar chart with hardcoded SHAP data from `sample_outlets.json`
  - [ ] Positive SHAP → blue bars right
  - [ ] Negative SHAP → amber bars left
  - [ ] Top 5 contributors only
  - [ ] Tooltip with feature label and value
- [ ] AI Explanation panel — "Generate explanation ▶" button (no API call yet, show placeholder text on click)
- [ ] POI Context section — gravity scores with emoji icons
- [ ] Budget Allocation section — allocation_lkr, tier, ROI score, spend type (null-safe)
- [ ] "Outlet not found" fallback page with back button

---

## Phase 2 — Wire up API (mock server running)

### API layer
- [ ] `api/client.js` — Axios instance with `VITE_API_BASE_URL` as baseURL
- [ ] Mock adapter: when `VITE_API_MODE=mock`, intercept calls and return data from `sample_outlets.json`
- [ ] `api/outlets.js` — `getOutlets(params)` and `getOutletById(id)`
- [ ] `api/explain.js` — `getExplanation(id)`
- [ ] `api/budget.js` — `getBudgetSummary(params)`
- [ ] `api/pipeline.js` — `getPipelineHealth()`

### Zustand store
- [ ] `store/useFilters.js` — province, distributor, outlet_type, outlet_size filter state
- [ ] Filter state shared between Explorer and Map views

### View 1 — Outlet Explorer (live)
- [ ] Replace hardcoded rows with `GET /outlets` API call
- [ ] Filters update query params and re-fetch
- [ ] Server-side sorting via `sort_by` + `sort_dir` params (clicking column headers)
- [ ] Pagination: `page` param updates on Prev/Next; display "Showing X–Y of Z"
- [ ] TanStack Table virtualisation active (do not render all rows to DOM)
- [ ] Loading skeleton while fetching

### View 2 — Map View (live)
- [ ] Fetch outlets in batches of 1000 via paginated `GET /outlets` calls
- [ ] Add markers progressively as each batch loads
- [ ] Progress bar while loading all batches
- [ ] Active filters from Zustand store applied to map markers

### View 3 — Outlet Detail (live)
- [ ] Replace hardcoded data with `GET /outlets/:id`
- [ ] Handle 404 — show "Outlet not found" page
- [ ] Handle network error — show `ErrorBanner` with retry

### View 4 — Budget Dashboard
- [ ] Banner: "Western Province only — January 2026"
- [ ] `BudgetDonut.jsx` — Recharts `PieChart` with 60% inner radius, tier legend below
  - [ ] High: `#2563eb`, Medium: `#0d9488`, Low: `#9ca3af`
- [ ] Distributor split horizontal bar chart
- [ ] Outlet type split horizontal bar chart
- [ ] Projected volume uplift stat card
- [ ] Top 20 outlets table (Western, sorted by `budget_allocation_lkr` desc)
- [ ] Distributor + tier filter dropdowns update `GET /budget/summary` params and re-render

### View 5 — Pipeline Health
- [ ] Dataset summary table: name, checked, passed, quarantined, rate
- [ ] Pass rate icon: ≥ 99% → ✅, 95–99% → ⚠️, < 95% → ❌
- [ ] Per-check accordion (collapsed by default, expand on click)
- [ ] "Corrected (not quarantined)" column shown when `corrected` field is non-zero

---

## Phase 3 — Real backend + XAI (backend team hands off)

- [ ] Receive real backend URL from backend team
- [ ] Set `VITE_API_MODE=real` and `VITE_API_BASE_URL` in `.env`
- [ ] Smoke-test all 5 views against real backend
- [ ] Fix any shape mismatches between mock and real responses

### XAI panel (Outlet Detail)
- [ ] "Generate explanation ▶" button triggers `GET /explain/:id`
- [ ] Loading skeleton shown with "Generating business insight…" while awaiting (5–10s)
- [ ] On response: fade-in animation for text content
- [ ] `headline` rendered in larger font weight above driver lists
- [ ] `drivers_up` rendered with ✅ icon (green)
- [ ] `drivers_down` rendered with ⚠️ icon (amber)
- [ ] `local_context` paragraph below driver lists
- [ ] `recommendation` paragraph at bottom
- [ ] Collapsed "Model transparency" section: `prompt_tokens_used` + `completion_tokens_used`
- [ ] 503 error → "Explanation service is temporarily unavailable. Try again." + retry button

### SHAP chart (live data)
- [ ] `ShapWaterfall.jsx` now reads real SHAP data from `GET /outlets/:id`
- [ ] Verify sort order: top 3 positive + top 2 negative displayed correctly

---

## Phase 4 — Polish & submission prep

- [ ] Loading skeletons on every async section across all views
- [ ] Error states (404, 503, network) on all API calls
- [ ] Responsive layout: sidebar → hamburger on < 1024px
- [ ] Numbers formatted consistently: thousand separators, 2 decimal places, "L" / "LKR" suffixes
- [ ] Page titles set correctly for each route (browser tab)
- [ ] Write `app/README.md` with setup instructions (`npm install && npm run dev`)
- [ ] End-to-end walkthrough: start mock server → open all 5 views → verify no console errors
- [ ] End-to-end walkthrough: switch to real backend → repeat above

---

## Definition of done

The app is submission-ready when:
- `npm install && npm run dev` works with zero manual steps
- All 5 views render correctly against the mock server
- All 5 views render correctly against the real backend
- No console errors in any view
- XAI panel works end-to-end (button → loading → result)
- Budget Dashboard correctly scopes to Western Province only
- Map renders outlet markers for all loaded outlets
