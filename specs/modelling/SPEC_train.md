# SPEC: train.py

## Purpose

Train a LightGBM gradient boosting model to predict outlet-level maximum monthly
purchase potential. Since there is no labelled target variable, a pseudo-label is
constructed from the 90th percentile historical monthly volume adjusted for
seasonality. The trained model is saved to `modelling/artifacts/model.pkl`.

## Layer
Modelling

## Inputs

| File | Path |
|------|------|
| master_features.parquet | `data/gold/master_features.parquet` |

## Outputs

| File | Path |
|------|------|
| model.pkl | `modelling/artifacts/model.pkl` |
| feature_importance.png | `modelling/artifacts/feature_importance.png` |
| cv_results.json | `modelling/artifacts/cv_results.json` |

---

## Pseudo-label construction — the core assumption

Because there is no ground-truth "maximum potential" column, we construct a target
variable (pseudo-label) that represents our best estimate of the demand ceiling.

**Formula:**
```
pseudo_target = hist_p90_monthly
              × seasonality_multiplier_jan_2026
              × (jan_2026_trading_days / 22.0)
```

**Rationale:**
- `hist_p90_monthly` is the 90th percentile monthly volume — close to but more
  robust than the raw maximum.
- Multiplying by the January 2026 seasonality multiplier adjusts for the fact that
  January is more or less active depending on the distributor's region.
- Multiplying by the trading-day ratio adjusts for January having a different number
  of working days vs the average month.

**For outlets with no transaction history** (`has_transaction_history = False`),
the pseudo-label comes from `baseline.py`'s cold-start estimator. Exclude these
rows from the training set (they have no signal to learn from).

```python
df_train = df[df["has_transaction_history"] == True].copy()
df_train["target"] = (
    df_train["hist_p90_monthly"]
    * df_train["seasonality_multiplier_jan_2026"]
    * (df_train["jan_2026_trading_days"] / 22.0)
)
log.info("Training set: %d outlets (excluded %d with no transaction history)",
         len(df_train), (df["has_transaction_history"] == False).sum())
```

---

## Step-by-step logic

### Step 1 — Load data

```python
df = pd.read_parquet(GOLD / "master_features.parquet")
```

### Step 2 — Define feature columns

```python
# Exclude non-feature columns
EXCLUDE_COLS = [
    "Outlet_ID", "Outlet_Size", "Outlet_Type", "province",
    "seasonality_jan_2026", "distributor_id",
    "target",  # will be added
]

feature_cols = [c for c in df.columns if c not in EXCLUDE_COLS]
log.info("Training with %d features: %s", len(feature_cols), feature_cols)
```

Verify all `feature_cols` are numeric:
```python
non_numeric = df[feature_cols].select_dtypes(exclude=["number"]).columns.tolist()
if non_numeric:
    raise ValueError(f"Non-numeric feature columns found: {non_numeric}")
```

### Step 3 — Build training set and target

```python
df_train = df[
    (df["has_transaction_history"] == True) & 
    (df["exclude_from_training"] == False)
].copy()

df_train["target"] = (
    df_train["hist_p90_monthly"]
    * df_train["seasonality_multiplier_jan_2026"]
    * (df_train["jan_2026_trading_days"] / 22.0)
)

X = df_train[feature_cols]
y = df_train["target"]
log.info("Training target — min: %.2f, median: %.2f, max: %.2f",
         y.min(), y.median(), y.max())
```

### Step 4 — Cross-validation

Use 5-fold cross-validation (k from `config.yaml: modelling.cv_folds`).
Split on `Outlet_ID` (not time-based — this is a cross-sectional problem).

```python
from sklearn.model_selection import KFold
import lightgbm as lgb
import numpy as np

kf = KFold(
    n_splits=CFG["modelling"]["cv_folds"],
    shuffle=True,
    random_state=CFG["modelling"]["random_seed"],
)

cv_rmse_scores = []
cv_mae_scores  = []

for fold, (train_idx, val_idx) in enumerate(kf.split(X), 1):
    X_tr, X_val = X.iloc[train_idx], X.iloc[val_idx]
    y_tr, y_val = y.iloc[train_idx], y.iloc[val_idx]

    model = lgb.LGBMRegressor(**CFG["modelling"]["lgbm_params"],
                               random_state=CFG["modelling"]["random_seed"])
    model.fit(
        X_tr, y_tr,
        eval_set=[(X_val, y_val)],
        callbacks=[lgb.early_stopping(50, verbose=False),
                   lgb.log_evaluation(100)],
    )

    preds = model.predict(X_val)
    rmse  = np.sqrt(np.mean((preds - y_val) ** 2))
    mae   = np.mean(np.abs(preds - y_val))
    cv_rmse_scores.append(rmse)
    cv_mae_scores.append(mae)
    log.info("Fold %d — RMSE: %.2f  MAE: %.2f", fold, rmse, mae)

log.info("CV RMSE: %.2f ± %.2f", np.mean(cv_rmse_scores), np.std(cv_rmse_scores))
log.info("CV MAE : %.2f ± %.2f", np.mean(cv_mae_scores),  np.std(cv_mae_scores))
```

### Step 5 — Train final model on full training data

```python
final_model = lgb.LGBMRegressor(**CFG["modelling"]["lgbm_params"],
                                  random_state=CFG["modelling"]["random_seed"])
final_model.fit(X, y)
log.info("Final model trained on %d samples", len(X))
```

### Step 6 — Save model

```python
import pickle
from pathlib import Path

ARTIFACTS = Path(__file__).parent / "artifacts"
ARTIFACTS.mkdir(exist_ok=True)

with open(ARTIFACTS / "model.pkl", "wb") as f:
    pickle.dump({"model": final_model, "feature_cols": feature_cols}, f)
log.info("Model saved → modelling/artifacts/model.pkl")
```

### Step 7 — Feature importance plot

```python
import matplotlib.pyplot as plt

importance_df = pd.DataFrame({
    "feature":    feature_cols,
    "importance": final_model.feature_importances_,
}).sort_values("importance", ascending=False).head(30)

fig, ax = plt.subplots(figsize=(10, 12))
ax.barh(importance_df["feature"][::-1], importance_df["importance"][::-1])
ax.set_xlabel("Feature Importance (gain)")
ax.set_title("Top 30 Feature Importances — LightGBM")
plt.tight_layout()
plt.savefig(ARTIFACTS / "feature_importance.png", dpi=150)
plt.close()
log.info("Feature importance plot saved")
```

### Step 8 — Save CV results

```python
import json

cv_results = {
    "cv_folds":        CFG["modelling"]["cv_folds"],
    "cv_rmse_mean":    float(np.mean(cv_rmse_scores)),
    "cv_rmse_std":     float(np.std(cv_rmse_scores)),
    "cv_mae_mean":     float(np.mean(cv_mae_scores)),
    "cv_mae_std":      float(np.std(cv_mae_scores)),
    "n_features":      len(feature_cols),
    "n_train_samples": len(X),
}
with open(ARTIFACTS / "cv_results.json", "w") as f:
    json.dump(cv_results, f, indent=2)
```

---

## Assertions

```python
assert (ARTIFACTS / "model.pkl").exists()
# Spot-check: model can make predictions
sample = X.head(5)
preds  = final_model.predict(sample)
assert len(preds) == 5
assert all(p > 0 for p in preds), "Model predicting non-positive values"
```

---

## CLI usage

```bash
python modelling/train.py
```

## Dependencies

- pandas, numpy, pyarrow, pyyaml
- lightgbm
- scikit-learn (KFold)
- matplotlib
- Standard library: pickle, json, logging
