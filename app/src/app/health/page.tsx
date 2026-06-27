import { getPipelineHealth } from '@/data_access/queries';

export const dynamic = 'force-dynamic';

export default async function PipelineHealthPage() {
  const rawHealthData = await getPipelineHealth();

  let totalChecked = 0;
  let totalPassed = 0;
  let totalQuarantined = 0;

  const datasets = rawHealthData.map(d => {
    let checks: any[] = [];
    try {
      if (d.check_details_json) {
        const parsed = JSON.parse(d.check_details_json);
        if (Array.isArray(parsed)) {
          checks = parsed;
        }
      }
    } catch (e) {
      console.error("Failed to parse check_details_json", e);
    }

    totalChecked += d.records_checked;
    totalPassed += d.records_passed;
    totalQuarantined += d.records_quarantined;

    return {
      dataset: d.dataset,
      records_checked: d.records_checked,
      records_passed: d.records_passed,
      records_quarantined: d.records_quarantined,
      quarantine_rate: d.quarantine_rate,
      checks
    };
  });

  const overall_pass_rate = totalChecked > 0 ? (totalPassed / totalChecked) : 0;
  const overall_quarantine_rate = totalChecked > 0 ? (totalQuarantined / totalChecked) : 0;

  const datasetHealths = datasets.map(d => d.records_checked > 0 ? d.records_passed / d.records_checked : 0);
  const average_dataset_health = datasetHealths.length > 0 ? datasetHealths.reduce((a, b) => a + b, 0) / datasetHealths.length : 0;
  const isGlobalHealthy = overall_pass_rate > 0.99;

  const healthData = {
    overall_pass_rate,
    overall_quarantine_rate,
    average_dataset_health,
    isGlobalHealthy,
    total_records_checked: totalChecked,
    total_records_quarantined: totalQuarantined,
    datasets
  };

  return (
    <div className="space-y-8 animate-fade-in">
      {/* Title */}
      <div>
        <h2 className="font-heading font-extrabold text-3xl tracking-tight text-white">🩺 Data Quality & System Health</h2>
        <p className="text-slate-400 text-sm mt-1">Real-time monitoring of data accuracy, reliability, and flagged records.</p>
      </div>

      {/* Global pass rate KPIs */}
      <div className="grid grid-cols-1 md:grid-cols-4 gap-6">
        {/* Pass rate circle */}
        <div className={`glass-panel p-6 rounded-2xl md:col-span-2 flex items-center justify-between border-l-4 ${healthData.isGlobalHealthy ? 'border-l-emerald-500' : 'border-l-rose-500'}`}>
          <div className="space-y-1">
            <p className="text-xs font-semibold uppercase tracking-wider text-slate-400">Overall Portfolio Pass Rate</p>
            <p className={`text-4xl font-heading font-extrabold mt-2 ${healthData.isGlobalHealthy ? 'text-emerald-400 text-glow-emerald' : 'text-rose-500 text-glow-rose'}`}>
              {(healthData.overall_pass_rate * 100).toFixed(1)}%
            </p>
            <span className="text-sm text-slate-400 font-mono mt-1.5 block">
              Unweighted dataset average: {(healthData.average_dataset_health * 100).toFixed(1)}%
            </span>
          </div>
          {/* Circular progress display */}
          <div className={`w-16 h-16 rounded-full border-4 border-slate-800 flex items-center justify-center font-mono text-xs font-bold shrink-0 shadow-lg ${healthData.isGlobalHealthy ? 'border-t-emerald-500 text-emerald-400 shadow-emerald-500/10' : 'border-t-rose-500 text-rose-500 shadow-rose-500/10'}`}>
            {healthData.isGlobalHealthy ? 'PASSED' : 'WARNING'}
          </div>
        </div>

        {/* Total records ingested */}
        <div className="glass-panel p-6 rounded-2xl relative overflow-hidden border-l-4 border-l-cyan-500">
          <p className="text-xs font-semibold uppercase tracking-wider text-slate-400">Total Records Analyzed</p>
          <p className="text-3xl font-heading font-extrabold text-white text-glow-cyan mt-2">
            {(healthData.total_records_checked || 0).toLocaleString()}
          </p>
          <span className="text-sm text-slate-400 mt-2 block font-mono">
            Across {healthData.datasets.length} critical data sources
          </span>
        </div>

        {/* Quarantined records */}
        <div className="glass-panel p-6 rounded-2xl relative overflow-hidden border-l-4 border-l-rose-500">
          <p className="text-xs font-semibold uppercase tracking-wider text-slate-400">Excluded Data Points</p>
          <p className="text-3xl font-heading font-extrabold text-rose-500 mt-2">
            {(healthData.total_records_quarantined || 0).toLocaleString()}
          </p>
          <span className="text-sm text-rose-400 mt-2 block font-mono">
            {(healthData.overall_quarantine_rate * 100).toFixed(2)}% total exclusion rate
          </span>
        </div>
      </div>

      {/* Dataset breakdowns */}
      <div className="space-y-6">
        <h3 className="font-heading font-bold text-lg text-white">Data Source Quality Report</h3>

        {healthData.datasets.length === 0 && (
          <div className="glass-panel p-8 text-center rounded-2xl border border-slate-800">
            <p className="text-slate-400 font-mono text-sm">No data quality logs available.</p>
          </div>
        )}

        {healthData.datasets.map((data, idx) => {
          const passPercent = data.records_checked > 0 ? ((data.records_passed / data.records_checked) * 100).toFixed(2) : "0.00";
          const quarantinePercent = data.records_checked > 0 ? ((data.records_quarantined / data.records_checked) * 100).toFixed(2) : "0.00";
          const isHealthy = data.quarantine_rate < 0.01;

          return (
            <div key={idx} className="glass-panel rounded-2xl border border-slate-800 overflow-hidden shadow-xl">
              {/* Card header */}
              <div className="p-6 border-b border-slate-800 bg-slate-900/30 flex flex-wrap gap-4 justify-between items-center">
                <div className="space-y-1">
                  <div className="flex items-center gap-3">
                    <span className="text-xl">📄</span>
                    <h4 className="font-mono font-bold text-sm text-white tracking-wide">
                      {(data.dataset || 'Unknown_Dataset').split('_').map(word => word.charAt(0).toUpperCase() + word.slice(1)).join(' ')}
                    </h4>
                    <span className={`px-2 py-0.5 rounded text-xs uppercase font-extrabold tracking-wider ${
                      isHealthy ? 'bg-emerald-500/20 text-emerald-400 border border-emerald-500/30' : 'bg-rose-500/20 text-rose-400 border border-rose-500/30'
                    }`}>
                      {isHealthy ? 'Healthy' : 'Warning'}
                    </span>
                  </div>
                  <p className="text-sm text-slate-400 font-mono">
                    Total analyzed: {(data.records_checked || 0).toLocaleString()} records
                  </p>
                </div>

                <div className="text-right">
                  <span className="block text-xs font-bold text-slate-500 uppercase tracking-widest leading-none">Validation rate</span>
                  <span className="text-lg font-bold font-mono text-white mt-1 block">{passPercent}%</span>
                </div>
              </div>

              {/* Progress bar visualizer */}
              <div className="px-6 py-4 border-b border-slate-800/40 bg-slate-950/20">
                <div className="flex justify-between items-center text-sm text-slate-400 mb-1.5 font-mono">
                  <span>Valid: {(data.records_passed || 0).toLocaleString()}</span>
                  <span>Excluded: {(data.records_quarantined || 0).toLocaleString()} ({ ((data.quarantine_rate || 0) * 100).toFixed(2) }%)</span>
                </div>
                <div className="w-full h-2 rounded-full bg-slate-800 overflow-hidden flex">
                  <div className="h-full bg-emerald-500" style={{ width: `${passPercent}%` }}></div>
                  <div className="h-full bg-rose-500" style={{ width: `${quarantinePercent}%` }}></div>
                </div>
              </div>

              {/* Detail checks subtable */}
              <div className="overflow-x-auto">
                <table className="w-full text-left text-xs border-collapse">
                  <thead>
                    <tr className="bg-slate-900/40 text-slate-500 border-b border-slate-800 text-xs tracking-wider uppercase font-semibold">
                      <th className="px-6 py-3">Validation Rule</th>
                      <th className="px-6 py-3 text-right">Valid Records</th>
                      <th className="px-6 py-3 text-right">Excluded Records</th>
                      <th className="px-6 py-3">Error Details</th>
                      <th className="px-6 py-3 text-center">Status</th>
                    </tr>
                  </thead>
                  <tbody className="divide-y divide-slate-800/30 font-mono">
                    {data.checks.map((check, cIdx) => {
                      const checkHealthy = (check.quarantined || 0) === 0;

                      return (
                        <tr key={cIdx} className="hover:bg-slate-900/20 transition-colors text-sm">
                          <td className="px-6 py-3.5 text-slate-300 font-semibold">{check.check_name}</td>
                          <td className="px-6 py-3.5 text-right text-slate-400">{(check.passed || 0).toLocaleString()}</td>
                          <td className="px-6 py-3.5 text-right text-rose-400">{(check.quarantined || 0).toLocaleString()}</td>
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
