# Target Value Generation Strategies — Unimplemented

This document outlines target variable generation strategies described in the original roadmap that have **not been implemented** in the current modelling pipeline.

---

## Approach 2: The "Sliding Window" / Panel Data Approach ✗ NOT IMPLEMENTED

### Overview
To combat the small training dataset of the Direct Month approach, this strategy treats every historical month as a separate training record, dramatically increasing data points.

### Proposed Logic

**Data Generation Method**:
- For each historical month, create a training record
- Features are calculated using all data up to the target month (time-aware)
- Target is the actual volume sold in that specific month

### Example Training Data

| Training Record | Features Calculated From | Target Month | y (Volume) |
|---|---|---|---|
| Record 1 | All data up to Jan 2024 | **Feb 2024** | Actual volume in Feb 2024 |
| Record 2 | All data up to Feb 2024 | **Mar 2024** | Actual volume in Mar 2024 |
| Record 3 | All data up to Mar 2024 | **Apr 2024** | Actual volume in Apr 2024 |
| ... | ... | ... | ... |
| Record 60 | All data up to Nov 2025 | **Dec 2025** | Actual volume in Dec 2025 |

### Dataset Size
- For outlets existing since 2020: ~60 training records per outlet
- Total training samples: 20,000 outlets × 60 months = **1.2 million records**
- Massive increase in training data → more robust model learning

### Pros
✓ **Huge training dataset** — Increases from ~20k (1 per outlet) to ~1.2 million samples
✓ **General sales dynamics learning** — Model learns how volume changes across seasons naturally
✓ **Trend momentum capture** — Model learns to extrapolate trends better with more data
✓ **Noise reduction** — More data reduces overfitting risk

### Cons
✗ **Diluted seasonal focus** — Model spends 90% of training time on non-January months
✗ **Poor January performance** — May significantly underperform when predicting the specific target month (January)
✗ **Requires strong seasonality features** — Must include explicit `month`, `seasonality_index`, and seasonal lags as features to guide model
✗ **Complex feature engineering** — Features must be time-aware and not leak future information
✗ **Data leakage risk** — Easy to accidentally include information not available at prediction time

### Mitigation Strategies (if implemented)
1. **Stratified loss weighting**: Give higher weight to January records during training
2. **Month-specific early stopping**: Monitor validation RMSE on January holdout separately
3. **Explicit month encoding**: Ensure `month` feature is strong and informative
4. **Lag feature engineering**: Include explicit `volume_lag_1`, `volume_lag_12` (YoY) features

### Why Not Implemented
- **Direct Month approach already working well** (CV RMSE 40.38)
- **Higher implementation complexity** — Requires careful feature engineering to avoid data leakage
- **Unclear if January performance would be better** — Theoretical advantage doesn't guarantee empirical improvement
- **Validation challenges** — Harder to set up proper train/test splits that don't leak temporal information

---

## Approach 3: The "Lagged" / Growth Approach ✗ NOT IMPLEMENTED

### Overview
Instead of predicting absolute volumes, this approach predicts the *change* (delta) in volume between two time periods. This can stabilize variance and handle outliers better.

### Proposed Logic — Month-over-Month Delta

**Target Variable**:
```
y = Volume(target_month) - Volume(reference_month)
```

**Example**:
```
y = Volume(Jan 2025) - Volume(Dec 2024)
```

### Proposed Logic — Year-over-Year Delta

**Target Variable**:
```
y = Volume(Jan 2025) - Volume(Jan 2024)
```

**Example**:
```
If Jan 2025 sold 100L and Jan 2024 sold 80L:
y = 100 - 80 = +20L (growth)
```

### Proposed Logic — Percentage Growth

**Target Variable**:
```
y = (Volume(target_month) - Volume(reference_month)) / Volume(reference_month)
```

**Example**:
```
y = (100 - 80) / 80 = 0.25 (25% growth)
```

### Dataset Size
- Similar to Approach 2: ~1.2 million records if used with sliding window
- Or limited sample if paired with direct month approach

### Advantages
✓ **Stabilizes variance** — Differences are more normally distributed than raw volumes
✓ **Reduces extreme outliers** — Delta-based targets are less sensitive to one-off spikes
✓ **Interpretable** — Model learns "growth" rather than "absolute volume", which is psychologically intuitive
✓ **Handles cold-start better** — New outlets with zero baseline don't cause division-by-zero errors

### Disadvantages
✗ **Requires inverse transformation** — To get final `Maximum_Monthly_Litres`, must add delta back to reference volume: `Prediction = Reference_Volume + Model_Prediction_Delta`
✗ **Reference choice matters** — If reference month is anomalous (spike/drop), final prediction will also be anomalous
✗ **Information loss** — For outlets with no history, cannot compute delta (must use fallback)
✗ **More complex pipeline** — Additional transformation/inverse transformation steps
✗ **Harder to interpret failure modes** — When model mispredicts, is it a growth estimation problem or reference month selection issue?

