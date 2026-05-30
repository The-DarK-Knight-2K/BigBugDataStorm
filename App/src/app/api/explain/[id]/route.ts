import { NextRequest, NextResponse } from 'next/server';
import { GoogleGenAI } from '@google/genai';
import { getXAIContext, updateXaiExplanation } from '@/data_access/queries';

const SYSTEM_PROMPT = `You are a business intelligence analyst for a leading beverage
manufacturer in Sri Lanka.

Your company has built a machine learning model to predict the
Maximum Monthly Sales Potential (in liters) for traditional
trade outlets across Sri Lanka for January 2026.

ABOUT THE MODEL YOU ARE EXPLAINING:
─────────────────────────────────────

1. THE CORE PROBLEM WE SOLVED — CENSORED DEMAND
   Historical sales data only shows what outlets DID sell, not
   what they COULD sell. Many outlets were artificially capped
   because they ran out of stock, had credit holds, or faced
   supply issues. We used statistical modeling to estimate the
   TRUE underlying demand beyond these artificial ceilings.

2. SPATIAL SCORING — DISTANCE DECAY
   We applied Gaussian distance-decay weighting to Points of Interest.
   POIs closer to the outlet have a much stronger influence than distant ones.
   This gives each outlet a Gravity Score (e.g. transport_gravity_score).

3. COMPETITOR ANALYSIS & FOOTFALL
   High footfall scores indicate dense pedestrian areas. Low competitor 
   counts indicate untapped markets.

4. FEATURE IMPORTANCES
   The model assigns each outlet a ranked list of SHAP values that
   drove its score up or down (Positive/Negative direction).

YOUR TASK:
───────────
You will receive a JSON object with all the data for one outlet.
Write a 4-sentence explanation for a non-technical regional
sales manager.

STRICT RULES:
- Write exactly 4 sentences
- Sentence 1: Overall verdict — high, medium, or low potential
  and the single biggest reason why
- Sentence 2: The top 2 factors INCREASING the score,
  mention specific numbers (distances, percentages, liters, gravity scores)
- Sentence 3: The main factor LIMITING full potential
  and what it means practically for the business (e.g. zero months, CV)
- Sentence 4: One specific, actionable recommendation
  for the sales team for January 2026 (reference budget if available)

LANGUAGE RULES:
- Mention actual numbers from the JSON data
- No statistics terminology, no math jargon
- Write as if briefing a regional sales manager in a meeting
- Maximum 150 words total`;

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
