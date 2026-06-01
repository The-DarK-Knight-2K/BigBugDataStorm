# Spec 04: UI & Pages (Fully Documented Implementation)

> [!WARNING]
> **PHASE 1 BASELINE**: This document reflects the baseline components, state, layouts, and styles from Phase 1. For Phase 2 modifications (e.g., adding the 5th KPI card, Market Saturation filters, and Cooler Capacity panels), refer strictly to `05_phase2_migration.md`.

This document reflects the foundational components currently implemented in the React codebase (`App/src/components` and `App/src/app`).

## Global Layout (`layout.tsx`)
The application is wrapped in a full-height, dark-themed dashboard shell.
- **Theme**: Dark mode by default (`bg-slate-950`). Uses `Inter` for sans text and `Outfit` for headings.
- **Sidebar (Left)**: 
  - Glassmorphic dark background (`bg-slate-900/60`).
  - **Logo**: A lightning bolt (⚡) icon on a cyan-to-violet gradient background, alongside the title "Outlet Intelligence" and a "Data Storm v7.0" subtitle.
  - **Navigation**: Links for 📊 Dashboard (`/`), 💰 WP Budget Spend (`/budget`), and 🩺 Pipeline Health (`/health`). Links feature a hover effect where the emoji icon scales up (`group-hover:scale-110`).
  - **Footer**: Displays "Model Version: v7.0.4-LOCKED".
- **Top Bar (Sticky)**:
  - Blinking emerald pulse indicator showing "Region: Sri Lanka".
  - Right-aligned "API Connection: Active" status badge.

---

## Page 1: Dashboard (`/`) -> `DashboardClient.tsx`
The primary landing page for exploring the 20,000 outlets.

- **KPI Cards Grid (4 Cards)**: Features glass-panel styling, bottom-right watermark emojis, hover scale effects, and distinct colored left-borders.
  1. **Total Outlets**: Cyan border. Shows total count.
  2. **Max Monthly Potential**: Violet border. Shows total predicted litres for January 2026.
  3. **Western Province Budget**: Emerald border if > 0, otherwise slate. Shows total allocated LKR.
  4. **High Potential Outlets**: Amber border. Shows count of Tier 1 targets.
- **Interactive Filter Toolbar**: 
  - Dropdowns for Province, Distributor, Outlet Type, and Spend Tier.
  - **Clear Filters Button**: Red-styled (`text-rose-400`) button that appears only when a filter is active.
- **Geospatial Map Grid (`Map.tsx`)**:
  - Uses `react-leaflet` to plot circular markers for outlets. 
  - **Loading State**: Displays a spinning cyan ring with "Loading Map Coordinates..." while fetching data.
- **Data Table**:
  - Displays paginated records (50 per page).
  - **Columns**: Outlet ID, Province, Outlet Type, Distributor ID, Potential (L), Recent 3M Avg (L), T1 Potential Tier (Color-coded badges: Emerald for High, Amber for Medium, Rose for Low), and an Actions column.
  - **Action Button**: A cyan-styled "Details &rarr;" button linking to `/outlets/[id]`.
  - **Loading State**: Shows a spinning cyan ring overlay when changing pages or filtering.

---

## Page 2: Outlet Detail (`/outlets/[id]`) -> `OutletDetailClient.tsx`
A deep-dive view into a single outlet's prediction, SHAP values, and XAI business explanation.

- **Header / Hero Panel**:
  - "← Back to Dashboard" navigation link.
  - Prominent Outlet ID display with a dynamic Tier Badge (Emerald/Amber/Rose).
  - Secondary attributes: Province, Type, Distributor, Size.
  - Info blocks (Right-aligned): Cooler count and precise GPS coordinates.
- **Metrics Grid (4 Cards)**:
  - **Max monthly potential**: Shows total L with seasonality multiplier note.
  - **Recent 3M average**: Shows historical average and active months.
  - **Uplift volume gap**: Emphasized in emerald glow, shows the absolute gap and percentage growth space.
  - **Composite gravity score**: Shows the overall score and the individual footfall score.
- **Map View (`SingleMap.tsx`)**: A smaller Leaflet map zoomed in on the specific outlet.
- **SHAP Impact Chart**: 
  - Uses `Recharts` for a vertical BarChart mapping `shap_values`.
  - Positive impacts use a green gradient (`#059669` to `#10b981`).
  - Negative impacts use a red gradient (`#b91c1c` to `#f43f5e`).
  - Features a custom dark-themed tooltip detailing the exact L impact.
- **Right Side Panels**:
  - **Spatial Analysis Scorecard**: Lists individual gravity scores (Transport, School, Worship, Hospitality) with distinct emojis.
  - **WP Budget Spend**: If allocated, displays the Recommended Spend (LKR), ROI Score (emerald), and the specific Spend Activity Type (e.g., Cooler Grant Program). Shows an empty state message if out of region.
- **Business XAI Explanation (Gemini Integration)**:
  - **Initial State**: A primary action button ("⚡ Generate Explanatory Briefing") using a cyan-to-violet gradient.
  - **Loading State**: A custom animated robot 🤖 spinner with rotating status text (e.g., "Initializing Gemini...", "Evaluating SHAP...").
  - **Success State (JSON parsing)**:
    - **Diagnostic Alert Box**: Styled dynamically based on type (warning=amber, critical=rose, success=emerald, info=cyan).
    - **Driver Cards**: A 3-column grid displaying the "Why" with large emojis and descriptive text.
    - **Field Rep Negotiation Plan**: A checklist UI using custom cyan-styled checkboxes.
  - **Regenerate Button**: A secondary outline button ("🔄 Regenerate Insight") to bypass the SQLite cache.

---

## Page 3: Budget Dashboard (`/budget`) -> `BudgetClient.tsx`
A Western-Province specific view analyzing trade spend ROI across territories.

- **KPI Stats Cards (3 Cards)**:
  - Total trade spends allocated (LKR).
  - Projected volume uplift (L).
  - Net portfolio ROI score (Average).
- **Visual Analytics Charts (Recharts)**:
  - **Spends Share by Distributor**: A Donut PieChart (`innerRadius={65}`). Features a custom center text overlay showing "Total WP XX.X M LKR" and a bottom legend.
  - **Expected Volume Lift by Territory**: A BarChart using an emerald-to-transparent vertical gradient (`#10b981`), displaying uplift volume (L) against spend.
- **Allocation Data Table**:
  - **Filter**: A local Territory dropdown to filter by specific distributors.
  - **Columns**: Outlet ID, Territory, Type, Uplift Volume Gap (emerald text), Trade Spends Recommendation (LKR), ROI Priority Tier (Badge), Spend Activity Type, and a "Details" action button.
  - **Empty State**: "⚠️ No budget spending matches this distributor filter."
