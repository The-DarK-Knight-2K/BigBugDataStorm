# Modelling Spec: Colab Experiments & Algorithm Selection

## Target Notebook
`notebooks/04_model_evaluation.ipynb`

## Context Needed
When feeding this spec to Gemini in Google Colab, ensure you also provide:
- `specs/architecture/DATA_CONTRACTS.md` (To understand table schemas)
- `specs/architecture/CONVENTIONS.md` (For coding standard and hyperparameter defaults)
- `config.yaml` (For standard parameters)
- `docs/target_generation_strategies.md` (Details options for structuring the target variable $y$)
- `docs/optimizations.md` (Outlines advanced features, models, preprocessing switch, and clean train logic)
- `specs/modelling/SPEC_train.md` & `specs/modelling/SPEC_predict.md` (The destination script specs the Colab model will lay the foundation for)
- The contents of `modelling/baseline.py` (For the exact safety floor blending logic)

## Objectives
Write Python code to evaluate and compare different Gradient Boosting frameworks (LightGBM and CatBoost) to predict the latent demand ceiling for outlets. Determine the best algorithm and optimal hyperparameters before finalizing `train.py` and `predict.py`.

### Requirements

1. **Data Loading & Preparation**:
   - Load `Data/Gold/master_features.parquet` and `Data/Gold/baseline_predictions.parquet`.
   - **Crucial Rule ("Clean Train")**: Create the training dataset by filtering out records where `exclude_from_training == True` and `has_transaction_history == False`.
   - Construct the pseudo-label target for the training set: 
     `target = hist_p90_monthly * seasonality_multiplier_jan_2026 * (jan_2026_trading_days / 22.0)`
   - Define your feature columns (drop `Outlet_ID`, `target`, and text columns like `seasonality_jan_2026` depending on the framework's needs).

2. **Algorithm Comparison**:
   - Setup a 5-Fold Cross-Validation scheme (`sklearn.model_selection.KFold`).
   - Train and evaluate **LightGBM** (using `astype("category")` for string columns).
   - Train and evaluate **CatBoost** (passing string columns to the `cat_features` parameter).
   - *Optional:* Compare against XGBoost.

3. **Metric Tracking**:
   - Calculate and log **RMSE** (Root Mean Squared Error) and **MAE** (Mean Absolute Error) across the folds for each algorithm.

4. **The Baseline Blend Test ("Predict All")**:
   - For your validation sets in the CV loop, generate the raw model prediction.
   - Merge the validation predictions with the `baseline_potential_litres` from the baseline dataset.
   - Apply the final competition logic: `final_prediction = max(model_prediction, baseline_potential)`.
   - Calculate RMSE/MAE *after* this blending step to see how the model behaves in production.

5. **Feature Importance**:
   - Extract and plot the Top 20 feature importances (gain or split) for the best performing model.
   - Verify that logical features (e.g., `jan_avg_volume`, `hist_p90_monthly`, `ema_3m`) rank highly.

6. **Hyperparameter Tuning (Optional but Recommended)**:
   - Use `optuna` to run a small trial (20-30 iterations) to find optimal parameters (learning rate, depth, number of leaves) for the winning algorithm.

## Output Expectations
- Use clear markdown headers for each section.
- Output a clean comparison table (e.g., a pandas DataFrame) showing CV RMSE and MAE for LightGBM vs. CatBoost.
- Output high-quality `matplotlib` or `seaborn` horizontal bar charts for feature importance.
- Provide a markdown summary concluding which algorithm and hyperparameters should be used for the final `train.py` script.
