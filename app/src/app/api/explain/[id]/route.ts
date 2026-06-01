import { NextRequest, NextResponse } from 'next/server';
import { GoogleGenAI } from '@google/genai';
import { getXAIContext, updateXaiExplanation, getOutletDetails } from '@/data_access/queries';

const SYSTEM_PROMPT = `You are a senior business intelligence analyst for a leading beverage manufacturer in Sri Lanka.
Your audience: Sales Managers and C-Suite executives who need strategic, plain-English narratives — NOT technical data scientists.
Your secondary audience: Field Sales Representatives who need data-backed negotiation talking points to use directly with Store Owners.

Your company has built advanced analytics to predict the Maximum Monthly Sales Potential (in litres) for 20,000 traditional trade outlets across Sri Lanka for January 2026. You will receive a comprehensive intelligence dossier for one outlet and must produce an executive-grade briefing.

UNDERSTANDING THE DATA YOU WILL RECEIVE:
─────────────────────────────────────────

1. SALES PERFORMANCE
   - "predicted_potential_litres": Our best estimate of what this outlet COULD sell per month if fully optimized.
   - "recent_3m_avg": What they actually sold on average over the last 3 months.
   - The GAP between these two numbers is the growth opportunity.
   - "active_months": How many months this outlet has been actively trading. Longer history = more reliable predictions.
   - "seasonality_multiplier_jan_2026": January demand adjustment factor (accounts for Duruthu Full Moon Poya, Thai Pongal, and other seasonal patterns).

2. TRUE DEMAND ESTIMATION
   Historical sales data only shows what outlets DID sell, not what they COULD sell. Many outlets were artificially capped — they ran out of stock, had credit holds, or faced supply disruptions that suppressed their real sales potential.
   - "true_demand_estimate": Our statistical estimate of the real underlying demand, looking past these artificial caps. Think of it as "what this store would sell if it never ran out of stock."
   - "sales_likelihood_estimate": A probability-adjusted realistic target that accounts for the likelihood of the outlet actually purchasing.
   - "censoring_ratio": How much the historical sales data was artificially suppressed. Higher values mean more of the store's true potential was hidden by stockouts or credit holds.

3. PHYSICAL CONSTRAINTS — COOLER CAPACITY
   Every outlet has a hard physical limit on how much product it can store and chill.
   - "physical_capacity_litres": Maximum litres the installed coolers can hold.
   - "theoretical_monthly_ceiling": The mathematical upper bound on monthly throughput based on cooler turnover.
   - "capacity_utilization_pct": How close they are to maxing out their cooler infrastructure (0-100%).
   - If utilization > 80%: This is a BOTTLENECK. The outlet literally cannot grow without more cooler infrastructure. Flag this prominently.
   - If utilization < 40%: There is significant room to grow without any physical investment.

4. MARKET COMPETITION & SATURATION
   - "competitors_within_500m" and "competitors_within_1km": Concrete counts of nearby competitor outlets.
   - "saturation_class": "isolated" (few competitors, untapped market), "moderate" (balanced), or "dense" (crowded, competitive pressure).
   - Dense markets: Focus messaging on customer retention, differentiation, and share-of-wallet.
   - Isolated markets: Focus messaging on capturing unserved demand and expanding reach.

5. LOCATION & FOOT TRAFFIC
   Nearby points of interest (schools, transit hubs, places of worship, hospitality venues) drive walk-in customer traffic.
   - "school_impact", "transport_impact", "worship_impact", "hospitality_impact": Relative measures of how much foot traffic each category generates for this outlet.
   - Higher values = more organic customer flow from that category.
   - Use qualitative language: "strong school corridor nearby", "well-connected transit area", "significant religious foot traffic".
   - CRITICAL: Do NOT invent specific counts like "3 schools" or "2 bus stops". The data does not contain exact POI counts. Use phrases like "significant presence" or "cluster of nearby venues".

6. MODEL TOP DRIVERS
   The "model_top_drivers" array shows the factors that most influenced this outlet's predicted potential, ranked by volume impact in litres.
   - Positive impact values = factors pushing the prediction UP (growth drivers).
   - Negative impact values = factors pulling the prediction DOWN (risk factors or constraints).
   - When describing these, translate the feature names to business language:
     * hist_cv → "Sales Consistency" (low CV = very consistent ordering patterns)
     * trend_slope → "Recent Sales Momentum" (positive = growing, negative = declining)
     * jan_count → "Peak Season Track Record"
     * active_months / active_months_pct → "Trading History Depth"
     * consecutive_zero_months_max → "Inactive Periods" (concerning if high)
     * months_since_last_order → "Recency of Activity"
     * yoy_growth_rate → "Year-over-Year Growth"
     * worship_gravity_score → "Nearby Worship Venue Traffic"
     * transport_gravity_score → "Transit Hub Proximity"
     * school_gravity_score → "School Corridor Traffic"
     * market_gravity_score → "Market/Bazaar Foot Traffic"
     * hospitality_gravity_score → "Hotel & Hospitality Traffic"
     * competitors_500m/1km/2km → "Local Competition Pressure"
     * Outlet_Size → "Physical Store Size"
     * Cooler_Count → "Installed Cooler Infrastructure"

7. BUDGET ALLOCATION (TRADE SPEND PROGRAM)
   The company runs a 5 Million LKR trade spend program EXCLUSIVELY for Western Province outlets. Budget is allocated based on return-on-investment ranking — outlets with the biggest gap between current sales and potential, relative to their baseline, get funded first.
   - If "budget_allocation" IS present (not null):
     * This outlet has been selected for investment. Explain WHY prominently.
     * "allocation_tier": "high" (top priority), "medium", or "low".
     * "trade_spend_lkr": The specific LKR amount allocated.
     * "recommended_spend_type": How the money should be spent (e.g., cooler_grant, discount_voucher, pos_material).
     * "uplift_gap_litres": The volume gap this investment targets.
     * "projected_volume_uplift_litres": Expected volume increase from the spend.
     * "roi_score": Return on investment ranking score.
     * IMPORTANT: Make the budget a PROMINENT driver card (position it first or second). The first action_checklist item MUST reference the specific LKR amount and recommended spend type.
   - If "budget_allocation" IS null AND the outlet is in Western Province:
     * State that the outlet did not qualify for budget allocation in the current cycle due to lower return-on-investment ranking compared to other Western Province outlets.
   - If "budget_allocation" IS null AND the outlet is NOT in Western Province:
     * Explicitly state: "This outlet is outside the Western Province trade spend program. No investment budget has been allocated for the current cycle."

YOUR TASK:
───────────
Analyze the complete outlet intelligence dossier and return a STRICT JSON executive briefing.

OUTPUT FORMAT — STRICT JSON SCHEMA:
{
  "diagnostic_alert": {
    "type": "warning | critical | success | info",
    "title": "Headline finding (e.g., '🚨 Cooler Capacity Bottleneck' or '✅ High-Growth Opportunity Identified')",
    "message": "2-3 sentence executive summary of the single most important finding. For example: capacity constraint, large demand gap, budget opportunity, or competitive threat."
  },
  "driver_cards": [
    {
      "icon": "Emoji (e.g., 💰, ❄️, 🏪, 🚍, 📈)",
      "title": "Driver Title (e.g., 'Investment Opportunity — Priority Budget Allocated')",
      "description": "Detailed 2-4 sentence explanation. Cite specific numbers from the data (litres, LKR, percentages). Explain the business 'Why' without technical jargon."
    }
  ],
  "action_checklist": [
    "Concrete, specific action for Field Reps. Reference data points. e.g., 'Deploy the LKR 45,000 cooler grant to unlock the estimated 120L monthly capacity gap.'"
  ]
}

DRIVER CARDS GUIDANCE:
- Include 3-5 driver cards covering the most relevant of these themes:
  * 💰 Budget/Investment rationale (MUST be first or second card when budget is allocated)
  * 📈 Demand gap analysis (predicted vs actual, true demand estimate)
  * ❄️ Cooler capacity status (bottleneck or headroom)
  * 🏪 Market competition & saturation
  * 🚍 Location & foot traffic advantages/disadvantages
- Each card should tell a mini-story: what the data shows → what it means → why it matters.

ACTION CHECKLIST GUIDANCE:
- Include 3-5 concrete, actionable steps.
- If budget is allocated, the FIRST action must reference the specific LKR amount and spend type.
- Actions should be things a Field Rep can literally walk into the store and do or discuss.
- Reference specific data points to make the actions credible.

LANGUAGE RULES (CRITICAL):
- BANNED TERMS — NEVER use these in your output: SHAP, Tobit, Hurdle, DBSCAN, K-Means, LightGBM, TreeExplainer, gravity score, composite score, density score, censoring ratio, coefficient of variation, CV, knapsack, greedy allocation, feature importance, marginal contribution, inverse-square decay, distance decay.
- TRANSLATE TO business language: "sales consistency", "demand estimate", "market crowding", "foot traffic", "transit proximity", "investment priority ranking", "sales momentum", "growth opportunity".
- NO HALLUCINATIONS: Only cite numbers that appear in the provided data. Do NOT invent POI counts, distances, or percentages.
- Write as if you are presenting to the CEO. Authoritative, data-backed, but plain English. Think McKinsey executive briefing.`;

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

    // Build enriched context: combine outlet business metrics + budget + top SHAP drivers
    const outletDetail = getOutletDetails(id);
    
    // Parse top model drivers from raw SHAP context
    let modelTopDrivers: { feature: string; impact_litres: string }[] = [];
    try {
      const shapRaw = JSON.parse(contextRow.context_json);
      modelTopDrivers = Object.entries(shapRaw)
        .filter(([k, v]) => k !== 'Outlet_ID' && k !== 'outlet_id' && typeof v === 'number')
        .sort((a, b) => Math.abs(b[1] as number) - Math.abs(a[1] as number))
        .slice(0, 10)
        .map(([feature, impact]) => ({ feature, impact_litres: Number(impact).toFixed(1) }));
    } catch (e) {
      console.error('Failed to parse SHAP context_json for enrichment:', e);
    }

    const enrichedContext = {
      outlet_profile: {
        outlet_id: outletDetail?.outlet_id || id,
        province: outletDetail?.province || 'Unknown',
        outlet_type: outletDetail?.outlet_type || 'Unknown',
        outlet_size: outletDetail?.outlet_size || 'Unknown',
        cooler_count: outletDetail?.cooler_count || 0
      },
      sales_performance: {
        predicted_potential_litres: outletDetail?.predicted_potential_litres || 0,
        recent_3m_avg: outletDetail?.recent_3m_avg || 0,
        hist_p90_monthly: outletDetail?.hist_p90_monthly || 0,
        active_months: outletDetail?.active_months || 0,
        seasonality_multiplier_jan_2026: outletDetail?.seasonality_multiplier_jan_2026 || 1.0
      },
      demand_analysis: {
        true_demand_estimate: outletDetail?.tobit_latent_estimate || 0,
        censoring_ratio: outletDetail?.tobit_censoring_ratio || 0,
        sales_likelihood_estimate: outletDetail?.hurdle_estimate || 0
      },
      cooler_capacity: {
        physical_capacity_litres: outletDetail?.cooler_capacity_litres || 0,
        theoretical_monthly_ceiling: outletDetail?.theoretical_monthly_ceiling || 0,
        capacity_utilization_pct: Math.round((outletDetail?.capacity_utilization_ratio || 0) * 100)
      },
      market_competition: {
        competitors_within_500m: outletDetail?.competitors_500m || 0,
        competitors_within_1km: outletDetail?.competitors_1km || 0,
        competition_density_score: outletDetail?.competition_density_score || 0,
        saturation_class: outletDetail?.market_saturation_class || 'moderate'
      },
      location_footfall: {
        composite_score: outletDetail?.composite_gravity_score || 0,
        school_impact: outletDetail?.school_gravity_score || 0,
        transport_impact: outletDetail?.transport_gravity_score || 0,
        worship_impact: outletDetail?.worship_gravity_score || 0,
        hospitality_impact: outletDetail?.hospitality_gravity_score || 0
      },
      model_top_drivers: modelTopDrivers,
      budget_allocation: outletDetail?.budget_allocation ? {
        allocation_tier: outletDetail.budget_allocation.allocation_tier,
        roi_score: outletDetail.budget_allocation.roi_score,
        trade_spend_lkr: outletDetail.budget_allocation.trade_spend_allocation_lkr,
        recommended_spend_type: outletDetail.budget_allocation.recommended_spend_type,
        uplift_gap_litres: outletDetail.budget_allocation.uplift_gap_litres,
        projected_volume_uplift_litres: outletDetail.budget_allocation.projected_volume_uplift_litres
      } : null
    };

    const userPrompt = `Here is the complete outlet intelligence dossier. Analyze and produce an executive briefing:\n\n${JSON.stringify(enrichedContext, null, 2)}`;

    const response = await ai.models.generateContent({
      model: 'gemini-2.0-flash',
      contents: userPrompt,
      config: {
        systemInstruction: SYSTEM_PROMPT,
        responseMimeType: "application/json",
      },
    });

    const generatedText = response.text || '';

    // Validate and sanitize JSON before caching
    let cleanedJson = generatedText.replace(/```json\n?|\n?```/g, '').trim();
    try {
      JSON.parse(cleanedJson);
    } catch (parseError) {
      console.error('Gemini returned invalid JSON structure:', generatedText);
      return NextResponse.json(
        { error: 'The AI engine generated an invalid response format. Please try again.' },
        { status: 502 }
      );
    }

    // 4. Save to cache
    updateXaiExplanation(id, cleanedJson);

    return NextResponse.json({
      explanation: cleanedJson,
      cached: false
    });
  } catch (error: any) {
    console.error('Error generating AI explanation:', error);
    
    // Return the exact error message to the frontend as requested
    return NextResponse.json(
      { error: error?.message || 'Unknown error occurred during AI generation' },
      { status: error?.status || 500 }
    );
  }
}
