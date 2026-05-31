# Spec 04: UI & Pages

## Page 1: Dashboard (`/`)
- **Top Stats:** Total Outlets, Total Predicted Volume, Total Budget (Western Province), High Potential Outlets.
- **Filters:** Province, Distributor, Type, Tier.
- **Map View (React-Leaflet):** 
  - Centered on Sri Lanka `[7.8731, 80.7718]`.
  - Markers color-coded by potential tier: Green (High), Yellow (Medium), Red (Low).
  - Popups should show outlet name, predicted liters, and a link to `/outlets/[id]`.
- **Table View:** Clean, paginated data table showing:
  - `outlet_id`, `outlet_type`, `predicted_potential_litres`, `recent_3m_avg`, `composite_gravity_score`.

## Page 2: Outlet Detail (`/outlets/[id]`)
- **Header:** Basic attributes (ID, Type, Province, Distributor) and Tier Badge.
- **Metrics Grid (4 Cards):** 
  1. Predicted Maximum (L)
  2. Recent 3M Avg (L)
  3. Uplift Gap (L)
  4. Composite Gravity Score
- **Map View:** Display the outlet's location on a Leaflet map.
- **SHAP Impact Chart:** Recharts horizontal bar chart mapping `shap_values` array.
  - Green bars for Positive direction.
  - Red bars for Negative direction.
- **Business Insight:** Interactive XAI explanation block powered by the Gemini API. 
  - Displays a spinner and button on first generation.
  - Displays cached text gracefully on subsequent visits.
- **Budget Section:** Display allocations if the outlet exists in `budget_allocations` (trade spend, tier, ROI score, recommended activity).
- **Spatial Analysis:** Display Footfall score and individual gravity scores.

## Page 3: Budget Dashboard (`/budget`)
- **Stats:** Total Allocated Budget, Expected Volume Lift.
- **Charts:** 
  - Donut chart of budget per distributor (`DIST_W_01`, `DIST_W_02`, etc.).
  - Bar chart of expected volume lift by distributor.
- **Data Table:** Filterable allocations table showing Outlet ID, Type, Allocated LKR, Lift, and Activity.

## Page 4: Pipeline Health (`/health`)
- Overview of data pipeline validation results.
- Render the data from `pipeline_health` table.
- Display cards/lists for each dataset (e.g. `transactions_history_final.csv`), showing `records_passed`, `records_quarantined`, and the breakdown of checks.
