# Modelling Strategy & Experiments

This document tracks all the modelling combinations, algorithms, and experiments you can run to improve the prediction RMSE. It is ordered by priority and impact.

## 🔴 Must Do (Core Fixes & Baseline)

These are critical for the pipeline to function correctly and to score well on the basic Data Science evaluation criteria.

1. **Remove Target Leakage (Strategy A)**
   - **What:** Add `hist_p90_monthly`, `jan_avg_volume`, and similar direct historical target proxies to `EXCLUDE_COLS`.
   - **Why:** Forces the model to use POI and Gravity features. If you skip this, your spatial features will have 0% importance.
   - **Algorithm:** CatBoost (GPU)

2. **Add Individual Gravity Scores**
   - **What:** Include all 6 individual gravity scores (`school`, `hospital`, `transport`, `market`, `worship`, `hospitality`) in the feature set, not just the composite.
   - **Why:** CatBoost will naturally figure out which POI categories matter most for beverage sales.

3. **Implement Basic Run Tracking**
   - **What:** Update `train.py` to save models and results in timestamped folders (e.g., `artifacts/runs/run_YYYYMMDD_HHMM/`) instead of overwriting a single `model.pkl`. Maintain a `run_registry.csv` that logs CV RMSE, features used, and algorithm for every run.
   - **Why:** Essential for keeping track of your 20+ experiments and proving a systematic approach to the judges.

---

## 🟡 Can Do (High ROI Enhancements)

These will noticeably improve your score or provide great talking points for your final report.

4. **Multi-Model Comparison**
   - **What:** Train **XGBoost (GPU)** and **LightGBM (GPU)** alongside CatBoost using the exact same features and cross-validation splits.
   - **Why:** Proves you didn't just blindly pick the first algorithm. It's a standard requirement for "Enterprise-Grade" data science.

5. **Hyperparameter Tuning (Optuna)**
   - **What:** Run a 50-trial Optuna study for CatBoost (and XGBoost/LightGBM) using the new spatial feature set.
   - **Why:** The optimal tree depth and learning rate change when you introduce spatial features.

6. **Feature Interaction Engineering (Strategy C)**
   - **What:** Create cross-features like `gravity_x_cooler = composite_gravity_score * Cooler_Count`.
   - **Why:** Helps tree models find complex relationships faster (e.g., "A high footfall area only matters if the outlet has cooler capacity").

---

## 🟢 Try To Do (Bonus / Time Permitting)

Do these only if Phases 1-4 of the main pipeline are completely finished and working.

7. **Model Ensembling (Blending)**
   - **What:** If CatBoost and XGBoost have similar RMSE, average their predictions: `0.6 * CatBoost + 0.4 * XGBoost`.
   - **Why:** Usually guarantees a 2-5% reduction in RMSE.

8. **Experiment with Decay Functions (Gaussian / Exponential)**
   - **What:** Swap the Node 1 `inverse_square` function for `gaussian` or `exponential` and re-run the pipeline.
   - **Why:** To see if a different decay shape better matches Sri Lankan retail dynamics. (You can log this in your `run_registry.csv`).

9. **Tune the Epsilon / Radius**
   - **What:** Change the inverse-square `epsilon` from `0.05` to `0.02` or `0.10`. Change the catchment radius from 500m to 250m.
   - **Why:** Fine-tuning the spatial definition of a "local market".

---

## 🚫 Don't Do (Low ROI / Distractions)

10. **Two-Stage Modelling (Strategy B)**
    - **What:** Training one model on history, and a second model on the residuals using POI data.
    - **Why:** Too complex to implement robustly within the competition timeframe. Strategy A (removing leak features) achieves the same goal much faster.

11. **Deep Learning / Neural Networks**
    - **What:** PyTorch/TensorFlow models for tabular data.
    - **Why:** Overkill. Tree-based models (CatBoost/XGBoost) consistently outperform NNs on small tabular datasets (20K rows) and require much less tuning.

12. **Decay Functions for Catchment Density**
    - **What:** Using gravity models for competitor counts.
    - **Why:** Competitors in the same neighborhood split the market regardless of exact distance. Flat counts within radius bands (500m, 1km) are standard and sufficient.
