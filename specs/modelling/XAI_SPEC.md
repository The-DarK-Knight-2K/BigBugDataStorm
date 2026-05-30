# XAI Spec — Explainable AI Module

## Purpose

Transform the CatBoost model's SHAP-level technical output into a clear,
human-readable business narrative for each outlet. The explanation must be
accurate (grounded in real feature values and SHAP contributions), localised
(incorporating POI and geographic context), and non-technical (legible to a
field sales manager or a C-suite executive).

The XAI module has three components:

1. `pipeline/xai/context_packager.py` — assembles the structured context payload per outlet
2. `pipeline/xai/prompt_builder.py` — renders the context into the LLM prompt
3. `pipeline/xai/xai_service.py` (or Next.js API Route) — calls the LLM and returns the explanation

All three must be implemented by **Member A** in Phase 3 (with JSON data exports for the Next.js app). The endpoint spec is
defined in `specs/webapp/API_SPEC.md` (section 3).

---

## Step 1 — SHAP value extraction (during model training)

After `modelling/train.py` trains the final CatBoost model, extract SHAP values
for all 20,000 outlets immediately:

```python
import shap

explainer = shap.TreeExplainer(model)
shap_values = explainer.shap_values(X_all)   # X_all = all 20k outlets

shap_df = pd.DataFrame(shap_values, columns=X_all.columns)
shap_df.insert(0, "Outlet_ID", outlet_ids)
shap_df.to_parquet("data/gold/shap_values.parquet", index=False)
```

SHAP values are signed floats — positive means the feature pushed the prediction
up, negative means it pulled it down. The magnitude indicates contribution strength.

---

## Step 2 — Context packager

`pipeline/xai/context_packager.py` reads:
- `data/gold/shap_values.parquet`
- `data/gold/master_features.parquet`
- `data/gold/gravity_features.parquet`
- `data/gold/budget_features.parquet`
- `outputs/teamname_predictions.csv`

For a given `outlet_id`, it assembles a `context` dict that the prompt builder
consumes. This dict must be serialisable as JSON and stored in
`data/gold/xai_context.parquet` (one row per outlet, `context` stored as a
JSON string column).

### Context payload schema

```python
context = {
    # Outlet identity
    "outlet_id": "OUT_W_00042",
    "outlet_type": "Grocery",
    "outlet_size": "Medium",
    "province": "Western",
    "distributor_id": "DIST_W_01",

    # Prediction result
    "predicted_potential_litres": 1240.50,
    "current_avg_monthly_litres": 820.30,
    "uplift_gap_litres": 420.20,
    "uplift_gap_pct": 51.2,              # (gap / current) × 100

    # Top positive SHAP drivers — top 3 by absolute value, positive direction
    "top_positive_drivers": [
        {
            "feature": "transport_gravity_score",
            "shap_contribution_litres": 182.40,
            "feature_value": 8.75,
            "human_label": "Transit hub proximity",
            "human_description": "4 bus stops within 500m"
        },
        {
            "feature": "footfall_score",
            "shap_contribution_litres": 134.20,
            "feature_value": 67.40,
            "human_label": "Area footfall score",
            "human_description": "67.4 out of 100"
        },
        {
            "feature": "competition_density_score",
            "shap_contribution_litres": 98.10,
            "feature_value": 12.50,
            "human_label": "Low local competition",
            "human_description": "Only 2 competitors within 1km (isolated market)"
        }
    ],

    # Top negative SHAP drivers — top 2 by absolute value, negative direction
    "top_negative_drivers": [
        {
            "feature": "hist_cv",
            "shap_contribution_litres": -45.80,
            "feature_value": 0.137,
            "human_label": "Order volatility",
            "human_description": "Coefficient of variation: 0.14"
        },
        {
            "feature": "consecutive_zero_months_max",
            "shap_contribution_litres": -38.10,
            "feature_value": 2,
            "human_label": "Longest stockout gap",
            "human_description": "2 consecutive months with no orders"
        }
    ],

    # Seasonality and calendar context
    "seasonality_jan_2026": "Favorable",
    "seasonality_multiplier": 1.15,
    "jan_2026_trading_days": 20,

    # Budget context (null if not Western Province)
    "budget_allocation_lkr": 45000.00,
    "allocation_tier": "high",
    "recommended_spend_type": "cooler_grant"
}
```

