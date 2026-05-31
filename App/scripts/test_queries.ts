import { getDashboardStats, getPaginatedOutlets, getOutletDetails, getBudgetAllocations, getPipelineHealth } from '../src/data_access/queries';

async function test() {
  console.log("=== Testing DB Queries ===");
  try {
    const stats = getDashboardStats();
    console.log("Dashboard Stats:", stats);

    const { outlets } = getPaginatedOutlets(undefined, 1, 5);
    console.log(`Outlets (first ${outlets.length}):`, outlets);

    if (outlets.length > 0) {
      const details = getOutletDetails(outlets[0].outlet_id);
      console.log(`Details for ${outlets[0].outlet_id}:`, details ? "Found" : "Not Found");
    }

    const budgets = getBudgetAllocations();
    console.log(`Budget Allocations count: ${budgets.length}`);

    const health = getPipelineHealth();
    console.log(`Pipeline Health checks: ${health.length}`);
    
    console.log("ALL SUCCESS!");
  } catch (e) {
    console.error("ERROR", e);
  }
}

test();
