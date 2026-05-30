import { getDashboardStats, getOutlets, getOutletDetails, getBudgetAllocations, getPipelineHealth } from '../src/data_access/queries';

async function test() {
  console.log("=== Testing DB Queries ===");
  try {
    const stats = getDashboardStats();
    console.log("Stats:", stats);

    const outlets = getOutlets({ tier: 'high' });
    console.log(`Found ${outlets.length} high tier outlets`);

    if (outlets.length > 0) {
      const details = getOutletDetails(outlets[0].outlet_id);
      console.log(`Details for ${outlets[0].outlet_id}:`, {
        parsed_context: details?.parsed_context ? "SUCCESS" : "FAIL",
        budget: details?.budget_allocation ? "SUCCESS" : "FAIL"
      });
    }

    const allocations = getBudgetAllocations();
    console.log(`Found ${allocations.length} budget allocations`);

    const health = getPipelineHealth();
    console.log(`Found ${health.length} pipeline health records`);
    
    console.log("ALL SUCCESS!");
  } catch (e) {
    console.error("ERROR", e);
  }
}

test();
