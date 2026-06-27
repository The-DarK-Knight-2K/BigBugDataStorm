import { getDashboardStats, getPaginatedOutlets, getOutletDetails, getBudgetAllocations, getPipelineHealth } from '../src/data_access/queries';

async function test() {
  console.log("=== Testing DB Queries ===");
  try {
    const stats = await getDashboardStats();
    console.log("Dashboard Stats:", stats);

    const { outlets } = await getPaginatedOutlets(undefined, 1, 5);
    console.log(`Outlets (first ${outlets.length}):`, outlets);

    if (outlets.length > 0) {
      const details = await getOutletDetails(outlets[0].outlet_id);
      console.log(`Details for ${outlets[0].outlet_id}:`, details ? "Found" : "Not Found");
    }

    const budgets = await getBudgetAllocations();
    console.log(`Budget Allocations count: ${budgets.length}`);

    const health = await getPipelineHealth();
    console.log(`Pipeline Health checks: ${health.length}`);
    
    console.log("ALL SUCCESS!");
  } catch (e) {
    console.error("ERROR", e);
  }
}

test();
