# EDA Spec: Transactions, Seasonality, and Holidays

## Target Notebook
`notebooks/01_eda_transactions.ipynb`

## Context Needed
When feeding this spec to Gemini, ensure you also provide:
- `specs/architecture/DATA_CONTRACTS.md`
- `specs/architecture/CONVENTIONS.md`

## Objectives
Write Python code using `pandas`, `matplotlib`, and `seaborn` to perform Exploratory Data Analysis on the following files in `Data/bronze/`:
1. `transactions.parquet`
2. `seasonality.parquet`
3. `holidays.parquet`

### Requirements
1. **Missing Values**:
   - Check and count missing values in `Date`, `Distributor_ID`, and `Volume_Litres`.
2. **Data Integrity (Transactions)**:
   - Identify negative volumes (refunds/returns). Print their frequency and suggest a handling strategy.
   - Analyze date ranges to identify any gaps or anomalies (e.g., blackout periods where no transactions occurred).
3. **Distribution Analysis**:
   - Plot the distribution of transaction volumes.
   - Identify outliers using standard IQR or Z-score methods.
4. **External Factors (Holidays)**:
   - Join/cross-reference transactions with `holidays.parquet`.
   - Plot transaction volumes to identify dips or spikes around specific holiday types.
5. **Seasonality Check**:
   - Validate that the time-series in `transactions` aligns with the periods in `seasonality.parquet`.
   - Ensure all distributors are represented across time periods.

## Output Expectations
- Use clear markdown headers for each section.
- Write robust pandas code using the `pyarrow` engine where applicable.
- Output high-quality seaborn/matplotlib plots with titles, axis labels, and legends.
