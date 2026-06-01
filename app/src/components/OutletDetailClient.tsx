"use client";

import { useState, useMemo, useEffect } from 'react';
import Link from 'next/link';
import { ResponsiveContainer, BarChart, Bar, XAxis, YAxis, Tooltip, Cell, ReferenceLine } from 'recharts';
import dynamic from 'next/dynamic';
import { OutletDetail } from '@/data_access/queries';

const SingleMap = dynamic(() => import('./SingleMap'), { ssr: false });

export default function OutletDetailClient({ outlet }: { outlet: OutletDetail }) {
  // Use parsed context to fill in details structured identically to the mock
  const context = outlet.parsed_context;
  
  const shapValues = useMemo(() => {
    if (!context) return [];
    if (Array.isArray(context.shap_values)) {
      return context.shap_values; // Fallback to Phase 1 format
    }
    // Parse Phase 2 flat format
    return Object.entries(context)
      .filter(([key, val]) => key !== 'outlet_id' && typeof val === 'number')
      .map(([key, val]) => ({
        feature: key,
        shap_value: val,
        direction: (val as number) >= 0 ? 'positive' : 'negative',
        feature_value: (outlet as any)[key] !== undefined ? (outlet as any)[key] : null
      }))
      .sort((a, b) => Math.abs(b.shap_value) - Math.abs(a.shap_value))
      .slice(0, 12);
  }, [context]);

  // Dynamic interactive simulation state for the Gemini XAI Generator
  const [xaiLoading, setXaiLoading] = useState(false);
  const [xaiExplanation, setXaiExplanation] = useState<string | null>(outlet.xai_explanation);
  
  // Rotating loading messages
  const loadingSteps = useMemo(() => [
    "Initializing Gemini 2.0 Flash engine...",
    "Compiling contextual JSON payload...",
    "Analyzing historical volume constraints...",
    "Calculating Spatial Distance Decay algorithms...",
    "Evaluating SHAP marginal contributions...",
    "Formulating Field Rep Negotiation Plan...",
    "Finalizing executive insights..."
  ], []);
  
  const [loadingStepIdx, setLoadingStepIdx] = useState(0);

  useEffect(() => {
    let interval: NodeJS.Timeout;
    if (xaiLoading) {
      setLoadingStepIdx(0);
      interval = setInterval(() => {
        setLoadingStepIdx((prev) => (prev < loadingSteps.length - 1 ? prev + 1 : prev));
      }, 1500);
    }
    return () => {
      if (interval) clearInterval(interval);
    };
  }, [xaiLoading, loadingSteps]);

  const generateXaiInsight = async (force: boolean = false) => {
    setXaiLoading(true);
    
    try {
      const res = await fetch(`/api/explain/${outlet.outlet_id}${force ? '?force=true' : ''}`);
      const data = await res.json();
      
      if (!res.ok) {
        throw new Error(data.error || 'Failed to generate explanation');
      }
      
      setXaiExplanation(data.explanation);
    } catch (err: any) {
      console.error(err);
      setXaiExplanation(`Error: ${err.message}. Please check if the API Key is configured correctly.`);
    } finally {
      setXaiLoading(false);
    }
  };

  // Business Glossary Dictionary for mapping raw model features to C-Suite friendly labels
  const FEATURE_MAP: Record<string, string> = {
    "hist_cv": "Historical Sales Volatility",
    "trend_slope": "Recent Sales Momentum",
    "yoy_growth_rate": "Year-over-Year Growth",
    "jan_count": "Peak Season Activity (Jan)",
    "active_months": "Active Trading Months",
    "active_months_pct": "Trading Frequency (%)",
    "consecutive_zero_months_max": "Max Consecutive Zero-Sales Months",
    "worship_gravity_score": "Nearby Worship Places",
    "market_gravity_score": "Market Catchment Density",
    "transport_gravity_score": "Nearby Transport Hubs",
    "hospitality_gravity_score": "Nearby Hospitality/Hotels",
    "school_gravity_score": "Nearby Schools",
    "hospital_gravity_score": "Nearby Hospitals",
    "competitors_500m": "Close Competitors (500m)",
    "competitors_1km": "Local Competitors (1km)",
    "competitors_2km": "Regional Competitors (2km)",
    "outlet_size": "Physical Store Size",
    "cooler_count": "Installed Coolers",
    "recent_3m_avg": "Recent 3M Sales Baseline",
    "hist_p90_monthly": "Historical Peak Sales",
    "months_since_last_order": "Months Since Last Order"
  };

  // Recharts custom label mapping for readability
  const chartData = useMemo(() => {
    return shapValues
      .filter((v: any) => v.feature !== 'latitude' && v.feature !== 'longitude') // Filter out abstract GPS coords
      .map((v: any) => {
        // Find human-readable label or fallback to cleaned raw string
        const mappedName = FEATURE_MAP[v.feature] || v.feature.replace(/_/g, ' ').replace(/score/, '').trim();
        return {
          name: mappedName,
          val: v.shap_value,
          orig: v.feature_value
        };
      });
  }, [shapValues]);

  // Parse GenAI JSON
  const parsedExplanation = useMemo(() => {
    if (!xaiExplanation) return null;
    try {
      // Remove any markdown code block wrappers if Gemini accidentally includes them
      const cleanedJson = xaiExplanation.replace(/```json\n?|\n?```/g, '').trim();
      return JSON.parse(cleanedJson);
    } catch (e) {
      // Fallback for older cached markdown strings or parse errors
      return {
        diagnostic_alert: null,
        driver_cards: [],
        action_checklist: [],
        raw_fallback: xaiExplanation
      };
    }
  }, [xaiExplanation]);

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
              outlet.budget_allocation?.allocation_tier === 'high' ? 'bg-emerald-500/20 text-emerald-400 border border-emerald-500/30' :
              outlet.budget_allocation?.allocation_tier === 'medium' ? 'bg-amber-500/20 text-amber-400 border border-amber-500/30' :
              outlet.budget_allocation?.allocation_tier === 'low' ? 'bg-rose-500/20 text-rose-400 border border-rose-500/30' :
              'bg-slate-800 text-slate-400 border border-slate-700/50'
            }`}>
              Tier: {outlet.budget_allocation?.allocation_tier || 'NO ALLOCATION'}
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
            {Math.round(outlet.predicted_potential_litres || context?.prediction?.Maximum_Monthly_Liters || 0).toLocaleString()} <span className="text-xs text-slate-400">L</span>
          </p>
          <div className="text-[10px] text-slate-400 mt-2 font-mono flex items-center gap-1">
            <span>Multiplier:</span>
            <span className="text-cyan-400 font-bold">{outlet.seasonality_multiplier_jan_2026 || context?.prediction?.seasonality_multiplier_jan_2026 || 1.0}x</span>
            <span>(January)</span>
          </div>
        </div>

        {/* Recent 3m avg */}
        <div className="glass-panel p-6 rounded-2xl relative overflow-hidden group hover:border-slate-700 transition-colors">
          <p className="text-xs font-semibold uppercase tracking-wider text-slate-400">Recent 3M average</p>
          <p className="text-3xl font-heading font-extrabold text-white mt-2">
            {Math.round(outlet.recent_3m_avg || context?.prediction?.recent_3m_avg || 0).toLocaleString()} <span className="text-xs text-slate-400">L</span>
          </p>
          <div className="text-[10px] text-slate-400 mt-2 font-mono flex items-center gap-1">
            <span>Active Months:</span>
            <span className="text-slate-300 font-bold">{outlet.active_months || context?.sales_history?.active_months || 0}m</span>
          </div>
        </div>

        {/* Uplift gap */}
        <div className="glass-panel p-6 rounded-2xl relative overflow-hidden group hover:border-slate-700 transition-colors">
          <p className="text-xs font-semibold uppercase tracking-wider text-slate-400">Uplift volume gap</p>
          <p className="text-3xl font-heading font-extrabold text-emerald-400 text-glow-emerald mt-2">
            {outlet.budget_allocation?.uplift_gap_litres || context?.prediction?.uplift_gap_litres ? `${Math.round(outlet.budget_allocation?.uplift_gap_litres || context?.prediction?.uplift_gap_litres || 0).toLocaleString()} L` : '0 L'}
          </p>
          <div className="text-[10px] text-slate-400 mt-2 font-mono flex items-center gap-1">
            <span>Growth Space:</span>
            <span className="text-emerald-400 font-bold">
              {(outlet.budget_allocation?.uplift_gap_litres || context?.prediction?.uplift_gap_litres) && outlet.recent_3m_avg ? `+${Math.round(((outlet.budget_allocation?.uplift_gap_litres || context?.prediction?.uplift_gap_litres || 0) / outlet.recent_3m_avg) * 100)}%` : '0%'}
            </span>
          </div>
        </div>

        {/* Composite gravity score */}
        <div className="glass-panel p-6 rounded-2xl relative overflow-hidden group hover:border-slate-700 transition-colors">
          <p className="text-xs font-semibold uppercase tracking-wider text-slate-400">Composite gravity score</p>
          <p className="text-3xl font-heading font-extrabold text-violet-400 mt-2">
            {(outlet.composite_gravity_score || 0).toFixed(1)}
          </p>
          <div className="text-[10px] text-slate-400 mt-2 font-mono flex items-center gap-1">
            <span>Footfall Score:</span>
            <span className="text-violet-400 font-bold">{(outlet.footfall_score || 0).toFixed(1)}</span>
          </div>
        </div>
      </div>

      {/* New Panels for Phase 2: Cooler Capacity & Market Catchment */}
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
        {/* Cooler & Capacity Ceiling Panel */}
        <div className="glass-panel p-6 rounded-2xl border border-slate-800 flex flex-col justify-between">
          <div className="space-y-4">
            <div>
              <h3 className="font-heading font-bold text-lg text-white">❄️ Cooler & Capacity Ceiling</h3>
              <p className="text-slate-400 text-[11px] mt-0.5">Physics-based constraints on maximum monthly volume.</p>
            </div>
            
            <div className="space-y-3 font-mono text-xs">
              <div className="p-3 rounded-xl bg-slate-900/60 border border-slate-800 flex justify-between items-center">
                <span className="text-slate-400">Physical Capacity</span>
                <span className="text-white font-bold text-sm">{(outlet.cooler_capacity_litres || 0).toLocaleString()} L</span>
              </div>
              <div className="p-3 rounded-xl bg-slate-900/60 border border-slate-800 flex justify-between items-center">
                <span className="text-slate-400">Max Potential Target</span>
                <span className="text-cyan-400 font-bold text-sm">{(outlet.theoretical_monthly_ceiling || 0).toLocaleString()} L</span>
              </div>
              
              <div className="p-3 rounded-xl bg-slate-900/60 border border-slate-800">
                <div className="flex justify-between items-center mb-1.5">
                  <span className="text-slate-400 text-[10px] uppercase">Utilization Ratio</span>
                  <span className="text-white font-bold">{Math.round((outlet.capacity_utilization_ratio || 0) * 100)}%</span>
                </div>
                <div className="w-full bg-slate-800 rounded-full h-1.5">
                  <div 
                    className={`h-1.5 rounded-full ${
                      (outlet.capacity_utilization_ratio || 0) > 0.8 ? 'bg-rose-500' :
                      (outlet.capacity_utilization_ratio || 0) > 0.5 ? 'bg-amber-500' :
                      'bg-emerald-500'
                    }`}
                    style={{ width: `${Math.min((outlet.capacity_utilization_ratio || 0) * 100, 100)}%` }}
                  ></div>
                </div>
              </div>
            </div>
          </div>
        </div>

        {/* Market & Catchment Panel */}
        <div className="glass-panel p-6 rounded-2xl border border-slate-800 flex flex-col justify-between">
          <div className="space-y-4">
            <div>
              <h3 className="font-heading font-bold text-lg text-white">🎯 Market & Catchment</h3>
              <p className="text-slate-400 text-[11px] mt-0.5">Statistical Hurdle/Tobit demand estimates & saturation.</p>
            </div>
            
            <div className="space-y-3 font-mono text-xs">
              <div className="p-3 rounded-xl bg-slate-900/60 border border-slate-800 flex justify-between items-center">
                <span className="text-slate-400">Local Competitor Crowding</span>
                <span className="text-white font-bold text-sm">{(outlet.competition_density_score || 0).toFixed(2)}</span>
              </div>
              <div className="p-3 rounded-xl bg-slate-900/60 border border-slate-800 flex justify-between items-center">
                <span className="text-slate-400">Saturation Class</span>
                <span className={`text-white font-bold text-[10px] uppercase px-2 py-1 rounded ${
                  outlet.market_saturation_class === 'isolated' ? 'bg-emerald-500/20 text-emerald-400' :
                  outlet.market_saturation_class === 'moderate' ? 'bg-amber-500/20 text-amber-400' :
                  outlet.market_saturation_class === 'dense' ? 'bg-rose-500/20 text-rose-400' :
                  'bg-slate-800'
                }`}>
                  {outlet.market_saturation_class || 'N/A'}
                </span>
              </div>
              
              <div className="grid grid-cols-2 gap-3 mt-2">
                <div className="p-3 rounded-xl bg-slate-900/60 border border-slate-800">
                  <span className="block text-[9px] font-bold text-slate-500 uppercase tracking-widest">True Demand Est.</span>
                  <span className="text-sm font-extrabold text-white mt-1 block">{(outlet.tobit_latent_estimate || 0).toLocaleString()} L</span>
                </div>
                <div className="p-3 rounded-xl bg-slate-900/60 border border-slate-800">
                  <span className="block text-[9px] font-bold text-slate-500 uppercase tracking-widest">Sales Likelihood</span>
                  <span className="text-sm font-extrabold text-white mt-1 block">{(outlet.hurdle_estimate || 0).toLocaleString()} L</span>
                </div>
              </div>
            </div>
          </div>
        </div>
      </div>

      {/* Map View */}
      <div className="glass-panel p-1 rounded-2xl border border-slate-800 h-[350px]">
        <SingleMap outlet={{
          outlet_id: outlet.outlet_id,
          latitude: outlet.latitude,
          longitude: outlet.longitude,
          outlet_type: outlet.outlet_type,
          allocation_tier: outlet.budget_allocation?.allocation_tier
        }} />
      </div>

      {/* SHAP Chart & spatial scores */}
      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
        {/* SHAP impact chart panel */}
        <div className="glass-panel p-6 rounded-2xl border border-slate-800 lg:col-span-2 flex flex-col">
          <div className="mb-4">
            <h3 className="font-heading font-bold text-lg text-white">SHAP Prediction Drivers Impact</h3>
            <p className="text-slate-400 text-[11px] mt-0.5">Quantifying the impact of model features pushing the volume prediction up or down.</p>
          </div>
          <div className="flex-1 min-h-[280px] w-full text-xs">
            {chartData.length > 0 ? (
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
                            <p className="text-slate-300 mt-1">Impact Value: <span className="font-bold font-mono text-white">{data.val > 0 ? '+' : ''}{Number(data.val).toFixed(1)} L</span></p>
                            {data.orig !== null && data.orig !== undefined && (
                              <p className="text-slate-400 mt-1">Feature Value: <span className="font-mono text-slate-300">{typeof data.orig === 'number' ? Number(data.orig).toFixed(2) : data.orig}</span></p>
                            )}
                          </div>
                        );
                      }
                      return null;
                    }}
                  />
                  <ReferenceLine x={0} stroke="#475569" strokeDasharray="3 3" />
                  <Bar dataKey="val">
                    {chartData.map((entry: any, index: number) => (
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
            ) : (
              <div className="flex items-center justify-center h-full text-slate-500">No SHAP data available</div>
            )}
          </div>
        </div>

        {/* Right side panels */}
        <div className="space-y-6 flex flex-col">
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
                  <span className="text-slate-400">🚍 Transport Footfall Impact</span>
                  <span className="text-white font-bold text-sm">{(outlet.transport_gravity_score || context?.gravity_features?.transport_gravity_score || 0).toFixed(2)}</span>
                </div>

                {/* School Gravity */}
                <div className="p-3 rounded-xl bg-slate-900/60 border border-slate-800 flex justify-between items-center">
                  <span className="text-slate-400">🏫 School Footfall Impact</span>
                  <span className="text-white font-bold text-sm">{(outlet.school_gravity_score || context?.gravity_features?.school_gravity_score || 0).toFixed(2)}</span>
                </div>

                {/* Worship Gravity */}
                <div className="p-3 rounded-xl bg-slate-900/60 border border-slate-800 flex justify-between items-center">
                  <span className="text-slate-400">🛕 Worship Footfall Impact</span>
                  <span className="text-white font-bold text-sm">{(outlet.worship_gravity_score || (context?.gravity_features as any)?.worship_gravity_score || 0).toFixed(2)}</span>
                </div>

                {/* Hospitality Gravity */}
                <div className="p-3 rounded-xl bg-slate-900/60 border border-slate-800 flex justify-between items-center">
                  <span className="text-slate-400">🏨 Hospitality Footfall Impact</span>
                  <span className="text-white font-bold text-sm">{(outlet.hospitality_gravity_score || (context?.gravity_features as any)?.hospitality_gravity_score || 0).toFixed(2)}</span>
                </div>
              </div>
            </div>

            <div className="text-[10px] text-slate-500 font-sans italic border-t border-slate-800/60 pt-3 mt-4">
              💡 Footfall Impact calculated via distance decay algorithm. Closer features carry exponentially heavier weighting.
            </div>
          </div>

          {/* Budget spend details (Moved to right column) */}
          <div className="glass-panel p-6 rounded-2xl border border-slate-800 flex flex-col justify-between">
            <div>
              <h3 className="font-heading font-bold text-lg text-white">💰 WP Budget spend</h3>
              <p className="text-slate-400 text-[11px] mt-0.5">ROI spending allocations calculated for Western Province trade programs.</p>
            </div>

            {outlet.budget_allocation ? (
              <div className="my-4 space-y-3">
                <div className="grid grid-cols-2 gap-3">
                  <div className="p-3 rounded-xl bg-slate-900/60 border border-slate-800">
                    <span className="block text-[9px] font-bold text-slate-500 uppercase tracking-widest">Rec. Spend</span>
                    <span className="text-sm font-extrabold text-white mt-1 block font-mono">
                      LKR {outlet.budget_allocation.trade_spend_allocation_lkr.toLocaleString()}
                    </span>
                  </div>
                  <div className="p-3 rounded-xl bg-slate-900/60 border border-slate-800">
                    <span className="block text-[9px] font-bold text-slate-500 uppercase tracking-widest">ROI Score</span>
                    <span className="text-sm font-extrabold text-emerald-400 mt-1 block font-mono text-glow-emerald">
                      {outlet.budget_allocation.roi_score.toFixed(3)}
                    </span>
                  </div>
                </div>

                <div className="p-3 rounded-xl bg-slate-950/40 border border-slate-800 flex items-center justify-between">
                  <div>
                    <span className="block text-[9px] font-bold text-slate-500 uppercase tracking-widest"> spend activity type</span>
                    <span className="text-xs font-semibold text-slate-200 mt-0.5 block capitalize">
                      {outlet.budget_allocation.recommended_spend_type.replace(/_/g, ' ')}
                    </span>
                  </div>
                  <span className="text-lg">⚡</span>
                </div>
              </div>
            ) : (
              <div className="my-4 p-4 rounded-xl bg-slate-900/30 border border-slate-800/50 flex flex-col items-center justify-center text-center gap-2">
                <span className="text-2xl text-slate-600">ⓘ</span>
                {!outlet.province?.includes('Western') ? (
                  <p className="text-xs text-amber-500/80">Allocation strictly restricted to Western Province.</p>
                ) : (
                  <p className="text-xs text-slate-500">Outlet did not qualify for a budget allocation.</p>
                )}
              </div>
            )}

            <div className="text-[10px] text-slate-500 font-sans italic border-t border-slate-800/60 pt-3">
              💡 Spend types: cooler grants, discount vouchers, or POS support.
            </div>
          </div>
        </div>
      </div>

      {/* Business XAI explanation (Full Width) */}
      <div className="glass-panel p-8 rounded-2xl border border-slate-800/80 flex flex-col justify-between">
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
        <div className="my-6 flex-1 flex flex-col justify-center">
          {xaiLoading ? (
            <div className="flex flex-col items-center justify-center my-12 gap-5 min-h-[200px]">
              <div className="relative">
                <div className="w-16 h-16 rounded-full border-4 border-slate-800 absolute top-0 left-0"></div>
                <div className="w-16 h-16 rounded-full border-4 border-cyan-500 border-t-transparent animate-spin relative z-10"></div>
                <div className="absolute inset-0 flex items-center justify-center text-xl animate-pulse">🤖</div>
              </div>
              <div className="text-center h-12 flex flex-col items-center justify-center">
                <p className="text-sm font-bold text-white tracking-widest uppercase mb-1">Thinking...</p>
                <p className="text-xs text-cyan-400 font-mono transition-all duration-300 ease-in-out">
                  {loadingSteps[loadingStepIdx]}
                </p>
              </div>
            </div>
          ) : parsedExplanation ? (
            <div className="space-y-6">
              {/* 1. Diagnostic Alert */}
              {parsedExplanation.diagnostic_alert ? (
                <div className={`p-5 rounded-xl border flex items-start gap-4 shadow-lg ${
                  parsedExplanation.diagnostic_alert.type === 'warning' ? 'bg-amber-900/20 border-amber-500/50 text-amber-200' :
                  parsedExplanation.diagnostic_alert.type === 'critical' ? 'bg-rose-900/20 border-rose-500/50 text-rose-200' :
                  parsedExplanation.diagnostic_alert.type === 'success' ? 'bg-emerald-900/20 border-emerald-500/50 text-emerald-200' :
                  'bg-cyan-900/20 border-cyan-500/50 text-cyan-200'
                }`}>
                  <div className="text-2xl shrink-0 mt-0.5">
                    {parsedExplanation.diagnostic_alert.type === 'warning' ? '⚠️' : 
                     parsedExplanation.diagnostic_alert.type === 'critical' ? '🚨' : 
                     parsedExplanation.diagnostic_alert.type === 'success' ? '✅' : 'ℹ️'}
                  </div>
                  <div>
                    <h4 className="font-bold text-base">{parsedExplanation.diagnostic_alert.title}</h4>
                    <p className="text-sm mt-1.5 opacity-90 leading-relaxed">{parsedExplanation.diagnostic_alert.message}</p>
                  </div>
                </div>
              ) : parsedExplanation.raw_fallback ? (
                <div className="bg-slate-900/50 rounded-xl border border-slate-800/60 p-5 text-sm text-slate-300">
                   <p>{parsedExplanation.raw_fallback}</p>
                </div>
              ) : null}

              {/* 2. Driver Cards */}
              {parsedExplanation.driver_cards && parsedExplanation.driver_cards.length > 0 && (
                <div className="grid grid-cols-1 md:grid-cols-3 gap-6">
                  {parsedExplanation.driver_cards.map((card: any, i: number) => (
                    <div key={i} className="bg-slate-900/40 border border-slate-800/60 rounded-2xl p-6 flex flex-col gap-3 shadow-lg hover:border-slate-700 hover:bg-slate-900/60 transition-all">
                      <div className="text-4xl mb-1">{card.icon}</div>
                      <h4 className="font-bold text-base text-white leading-tight">{card.title}</h4>
                      <p className="text-[15px] text-slate-300 leading-relaxed">{card.description}</p>
                    </div>
                  ))}
                </div>
              )}

              {/* 3. Action Checklist */}
              {parsedExplanation.action_checklist && parsedExplanation.action_checklist.length > 0 && (
                <div className="bg-gradient-to-br from-slate-900/80 to-slate-900/30 border border-slate-800/60 border-l-4 border-l-cyan-500 rounded-xl p-8 shadow-xl mt-4">
                  <h4 className="font-bold text-base text-white mb-6 flex items-center gap-3">
                    <span className="text-xl">📋</span> Field Rep Negotiation Plan
                  </h4>
                  <div className="space-y-5">
                    {parsedExplanation.action_checklist.map((action: string, i: number) => (
                      <label key={i} className="flex items-start gap-4 cursor-pointer group bg-slate-900/30 p-4 rounded-lg border border-slate-800/50 hover:bg-slate-800/60 transition-colors">
                        <input type="checkbox" className="mt-0.5 w-5 h-5 rounded border-slate-600 bg-slate-800 text-cyan-500 focus:ring-cyan-500 focus:ring-offset-slate-900 cursor-pointer" />
                        <span className="text-[15px] text-slate-300 group-hover:text-white transition-colors leading-relaxed">{action}</span>
                      </label>
                    ))}
                  </div>
                </div>
              )}

              <div className="flex justify-end pt-2 border-t border-slate-800/60 mt-4">
                <span className="text-[9px] font-mono text-emerald-400">✓ Cached securely in SQLite local database</span>
              </div>
            </div>
          ) : (
            <div className="text-center space-y-2 py-12">
              <p className="text-sm text-slate-500">No cached explanation found for this outlet.</p>
              <p className="text-xs text-slate-600">First-time generation requires calling the model on-demand.</p>
            </div>
          )}
        </div>

        {/* Action button */}
        {!xaiExplanation && !xaiLoading && (
          <button
            onClick={() => generateXaiInsight()}
            className="w-full py-3.5 rounded-xl bg-gradient-to-r from-cyan-500 to-violet-600 text-white font-semibold text-sm hover:scale-[1.01] hover:shadow-lg hover:shadow-cyan-500/10 active:scale-95 transition-all flex items-center justify-center gap-2"
          >
            <span>⚡</span> Generate Explanatory Briefing
          </button>
        )}

        {xaiExplanation && !xaiLoading && (
          <button
            onClick={() => generateXaiInsight(true)}
            className="w-full py-3 rounded-xl border border-slate-800 bg-slate-900/40 text-slate-400 font-medium text-xs hover:text-white hover:bg-slate-800 transition-all flex items-center justify-center gap-2"
          >
            <span>🔄</span> Regenerate Insight
          </button>
        )}
      </div>
    </div>
  );
}
