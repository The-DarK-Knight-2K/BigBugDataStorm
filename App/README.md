# Outlet Intelligence Web App

This is the interactive decision-support engine for the Data Storm v7.0 Final Round. It allows business users to explore the predicted maximum possible sales volume across the 20,000 traditional trade outlet network in Sri Lanka and utilizes Gemini 2.0 Flash to generate dynamic Explainable AI (XAI) insights.

## Prerequisites

- **Node.js**: v18+ (v20+ recommended)
- **Python**: 3.9+ (for generating the local database)
- **API Key**: You need a valid Gemini API Key from Google AI Studio.

## Setup Instructions

### 1. Generate the Local Database

The web app relies on a local, highly-optimized SQLite database (`outlets.db`). You must generate it first from the provided CSV data.

```bash
# Navigate to the App directory (if you aren't already there)
cd App

# Install Python dependencies (pandas, sqlite3 is built-in)
pip install pandas

# Run the database generation script
python scripts/setup_db.py
```

This will parse the data files in `data/` and generate `data/outlets.db`.

### 2. Environment Variables

Create a file named `.env.local` in the root of the `App` directory and add your Gemini API Key:

```env
GEMINI_API_KEY=your_gemini_api_key_here
```

### 3. Install Dependencies & Run

```bash
# Install Node modules
npm install

# Start the Next.js development server
npm run dev
```

The application will be accessible at [http://localhost:3000](http://localhost:3000).

## Features

- **Global Browsing:** Explore predictions across the entire dataset of 20,000 traditional trade outlets.
- **Dynamic Filtering:** Filter data dynamically by province and specific distributors.
- **Deep-Dive Analysis:** Drill down into any specific outlet to view its predicted potential and spatial gravity metrics.
- **Dynamic XAI Module:** Click on any outlet to generate a dynamic, plain-English narrative explaining the reasoning behind the outlet's predicted score, translating model drivers (like SHAP values) into a Field Rep Negotiation Plan.
