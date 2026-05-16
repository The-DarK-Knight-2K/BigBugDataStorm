# EDA Spec: Feature Exploration & Imputation Heuristics

## Target Notebook
`notebooks/03_feature_exploration.ipynb`

## Context Needed
When feeding this spec to Gemini, ensure you also provide:
- `specs/architecture/DATA_CONTRACTS.md`
- `specs/architecture/CONVENTIONS.md`

## Objectives
Write Python code using `pandas`, `matplotlib`, and `seaborn` to perform Exploratory Data Analysis by joining the bronze tables to look for correlations and imputation strategies.

### Requirements
1. **Correlation Analysis**:
   - Join `transactions.parquet` aggregated volumes with `outlet_master.parquet` features.
   - Explore relationships between outlet features (size, type) and sales volume. Plot boxplots or violin plots.
2. **Heuristic Development**:
   - Analyze the relationship between `Outlet_Size` and `Cooler_Count`.
   - Brainstorm and validate rules for missing data imputation (e.g., if `Outlet_Size` is missing but `Cooler_Count` is > 0, what is the most likely size?).
3. **Target Analysis**:
   - Prepare for Phase 4 (Gold Layer) by identifying key predictive signals in the data.

## Output Expectations
- Use clear markdown headers for each section.
- Output high-quality plots with titles and axis labels.
- Provide a markdown summary of the recommended imputation heuristics based on the data findings.
