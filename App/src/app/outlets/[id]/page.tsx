"use client";

import { useState, use, useMemo } from 'react';
import Link from 'next/link';
import { mockOutletDetails } from '@/lib/mockData';
import { ResponsiveContainer, BarChart, Bar, XAxis, YAxis, Tooltip, Cell, ReferenceLine } from 'recharts';

export default function OutletDetailPage({ params }: { params: Promise<{ id: string }> }) {
  const { id } = use(params);

  // Fetch or synthesize detailed data for the outlet
  const outlet = useMemo(() => {
    const data = mockOutletDetails[id];
    if (data) return data;

    // Build synthetic fallback data if user navigates to an ID not explicitly in our detailed mock dataset
    return {
      outlet_id: id,
      province: "Western",
      distributor_id: "DIST_W_01",
      outlet_type: "Grocery",
      outlet_size: "Medium",
      cooler_count: 1,
      latitude: 6.9271,
      longitude: 79.8612,
      prediction: {
        uplift_gap_litres: 150.0,
        seasonality_jan_2026: "Moderate",
        jan_2026_trading_days: 20,
        jan_2026_holiday_count: 2,
        Maximum_Monthly_Liters: 850.0,
        recent_3m_avg: 700.0,
        seasonality_multiplier_jan_2026: 1.0
      },
      sales_history: {
        hist_max_monthly: 900.0,
        hist_p90_monthly: 820.0,
        hist_mean_monthly: 700.0,
        hist_std_monthly: 80.0,
        hist_cv: 0.114,
        active_months: 24,
        consecutive_zero_months_max: 1,
        months_since_last_order: 1
      },
      poi_features: {
        footfall_score: 55.4,
        poi_data_available: true
      },
      gravity_features: {
        school_gravity_score: 1.5,
        hospital_gravity_score: 0.5,
        transport_gravity_score: 3.2,
        market_gravity_score: 1.1,
        worship_gravity_score: 1.0,
        hospitality_gravity_score: 1.2,
        composite_gravity_score: 45.2
      },
      shap_values: [
        { "feature": "transport_gravity_score", "shap_value": 75.4, "direction": "positive", "feature_value": 3.2 },
        { "feature": "footfall_score", "shap_value": 48.2, "direction": "positive", "feature_value": 55.4 },
        { "feature": "hist_cv", "shap_value": -15.1, "direction": "negative", "feature_value": 0.114 },
        { "feature": "consecutive_zero_months_max", "shap_value": -12.4, "direction": "negative", "feature_value": 1 }
      ],
      budget: null
    };
  }, [id]);

  // Dynamic interactive simulation state for the Gemini XAI Generator
  const [xaiLoading, setXaiLoading] = useState(false);
  const [xaiExplanation, setXaiExplanation] = useState<string | null>(null);

  const generateXaiInsight = () => {
    setXaiLoading(true);
    // Simulate Gemini API processing lag
    setTimeout(() => {
      let mockText = "";
      if (id === "OUT_W_00042") {
        mockText = "This Western Province Grocery is designated as a High Potential target due to high pedestrian transit access. The model predicts a high monthly volume of 1,240.5 L, driven by a transport gravity score of 8.75 and a footfall score of 67.4. However, historical demand variability (CV: 0.137) and two consecutive zero-volume months represent minor risks to this projection. We strongly recommend allocating a High Tier cooler grant of 45,000 LKR to fully resolve physical capacity constraints and unlock the 420.2 L uplift.";
      } else if (id === "OUT_C_01022") {
        mockText = "This Central Province Grocery displays Moderate overall potential with a maximum predicted ceiling of 960 L. Solid underlying demand is indicated by a historical P90 volume of 820 L, though transit access is moderate (gravity score: 4.32). Volume is significantly limited by three consecutive zero-volume months in the history, indicating a recurring supply chain bottleneck. The sales team should prioritize correcting distributor delivery schedules before allocating trade spends.";
      } else {
        mockText = `This ${outlet.province} ${outlet.outlet_type} represents a solid target with a predicted maximum potential of ${outlet.prediction.Maximum_Monthly_Liters} L. Demand is actively driven by favorable local POI access, including a composite gravity score of ${outlet.gravity_features.composite_gravity_score}. However, a standard order gap of ${outlet.sales_history.months_since_last_order} months indicates subtle distribution friction that slightly caps the baseline performance. We recommend utilizing promotional trade spends to incentivize ordering consistency for January 2026.`;
      }
      setXaiExplanation(mockText);
      setXaiLoading(false);
    }, 1800);
  };

  // Recharts custom label mapping for readability
  const chartData = useMemo(() => {
    return outlet.shap_values.map(v => ({
      name: v.feature.replace(/_/, ' ').replace(/score/, '').trim(),
      val: v.shap_value,
      orig: v.feature_value
    }));
  }, [outlet]);

  return (
    <div className="space-y-8 animate-fade-in">
      {/* Header breadcrumb & back button */}
      <div>
        <Link 
          href="/" 
          className="inline-flex items-center gap-2 text-xs text-slate-400 hover:text-cyan-400 transition-colors uppercase tracking-widest font-semibold"
        >
          &larr; Back to Dashboard
        </Link>
      </div>

      {/* Hero Profile Panel */}
      <div className="glass-panel p-8 rounded-2xl flex flex-col md:flex-row justify-between gap-6 border-slate-800">
        <div className="space-y-3">
          <div className="flex flex-wrap items-center gap-3">
            <span className="text-2xl">🏪</span>
            <h2 className="font-heading font-extrabold text-3xl tracking-tight text-white">{outlet.outlet_id}</h2>
            <span className={`px-2.5 py-0.5 rounded-full text-[10px] font-extrabold tracking-wider uppercase ${
              outlet.budget?.allocation_tier === 'high' ? 'bg-emerald-500/20 text-emerald-400 border border-emerald-500/30' :
              outlet.budget?.allocation_tier === 'medium' ? 'bg-amber-500/20 text-amber-400 border border-amber-500/30' :
              outlet.budget?.allocation_tier === 'low' ? 'bg-rose-500/20 text-rose-400 border border-rose-500/30' :
              'bg-slate-800 text-slate-400 border border-slate-700/50'
            }`}>
              Tier: {outlet.budget?.allocation_tier || 'NO ALLOCATION'}
            </span>
          </div>
          <div className="grid grid-cols-2 md:grid-cols-4 gap-y-2 gap-x-8 text-sm">
            <p className="text-slate-400">Province: <span className="text-white font-semibold">{outlet.province}</span></p>
            <p className="text-slate-400">Type: <span className="text-white font-semibold">{outlet.outlet_type}</span></p>
            <p className="text-slate-400">Distributor: <span className="text-white font-semibold font-mono">{outlet.distributor_id}</span></p>
            <p className="text-slate-400">Size: <span className="text-white font-semibold">{outlet.outlet_size}</span></p>
          </div>
        </div>

        <div className="flex items-center md:justify-end gap-3 shrink-0">
          <div className="px-4 py-2.5 rounded-xl bg-slate-900/80 border border-slate-800 text-right">
            <span className="block text-[9px] uppercase font-bold text-slate-500 tracking-widest leading-none">Coolers</span>
            <span className="text-lg font-bold font-mono text-white mt-1 block">{outlet.cooler_count} Installed</span>
          </div>
          <div className="px-4 py-2.5 rounded-xl bg-slate-900/80 border border-slate-800 text-right">
            <span className="block text-[9px] uppercase font-bold text-slate-500 tracking-widest leading-none">Coords</span>
            <span className="text-xs font-semibold font-mono text-cyan-400 mt-1.5 block">
              {outlet.latitude.toFixed(4)}, {outlet.longitude.toFixed(4)}
            </span>
          </div>
        </div>
      </div>

      {/* Metrics Cards Grid */}
      <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-6">
        {/* Maximum monthly litres */}
        <div className="glass-panel p-6 rounded-2xl relative overflow-hidden group hover:border-slate-700 transition-colors">
          <p className="text-xs font-semibold uppercase tracking-wider text-slate-400">Max monthly potential</p>
          <p className="text-3xl font-heading font-extrabold text-white mt-2">
            {Math.round(outlet.prediction.Maximum_Monthly_Liters).toLocaleString()} <span className="text-xs text-slate-400">L</span>
          </p>
          <div className="text-[10px] text-slate-400 mt-2 font-mono flex items-center gap-1">
            <span>Multiplier:</span>
            <span className="text-cyan-400 font-bold">{outlet.prediction.seasonality_multiplier_jan_2026}x</span>
            <span>({outlet.prediction.seasonality_jan_2026})</span>
          </div>
        </div>

        {/* Recent 3m avg */}
        <div className="glass-panel p-6 rounded-2xl relative overflow-hidden group hover:border-slate-700 transition-colors">
          <p className="text-xs font-semibold uppercase tracking-wider text-slate-400">Recent 3M average</p>
          <p className="text-3xl font-heading font-extrabold text-white mt-2">
            {Math.round(outlet.prediction.recent_3m_avg).toLocaleString()} <span className="text-xs text-slate-400">L</span>
          </p>
          <div className="text-[10px] text-slate-400 mt-2 font-mono flex items-center gap-1">
            <span>Active Months:</span>
            <span className="text-slate-300 font-bold">{outlet.sales_history.active_months}m</span>
          </div>
        </div>

        {/* Uplift gap */}
        <div className="glass-panel p-6 rounded-2xl relative overflow-hidden group hover:border-slate-700 transition-colors">
          <p className="text-xs font-semibold uppercase tracking-wider text-slate-400">Uplift volume gap</p>
          <p className="text-3xl font-heading font-extrabold text-emerald-400 text-glow-emerald mt-2">
            {outlet.prediction.uplift_gap_litres ? `${Math.round(outlet.prediction.uplift_gap_litres).toLocaleString()} L` : '0 L'}
          </p>
          <div className="text-[10px] text-slate-400 mt-2 font-mono flex items-center gap-1">
            <span>Growth Space:</span>
            <span className="text-emerald-400 font-bold">
              {outlet.prediction.uplift_gap_litres ? `+${Math.round((outlet.prediction.uplift_gap_litres / outlet.prediction.recent_3m_avg) * 100)}%` : '0%'}
            </span>
          </div>
        </div>

        {/* Composite gravity score */}
        <div className="glass-panel p-6 rounded-2xl relative overflow-hidden group hover:border-slate-700 transition-colors">
          <p className="text-xs font-semibold uppercase tracking-wider text-slate-400">Composite gravity score</p>
          <p className="text-3xl font-heading font-extrabold text-violet-400 mt-2">
            {outlet.gravity_features.composite_gravity_score.toFixed(1)}
          </p>
          <div className="text-[10px] text-slate-400 mt-2 font-mono flex items-center gap-1">
            <span>Footfall Score:</span>
            <span className="text-violet-400 font-bold">{outlet.poi_features.footfall_score.toFixed(1)}</span>
          </div>
        </div>
      </div>

      {/* SHAP Chart & spatial scores */}
      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
        {/* SHAP impact chart panel */}
        <div className="glass-panel p-6 rounded-2xl border border-slate-800 lg:col-span-2 space-y-4">
          <div>
            <h3 className="font-heading font-bold text-lg text-white">SHAP Prediction Drivers Impact</h3>
            <p className="text-slate-400 text-[11px] mt-0.5">Quantifying the impact of model features pushing the volume prediction up or down.</p>
          </div>
          <div className="h-[280px] w-full text-xs">
            <ResponsiveContainer width="100%" height="100%">
              <BarChart
                data={chartData}
                layout="vertical"
                margin={{ top: 10, right: 30, left: 40, bottom: 5 }}
              >
                <XAxis type="number" stroke="#94a3b8" fontSize={10} tickLine={false} />
                <YAxis 
                  dataKey="name" 
                  type="category" 
                  stroke="#94a3b8" 
                  fontSize={10} 
                  tickLine={false} 
                  width={120} 
                />
                <Tooltip
                  content={({ active, payload }) => {
                    if (active && payload && payload.length) {
                      const data = payload[0].payload;
                      return (
                        <div className="bg-slate-900 border border-slate-800 p-2.5 rounded-lg shadow-xl text-[11px]">
                          <p className="font-bold text-white uppercase">{data.name}</p>
                          <p className="text-slate-300 mt-1">Impact Value: <span className="font-bold font-mono text-white">{data.val > 0 ? '+' : ''}{data.val} L</span></p>
                          <p className="text-slate-400">Feature Value: <span className="font-mono text-slate-300">{data.orig}</span></p>
                        </div>
                      );
                    }
                    return null;
                  }}
                />
                <ReferenceLine x={0} stroke="#475569" strokeDasharray="3 3" />
                <Bar dataKey="val">
                  {chartData.map((entry, index) => (
                    <Cell 
                      key={`cell-${index}`} 
                      fill={entry.val >= 0 ? 'url(#greenGradient)' : 'url(#redGradient)'} 
                    />
                  ))}
                </Bar>
                <defs>
                  <linearGradient id="greenGradient" x1="0" y1="0" x2="1" y2="0">
                    <stop offset="0%" stopColor="#059669" stopOpacity={0.8} />
                    <stop offset="100%" stopColor="#10b981" stopOpacity={0.9} />
                  </linearGradient>
                  <linearGradient id="redGradient" x1="1" y1="0" x2="0" y2="0">
                    <stop offset="0%" stopColor="#b91c1c" stopOpacity={0.8} />
                    <stop offset="100%" stopColor="#f43f5e" stopOpacity={0.9} />
                  </linearGradient>
                </defs>
              </BarChart>
            </ResponsiveContainer>
          </div>
        </div>

        {/* Spatial scores panel */}
        <div className="glass-panel p-6 rounded-2xl border border-slate-800 flex flex-col justify-between">
          <div className="space-y-4">
            <div>
              <h3 className="font-heading font-bold text-lg text-white">Spatial Analysis Scorecard</h3>
              <p className="text-slate-400 text-[11px] mt-0.5">POI Distance Decay Gravity calculations.</p>
            </div>
            
            <div className="space-y-3 font-mono text-xs">
              {/* Transport Gravity */}
              <div className="p-3 rounded-xl bg-slate-900/60 border border-slate-800 flex justify-between items-center">
                <span className="text-slate-400">🚍 Transport Gravity</span>
                <span className="text-white font-bold text-sm">{outlet.gravity_features.transport_gravity_score.toFixed(2)}</span>
              </div>

              {/* School Gravity */}
              <div className="p-3 rounded-xl bg-slate-900/60 border border-slate-800 flex justify-between items-center">
                <span className="text-slate-400">🏫 School Gravity</span>
                <span className="text-white font-bold text-sm">{outlet.gravity_features.school_gravity_score.toFixed(2)}</span>
              </div>

              {/* Worship Gravity */}
              <div className="p-3 rounded-xl bg-slate-900/60 border border-slate-800 flex justify-between items-center">
                <span className="text-slate-400">🛕 Worship Gravity</span>
                <span className="text-white font-bold text-sm">{outlet.gravity_features.worship_gravity_score.toFixed(2)}</span>
              </div>

              {/* Hospitality Gravity */}
              <div className="p-3 rounded-xl bg-slate-900/60 border border-slate-800 flex justify-between items-center">
                <span className="text-slate-400">🏨 Hospitality Gravity</span>
                <span className="text-white font-bold text-sm">{outlet.gravity_features.hospitality_gravity_score.toFixed(2)}</span>
              </div>
            </div>
          </div>

          <div className="text-[10px] text-slate-500 font-sans italic border-t border-slate-800/60 pt-3 mt-4">
            💡 Gravity scores calculated via distance decay algorithm. Closer features carry exponentially heavier weighting.
          </div>
        </div>
      </div>

      {/* Business XAI explanation & budget allocation */}
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
        {/* Business XAI block */}
        <div className="glass-panel p-8 rounded-2xl border border-slate-800/80 flex flex-col justify-between min-h-[300px]">
          <div>
            <div className="flex items-center justify-between">
              <h3 className="font-heading font-bold text-xl text-white flex items-center gap-2">
                🤖 AI-Powered Explanations
              </h3>
              <span className="text-[9px] bg-cyan-500/20 text-cyan-400 px-2 py-0.5 rounded font-mono uppercase tracking-wider">Gemini 2.0 Flash</span>
            </div>
            <p className="text-slate-400 text-xs mt-1">Generate dynamic, non-technical briefings detailing models prediction drivers.</p>
          </div>

          {/* Dynamic Content state */}
          <div className="my-6 flex-1 flex items-center justify-center">
            {xaiLoading ? (
              <div className="flex flex-col items-center gap-3">
                <div className="w-10 h-10 rounded-full border-4 border-cyan-500 border-t-transparent animate-spin"></div>
                <p className="text-xs text-slate-400 font-mono animate-pulse">Invoking Gemini model. Compiling context JSON...</p>
              </div>
            ) : xaiExplanation ? (
              <div className="bg-slate-900/50 rounded-xl border border-slate-800/60 p-5 space-y-3 leading-relaxed text-sm text-slate-200">
                <p className="font-sans text-[13px]">{xaiExplanation}</p>
                <div className="flex justify-end pt-1">
                  <span className="text-[9px] font-mono text-emerald-400">✓ Cached securely in SQLite local database</span>
                </div>
              </div>
            ) : (
              <div className="text-center space-y-2">
                <p className="text-sm text-slate-500">No cached explanation found for this outlet.</p>
                <p className="text-xs text-slate-600">First-time generation requires calling the model on-demand.</p>
              </div>
            )}
          </div>

          {/* Action button */}
          {!xaiExplanation && !xaiLoading && (
            <button
              onClick={generateXaiInsight}
              className="w-full py-3.5 rounded-xl bg-gradient-to-r from-cyan-500 to-violet-600 text-white font-semibold text-sm hover:scale-[1.01] hover:shadow-lg hover:shadow-cyan-500/10 active:scale-95 transition-all flex items-center justify-center gap-2"
            >
              <span>⚡</span> Generate Explanatory Briefing
            </button>
          )}

          {xaiExplanation && !xaiLoading && (
            <button
              onClick={generateXaiInsight}
              className="w-full py-3 rounded-xl border border-slate-800 bg-slate-900/40 text-slate-400 font-medium text-xs hover:text-white hover:bg-slate-800 transition-all flex items-center justify-center gap-2"
            >
              <span>🔄</span> Force Regenerate Insight
            </button>
          )}
        </div>

        {/* Budget spend details */}
        <div className="glass-panel p-8 rounded-2xl border border-slate-800/80 flex flex-col justify-between min-h-[300px]">
          <div>
            <h3 className="font-heading font-bold text-xl text-white">💰 WP Budget spend recommendation</h3>
            <p className="text-slate-400 text-xs mt-1">ROI spending allocations calculated for Western Province trade programs.</p>
          </div>

          {outlet.budget ? (
            <div className="my-6 space-y-4">
              <div className="grid grid-cols-2 gap-4">
                <div className="p-4 rounded-xl bg-slate-900/60 border border-slate-800">
                  <span className="block text-[9px] font-bold text-slate-500 uppercase tracking-widest">Recommended Spend</span>
                  <span className="text-lg font-extrabold text-white mt-1 block font-mono">
                    LKR {outlet.budget.trade_spend_allocation_lkr.toLocaleString()}
                  </span>
                </div>
                <div className="p-4 rounded-xl bg-slate-900/60 border border-slate-800">
                  <span className="block text-[9px] font-bold text-slate-500 uppercase tracking-widest">ROI Efficiency Score</span>
                  <span className="text-lg font-extrabold text-emerald-400 mt-1 block font-mono text-glow-emerald">
                    {outlet.budget.roi_score.toFixed(3)}
                  </span>
                </div>
              </div>

              <div className="p-4 rounded-xl bg-slate-950/40 border border-slate-800 flex items-center justify-between">
                <div>
                  <span className="block text-[9px] font-bold text-slate-500 uppercase tracking-widest"> spend activity type</span>
                  <span className="text-sm font-semibold text-slate-200 mt-0.5 block capitalize">
                    {outlet.budget.recommended_spend_type.replace(/_/g, ' ')}
                  </span>
                </div>
                <span className="text-2xl">⚡</span>
              </div>
            </div>
          ) : (
            <div className="my-6 p-6 rounded-xl bg-slate-900/30 border border-slate-800/50 flex flex-col items-center justify-center text-center gap-2">
              <span className="text-3xl text-slate-600">ⓘ</span>
              <p className="text-sm text-slate-500">No budget spend recommendation available.</p>
              <p className="text-xs text-slate-600">Trade spends allocations are strictly mapped for Western Province trade programs only.</p>
            </div>
          )}

          <div className="text-[10px] text-slate-500 font-sans italic border-t border-slate-800/60 pt-3">
            💡 Spend types include: cooler grants (high storage capacity), discount vouchers, or local POS brand support.
          </div>
        </div>
      </div>
    </div>
  );
}
