"use client";

import { useState, useMemo } from 'react';
import Link from 'next/link';
import { ResponsiveContainer, PieChart, Pie, BarChart, Bar, XAxis, YAxis, Tooltip, Cell, Legend } from 'recharts';
import { BudgetAllocation } from '@/data_access/queries';

export interface BudgetSummaryData {
  total_trade_spend_allocation_lkr: number;
  projected_volume_uplift_litres: number;
  summary_by_distributor: Array<{
    distributor_id: string;
    lift: number;
    total_spend: number;
    pct_of_budget: number;
  }>;
}

export default function BudgetClient({ 
  allocations, 
  budgetSummary 
}: { 
  allocations: (BudgetAllocation & { distributor_id: string; outlet_type: string })[], 
  budgetSummary: BudgetSummaryData 
}) {
  const [selectedDistributor, setSelectedDistributor] = useState('');

  // Clean, premium colors matching our cyberpunk theme
  const COLOR_PALETTE = ['#06b6d4', '#8b5cf6', '#3b82f6'];

  // Total WP budget spend aggregates from summary data
  const totalBudget = budgetSummary.total_trade_spend_allocation_lkr;
  const expectedLift = budgetSummary.projected_volume_uplift_litres;
  const avgROI = allocations.length > 0 ? (allocations.reduce((sum, a) => sum + (a.roi_score || 0), 0) / allocations.length) : 0;

  // Donut chart: Budget per Distributor
  const donutData = useMemo(() => {
    return budgetSummary.summary_by_distributor.map((d, index) => ({
      name: d.distributor_id,
      value: d.total_spend,
      percentage: d.pct_of_budget,
      color: COLOR_PALETTE[index % COLOR_PALETTE.length]
    }));
  }, [budgetSummary]);

  // Bar chart: Expected Volume Lift by Distributor
  const barData = useMemo(() => {
    return budgetSummary.summary_by_distributor.map(d => ({
      name: d.distributor_id,
      litres: d.lift,
      spend: d.total_spend
    }));
  }, [budgetSummary]);

  // Budget allocations table (filtering by distributor and sorting by spend)
  const allocationOutlets = useMemo(() => {
    let result = [...allocations];
    if (selectedDistributor) {
      result = result.filter(o => o.distributor_id === selectedDistributor);
    }
    return result.sort((a, b) => (b.trade_spend_allocation_lkr || 0) - (a.trade_spend_allocation_lkr || 0));
  }, [selectedDistributor, allocations]);

  // Extract unique distributors for the filter dropdown
  const uniqueDistributors = useMemo(() => {
    return Array.from(new Set(allocations.map(a => a.distributor_id))).filter(Boolean);
  }, [allocations]);

  // Activity mapping for outlet list items
  const getActivityType = (tier: string) => {
    if (tier === 'high') return 'Cooler Grant Program';
    if (tier === 'medium') return 'Discount Voucher Program';
    return 'Brand Display Material';
  };

  return (
    <div className="space-y-8 animate-fade-in">
      {/* Title section */}
      <div>
        <h2 className="font-heading font-extrabold text-3xl tracking-tight text-white">💰 WP Spend Recommendations</h2>
        <p className="text-slate-400 text-sm mt-1">Data-driven trade spend recommendations across Western Province territories.</p>
        <div className="mt-3 inline-flex items-center gap-2 px-3 py-1.5 rounded-lg bg-cyan-500/10 border border-cyan-500/20 text-cyan-400 text-xs">
          <span className="text-sm">ℹ️</span> Note: AI spend recommendations are currently active only for Western Province.
        </div>
      </div>

      {/* KPI Stats cards */}
      <div className="grid grid-cols-1 md:grid-cols-3 gap-6">
        {/* Total Allocated WP spend */}
        <div className="glass-panel p-6 rounded-2xl relative overflow-hidden border-l-4 border-l-cyan-500">
          <p className="text-xs font-semibold uppercase tracking-wider text-slate-400">Total trade spends allocated</p>
          <p className="text-3xl font-heading font-extrabold text-white text-glow-cyan mt-2">
            LKR {Math.round(totalBudget).toLocaleString()}
          </p>
          <span className="text-[10px] text-slate-400 mt-2 block font-mono">
            Across {allocations.length.toLocaleString()} optimized trade accounts
          </span>
        </div>

        {/* Expected Lift volume */}
        <div className="glass-panel p-6 rounded-2xl relative overflow-hidden border-l-4 border-l-emerald-500">
          <p className="text-xs font-semibold uppercase tracking-wider text-slate-400">Projected volume uplift</p>
          <p className="text-3xl font-heading font-extrabold text-emerald-400 text-glow-emerald mt-2">
            {Math.round(expectedLift).toLocaleString()} <span className="text-xs text-slate-400">L</span>
          </p>
          <span className="text-[10px] text-emerald-400 mt-2 block font-mono">
            {expectedLift > 0 ? `Average LKR ${Math.round(totalBudget / expectedLift).toFixed(1)} spend per liter lift` : 'No projected lift'}
          </span>
        </div>

        {/* Average ROI Score */}
        <div className="glass-panel p-6 rounded-2xl relative overflow-hidden border-l-4 border-l-violet-500">
          <p className="text-xs font-semibold uppercase tracking-wider text-slate-400">Net portfolio ROI score</p>
          <p className="text-3xl font-heading font-extrabold text-violet-400 mt-2">
            {avgROI.toFixed(3)}
          </p>
          <span className="text-[10px] text-slate-400 mt-2 block font-mono">
            Based on predictive AI data models
          </span>
        </div>
      </div>

      {/* Visual Analytics Charts Grid */}
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
        {/* Pie chart budget distribution */}
        <div className="glass-panel p-6 rounded-2xl border border-slate-800 space-y-4 flex flex-col justify-between">
          <div>
            <h3 className="font-heading font-bold text-lg text-white">Spends Share by Distributor</h3>
            <p className="text-slate-400 text-[11px] mt-0.5">Budget split across WP regional distributors.</p>
          </div>
          
          <div className="h-[250px] w-full flex items-center justify-center relative">
            {donutData.length > 0 ? (
              <ResponsiveContainer width="100%" height="100%" minHeight={250}>
                <PieChart>
                  <Pie
                    data={donutData}
                    cx="50%"
                    cy="50%"
                    innerRadius={65}
                    outerRadius={90}
                    paddingAngle={5}
                    dataKey="value"
                  >
                    {donutData.map((entry, index) => (
                      <Cell key={`cell-${index}`} fill={entry.color} />
                    ))}
                  </Pie>
                  <Tooltip
                    content={({ active, payload }) => {
                      if (active && payload && payload.length) {
                        const data = payload[0].payload;
                        return (
                          <div className="bg-slate-900 border border-slate-800 p-2.5 rounded-lg shadow-xl text-[11px]">
                            <p className="font-bold text-white uppercase">{data.name}</p>
                            <p className="text-slate-300 mt-1">Allocation: <span className="font-bold font-mono text-white">LKR {Math.round(data.value).toLocaleString()}</span></p>
                            <p className="text-slate-400">Share of Spend: <span className="font-mono text-slate-300">{data.percentage}%</span></p>
                          </div>
                        );
                      }
                      return null;
                    }}
                  />
                  <Legend 
                    verticalAlign="bottom" 
                    height={36}
                    iconType="circle"
                    formatter={(value) => <span className="text-[11px] text-slate-300 font-mono">{value}</span>}
                  />
                </PieChart>
              </ResponsiveContainer>
            ) : (
              <div className="text-slate-500">No data available</div>
            )}
            <div className="absolute flex flex-col items-center justify-center pointer-events-none">
              <span className="text-[10px] text-slate-400 uppercase tracking-widest leading-none font-bold">Total WP</span>
              <span className="text-xl font-heading font-extrabold text-white mt-1.5 font-mono">{(totalBudget / 1000000).toFixed(1)} M LKR</span>
            </div>
          </div>
        </div>

        {/* Bar chart expected lift by distributor */}
        <div className="glass-panel p-6 rounded-2xl border border-slate-800 space-y-4">
          <div>
            <h3 className="font-heading font-bold text-lg text-white">Expected Volume Lift by Territory</h3>
            <p className="text-slate-400 text-[11px] mt-0.5">Expected sales volume growth from recommended spending.</p>
          </div>
          
          <div className="h-[250px] w-full text-xs">
            {barData.length > 0 ? (
              <ResponsiveContainer width="100%" height="100%" minHeight={250}>
                <BarChart data={barData} margin={{ top: 10, right: 10, left: 10, bottom: 5 }}>
                  <XAxis dataKey="name" stroke="#94a3b8" fontSize={10} tickLine={false} />
                  <YAxis stroke="#94a3b8" fontSize={10} tickLine={false} />
                  <Tooltip
                    content={({ active, payload }) => {
                      if (active && payload && payload.length) {
                        const data = payload[0].payload;
                        return (
                          <div className="bg-slate-900 border border-slate-800 p-2.5 rounded-lg shadow-xl text-[11px]">
                            <p className="font-bold text-white uppercase">{data.name}</p>
                            <p className="text-emerald-400 mt-1 font-bold">Projected Lift: <span className="font-mono">{Math.round(data.litres).toLocaleString()} L</span></p>
                            <p className="text-slate-400">Total Spend LKR: <span className="font-mono">{Math.round(data.spend).toLocaleString()}</span></p>
                          </div>
                        );
                      }
                      return null;
                    }}
                  />
                  <Bar dataKey="litres" radius={[8, 8, 0, 0]}>
                    {barData.map((entry, index) => (
                      <Cell key={`cell-${index}`} fill="url(#barGradient)" />
                    ))}
                  </Bar>
                  <defs>
                    <linearGradient id="barGradient" x1="0" y1="0" x2="0" y2="1">
                      <stop offset="0%" stopColor="#10b981" stopOpacity={0.8} />
                      <stop offset="100%" stopColor="#059669" stopOpacity={0.2} />
                    </linearGradient>
                  </defs>
                </BarChart>
              </ResponsiveContainer>
            ) : (
              <div className="flex items-center justify-center h-full text-slate-500">No data available</div>
            )}
          </div>
        </div>
      </div>

      {/* Allocation data table */}
      <div className="glass-panel rounded-2xl border border-slate-800 overflow-hidden shadow-2xl">
        <div className="p-6 border-b border-slate-800 flex flex-wrap gap-4 justify-between items-center">
          <div>
            <h3 className="font-heading font-bold text-lg text-white">Spend Recommendation Accounts</h3>
            <p className="text-slate-400 text-[11px] mt-0.5">Filter specific trade programs and outlet-level spend.</p>
          </div>
          
          {/* Interactive filter dropdown */}
          <div className="flex items-center gap-2">
            <span className="text-[10px] text-slate-400 font-semibold uppercase tracking-wider">Territory:</span>
            <select
              value={selectedDistributor}
              onChange={(e) => setSelectedDistributor(e.target.value)}
              className="bg-slate-900 border border-slate-800 text-slate-200 text-xs rounded-xl p-2 outline-none focus:border-cyan-500 transition-colors"
            >
              <option value="">All WP Distributors</option>
              {uniqueDistributors.map(d => (
                <option key={d} value={d}>{d}</option>
              ))}
            </select>
          </div>
        </div>

        <div className="overflow-x-auto">
          <table className="w-full text-left text-xs border-collapse">
            <thead>
              <tr className="bg-slate-900/80 border-b border-slate-800 text-slate-400 font-semibold tracking-wider uppercase text-[10px]">
                <th className="px-6 py-4">Outlet ID</th>
                <th className="px-6 py-4">Territory</th>
                <th className="px-6 py-4">Type</th>
                <th className="px-6 py-4 text-right">Projected Sales Lift</th>
                <th className="px-6 py-4 text-right">Trade Spends Recommendation</th>
                <th className="px-6 py-4 text-center">ROI Priority Tier</th>
                <th className="px-6 py-4">Spend Activity Type</th>
                <th className="px-6 py-4 text-center">Action</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-slate-800/50">
              {allocationOutlets.length > 0 ? (
                allocationOutlets.map((outlet) => (
                  <tr key={outlet.outlet_id} className="hover:bg-slate-900/40 transition-colors">
                    <td className="px-6 py-4 font-mono font-bold text-white tracking-wider">{outlet.outlet_id}</td>
                    <td className="px-6 py-4 text-slate-400 font-mono">{outlet.distributor_id}</td>
                    <td className="px-6 py-4 text-slate-300">{outlet.outlet_type}</td>
                    <td className="px-6 py-4 text-right text-emerald-400 font-bold font-mono">
                      +{Math.round(outlet.uplift_gap_litres || 0).toLocaleString()} L
                    </td>
                    <td className="px-6 py-4 text-right text-white font-semibold font-mono">
                      LKR {Math.round(outlet.trade_spend_allocation_lkr || 0).toLocaleString()}
                    </td>
                    <td className="px-6 py-4 text-center">
                      <span className={`px-2 py-0.5 rounded text-[9px] uppercase font-extrabold tracking-wider ${
                        outlet.allocation_tier === 'high' ? 'bg-emerald-500/20 text-emerald-400 border border-emerald-500/30' :
                        outlet.allocation_tier === 'medium' ? 'bg-amber-500/20 text-amber-400 border border-amber-500/30' :
                        'bg-rose-500/20 text-rose-400 border border-rose-500/30'
                      }`}>
                        {outlet.allocation_tier}
                      </span>
                    </td>
                    <td className="px-6 py-4 text-slate-300 font-medium">
                      {outlet.recommended_spend_type ? outlet.recommended_spend_type.replace(/_/g, ' ') : getActivityType(outlet.allocation_tier)}
                    </td>
                    <td className="px-6 py-4 text-center">
                      <Link
                        href={`/outlets/${outlet.outlet_id}`}
                        className="inline-flex items-center gap-1 px-2.5 py-1 rounded bg-slate-800 text-slate-300 border border-slate-700/60 hover:bg-cyan-500 hover:text-slate-950 transition-all text-[11px] font-semibold"
                      >
                        Details
                      </Link>
                    </td>
                  </tr>
                ))
              ) : (
                <tr>
                  <td colSpan={8} className="px-6 py-12 text-center text-slate-500 font-mono">
                    ⚠️ No budget spending matches this distributor filter.
                  </td>
                </tr>
              )}
            </tbody>
          </table>
        </div>
      </div>
    </div>
  );
}
