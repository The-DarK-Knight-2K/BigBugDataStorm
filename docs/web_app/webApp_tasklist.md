# Outlet Intelligence Web App — Complete Plan

### Data Storm v7.0| Deliverable 4

#IMPORTANT - The schemas and tables in this are just guesses. Has to be updated with correct schemas,tables and values.

---

## ✅ Current Status (Completed Work)

- **Next.js Setup**: Next.js 15 is successfully initialized in the `App` root folder.
- **Styling**: Tailwind CSS and `shadcn/ui` are fully configured.
- **Folder Structure**: Integrated the Next.js `src/` directory seamlessly alongside the existing `data` and `scripts` folders.
- **Dependencies Installed**: `better-sqlite3`, `react-leaflet`, `leaflet`, `recharts`, `lucide-react`.
- **Skeleton Pages Built**: Empty placeholder files have been created for all required routes and API endpoints.

---

## Table of Contents

1. [What This App Is](#1-what-this-app-is)
2. [Tech Stack Decision](#2-tech-stack-decision)
3. [High Level Architecture](#3-high-level-architecture)
4. [Project Structure](#4-project-structure)
5. [Data Flow — End to End](#5-data-flow--end-to-end)
6. [Database Schema (SQLite)](#6-database-schema-sqlite)
7. [The Outlet JSON Structure](#7-the-outlet-json-structure)
8. [LLM Integration — Complete Plan](#8-llm-integration--complete-plan)
9. [Prompts to Send to Gemini](#9-prompts-to-send-to-gemini)
10. [Caching Strategy](#10-caching-strategy)
11. [Web App Pages](#11-web-app-pages)
12. [Git Strategy](#12-git-strategy)
13. [Judge Setup Instructions (README)](#13-judge-setup-instructions-readme)
14. [Build Checklist](#14-build-checklist)

---

## 1. What This App Is

The Outlet Intelligence Web App is **Deliverable 4** of the Data Storm v7.0 Final Round. It is a
functional business intelligence tool that allows non-technical sales managers and judges to:

- Browse all 20,000 outlet predictions across Sri Lanka
- Filter by province and distributor
- Drill into any single outlet to see its predicted potential
- Read an AI-generated plain-English explanation of WHY that outlet got its score

This deliverable is worth a combined **40% of total marks**:

- Business Viability & Web App Quality: **25%**
- GenAI / XAI Integration Quality: **15%**

The problem statement says the app must be **runnable locally** with setup instructions in README.md.
There is no requirement to host it online.

---

## 2. Tech Stack Decision

### Why Not Streamlit

Streamlit looks like a student demo project. Judges include business leaders and data engineers
who will visually judge the app as a product. Next.js looks like a real enterprise tool.

### Why Not FastAPI

A separate Python backend is not needed. Predictions are pre-computed offline and stored locally.
Next.js API routes handle all server-side logic — they query SQLite, call Gemini, and return JSON.
No separate server process needed.

### Why Not Supabase + Drizzle

The app runs locally per the competition requirement. Supabase is a cloud service that adds an
external dependency. Drizzle ORM adds complexity that is not needed at this scale. SQLite gives
you a proper queryable database with zero setup — it is a single file that ships with your repo.

### Why Not Raw CSVs

Loading and filtering 20,000 rows from a CSV on every request is slow and hacky. SQLite handles
20,000 rows with proper SQL queries instantly. Much more professional and reliable.

### Final Stack

| Layer              | Technology              | Reason                                      |
| ------------------ | ----------------------- | ------------------------------------------- |
| Frontend + Backend | Next.js (App Router)    | Full-stack, professional UI, API routes     |
| Database           | SQLite (local .db file) | Single file, zero setup, fast SQL queries   |
| SQLite Client      | better-sqlite3          | Synchronous, fastest SQLite option for Node |
| Maps               | React-Leaflet           | Free, no API key, handles 20k markers       |
| Charts             | Recharts                | Clean, works natively with React            |
| LLM / XAI          | Gemini 2.0 Flash (Free) | Sufficient for demo, zero cost              |
| Styling            | Tailwind + shadcn/ui    | Premium, industry-standard component library|
| Hosting            | None — runs locally     | Meets competition requirement exactly       |

---

## 3. High Level Architecture

```
Python Pipeline (runs locally, offline)
         │
         │  generates predictions + feature metadata
         ▼
CSV files:
  outlets.csv
  predictions.csv
  budget_allocations.csv
         │
         │  one-time setup script
         ▼
setup_db.py
  reads all CSVs
  creates outlets.db (SQLite)
  single file with all data + empty xai_explanation column
         │
         ▼
outlets.db lives in /data folder of Next.js project
         │
         │  better-sqlite3 queries
         ▼
Next.js (App Router)
  Server Components → read from SQLite directly
  API Routes → handle Gemini XAI calls
  UI → filtered tables, maps, charts, outlet detail
         │
         │  user clicks outlet → needs XAI explanation
         ▼
Next.js API Route (/api/explain/[id])
  reads outlet row from SQLite
  checks if xai_explanation column is NULL
  if NOT NULL → return cached explanation instantly
  if NULL → build prompt from outlet data → call Gemini
         │
         ▼
Gemini 2.0 Flash API
  receives system prompt (your full methodology)
  receives outlet JSON (the actual data)
  returns plain-English business explanation
         │
         ▼
Save explanation back to outlets.db
xai_explanation column updated for that outlet
         │
         ▼
Display on outlet detail page
```

---

## 4. Project Structure

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
    /lib                        
      db.ts                     ← Database connection
  package.json                  
  tailwind.config.ts            
```

---

## 5. Data Flow — End to End

### Step 1 — Python Pipeline Outputs Three CSVs

Your Python ML pipeline generates these files after modeling is complete:

**outlets.csv** (20,000 rows — outlet master data)

```
outlet_id, name, outlet_type, province, distributor_id,
lat, lon, location_area
```

**predictions.csv** (20,000 rows — model outputs + feature metadata)

```
outlet_id, max_monthly_liters, historical_avg, potential_gap,
potential_gap_percent, confidence_level, seasonality_multiplier,
poi_decay_score, top_poi_1_type, top_poi_1_distance_m,
top_poi_2_type, top_poi_2_distance_m, top_poi_3_type, top_poi_3_distance_m,
competitor_count_300m, competition_level, market_saturation,
was_historically_capped, capping_reason,
cooler_capacity, optimal_cooler_capacity, credit_status, supply_consistency,
f1_name, f1_impact_pct, f1_direction, f1_plain_reason,
f2_name, f2_impact_pct, f2_direction, f2_plain_reason,
f3_name, f3_impact_pct, f3_direction, f3_plain_reason,
f4_name, f4_impact_pct, f4_direction, f4_plain_reason,
f5_name, f5_impact_pct, f5_direction, f5_plain_reason
```

**budget_allocations.csv** (Western Province outlets only)

```
outlet_id, trade_spend_lkr, allocation_tier,
expected_volume_lift_liters, recommended_activity
```

### Step 2 — Run setup_db.py Once

This script:

- Reads all three CSVs using pandas
- Creates outlets.db SQLite file in /data folder
- Creates the three tables and inserts all rows
- Adds an empty xai_explanation TEXT column (NULL by default)

Uses only Python built-ins (pandas + sqlite3). No pip installs beyond pandas.

### Step 3 — Next.js Reads SQLite via better-sqlite3

All Next.js pages and API routes query outlets.db using better-sqlite3.
Synchronous API — no async/await needed for DB calls. Simple and fast.

### Step 4 — Gemini Called On Demand Per Outlet

When a user clicks an outlet, the Next.js API route:

1. Reads that outlet's full data row from SQLite
2. Builds a structured JSON object from the row
3. Checks xai_explanation column
4. If NULL → calls Gemini with system prompt + outlet JSON
5. Saves returned explanation back to SQLite
6. Returns explanation to the UI

---

## 6. Database Schema (SQLite)

Three tables inside outlets.db, generated by setup_db.py from your CSVs.

### outlets table

```sql
CREATE TABLE outlets (
  outlet_id       TEXT PRIMARY KEY,
  name            TEXT,
  outlet_type     TEXT,
  province        TEXT,
  distributor_id  TEXT,
  lat             REAL,
  lon             REAL,
  location_area   TEXT
)
```

### predictions table

```sql
CREATE TABLE predictions (
  outlet_id                TEXT PRIMARY KEY,
  max_monthly_liters       REAL,
  historical_avg           REAL,
  potential_gap            REAL,
  potential_gap_percent    REAL,
  confidence_level         TEXT,
  seasonality_multiplier   REAL,

  poi_decay_score          REAL,
  top_poi_1_type           TEXT,
  top_poi_1_distance_m     REAL,
  top_poi_2_type           TEXT,
  top_poi_2_distance_m     REAL,
  top_poi_3_type           TEXT,
  top_poi_3_distance_m     REAL,
  competitor_count_300m    INTEGER,
  competition_level        TEXT,
  market_saturation        TEXT,

  was_historically_capped  INTEGER,   -- 0 or 1 (SQLite has no BOOLEAN)
  capping_reason           TEXT,

  cooler_capacity          INTEGER,
  optimal_cooler_capacity  INTEGER,
  credit_status            TEXT,
  supply_consistency       TEXT,

  f1_name                  TEXT,
  f1_impact_pct            REAL,
  f1_direction             TEXT,
  f1_plain_reason          TEXT,
  f2_name                  TEXT,
  f2_impact_pct            REAL,
  f2_direction             TEXT,
  f2_plain_reason          TEXT,
  f3_name                  TEXT,
  f3_impact_pct            REAL,
  f3_direction             TEXT,
  f3_plain_reason          TEXT,
  f4_name                  TEXT,
  f4_impact_pct            REAL,
  f4_direction             TEXT,
  f4_plain_reason          TEXT,
  f5_name                  TEXT,
  f5_impact_pct            REAL,
  f5_direction             TEXT,
  f5_plain_reason          TEXT,

  xai_explanation          TEXT       -- NULL by default, filled on first click
)
```

### budget_allocations table

```sql
CREATE TABLE budget_allocations (
  outlet_id                   TEXT PRIMARY KEY,
  trade_spend_lkr             REAL,
  allocation_tier             TEXT,
  expected_volume_lift_liters REAL,
  recommended_activity        TEXT
)
```

---

## 7. The Outlet JSON Structure

When a user clicks an outlet, the Next.js API route reads from SQLite and assembles this JSON.
This is what gets sent to Gemini. The richer this JSON, the better the explanation.

```json
{
  "outlet_id": "W_001",
  "name": "Perera Grocery",
  "type": "Grocery",
  "province": "Western",
  "distributor": "DIST_W_01",
  "location_area": "Colombo 03",

  "prediction": {
    "max_monthly_liters": 4250,
    "historical_avg_liters": 2100,
    "potential_gap_liters": 2150,
    "potential_gap_percent": 102,
    "confidence": "High",
    "january_seasonality_multiplier": 1.18
  },

  "censoring_analysis": {
    "was_historically_capped": true,
    "capping_reason": "Stockout detected in 8 out of 12 months",
    "plain_explanation": "True demand was hidden because the outlet ran out of stock repeatedly — historical sales understated real potential"
  },

  "spatial_analysis": {
    "poi_decay_score": 8.4,
    "poi_score_out_of": 10,
    "top_pois": [
      {
        "type": "Bus Terminal",
        "distance_meters": 45,
        "impact_level": "Very High"
      },
      {
        "type": "Public Market",
        "distance_meters": 120,
        "impact_level": "High"
      },
      {
        "type": "School",
        "distance_meters": 200,
        "impact_level": "Medium"
      }
    ],
    "competitor_count_300m": 2,
    "competition_level": "Low",
    "market_saturation": "Untapped"
  },

  "feature_importances": [
    {
      "rank": 1,
      "feature": "POI Decay Score",
      "impact_percent": 42,
      "direction": "UP",
      "plain_reason": "High foot traffic from nearby bus terminal"
    },
    {
      "rank": 2,
      "feature": "Low Competitor Density",
      "impact_percent": 28,
      "direction": "UP",
      "plain_reason": "Only 2 competing outlets within 300m radius"
    },
    {
      "rank": 3,
      "feature": "Historical Censoring Uplift",
      "impact_percent": 18,
      "direction": "UP",
      "plain_reason": "Past sales were suppressed by stockouts, true demand is higher"
    },
    {
      "rank": 4,
      "feature": "January Seasonality",
      "impact_percent": 18,
      "direction": "UP",
      "plain_reason": "January is above-average month for this distributor"
    },
    {
      "rank": 5,
      "feature": "Cooler Capacity",
      "impact_percent": 15,
      "direction": "DOWN",
      "plain_reason": "12-crate cooler is below the optimal 20-crate capacity"
    }
  ],

  "operational_constraints": {
    "cooler_capacity_crates": 12,
    "optimal_cooler_crates": 20,
    "cooler_gap": 8,
    "credit_status": "Good",
    "supply_consistency": "High",
    "constraint_summary": "Cooler capacity is the primary limiting factor"
  },

  "budget_allocation": {
    "allocated_lkr": 45000,
    "allocation_tier": "High Priority",
    "expected_volume_lift_liters": 850,
    "recommended_activity": "Cooler upgrade + display merchandising"
  }
}
```

### How to Generate This JSON

The JSON is assembled in the Next.js API route at runtime by:

1. Querying the predictions table JOIN outlets table for that outlet_id
2. Querying budget_allocations table for that outlet_id (if Western Province)
3. Building the structured JSON object from the flat SQL row
4. Passing it directly into the Gemini prompt as a string

No separate JSON generation step needed — it is assembled on demand from SQLite rows.

---

## 8. LLM Integration — Complete Plan

### Why Gemini 2.0 Flash Free Tier Is Enough

The app generates explanations on demand when a user clicks an outlet:

- Free tier allows 15 requests per minute
- Judges will click approximately 5-10 outlets during the entire demo
- Zero chance of hitting the rate limit
- 2-3 second loading spinner looks natural and shows the AI working live

### On-Demand Generation With SQLite Caching

```
User clicks outlet
       │
       ▼
Next.js API route reads outlet row from SQLite
       │
       ▼
Check xai_explanation column
       │
   ┌───┴────────────────┐
   │                    │
  NULL            Has value
   │                    │
   ▼                    ▼
Assemble         Return cached
outlet JSON      explanation
   │             instantly
   ▼
Build prompt:
  system prompt (your methodology)
  + outlet JSON (the data)
   │
   ▼
Call Gemini 2.0 Flash API
   │
   ▼
Receive explanation text
   │
   ▼
UPDATE predictions SET
xai_explanation = '...'
WHERE outlet_id = 'W_001'
   │
   ▼
Return explanation to UI
   │
   ▼
Display in outlet detail page
```

### Why On-Demand Beats Pre-Generating

```
Pre-generating all 20,000:
  Gemini free tier = 1,500 requests/day
  20,000 ÷ 1,500 = 14 days — not feasible

On-demand with caching:
  Only called when clicked
  Judges click ~5-10 outlets
  Zero rate limit risk
  Cached immediately after first click
  Looks impressive — AI generates live
```

---

## 9. Prompts to Send to Gemini

Every Gemini call has exactly two parts: a system prompt and a user message.

---

### Part 1 — System Prompt

_(Written once, hardcoded in your API route, sent with every call, never changes)_

```
You are a business intelligence analyst for a leading beverage
manufacturer in Sri Lanka.

Your company has built a machine learning model to predict the
Maximum Monthly Sales Potential (in liters) for 20,000 traditional
trade outlets across Sri Lanka for January 2026.

ABOUT THE MODEL YOU ARE EXPLAINING:
─────────────────────────────────────

1. THE CORE PROBLEM WE SOLVED — CENSORED DEMAND
   Historical sales data only shows what outlets DID sell, not
   what they COULD sell. Many outlets were artificially capped
   because they ran out of stock, had credit holds, or faced
   supply issues. We used statistical modeling to estimate the
   TRUE underlying demand beyond these artificial ceilings.
   This is called "uncapping censored demand."

2. SPATIAL SCORING — DISTANCE DECAY
   We pulled Points of Interest (POIs) from OpenStreetMap
   around each outlet: bus terminals, markets, schools,
   hospitals, restaurants, transit hubs.
   We did NOT just count them. We applied Gaussian distance-decay
   weighting — meaning POIs closer to the outlet have a much
   stronger influence than distant ones.
   Example: A bus stop 20m away has nearly full impact.
            A bus stop 400m away has very little impact.
   This gives each outlet a POI Decay Score from 0 to 10.

3. COMPETITOR ANALYSIS
   We counted competing beverage outlets within a 300m radius
   of each outlet. Fewer competitors means the outlet has more
   of the local market to itself — higher untapped potential.

4. SEASONALITY
   Each distributor has a monthly seasonality multiplier.
   January's multiplier is applied to adjust the final prediction
   for realistic seasonal demand patterns.

5. FEATURE IMPORTANCES
   The model assigns each outlet a ranked list of features that
   drove its score up or down. These are specific to each outlet
   and represent the model's actual reasoning for that prediction.

6. OPERATIONAL CONSTRAINTS
   Physical limits like cooler capacity, credit status, and
   supply consistency act as ceilings on what the outlet can
   actually sell even if demand is high.

YOUR TASK:
───────────
You will receive a JSON object with all the data for one outlet.
Write a 4-sentence explanation for a non-technical regional
sales manager.

STRICT RULES:
- Write exactly 4 sentences
- Sentence 1: Overall verdict — high, medium, or low potential
  and the single biggest reason why
- Sentence 2: The top 2 factors INCREASING the score,
  mention specific numbers (distances, percentages, liters)
- Sentence 3: The main factor LIMITING full potential
  and what it means practically for the business
- Sentence 4: One specific, actionable recommendation
  for the sales team for January 2026

LANGUAGE RULES:
- Use the outlet name
- Mention actual numbers from the JSON data
- No statistics terminology, no math jargon
- Write as if briefing a regional sales manager in a meeting
- Maximum 150 words total
- Conversational but professional tone
```

---

### Part 2 — User Message

_(Assembled dynamically per outlet from SQLite data)_

```
Here is the outlet data. Explain this outlet's prediction:

{
  "outlet_id": "W_001",
  "name": "Perera Grocery",
  ... (full outlet JSON as shown in Section 7)
}
```

That is the entire message. The raw JSON is pasted directly as a string.
Gemini reads it and explains it according to your methodology in the system prompt.

---

### Example of What Gemini Returns

```
Perera Grocery in Colombo 03 is a HIGH potential outlet,
primarily because it sits just 45 meters from a major bus
terminal that generates strong daily foot traffic. Its POI
decay score of 8.4 out of 10 and the fact that only 2
competitors exist within 300 meters means it has significant
untapped market share available for January 2026. However,
its cooler capacity of only 12 crates — 8 below the optimal
level — acts as a physical ceiling that will prevent it from
capturing its full 4,250-liter potential even if demand is
there. The sales team should prioritize a cooler upgrade for
this outlet before January and pair it with the allocated
LKR 45,000 in display merchandising to maximize the projected
850-liter volume lift.
```

---

### Why This Prompt Strategy Works

```
Without system prompt context:
  Gemini guesses why the outlet scored high
  → Generic, vague, inaccurate
  → Judges see through it immediately
  → Lose XAI marks

With full system prompt + structured JSON:
  Gemini explains YOUR model's actual reasoning
  → References your distance-decay method by name
  → Cites real numbers from your analysis
  → Reads like a real business analyst wrote it
  → Judges impressed → full XAI marks
```

### The Key Principle

```
Quality of JSON from Python pipeline
              ↓
Richness of context in the prompt
              ↓
Accuracy of Gemini explanation
              ↓
XAI marks scored
```

Feature importances, POI details, and censoring analysis are the
most critical fields. Make sure your Python pipeline exports all of them.

---

## 10. Caching Strategy

### How It Works in SQLite

```
predictions table has column: xai_explanation TEXT DEFAULT NULL

First click on outlet W_001:
  → xai_explanation is NULL in SQLite
  → Call Gemini (2-3 seconds, show spinner)
  → Receive explanation text
  → UPDATE predictions SET xai_explanation = '...'
     WHERE outlet_id = 'W_001'
  → Display explanation

Any future click on outlet W_001:
  → xai_explanation is NOT NULL
  → Skip Gemini call entirely
  → Return from SQLite instantly
  → Display explanation (no spinner)
```

### Why This Matters

During the demo, if a judge clicks back to an outlet they already visited,
or two judges explore the same outlet, it loads instantly. No spinner,
no wait. Looks polished and reliable.

The SQLite .db file naturally accumulates explanations as the app is used.
The more outlets clicked, the faster the app becomes.

---

## 11. Web App Pages

### Page 1 — Dashboard / Home

```
Route: /

TOP BAR — Summary Stats
  Total Outlets: 20,000
  Total Predicted Volume: X,XXX,XXX L
  Western Province Budget: LKR 5,000,000
  High Potential Outlets: X,XXX

FILTER PANEL (sidebar or top bar)
  Province:     All / Western / Central / North-Western / Southern
  Distributor:  dynamically updates based on province selected
  Outlet Type:  All / Grocery / Kade / Eatery / Pharmacy
  Tier:         All / High / Medium / Low

MAIN CONTENT — Two switchable views

  MAP VIEW (default)
  - React-Leaflet map centered on Sri Lanka
  - 20,000 outlet markers, color coded:
      Green  = High potential
      Yellow = Medium potential
      Red    = Low potential
  - Filters update visible markers in real time
  - Click any marker → go to /outlets/[id]

  TABLE VIEW
  - Sortable columns:
    Outlet ID | Name | Type | Province | Distributor |
    Predicted (L) | Historical (L) | Gap (L) | Gap % | Tier
  - 100 rows per page with pagination
  - Click any row → go to /outlets/[id]
```

### Page 2 — Outlet Detail Page

```
Route: /outlets/[id]

OUTLET HEADER
  Name, Type badge, Province, Distributor
  Location area
  Potential tier badge (High / Medium / Low)

PREDICTION METRICS ROW (4 cards)
  Predicted Maximum  | Historical Average | Potential Gap | Confidence
  4,250 L            | 2,100 L            | +2,150 L      | High
                                            (+102%)

SPATIAL ANALYSIS SECTION
  POI Decay Score: 8.4 / 10 (visual progress bar)
  Top 3 Nearby POIs:
    Bus Terminal   45m   Very High Impact
    Public Market  120m  High Impact
    School         200m  Medium Impact
  Competitors within 300m: 2
  Competition Level: Low (badge)
  Market Saturation: Untapped (badge)

FEATURE IMPORTANCE CHART
  Horizontal bar chart (Recharts)
  5 features ranked by impact
  Green bars = pushed score UP
  Red bars   = pushed score DOWN
  Each bar shows feature name, % impact, plain reason

OPERATIONAL CONSTRAINTS
  Cooler Capacity: 12 / 20 crates (visual gap bar)
  Credit Status: Good
  Supply Consistency: High

BUDGET ALLOCATION (Western Province outlets only)
  Allocated Trade Spend:  LKR 45,000
  Allocation Tier:        High Priority
  Expected Volume Lift:   +850 L
  Recommended Activity:   Cooler upgrade + display merchandising

XAI EXPLANATION SECTION (bottom of page)
  Heading: "AI Business Insight"

  If explanation already cached in SQLite:
    → Show explanation text immediately in a styled card

  If explanation is NULL in SQLite:
    → Show "Generate AI Explanation" button
    → User clicks button
    → Button changes to loading spinner
    → Text: "Analyzing outlet data..."
    → Gemini API called (2-3 seconds)
    → Explanation appears in card
    → Cached to SQLite for all future visits
```

### Page 3 — Budget Allocation Dashboard

```
Route: /budget

Western Province only — LKR 5,000,000 total budget

SUMMARY ROW
  Total Budget:    LKR 5,000,000
  Total Allocated: LKR X,XXX,XXX
  Outlets Covered: X,XXX
  Expected Lift:   X,XXX L

CHARTS ROW
  Donut chart — budget split by distributor
                (DIST_W_01 / DIST_W_02 / DIST_W_03)
  Bar chart   — expected volume lift by distributor

ALLOCATIONS TABLE
  Outlet | Type | Distributor | Tier | Allocated LKR |
  Expected Lift (L) | Recommended Activity
  Sortable, filterable by distributor
  Click outlet row → goes to /outlets/[id]
```

---

## 12. Git Strategy

### What Gets Committed

```
✅ /data/outlets.csv
✅ /data/predictions.csv
✅ /data/budget_allocations.csv
✅ /scripts/setup_db.py
✅ /app (all Next.js code)
✅ /lib/db.ts
✅ .env.example
✅ README.md
✅ package.json
```

### What Does NOT Get Committed

```
❌ /data/outlets.db      (generated locally, in .gitignore)
❌ .env.local            (contains API key, in .gitignore)
❌ node_modules/         (standard)
❌ .next/                (build output)
```

### Why CSVs Are Fine for Git

```
20,000 rows × ~30 columns = approximately 5-10 MB per CSV
Well within GitHub's 100MB file limit
Commits and clones fast
Judges get all the data they need
```

### .gitignore

```
/data/outlets.db
.env.local
node_modules/
.next/
```

---

## 13. Judge Setup Instructions (README)

This is exactly what your README.md should say:

```markdown
## Setup Instructions

### Prerequisites

- Node.js 18+
- Python 3.8+ with pandas installed

### Steps

1. Clone the repository
   git clone <repo-url>
   cd outlet-intelligence-app

2. Add your Gemini API key
   Copy .env.example to .env.local
   Add your free Gemini API key from aistudio.google.com

3. Generate the local database
   python scripts/setup_db.py
   This creates /data/outlets.db from the CSV files.
   Takes about 30 seconds.

4. Install dependencies
   npm install

5. Run the app
   npm run dev

6. Open in browser
   http://localhost:3000
```

**Five steps. That is all judges need to do.**

---

## 14. Build Checklist

### Python Pipeline Must Export

- [ ] `outlet_id`, `name`, `outlet_type`, `province`, `distributor_id`, `lat`, `lon`
- [ ] `max_monthly_liters` (uncapped prediction)
- [ ] `historical_avg`, `potential_gap`, `potential_gap_percent`
- [ ] `confidence_level`, `seasonality_multiplier`
- [ ] `poi_decay_score` (Gaussian decay weighted, 0-10 scale)
- [ ] Top 3 POI types and distances per outlet
- [ ] `competitor_count_300m`, `competition_level`, `market_saturation`
- [ ] `was_historically_capped`, `capping_reason`
- [ ] Top 5 feature importances with direction (UP/DOWN) and plain reason per outlet
- [ ] `cooler_capacity`, `optimal_cooler_capacity`, `credit_status`, `supply_consistency`
- [ ] `trade_spend_lkr`, `allocation_tier`, `expected_volume_lift`, `recommended_activity` (Western only)

### setup_db.py Script

- [ ] Reads all three CSVs using pandas
- [ ] Creates outlets.db with correct schema
- [ ] Inserts all rows from all three CSVs
- [ ] Adds xai_explanation TEXT column (NULL default) to predictions table
- [ ] Runs in under 60 seconds
- [ ] Tested on a clean machine

### Next.js App

- [ ] db.ts sets up better-sqlite3 connection to /data/outlets.db
- [ ] Dashboard page loads with map and table view
- [ ] Province filter works and updates results
- [ ] Distributor dropdown updates based on province selection
- [ ] Outlet detail page shows all sections with real data
- [ ] Feature importance chart renders correctly with UP/DOWN colors
- [ ] XAI section shows cached explanation or generate button
- [ ] Budget allocation page loads for Western Province
- [ ] Charts render correctly on budget page
- [ ] App runs cleanly on localhost:3000

### Gemini Integration

- [ ] System prompt written with complete methodology explanation
- [ ] User message assembles outlet JSON from SQLite row dynamically
- [ ] Explanation cached to SQLite after first generation
- [ ] Loading spinner shown during API call with descriptive text
- [ ] Error handling if Gemini call fails (show error message, do not crash)
- [ ] GEMINI_API_KEY read from environment variable, never hardcoded

### Git

- [ ] outlets.db in .gitignore
- [ ] .env.local in .gitignore
- [ ] .env.example committed with placeholder key
- [ ] README.md has clear 5-step setup instructions
- [ ] All CSV files committed and not too large

---

_Complete architecture plan for Data Storm v7.0 Final Round — Deliverable 4_
_Final Stack: Next.js + SQLite (better-sqlite3) + Gemini 2.0 Flash_
_No Supabase. No Drizzle. No hosting. Runs fully locally._
