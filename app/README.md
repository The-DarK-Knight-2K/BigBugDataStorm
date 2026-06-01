# BigBug Intelligence App

This is the interactive decision-support engine for Team BigBug's Data Storm v7.0 Final Round submission. It provides a visual interface for business users to explore the predicted maximum sales potential across 20,000 traditional retail outlets in Sri Lanka. 

The application features a **Dynamic GenAI Explainability (XAI) Module** that utilizes Google Gemini 2.0 Flash to translate complex underlying model signals (such as SHAP values, Tobit latent demand, and Gravity density) into plain-English **Field Rep Negotiation Plans**.

## Prerequisites

- **Node.js**: v18+ (v20+ recommended)
- **Python**: 3.9+ (for generating the local database)
- **API Key**: A valid Gemini API Key from Google AI Studio.

## Setup Instructions

### 1. Generate the Local Database

The web app relies on a local, highly-optimized SQLite database (`outlets.db`). It must be generated first from the Bronze, Silver, and Gold Parquet outputs created by the backend pipeline.

```bash
# Navigate to the app directory
cd app

# Install Python dependencies required for database construction
pip install pandas pyarrow

# Run the database generation script to build the full 20,000 outlet DB
python scripts/populate_real_db.py
```

This script parses the backend data files across the `Data/` and `outputs/` folders and generates `app/data/outlets.db`.

### 2. Environment Variables

Create a file named `.env.local` in the root of the `app` directory and add your Gemini API Key:

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

- **Global Browsing:** Explore maximum potential volume predictions across the entire dataset of 20,000 traditional trade outlets.
- **Dynamic Filtering:** Filter geographic data dynamically by province, district, and specific distributors to isolate strategic regions.
- **Deep-Dive Analysis:** Drill down into specific outlets to view granular predictive scores, competitive catchment counts, and spatial gravity metrics.
- **GenAI XAI Module:** Click on any outlet to trigger Google Gemini 2.0. The LLM evaluates the outlet's SHAP values and feature baselines to dynamically construct a personalized **Negotiation Plan** intended for frontline sales representatives.
