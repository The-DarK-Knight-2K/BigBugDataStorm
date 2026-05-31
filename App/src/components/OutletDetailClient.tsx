"use client";

import { useState, useMemo } from 'react';
import Link from 'next/link';
import { ResponsiveContainer, BarChart, Bar, XAxis, YAxis, Tooltip, Cell, ReferenceLine } from 'recharts';
import dynamic from 'next/dynamic';
import ReactMarkdown from 'react-markdown';
import { OutletDetail } from '@/data_access/queries';

const SingleMap = dynamic(() => import('./SingleMap'), { ssr: false });

export default function OutletDetailClient({ outlet }: { outlet: OutletDetail }) {
  // Use parsed context to fill in details structured identically to the mock
  const context = outlet.parsed_context;
  const shapValues = context?.shap_values || [];

  // Dynamic interactive simulation state for the Gemini XAI Generator
  const [xaiLoading, setXaiLoading] = useState(false);
  const [xaiExplanation, setXaiExplanation] = useState<string | null>(outlet.xai_explanation);

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

  // Recharts custom label mapping for readability
  const chartData = useMemo(() => {
    return shapValues.map((v: any) => ({
      name: v.feature.replace(/_/, ' ').replace(/score/, '').trim(),
      val: v.shap_value,
      orig: v.feature_value
    }));
  }, [shapValues]);

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
            {Math.round(outlet.predicted_potential_litres || context?.prediction.Maximum_Monthly_Liters || 0).toLocaleString()} <span className="text-xs text-slate-400">L</span>
          </p>
          <div className="text-[10px] text-slate-400 mt-2 font-mono flex items-center gap-1">
            <span>Multiplier:</span>
            <span className="text-cyan-400 font-bold">{context?.prediction.seasonality_multiplier_jan_2026 || 1.0}x</span>
            <span>(January)</span>
          </div>
        </div>

        {/* Recent 3m avg */}
        <div className="glass-panel p-6 rounded-2xl relative overflow-hidden group hover:border-slate-700 transition-colors">
          <p className="text-xs font-semibold uppercase tracking-wider text-slate-400">Recent 3M average</p>
          <p className="text-3xl font-heading font-extrabold text-white mt-2">
            {Math.round(outlet.recent_3m_avg || context?.prediction.recent_3m_avg || 0).toLocaleString()} <span className="text-xs text-slate-400">L</span>
          </p>
          <div className="text-[10px] text-slate-400 mt-2 font-mono flex items-center gap-1">
            <span>Active Months:</span>
            <span className="text-slate-300 font-bold">{context?.sales_history.active_months || 0}m</span>
          </div>
        </div>

        {/* Uplift gap */}
        <div className="glass-panel p-6 rounded-2xl relative overflow-hidden group hover:border-slate-700 transition-colors">
          <p className="text-xs font-semibold uppercase tracking-wider text-slate-400">Uplift volume gap</p>
          <p className="text-3xl font-heading font-extrabold text-emerald-400 text-glow-emerald mt-2">
            {outlet.budget_allocation?.uplift_gap_litres || context?.prediction.uplift_gap_litres ? `${Math.round(outlet.budget_allocation?.uplift_gap_litres || context?.prediction.uplift_gap_litres || 0).toLocaleString()} L` : '0 L'}
          </p>
          <div className="text-[10px] text-slate-400 mt-2 font-mono flex items-center gap-1">
            <span>Growth Space:</span>
            <span className="text-emerald-400 font-bold">
              {(outlet.budget_allocation?.uplift_gap_litres || context?.prediction.uplift_gap_litres) && outlet.recent_3m_avg ? `+${Math.round(((outlet.budget_allocation?.uplift_gap_litres || context?.prediction.uplift_gap_litres || 0) / outlet.recent_3m_avg) * 100)}%` : '0%'}
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
        <div className="glass-panel p-6 rounded-2xl border border-slate-800 lg:col-span-2 space-y-4">
          <div>
            <h3 className="font-heading font-bold text-lg text-white">SHAP Prediction Drivers Impact</h3>
            <p className="text-slate-400 text-[11px] mt-0.5">Quantifying the impact of model features pushing the volume prediction up or down.</p>
          </div>
          <div className="h-[280px] w-full text-xs">
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
                <span className="text-white font-bold text-sm">{(context?.gravity_features?.transport_gravity_score || 0).toFixed(2)}</span>
              </div>

              {/* School Gravity */}
              <div className="p-3 rounded-xl bg-slate-900/60 border border-slate-800 flex justify-between items-center">
                <span className="text-slate-400">🏫 School Gravity</span>
                <span className="text-white font-bold text-sm">{(context?.gravity_features?.school_gravity_score || 0).toFixed(2)}</span>
              </div>

              {/* Worship Gravity */}
              <div className="p-3 rounded-xl bg-slate-900/60 border border-slate-800 flex justify-between items-center">
                <span className="text-slate-400">🛕 Worship Gravity</span>
                <span className="text-white font-bold text-sm">{((context?.gravity_features as any)?.worship_gravity_score || 0).toFixed(2)}</span>
              </div>

              {/* Hospitality Gravity */}
              <div className="p-3 rounded-xl bg-slate-900/60 border border-slate-800 flex justify-between items-center">
                <span className="text-slate-400">🏨 Hospitality Gravity</span>
                <span className="text-white font-bold text-sm">{((context?.gravity_features as any)?.hospitality_gravity_score || 0).toFixed(2)}</span>
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
                <div className="text-[13px]">
                  <ReactMarkdown
                    components={{
                      h3: ({node, ...props}) => <h3 className="font-heading font-bold text-lg text-white mt-4 mb-2 border-b border-slate-700/50 pb-1" {...props} />,
                      p: ({node, ...props}) => <p className="mb-3 text-slate-300" {...props} />,
                      ul: ({node, ...props}) => <ul className="list-disc pl-5 mb-3 space-y-1 text-slate-300" {...props} />,
                      li: ({node, ...props}) => <li {...props} />,
                      strong: ({node, ...props}) => <strong className="font-bold text-white" {...props} />,
                    }}
                  >
                    {xaiExplanation}
                  </ReactMarkdown>
                </div>
                <div className="flex justify-end pt-1 border-t border-slate-800/60 mt-4">
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

          {outlet.budget_allocation ? (
            <div className="my-6 space-y-4">
              <div className="grid grid-cols-2 gap-4">
                <div className="p-4 rounded-xl bg-slate-900/60 border border-slate-800">
                  <span className="block text-[9px] font-bold text-slate-500 uppercase tracking-widest">Recommended Spend</span>
                  <span className="text-lg font-extrabold text-white mt-1 block font-mono">
                    LKR {outlet.budget_allocation.trade_spend_allocation_lkr.toLocaleString()}
                  </span>
                </div>
                <div className="p-4 rounded-xl bg-slate-900/60 border border-slate-800">
                  <span className="block text-[9px] font-bold text-slate-500 uppercase tracking-widest">ROI Efficiency Score</span>
                  <span className="text-lg font-extrabold text-emerald-400 mt-1 block font-mono text-glow-emerald">
                    {outlet.budget_allocation.roi_score.toFixed(3)}
                  </span>
                </div>
              </div>

              <div className="p-4 rounded-xl bg-slate-950/40 border border-slate-800 flex items-center justify-between">
                <div>
                  <span className="block text-[9px] font-bold text-slate-500 uppercase tracking-widest"> spend activity type</span>
                  <span className="text-sm font-semibold text-slate-200 mt-0.5 block capitalize">
                    {outlet.budget_allocation.recommended_spend_type.replace(/_/g, ' ')}
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