### Feature-to-human-label mapping

Store this mapping in `config.yaml` under `xai.feature_labels`. It maps raw
feature names to the plain-English labels and description templates used above.

```yaml
xai:
  feature_labels:
    transport_gravity_score:
      label: "Transit hub proximity"
      template: "{count} bus stops within 500m"
      value_field: "transport_500m"
    footfall_score:
      label: "Area footfall score"
      template: "{value:.1f} out of 100"
    competition_density_score:
      label: "Low local competition"
      template: "Only {count} competitors within 1km"
      value_field: "competitors_1km"
    hist_cv:
      label: "Order volatility"
      template: "Coefficient of variation: {value:.2f}"
    consecutive_zero_months_max:
      label: "Longest stockout gap"
      template: "{value:.0f} consecutive months with no orders"
    cooler_count:
      label: "Cooler capacity"
      template: "{value:.0f} coolers on premises"
    school_gravity_score:
      label: "School proximity"
      template: "{count} schools within 500m"
      value_field: "schools_500m"
    yoy_growth_rate:
      label: "Year-on-year growth"
      template: "{value:.1%} growth vs prior year"
    recent_3m_avg:
      label: "Operating in an isolated local market with only 2 competitors within 1km."
```

---

## Step 3 — Prompt template

`pipeline/xai/prompt_builder.py` renders the context dict into the final prompt.
The prompt is designed to produce structured output that maps directly to the
API response shape.

### System prompt

```
You are a senior trade marketing analyst for a beverage manufacturer in Sri Lanka.
Your job is to explain, in plain business English, why a specific retail outlet
has been assigned its predicted monthly sales potential by our machine learning model.

You must write for a non-technical audience: field sales managers and regional
directors who understand trade concepts but have no data science background.
Do not mention SHAP values, model weights, or statistical terms.
Write in clear, direct sentences. Be specific about numbers and locations.
Do not speculate beyond what the data tells you.
```

### User prompt template

```
Explain the predicted sales potential for the following outlet.

OUTLET PROFILE:
- ID: {outlet_id}
- Type: {outlet_type} ({outlet_size})
- Province: {province}, served by {distributor_id}

PREDICTION:
- Predicted monthly potential: {predicted_potential_litres:.0f} litres
- Current average monthly volume: {current_avg_monthly_litres:.0f} litres
- Untapped gap: {uplift_gap_litres:.0f} litres ({uplift_gap_pct:.0f}% above current)

KEY FACTORS THAT INCREASED THE SCORE:
{positive_drivers_text}

KEY FACTORS THAT REDUCED THE SCORE:
{negative_drivers_text}

MARKET CONDITIONS FOR JANUARY 2026:
- Seasonality outlook: {seasonality_jan_2026} (multiplier: {seasonality_multiplier:.2f}x)
- Trading days in January: {jan_2026_trading_days}

BUDGET CONTEXT:
{budget_text}

Respond ONLY in the following JSON format — no markdown, no preamble:
{{
  "headline": "<one sentence summarising the main story>",
  "drivers_up": ["<sentence 1>", "<sentence 2>", "<sentence 3>"],
  "drivers_down": ["<sentence 1>", "<sentence 2>"],
  "local_context": "<one or two sentences about geographic and seasonal context>",
  "recommendation": "<one sentence on what action this outlet warrants>"
}}
```

### Template rendering helpers

```python
def render_drivers(drivers: list[dict]) -> str:
    lines = []
    for d in drivers:
        sign = "+" if d["shap_contribution_litres"] > 0 else ""
        lines.append(
            f"- {d['human_label']}: {d['human_description']} "
            f"(impact: {sign}{d['shap_contribution_litres']:.0f} L)"
        )
    return "\n".join(lines)

def render_budget(context: dict) -> str:
    if context["budget_allocation_lkr"] is None:
        return "This outlet is outside the Western Province and is not included in the current budget allocation cycle."
    return (
        f"This outlet has been allocated LKR {context['budget_allocation_lkr']:,.0f} "
        f"({context['allocation_tier'].upper()} tier) for trade marketing spend. "
        f"Recommended spend type: {context['recommended_spend_type'].replace('_', ' ')}."
    )
```

