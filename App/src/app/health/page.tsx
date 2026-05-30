"use client";

import Link from 'next/link';
import { mockPipelineHealth } from '@/lib/mockData';

export default function PipelineHealthPage() {
  const healthData = mockPipelineHealth;

  return (
    <div className="space-y-8 animate-fade-in">
      {/* Title */}
      <div>
        <h2 className="font-heading font-extrabold text-3xl tracking-tight text-white">🩺 Pipeline Health & Validation</h2>
        <p className="text-slate-400 text-sm mt-1">Real-time data quality monitoring, schema validation rates, and quarantine audit logs.</p>
      </div>

      {/* Global pass rate KPIs */}
      <div className="grid grid-cols-1 md:grid-cols-4 gap-6">
        {/* Pass rate circle */}
        <div className="glass-panel p-6 rounded-2xl md:col-span-2 flex items-center justify-between border-l-4 border-l-emerald-500">
          <div className="space-y-1">
            <p className="text-xs font-semibold uppercase tracking-wider text-slate-400">Overall Portfolio Pass Rate</p>
            <p className="text-4xl font-heading font-extrabold text-emerald-400 text-glow-emerald mt-2">
              {(healthData.overall_pass_rate * 100).toFixed(1)}%
            </p>
            <span className="text-[10px] text-slate-400 font-mono mt-1.5 block">
              99.3% validation threshold successfully crossed
            </span>
          </div>
          {/* Circular progress display */}
          <div className="w-16 h-16 rounded-full border-4 border-slate-800 border-t-emerald-500 flex items-center justify-center font-mono text-[10px] text-emerald-400 font-bold shrink-0 shadow-lg shadow-emerald-500/10">
            PASSED
          </div>
        </div>

        {/* Total records ingested */}
        <div className="glass-panel p-6 rounded-2xl relative overflow-hidden border-l-4 border-l-cyan-500">
          <p className="text-xs font-semibold uppercase tracking-wider text-slate-400">Total Rows Audited</p>
          <p className="text-3xl font-heading font-extrabold text-white text-glow-cyan mt-2">
            2,416,389
          </p>
          <span className="text-[10px] text-slate-400 mt-2 block font-mono">
            Across 3 critical source tables
          </span>
        </div>

        {/* Quarantined records */}
        <div className="glass-panel p-6 rounded-2xl relative overflow-hidden border-l-4 border-l-rose-500">
          <p className="text-xs font-semibold uppercase tracking-wider text-slate-400">Quarantined Records</p>
          <p className="text-3xl font-heading font-extrabold text-rose-500 mt-2">
            16,660
          </p>
          <span className="text-[10px] text-rose-400 mt-2 block font-mono">
            0.69% total quarantine rate
          </span>
        </div>
      </div>

      {/* Dataset breakdowns */}
      <div className="space-y-6">
        <h3 className="font-heading font-bold text-lg text-white">Source Table Validation Ingestion Logs</h3>

        {healthData.datasets.map((data, idx) => {
          const passPercent = ((data.records_passed / data.records_checked) * 100).toFixed(2);
          const isHealthy = data.quarantine_rate < 0.01;

          return (
            <div key={idx} className="glass-panel rounded-2xl border border-slate-800 overflow-hidden shadow-xl">
              {/* Card header */}
              <div className="p-6 border-b border-slate-800 bg-slate-900/30 flex flex-wrap gap-4 justify-between items-center">
                <div className="space-y-1">
                  <div className="flex items-center gap-3">
                    <span className="text-xl">📄</span>
                    <h4 className="font-mono font-bold text-sm text-white tracking-wide">{data.dataset}</h4>
                    <span className={`px-2 py-0.5 rounded text-[9px] uppercase font-extrabold tracking-wider ${
                      isHealthy ? 'bg-emerald-500/20 text-emerald-400 border border-emerald-500/30' : 'bg-rose-500/20 text-rose-400 border border-rose-500/30'
                    }`}>
                      {isHealthy ? 'Healthy' : 'Warning'}
                    </span>
                  </div>
                  <p className="text-[10px] text-slate-400 font-mono">
                    Total checked: {data.records_checked.toLocaleString()} rows
                  </p>
                </div>

                <div className="text-right">
                  <span className="block text-[9px] font-bold text-slate-500 uppercase tracking-widest leading-none">Validation rate</span>
                  <span className="text-lg font-bold font-mono text-white mt-1 block">{passPercent}%</span>
                </div>
              </div>

              {/* Progress bar visualizer */}
              <div className="px-6 py-4 border-b border-slate-800/40 bg-slate-950/20">
                <div className="flex justify-between items-center text-[10px] text-slate-400 mb-1.5 font-mono">
                  <span>Passed: {data.records_passed.toLocaleString()}</span>
                  <span>Quarantined: {data.records_quarantined.toLocaleString()} ({ (data.quarantine_rate * 100).toFixed(2) }%)</span>
                </div>
                <div className="w-full h-2 rounded-full bg-slate-800 overflow-hidden flex">
                  <div className="h-full bg-emerald-500" style={{ width: `${passPercent}%` }}></div>
                  <div className="h-full bg-rose-500" style={{ width: `${100 - parseFloat(passPercent)}%` }}></div>
                </div>
              </div>

              {/* Detail checks subtable */}
              <div className="overflow-x-auto">
                <table className="w-full text-left text-xs border-collapse">
                  <thead>
                    <tr className="bg-slate-900/40 text-slate-500 border-b border-slate-800 text-[9px] tracking-wider uppercase font-semibold">
                      <th className="px-6 py-3">Audit Check ID</th>
                      <th className="px-6 py-3 text-right">Rows Passed</th>
                      <th className="px-6 py-3 text-right">Rows Quarantined</th>
                      <th className="px-6 py-3">Quarantine Trigger / Reason</th>
                      <th className="px-6 py-3 text-center">Status</th>
                    </tr>
                  </thead>
                  <tbody className="divide-y divide-slate-800/30 font-mono">
                    {data.checks.map((check, cIdx) => {
                      const checkHealthy = check.quarantined === 0;

                      return (
                        <tr key={cIdx} className="hover:bg-slate-900/20 transition-colors text-[11px]">
                          <td className="px-6 py-3.5 text-slate-300 font-semibold">{check.check_name}</td>
                          <td className="px-6 py-3.5 text-right text-slate-400">{check.passed.toLocaleString()}</td>
                          <td className="px-6 py-3.5 text-right text-rose-400">{check.quarantined.toLocaleString()}</td>
                          <td className="px-6 py-3.5 text-slate-400 max-w-[200px] truncate">
                            {check.failure_reason || <span className="text-slate-600 font-sans italic">None</span>}
                          </td>
                          <td className="px-6 py-3.5 text-center">
                            <span className={`inline-block w-2 h-2 rounded-full ${
                              checkHealthy ? 'bg-emerald-500 shadow-lg shadow-emerald-500/50' : 'bg-rose-500 shadow-lg shadow-rose-500/50'
                            }`}></span>
                          </td>
                        </tr>
                      );
                    })}
                  </tbody>
                </table>
              </div>
            </div>
          );
        })}
      </div>
    </div>
  );
}
