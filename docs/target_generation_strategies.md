# Target Value Generation Strategies for Modelling

This document outlines the logical decisions, methodologies, examples, and trade-offs for generating the target variable ($y$) used to train our machine learning models in the DataStorm 7.0 competition.

## Overview

The ultimate goal of the competition is to predict `Maximum_Monthly_Liters` for January 2026 for each outlet. In machine learning terms, the target $y$ is the aggregated `Volume_Litres` for an outlet in a specific future month. 

To train our models (like LightGBM or XGBoost), we need historical pairs of $(X, y)$, where:
*   **$X$ (Features)**: The state of the outlet known *prior* to the target month.
*   **$y$ (Target)**: The actual volume consumed in that target month.

How we construct these pairs significantly impacts the model's ability to generalize and capture seasonal trends.

---

## Approach 1: The "Direct Month" Approach (Highly Recommended)

Because FMCG sales are highly seasonal, January behaves very differently than December. Predicting January using a model trained on December targets might introduce massive bias. This approach isolates the problem to predicting Januaries only.

*   **Logic**: Train the model strictly on historical January targets.
*   **Data Generation Example**:
    *   **Record 1**: $X$ = Features calculated using data up to Dec 2023 $\rightarrow$ Target $y$ = Volume in **Jan 2024**.
    *   **Record 2**: $X$ = Features calculated using data up to Dec 2024 $\rightarrow$ Target $y$ = Volume in **Jan 2025**.
*   **Pros**: 
    *   The model perfectly learns the specific seasonal nuances of January (e.g., post-holiday restocking, local festival effects like Thai Pongal).
    *   Prevents the model from getting confused by the dynamics of other months.
*   **Cons**: 
    *   Produces a very small training dataset. For a store that has existed since 2020, we only have 5 training records.

---

## Approach 2: The "Sliding Window" / Panel Data Approach

To combat the small dataset size of the Direct Month approach, we can shift our feature calculation window month by month.

*   **Logic**: Every single historical month in the dataset becomes a target for a different training record.
*   **Data Generation Example**:
    *   $X$ (Features up to Jan 2024) $\rightarrow$ $y$ (Volume in **Feb 2024**)
    *   $X$ (Features up to Feb 2024) $\rightarrow$ $y$ (Volume in **Mar 2024**)
    *   ... and so on, up to $X$ (Features up to Nov 2025) $\rightarrow$ $y$ (Volume in **Dec 2025**).
*   **Pros**: 
    *   Massive increase in training data (up to ~60 records per outlet).
    *   The model learns general sales dynamics, trend momentum, and economic conditions extremely well.
*   **Cons**: 
    *   The target focus is diluted. The model might underperform on the exact target month (Jan 2026) because it spends 90% of its training time learning how to predict non-January months. (This can be mitigated by ensuring strong `month` and `seasonality_index` features are present in $X$).

---

## Approach 3: The "Lagged" / Growth Approach

Instead of predicting the absolute volume, the model predicts the change in volume. This is a common technique in time-series forecasting.

*   **Logic**: The target $y$ is the mathematical difference (or percentage growth) between the target month and a previous reference month.
*   **Data Generation Example**:
    *   $y$ = Volume(Jan 2025) - Volume(Dec 2024)
    *   Alternatively, $y$ = Volume(Jan 2025) - Volume(Jan 2024) (Year-over-Year difference)
*   **Pros**: 
    *   Stabilizes the variance of the data (achieves stationarity).
    *   Handles extreme absolute volume outliers well by focusing on relative momentum.
*   **Cons**: 
    *   Requires an inverse transformation step during inference. To get the final `Maximum_Monthly_Liters` for submission, we must add the predicted difference back to the reference month's absolute volume. If the reference volume is anomalous, the final prediction will also be anomalous.
