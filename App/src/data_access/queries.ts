import db from './db';

// --- Types & Interfaces ---

export interface Outlet {
  outlet_id: string;
  outlet_type: string;
  outlet_size: string;
  province: string;
  distributor_id: string;
  latitude: number;
  longitude: number;
  cooler_count: number;
  predicted_potential_litres: number;
  recent_3m_avg: number;
  hist_p90_monthly: number;
  has_transaction_history: number;
  composite_gravity_score: number;
  footfall_score: number;
}

export interface BudgetAllocation {
  outlet_id: string;
  uplift_gap_litres: number;
  roi_score: number;
  allocation_tier: string;
  trade_spend_allocation_lkr: number;
  recommended_spend_type: string;
  projected_volume_uplift_litres: number;
}

export interface XaiContext {
  outlet_id: string;
  context_json: string;
  xai_explanation: string | null;
}

export interface PipelineHealth {
  dataset: string;
  records_checked: number;
  records_passed: number;
  records_quarantined: number;
  quarantine_rate: number;
  check_details_json: string;
}

export interface ContextJson {
  outlet_id: string;
  province: string;
  distributor_id: string;
  outlet_type: string;
  outlet_size: string;
  cooler_count: number;
  latitude: number;
  longitude: number;
  prediction: {
    uplift_gap_litres: number;
    Maximum_Monthly_Liters: number;
    recent_3m_avg: number;
    seasonality_multiplier_jan_2026: number;
  };
  sales_history: {
    hist_max_monthly: number;
    hist_p90_monthly: number;
    hist_cv: number;
    active_months: number;
    consecutive_zero_months_max: number;
    months_since_last_order: number;
  };
  poi_features: {
    footfall_score: number;
    poi_data_available: boolean;
  };
  gravity_features: {
    school_gravity_score: number;
    transport_gravity_score: number;
    composite_gravity_score: number;
  };
  shap_values: Array<{
    feature: string;
    shap_value: number;
    direction: 'positive' | 'negative';
    feature_value: number;
  }>;
  budget?: {
    allocation_tier: string;
    roi_score: number;
    recommended_spend_type: string;
    trade_spend_allocation_lkr: number;
  };
}

// --- Combined Return Types ---

export interface OutletDetail extends Outlet {
  context_json: string;
  xai_explanation: string | null;
  parsed_context?: ContextJson;
  budget_allocation?: BudgetAllocation;
}

export interface DashboardStats {
  total_outlets: number;
  total_predicted_volume: number;
  total_budget: number;
  high_potential_outlets: number;
}

export interface OutletFilters {
  province?: string;
  distributor_id?: string;
  outlet_type?: string;
  tier?: string;
}

// --- Queries ---

/**
 * Get aggregated stats for the main dashboard.
 */
export function getDashboardStats(): DashboardStats {
  const outletsRow = db.prepare(`
    SELECT 
      COUNT(outlet_id) as total_outlets, 
      SUM(predicted_potential_litres) as total_predicted_volume 
    FROM outlets
  `).get() as { total_outlets: number; total_predicted_volume: number };

  const budgetRow = db.prepare(`
    SELECT SUM(trade_spend_allocation_lkr) as total_budget 
    FROM budget_allocations
  `).get() as { total_budget: number | null };

  const highPotentialRow = db.prepare(`
    SELECT COUNT(outlet_id) as high_potential_outlets 
    FROM budget_allocations 
    WHERE allocation_tier = 'high'
  `).get() as { high_potential_outlets: number };

  return {
    total_outlets: outletsRow?.total_outlets || 0,
    total_predicted_volume: outletsRow?.total_predicted_volume || 0,
    total_budget: budgetRow?.total_budget || 0,
    high_potential_outlets: highPotentialRow?.high_potential_outlets || 0,
  };
}

/**
 * Get outlets for the map and table views, optionally filtered.
 */
