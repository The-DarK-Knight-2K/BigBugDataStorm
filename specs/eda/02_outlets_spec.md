# EDA Spec: Outlets and Coordinates

## Target Notebook
`notebooks/02_eda_outlets.ipynb`

## Context Needed
When feeding this spec to Gemini, ensure you also provide:
- `specs/architecture/DATA_CONTRACTS.md`
- `specs/architecture/CONVENTIONS.md`

## Objectives
Write Python code using `pandas`, `matplotlib`, and `seaborn` to perform Exploratory Data Analysis on the following files in `Data/bronze/`:
1. `outlet_master.parquet`
2. `outlet_coordinates.parquet`

### Requirements
1. **Master Data Quality (`outlet_master.parquet`)**:
   - Check for missing values in `Outlet_Size`.
   - Validate `Cooler_Count` distribution (expecting range 0-5). Plot a histogram.
   - Validate `Outlet_Type` categories. Show counts of each type.
   - Identify duplicates or inconsistencies in `Outlet_ID`.
2. **Geospatial Validation (`outlet_coordinates.parquet`)**:
   - Identify missing coordinates.
   - Plot coordinates on a scatter plot or a map (using `matplotlib` or `plotly`) to check for points outside Sri Lanka (lat: 5.9-9.9, lon: 79.5-81.9).
   - Identify swapped latitude and longitude values based on these bounding boxes and plan a correction strategy.

## Output Expectations
- Use clear markdown headers for each section.
- Output high-quality plots with titles and axis labels.
- For geospatial points, color-code outliers or swapped coordinates.