---

## Step 4 — LLM API call

This handles the live explanation generation. It calls the Google Gemini API
using the rendered prompt. Use `gemini-2.0-flash` — it is accurate enough for
this task, fast enough for interactive use, and has a generous free tier.

```python
import google.generativeai as genai
import os
import json
from datetime import datetime

genai.configure(api_key=os.environ["GOOGLE_API_KEY"])
model = genai.GenerativeModel("gemini-2.0-flash")

def generate_explanation(outlet_id: str) -> dict:
    context = load_context(outlet_id)           # from xai_context.parquet
    prompt = build_prompt(context)              # from prompt_builder.py

    response = model.generate_content(
        [SYSTEM_PROMPT, prompt],
        generation_config={"response_mime_type": "application/json"}
    )

    raw_text = response.text.strip()

    try:
        explanation = json.loads(raw_text)
    except json.JSONDecodeError:
        # Fallback: extract JSON block if the model added any preamble
        import re
        match = re.search(r"\{.*\}", raw_text, re.DOTALL)
        explanation = json.loads(match.group()) if match else {}

    return {
        "outlet_id": outlet_id,
        "explanation": explanation,
        "model_version": "catboost_r2_v1",
        "generated_at": datetime.utcnow().isoformat() + "Z",
    }
```

---

## Step 5 — Quality validation rules

Before returning the LLM response to the frontend, validate the following.
If any check fails, return a fallback structured explanation built directly
from the context dict without an LLM call.

| Check | Validation |
|-------|-----------|
| JSON parseable | `json.loads()` succeeds |
| `headline` present | Non-empty string |
| `drivers_up` present | List with 1–4 items |
| `drivers_down` present | List with 1–3 items |
| `local_context` present | Non-empty string |
| `recommendation` present | Non-empty string |
| No hallucinated numbers | Numbers in explanation are within ±5% of values in context dict |

The number hallucination check extracts all numeric tokens from the explanation
text and verifies each appears (approximately) in the context payload.

---

## Pre-generation strategy

Do not call the LLM for all 20,000 outlets upfront — that would cost ~$40+ and
take hours. Instead:

1. **Pre-generate for Western Province outlets only** (~6,842 outlets) during
   the pipeline run, since these are the ones the web app will most frequently
   display. Store results in `data/gold/xai_pregenerated.parquet`.
2. **Generate on-demand** for all other outlets when `GET /explain/{outlet_id}`
   is called. Cache the result in memory for the duration of the server session.

The pre-generation script is `pipeline/xai/pregenerate_western.py`:

```bash
python pipeline/xai/pregenerate_western.py
# Estimated runtime: ~35 minutes for 6,842 outlets at ~0.3s per call
```

---

## Fallback explanation (no LLM)

If the LLM call fails or validation fails, return this deterministic fallback
built from the context dict:

```python
def build_fallback_explanation(context: dict) -> dict:
    top_up = context["top_positive_drivers"][0]["human_label"]
    top_down = context["top_negative_drivers"][0]["human_label"] if context["top_negative_drivers"] else None

    return {
        "headline": (
            f"Predicted potential of {context['predicted_potential_litres']:.0f} L "
            f"is driven primarily by {top_up.lower()}."
        ),
        "drivers_up": [
            f"{d['human_label']}: {d['human_description']} "
            f"(+{d['shap_contribution_litres']:.0f} L)"
            for d in context["top_positive_drivers"]
        ],
        "drivers_down": [
            f"{d['human_label']}: {d['human_description']} "
            f"({d['shap_contribution_litres']:.0f} L)"
            for d in context["top_negative_drivers"]
        ] if context["top_negative_drivers"] else ["No significant negative factors identified."],
        "local_context": (
            f"This {context['outlet_type']} in {context['province']} Province "
            f"faces a {context['seasonality_jan_2026'].lower()} January outlook "
            f"with {context['jan_2026_trading_days']} trading days."
        ),
        "recommendation": (
            f"An untapped gap of {context['uplift_gap_litres']:.0f} L suggests "
            f"this outlet warrants {context.get('recommended_spend_type', 'investment').replace('_', ' ')}."
        )
    }
```