export function getOutlets(filters?: OutletFilters): (Outlet & { allocation_tier?: string })[] {
  let query = `
    SELECT o.*, b.allocation_tier, b.trade_spend_allocation_lkr 
    FROM outlets o
    LEFT JOIN budget_allocations b ON o.outlet_id = b.outlet_id
    WHERE 1=1
  `;
  const params: any[] = [];

  if (filters) {
    if (filters.province) {
      query += ` AND o.province = ?`;
      params.push(filters.province);
    }
    if (filters.distributor_id) {
      query += ` AND o.distributor_id = ?`;
      params.push(filters.distributor_id);
    }
    if (filters.outlet_type) {
      query += ` AND o.outlet_type = ?`;
      params.push(filters.outlet_type);
    }
    if (filters.tier) {
      query += ` AND b.allocation_tier = ?`;
      params.push(filters.tier);
    }
  }

  const stmt = db.prepare(query);
  return stmt.all(...params) as (Outlet & { allocation_tier?: string })[];
}

/**
 * Get comprehensive details for a single outlet.
 */
export function getOutletDetails(outletId: string): OutletDetail | null {
  const row = db.prepare(`
    SELECT 
      o.*, 
      x.context_json, 
      x.xai_explanation,
      b.uplift_gap_litres, b.roi_score, b.allocation_tier, b.trade_spend_allocation_lkr, b.recommended_spend_type, b.projected_volume_uplift_litres
    FROM outlets o
    LEFT JOIN xai_contexts x ON o.outlet_id = x.outlet_id
    LEFT JOIN budget_allocations b ON o.outlet_id = b.outlet_id
    WHERE o.outlet_id = ?
  `).get(outletId) as any;

  if (!row) return null;

  // Manually reconstruct the budget allocation object if it exists
  let budget_allocation: BudgetAllocation | undefined = undefined;
  if (row.allocation_tier) {
    budget_allocation = {
      outlet_id: row.outlet_id,
      uplift_gap_litres: row.uplift_gap_litres,
      roi_score: row.roi_score,
      allocation_tier: row.allocation_tier,
      trade_spend_allocation_lkr: row.trade_spend_allocation_lkr,
      recommended_spend_type: row.recommended_spend_type,
      projected_volume_uplift_litres: row.projected_volume_uplift_litres
    };
  }

  // Parse context_json
  let parsed_context: ContextJson | undefined = undefined;
  try {
    if (row.context_json) {
      parsed_context = JSON.parse(row.context_json);
    }
  } catch (e) {
    console.error("Failed to parse context_json for outlet:", outletId);
  }

  return {
    outlet_id: row.outlet_id,
    outlet_type: row.outlet_type,
    outlet_size: row.outlet_size,
    province: row.province,
    distributor_id: row.distributor_id,
    latitude: row.latitude,
    longitude: row.longitude,
    cooler_count: row.cooler_count,
    predicted_potential_litres: row.predicted_potential_litres,
    recent_3m_avg: row.recent_3m_avg,
    hist_p90_monthly: row.hist_p90_monthly,
    has_transaction_history: row.has_transaction_history,
    composite_gravity_score: row.composite_gravity_score,
    footfall_score: row.footfall_score,
    context_json: row.context_json,
    xai_explanation: row.xai_explanation,
    parsed_context,
    budget_allocation
  };
}

/**
 * Update the XAI explanation for an outlet.
 */
export function updateXaiExplanation(outletId: string, explanation: string): void {
  const stmt = db.prepare(`
    UPDATE xai_contexts 
    SET xai_explanation = ? 
    WHERE outlet_id = ?
  `);
  stmt.run(explanation, outletId);
}

/**
 * Get the XAI context (JSON and any cached explanation) for a specific outlet.
 */
export function getXAIContext(outletId: string): { context_json: string; xai_explanation: string | null } | null {
  const stmt = db.prepare(`
    SELECT context_json, xai_explanation 
    FROM xai_contexts 
    WHERE outlet_id = ?
  `);
  return stmt.get(outletId) as { context_json: string; xai_explanation: string | null } | null;
}

/**
 * Get all budget allocations.
 */
export function getBudgetAllocations(): (BudgetAllocation & { distributor_id: string; outlet_type: string })[] {
  const stmt = db.prepare(`
    SELECT b.*, o.distributor_id, o.outlet_type
    FROM budget_allocations b
    JOIN outlets o ON b.outlet_id = o.outlet_id
  `);
  return stmt.all() as (BudgetAllocation & { distributor_id: string; outlet_type: string })[];
}

/**
 * Get pipeline health validation results.
 */
export function getPipelineHealth(): PipelineHealth[] {
  const stmt = db.prepare(`SELECT * FROM pipeline_health`);
  return stmt.all() as PipelineHealth[];
}