### Example Implementation (Pseudocode)

```python
# During training
reference_volume = df["hist_p90_monthly"]  # All-months P90
target_month_volume = actual_volume_jan_2025
delta_target = target_month_volume - (reference_volume * 0.85)

model.fit(X, delta_target)

# During prediction
model_prediction_delta = model.predict(X_test)
reference = test_df["hist_p90_monthly"]
final_prediction = reference + model_prediction_delta
```

### Why Not Implemented
- **Direct Month approach avoids this complexity** — Predicting absolute volume is more straightforward
- **Unclear if variance stabilization is needed** — Tree-based models (CatBoost) handle skewed targets reasonably well
- **Inverse transformation adds failure modes** — Extra pipeline step increases chance of bugs
- **No strong empirical evidence** — Would require experimentation to validate if delta approach outperforms direct approach
- **Reference selection is arbitrary** — Choosing `hist_p90_monthly - 15%` vs `hist_p90_monthly - 20%` adds tuning burden

---

## Alternative Approach: Quantile Regression ✗ NOT IMPLEMENTED

### Overview (Not in Original Roadmap, but Related)
Instead of predicting the mean (or 90th percentile) of volume, predict the **upper quantile** directly.

### Proposed Logic
```
Use CatBoost in quantile regression mode:
- Predict 0.95 quantile directly (maximum expected volume)
- Or ensemble predictions from multiple quantiles (0.75, 0.90, 0.95)
```

### Advantages
✓ Directly models the tail behavior (what we care about)
✓ More robust than P90 proxy for true demand ceiling
✓ CatBoost has native quantile regression support

### Why Not Implemented
- **Direct Month with P90 already effective** — CatBoost handles right-skew well
- **Quantile regression less interpretable** — Harder to explain why 95th quantile vs 90th
- **Would require threshold tuning** — Which quantile is "maximum potential"?

---

## Summary: Comparison of All Approaches

| Aspect | Approach 1: Direct Month | Approach 2: Sliding Window | Approach 3: Lagged |
|--------|---|---|---|
| **Data points per outlet** | 1 | 60+ | 60+ |
| **Training samples total** | ~20k | ~1.2M | ~1.2M |
| **Seasonal specificity** | Very High | Medium | Medium |
| **Variance of target** | High (right-skewed) | Lower (seasonal noise) | Lower (deltas more stable) |
| **Implementation complexity** | Low | High | Medium |
| **Interpretability** | High | Medium | Low |
| **Risk of data leakage** | None | High | Medium |
| **Inference complexity** | Simple | Simple | Complex (inverse transform) |
| **Current status** | ✓ Implemented | ✗ Not implemented | ✗ Not implemented |
| **CV Performance** | 40.38 RMSE | Unknown | Unknown |
| **Production readiness** | ✓ Yes | ✗ Requires validation | ✗ Requires validation |

---

## Recommendation: Why Approach 1 Was Best

1. **Direct alignment** — Predicting January 2026 with a January-trained model is theoretically and practically sound
2. **Simplicity** — Minimal feature engineering, minimal transformation/inverse transformation steps
3. **Interpretability** — Easy to explain: "Model learned from historical January sales"
4. **Proven performance** — CV RMSE 40.38 is competitive (better than LightGBM's 40.96)
5. **Production robustness** — Fewer failure modes, easier to debug, easier to maintain
6. **Time constraints** — Would require significant experimentation to validate Approach 2 or 3

---

## Future Experimentation Ideas

If model performance needs improvement, consider these explorations:

### Experiment 1: Hybrid Approach
- Train Approach 1 (Direct January) as primary model
- Train Approach 2 (Sliding Window) as secondary model
- Ensemble predictions: `final = 0.7 × approach1 + 0.3 × approach2`

### Experiment 2: January-Weighted Sliding Window
- Use Approach 2 but assign higher loss weight to January records
- E.g., January records get 10× weight, other months 1× weight
- Forces model to specialize on January despite seeing all months

### Experiment 3: Two-Stage Model
- **Stage 1**: Predict monthly volume (any month) using Approach 2
- **Stage 2**: Predict January-specific adjustment multiplier using January features
- **Ensemble**: `jan_2026_prediction = stage1_prediction × stage2_multiplier`

### Experiment 4: Quantile Ensemble
- Train Approach 1 but predict 0.75, 0.90, 0.95 quantiles simultaneously
- Use weighted average: `final = 0.3 × q75 + 0.5 × q90 + 0.2 × q95`
- Robustness against outliers

---

## Conclusion

The **Direct Month Approach (Approach 1)** was correctly chosen because:
- It's simple, interpretable, and performs well
- Trade-offs of Approaches 2 and 3 (complexity for marginal gains) are not worth it at current performance levels
- If CV RMSE needs to improve, hybrid ensemble approaches are safer bets than switching methods entirely
