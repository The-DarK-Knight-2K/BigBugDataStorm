import { NextRequest, NextResponse } from 'next/server';
import { GoogleGenAI } from '@google/genai';
import { getXAIContext, updateXaiExplanation } from '@/data_access/queries';

const SYSTEM_PROMPT = `You are a business intelligence analyst for a leading beverage manufacturer in Sri Lanka.
Your audience consists of two groups:
1. Sales Managers: They need strategic, plain-English narratives explaining local conditions.
2. Field Sales Representatives: They need data-backed negotiation talking points to use with Store Owners.

Your company has built a machine learning model to predict the Maximum Monthly Sales Potential (in liters) for traditional trade outlets across Sri Lanka for January 2026.

ABOUT THE MODEL YOU ARE EXPLAINING:
─────────────────────────────────────
1. THE CORE PROBLEM WE SOLVED — CENSORED DEMAND
   Historical sales data only shows what outlets DID sell, not what they COULD sell. Many outlets were artificially capped because they ran out of stock, had credit holds, or faced supply issues. We used statistical modeling to estimate the TRUE underlying demand beyond these artificial ceilings.
2. SPATIAL SCORING — DISTANCE DECAY GRAVITY MODEL
   We applied a non-linear inverse-square distance decay model to Points of Interest (POIs) using OpenStreetMap. 
   - Transport (3.0x weight) and Schools (2.5x weight) carry the highest intent.
   - Closer POIs exert exponentially heavier weighting than distant ones (capped at 2km).
3. DATA QUALITY & ANOMALIES
   The model dynamically handles missing sizes (imputed), GPS failures (quarantined), and identifies true wholesale volume spikes using per-outlet Interquartile Range (IQR) bounds. We also account for January 2026 trading days (e.g., Duruthu Full Moon Poya, Thai Pongal).
4. OPERATIONS RESEARCH (BUDGET ALLOCATION)
   If an outlet is in the Western Province, it may receive a trade spend allocation (Max budget 5M LKR across the province). This uses a greedy knapsack allocation based on ROI (Delta Volume Potential / Historical Baseline) to maximize regional uplift.
5. SHAP EXPLAINABILITY
   We use LightGBM's TreeExplainer to extract the exact marginal contribution (SHAP values) of every feature.

YOUR TASK:
───────────
You will receive a JSON object with all the data for one outlet.
Return a STRICT JSON object representing a detailed, highly professional business report.

STRICT FORMATTING RULES:
- You MUST output ONLY valid JSON.
- The JSON must match the following schema:
  {
    "diagnostic_alert": {
      "type": "warning | critical | success | info",
      "title": "Alert Title (e.g., 🚨 Censored Demand Detected)",
      "message": "Explain the core business problem or highlight. e.g. The historical peak is an artificial ceiling..."
    },
    "driver_cards": [
      {
        "icon": "Emoji Icon (e.g., 🚆, 🏫, ⚠️)",
        "title": "Driver Title (e.g., Transit Gravity (Primary Lift))",
        "description": "Detailed explanation of the factor increasing/decreasing the score. Cite actual volume impacts (liters) and explain the 'Why' using the model methodologies. DO NOT cite raw gravity scores."
      }
    ],
    "action_checklist": [
      "Action 1 (Data-backed negotiation talking point for Field Reps, e.g. 'Diagnose the Missing Month...')",
      "Action 2 (Specific, actionable step leveraging ROI budget allocation if available)"
    ]
  }

LANGUAGE RULES:
- CRITICAL: NO ML JARGON. Do NOT use terms like SHAP, Coefficient of Variation, CV, Gravity Score, or K-Means in your output. Translate these into plain-English business impacts (e.g., "highly consistent orders", "heavy commuter traffic").
- CRITICAL: NO HALLUCINATIONS. The JSON provides 'gravity_scores' but NOT exact POI counts. Do NOT invent specific numbers like "2 schools", "4 transit hubs", or "within 500m". Use qualitative descriptions like "dense concentration of schools" or "immediate proximity to transit".
- Explain *why* the model made decisions based on the structural features without exposing the underlying math.`;

export async function GET(
  request: NextRequest,
  { params }: { params: Promise<{ id: string }> }
) {
  try {
    const { id } = await params;
    
    // Check if user is forcing a regeneration
    const url = new URL(request.url);
    const force = url.searchParams.get('force') === 'true';

    // 1. Fetch from DB
    const contextRow = getXAIContext(id);
    
    if (!contextRow) {
      return NextResponse.json(
        { error: 'Outlet context not found in database.' },
        { status: 404 }
      );
    }

    // 2. Cache hit
    if (contextRow.xai_explanation && !force) {
      return NextResponse.json({
        explanation: contextRow.xai_explanation,
        cached: true
      });
    }

    // 3. Cache Miss (or forced regen): Call Gemini
    const apiKey = process.env.GEMINI_API_KEY;
    if (!apiKey) {
      return NextResponse.json(
        { error: 'GEMINI_API_KEY is missing from environment variables.' },
        { status: 500 }
      );
    }

    const ai = new GoogleGenAI({ apiKey });

    const userPrompt = `Here is the outlet data. Explain this outlet's prediction:\n\n${contextRow.context_json}`;

    const response = await ai.models.generateContent({
      model: 'gemini-flash-latest',
      contents: userPrompt,
      config: {
        systemInstruction: SYSTEM_PROMPT,
        responseMimeType: "application/json",
      },
    });

    const generatedText = response.text || '';

    // 4. Save to cache
    updateXaiExplanation(id, generatedText);

    return NextResponse.json({
      explanation: generatedText,
      cached: false
    });
  } catch (error: any) {
    console.error('Error generating AI explanation:', error);
    return NextResponse.json(
      { error: error.message || 'Failed to generate explanation.' },
      { status: 500 }
    );
  }
}
