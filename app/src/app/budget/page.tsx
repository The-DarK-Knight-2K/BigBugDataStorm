import { getBudgetAllocations } from '@/data_access/queries';
import BudgetClient, { BudgetSummaryData } from '@/components/BudgetClient';

export default async function BudgetDashboard() {
  const allAllocations = await getBudgetAllocations();
  const allocations = allAllocations.filter(a => a.allocation_tier !== 'none' && (a.trade_spend_allocation_lkr || 0) > 0);

  // Dynamically calculate the aggregated stats on the server
  const totalBudget = allocations.reduce((sum, a) => sum + (a.trade_spend_allocation_lkr || 0), 0);
  const expectedLift = allocations.reduce((sum, a) => sum + (a.projected_volume_uplift_litres || 0), 0);
  
  // Calculate summary by distributor
  const distributorMap = new Map<string, { lift: number, total_spend: number }>();
  allocations.forEach(a => {
    if (!distributorMap.has(a.distributor_id)) {
      distributorMap.set(a.distributor_id, { lift: 0, total_spend: 0 });
    }
    const d = distributorMap.get(a.distributor_id)!;
    d.lift += (a.projected_volume_uplift_litres || 0);
    d.total_spend += (a.trade_spend_allocation_lkr || 0);
  });

  const summary_by_distributor = Array.from(distributorMap.entries()).map(([id, data]) => ({
    distributor_id: id,
    lift: data.lift,
    total_spend: data.total_spend,
    pct_of_budget: totalBudget > 0 ? Number(((data.total_spend / totalBudget) * 100).toFixed(1)) : 0
  })).sort((a, b) => b.total_spend - a.total_spend); // Sort by highest spend

  const summary: BudgetSummaryData = {
    total_trade_spend_allocation_lkr: totalBudget,
    projected_volume_uplift_litres: expectedLift,
    summary_by_distributor
  };

  return <BudgetClient allocations={allocations} budgetSummary={summary} />;
}
