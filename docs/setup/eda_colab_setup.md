# EDA Setup and Google Colab Integration

This plan outlines the steps to set up the Exploratory Data Analysis (EDA) environment, bridging local development with Google Colab for collaborative or GPU-accelerated analysis.

## User Review Required

> [!IMPORTANT]
> The integration between Google Colab and local Git requires manual steps to "Save a copy to GitHub" or download/upload files, as Colab does not have a native, persistent Git client like VS Code.

## Proposed Changes

### 1. Local Jupyter Setup
Ensure the local environment is ready for notebook development.

- [ ] **Verify Dependencies**: Confirm `jupyter` and `ipykernel` are installed in the `venv`.
- [ ] **Initialize Notebooks**: Create skeleton `.ipynb` files in the `notebooks/` directory to match the `SYSTEM_OVERVIEW.md` structure.

### 2. Google Colab Workflow
Set up a seamless way to work in the cloud and keep files in Git.

#### Method A: Direct GitHub Integration (Recommended)
1. Open [Google Colab](https://colab.research.google.com/).
2. Go to `File` -> `Open notebook` -> `GitHub`.
3. Authorize Colab to access the `BigBugDataStorm` repository.
4. Select the `Sithum` branch and the specific notebook.
5. **To Save**: Go to `File` -> `Save a copy in GitHub`. This will prompt you to commit the changes back to your branch.

#### Method B: Local-to-Cloud Sync
1. Upload data from `Data/bronze/` to Google Drive.
2. Mount Google Drive in Colab:
   ```python
   from google.colab import drive
   drive.mount('/content/drive')
   ```
3. After working, download the `.ipynb` file and place it in the local `notebooks/` folder.

### 3. Repository Structure Updates

The following notebooks are available in the `notebooks/` directory.

#### [01_eda_transactions.ipynb](../../notebooks/01_eda_transactions.ipynb)
**Objectives:**
- **Missing Values**: Check Date, Distributor_ID, and Volume_Litres.
- **Data Integrity**: Identify negative volumes and anomalies in date ranges (blackout periods).
- **Distribution Analysis**: Analyze transaction volumes and detect outliers.
- **External Factors**: Cross-reference transactions with `holidays.csv` to see impact on volume.
- **Seasonality Check**: Validate time-series representation from `seasonality.csv`.

#### [02_eda_outlets.ipynb](../../notebooks/02_eda_outlets.ipynb)
**Objectives:**
- **Master Data Quality**: Check `Outlet_Size`, `Cooler_Count`, and `Outlet_Type` for inconsistencies.
- **Duplicate Detection**: Identify redundant or conflicting `Outlet_ID` records.
- **Geospatial Validation**: Map coordinates from `outlet_coordinates.csv` to identify points outside Sri Lanka and detect swapped Lat/Lon values.

#### [03_model_evaluation.ipynb](../../notebooks/03_model_evaluation.ipynb)
**Objectives:**
- **Data Loading & Preparation**: Load master features and baseline predictions, apply the "Clean Train" rule, and construct the pseudo-label target.
- **Algorithm Comparison**: Evaluate LightGBM and CatBoost using 5-Fold Cross-Validation.
- **Metric Tracking**: Calculate RMSE and MAE across folds.
- **The Baseline Blend Test**: Apply final competition logic (`max(model_prediction, baseline_potential)`) to validation sets.
- **Feature Importance**: Extract and plot Top 20 feature importances.
- **Hyperparameter Tuning**: Use Optuna for finding optimal parameters for the winning algorithm.

## Verification Plan

### Automated Tests
- Run a simple script to verify if `jupyter` can start locally: `jupyter notebook --version`.

### Manual Verification
- Verify that the notebooks appear in the `Sithum` branch after "Save a copy in GitHub" from Colab.
- Ensure local Jupyter can open the notebooks and access the `Data/bronze/` parquet files.
