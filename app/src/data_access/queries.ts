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
  school_gravity_score: number;
  transport_gravity_score: number;
  worship_gravity_score: number;
  hospitality_gravity_score: number;
  active_months: number;
  seasonality_multiplier_jan_2026: number;
  cooler_capacity_litres: number;
  theoretical_monthly_ceiling: number;
  capacity_utilization_ratio: number;
  competitors_500m: number;
  competitors_1km: number;
  competition_density_score: number;
  market_saturation_class: string;
  tobit_latent_estimate: number;
  tobit_censoring_ratio: number;
  hurdle_estimate: number;
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
  avg_capacity_utilization: number;
}

export interface OutletFilters {
  province?: string;
  distributor_id?: string;
  outlet_type?: string;
  tier?: string;
  market_saturation_class?: string;
}

export interface FilterOptions {
  provinces: string[];
  distributors: string[];
  types: string[];
  tiers: string[];
  saturation_classes: string[];
}

// --- Queries ---

/**
 * Get aggregated stats for the main dashboard.
 */
export async function getDashboardStats(filters?: OutletFilters): Promise<DashboardStats> {
  let baseWhere = 'WHERE 1=1';
  let budgetWhere = 'WHERE 1=1';
  const params: any[] = [];
  
  if (filters) {
    if (filters.province) {
      baseWhere += ` AND o.province = ?`;
      budgetWhere += ` AND o.province = ?`;
      params.push(filters.province);
    }
    if (filters.distributor_id) {
      baseWhere += ` AND o.distributor_id = ?`;
      budgetWhere += ` AND o.distributor_id = ?`;
      params.push(filters.distributor_id);
    }
    if (filters.outlet_type) {
      baseWhere += ` AND o.outlet_type = ?`;
      budgetWhere += ` AND o.outlet_type = ?`;
      params.push(filters.outlet_type);
    }
    if (filters.tier) {
      // Need to join budget_allocations to filter base by tier
      baseWhere += ` AND b.allocation_tier = ?`;
      budgetWhere += ` AND b.allocation_tier = ?`;
      params.push(filters.tier);
    }
    if (filters.market_saturation_class) {
      baseWhere += ` AND o.market_saturation_class = ?`;
      budgetWhere += ` AND o.market_saturation_class = ?`;
      params.push(filters.market_saturation_class);
    }
  }

  // Duplicate params for the three queries below
  
  let outletsQuery = `
    SELECT 
      COUNT(o.outlet_id) as total_outlets, 
      SUM(o.predicted_potential_litres) as total_predicted_volume,
      AVG(o.capacity_utilization_ratio) as avg_capacity_utilization
    FROM outlets o
  `;
  if (filters?.tier) outletsQuery += ` LEFT JOIN budget_allocations b ON o.outlet_id = b.outlet_id`;
  outletsQuery += ` ${baseWhere}`;

  let budgetQuery = `
    SELECT SUM(b.trade_spend_allocation_lkr) as total_budget 
    FROM budget_allocations b
    JOIN outlets o ON b.outlet_id = o.outlet_id
    ${budgetWhere}
  `;

  let highPotentialQuery = `
    SELECT COUNT(b.outlet_id) as high_potential_outlets 
    FROM budget_allocations b
    JOIN outlets o ON b.outlet_id = o.outlet_id
    ${budgetWhere} AND b.allocation_tier = 'high'
  `;

  const outletsRes = await db.execute({ sql: outletsQuery, args: params });
  const budgetRes = await db.execute({ sql: budgetQuery, args: params });
  const highPotentialRes = await db.execute({ sql: highPotentialQuery, args: params });

  const outletsRow = outletsRes.rows[0] as any;
  const budgetRow = budgetRes.rows[0] as any;
  const highPotentialRow = highPotentialRes.rows[0] as any;

  return {
    total_outlets: (outletsRow?.total_outlets as number) || 0,
    total_predicted_volume: (outletsRow?.total_predicted_volume as number) || 0,
    total_budget: (budgetRow?.total_budget as number) || 0,
    high_potential_outlets: (highPotentialRow?.high_potential_outlets as number) || 0,
    avg_capacity_utilization: (outletsRow?.avg_capacity_utilization as number) || 0,
  };
}

/**
 * Get distinct filter options from the database
 */
export async function getFilterOptions(): Promise<FilterOptions> {
  const provinces = (await db.execute('SELECT DISTINCT province FROM outlets WHERE province IS NOT NULL')).rows.map(r => r.province as string);
  const distributors = (await db.execute('SELECT DISTINCT distributor_id FROM outlets WHERE distributor_id IS NOT NULL')).rows.map(r => r.distributor_id as string);
  const types = (await db.execute('SELECT DISTINCT outlet_type FROM outlets WHERE outlet_type IS NOT NULL')).rows.map(r => r.outlet_type as string);
  const tiers = (await db.execute("SELECT DISTINCT allocation_tier FROM budget_allocations WHERE allocation_tier IS NOT NULL AND allocation_tier != 'none'")).rows.map(r => r.allocation_tier as string);
  const saturation_classes = (await db.execute("SELECT DISTINCT market_saturation_class FROM outlets WHERE market_saturation_class IS NOT NULL")).rows.map(r => r.market_saturation_class as string);
  
  return { provinces, distributors, types, tiers, saturation_classes };
}

/**
 * Get paginated outlets for the data table, optionally filtered.
 */
export async function getPaginatedOutlets(filters: OutletFilters | undefined, page: number, limit: number): Promise<{ outlets: (Outlet & { allocation_tier?: string })[], total: number }> {
  let baseWhere = 'WHERE 1=1';
  const params: any[] = [];

  if (filters) {
    if (filters.province) {
      baseWhere += ` AND o.province = ?`;
      params.push(filters.province);
    }
    if (filters.distributor_id) {
      baseWhere += ` AND o.distributor_id = ?`;
      params.push(filters.distributor_id);
    }
    if (filters.outlet_type) {
      baseWhere += ` AND o.outlet_type = ?`;
      params.push(filters.outlet_type);
    }
    if (filters.tier) {
      baseWhere += ` AND b.allocation_tier = ?`;
      params.push(filters.tier);
    }
    if (filters.market_saturation_class) {
      baseWhere += ` AND o.market_saturation_class = ?`;
      params.push(filters.market_saturation_class);
    }
  }

  // Count query
  const countQuery = `
    SELECT COUNT(*) as count
    FROM outlets o
    LEFT JOIN budget_allocations b ON o.outlet_id = b.outlet_id
    ${baseWhere}
  `;
  const countRes = await db.execute({ sql: countQuery, args: params });
  const countRow = countRes.rows[0] as any;

  // Data query
  const dataQuery = `
    SELECT o.*, b.allocation_tier, b.trade_spend_allocation_lkr 
    FROM outlets o
    LEFT JOIN budget_allocations b ON o.outlet_id = b.outlet_id
    ${baseWhere}
    LIMIT ? OFFSET ?
  `;
  const dataParams = [...params, limit, (page - 1) * limit];
  const outletsRes = await db.execute({ sql: dataQuery, args: dataParams });
  const outlets = outletsRes.rows as unknown as (Outlet & { allocation_tier?: string })[];

  return { outlets, total: countRow.count as number };
}

/**
 * Get map points efficiently (stripped down properties).
 */
export async function getMapPoints(filters?: OutletFilters): Promise<any[][]> {
  let baseWhere = 'WHERE 1=1';
  const params: any[] = [];

  if (filters) {
    if (filters.province) {
      baseWhere += ` AND o.province = ?`;
      params.push(filters.province);
    }
    if (filters.distributor_id) {
      baseWhere += ` AND o.distributor_id = ?`;
      params.push(filters.distributor_id);
    }
    if (filters.outlet_type) {
      baseWhere += ` AND o.outlet_type = ?`;
      params.push(filters.outlet_type);
    }
    if (filters.tier) {
      baseWhere += ` AND b.allocation_tier = ?`;
      params.push(filters.tier);
    }
    if (filters.market_saturation_class) {
      baseWhere += ` AND o.market_saturation_class = ?`;
      params.push(filters.market_saturation_class);
    }
  }

  const query = `
    SELECT o.outlet_id, o.latitude, o.longitude, o.outlet_type, o.predicted_potential_litres, o.market_saturation_class, b.allocation_tier
    FROM outlets o
    LEFT JOIN budget_allocations b ON o.outlet_id = b.outlet_id
    ${baseWhere} AND o.in_sea = 0
  `;
  
  const res = await db.execute({ sql: query, args: params });
  const rows = res.rows as any[];
  
  // Convert to array of arrays to minimize JSON size:
  // [id, lat, lng, type, vol, tier, saturation]
  return rows.map(r => [
    r.outlet_id, 
    r.latitude, 
    r.longitude, 
    r.outlet_type, 
    r.predicted_potential_litres, 
    r.allocation_tier,
    r.market_saturation_class
  ]);
}

/**
 * Get comprehensive details for a single outlet.
 */
export async function getOutletDetails(outletId: string): Promise<OutletDetail | null> {
  const res = await db.execute({ sql: `
    SELECT 
      o.*, 
      x.context_json, 
      x.xai_explanation,
      b.uplift_gap_litres, b.roi_score, b.allocation_tier, b.trade_spend_allocation_lkr, b.recommended_spend_type, b.projected_volume_uplift_litres
    FROM outlets o
    LEFT JOIN xai_contexts x ON o.outlet_id = x.outlet_id
    LEFT JOIN budget_allocations b ON o.outlet_id = b.outlet_id
    WHERE o.outlet_id = ?
  `, args: [outletId] });
  const row = res.rows[0] as any;

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
    school_gravity_score: row.school_gravity_score,
    transport_gravity_score: row.transport_gravity_score,
    worship_gravity_score: row.worship_gravity_score,
    hospitality_gravity_score: row.hospitality_gravity_score,
    active_months: row.active_months,
    seasonality_multiplier_jan_2026: row.seasonality_multiplier_jan_2026,
    cooler_capacity_litres: row.cooler_capacity_litres,
    theoretical_monthly_ceiling: row.theoretical_monthly_ceiling,
    capacity_utilization_ratio: row.capacity_utilization_ratio,
    competitors_500m: row.competitors_500m,
    competitors_1km: row.competitors_1km,
    competition_density_score: row.competition_density_score,
    market_saturation_class: row.market_saturation_class,
    tobit_latent_estimate: row.tobit_latent_estimate,
    tobit_censoring_ratio: row.tobit_censoring_ratio,
    hurdle_estimate: row.hurdle_estimate,
    context_json: row.context_json,
    xai_explanation: row.xai_explanation,
    parsed_context,
    budget_allocation
  };
}

/**
 * Update the XAI explanation for an outlet.
 */
export async function updateXaiExplanation(outletId: string, explanation: string): Promise<void> {
  await db.execute({ sql: `
    UPDATE xai_contexts 
    SET xai_explanation = ? 
    WHERE outlet_id = ?
  `, args: [explanation, outletId] });
}

/**
 * Get the XAI context (JSON and any cached explanation) for a specific outlet.
 */
export async function getXAIContext(outletId: string): Promise<{ context_json: string; xai_explanation: string | null } | null> {
  const res = await db.execute({ sql: `
    SELECT context_json, xai_explanation 
    FROM xai_contexts 
    WHERE outlet_id = ?
  `, args: [outletId] });
  return (res.rows[0] as unknown as { context_json: string; xai_explanation: string | null }) || null;
}

/**
 * Get all budget allocations.
 */
export async function getBudgetAllocations(): Promise<(BudgetAllocation & { distributor_id: string; outlet_type: string })[]> {
  const res = await db.execute(`
    SELECT b.*, o.distributor_id, o.outlet_type
    FROM budget_allocations b
    JOIN outlets o ON b.outlet_id = o.outlet_id
  `);
  return res.rows as unknown as (BudgetAllocation & { distributor_id: string; outlet_type: string })[];
}

/**
 * Get pipeline health validation results.
 */
export async function getPipelineHealth(): Promise<PipelineHealth[]> {
  try {
    const res = await db.execute(`SELECT * FROM pipeline_health ORDER BY dataset ASC`);
    return res.rows as unknown as PipelineHealth[];
  } catch (e) {
    console.error("Error querying pipeline_health:", e);
    return [];
  }
}

// --- Spatial Queries ---

export interface POI {
  id: number;
  cluster_id: number;
  lat: number;
  lon: number;
  poi_type: string;
  name: string;
  tags_json: string;
  distance_meters?: number;
}

/**
 * Calculate the great circle distance between two points on the earth in meters.
 * Uses the Haversine formula.
 */
function calculateDistance(lat1: number, lon1: number, lat2: number, lon2: number): number {
  const R = 6371e3; // Earth's radius in meters
  const toRadians = (deg: number) => deg * Math.PI / 180;
  const φ1 = toRadians(lat1);
  const φ2 = toRadians(lat2);
  const Δφ = toRadians(lat2 - lat1);
  const Δλ = toRadians(lon2 - lon1);

  const a = Math.sin(Δφ / 2) * Math.sin(Δφ / 2) +
            Math.cos(φ1) * Math.cos(φ2) *
            Math.sin(Δλ / 2) * Math.sin(Δλ / 2);
  const c = 2 * Math.atan2(Math.sqrt(a), Math.sqrt(1 - a));

  return R * c;
}

/**
 * Get all POIs within a 2km radius of a specific outlet.
 */
export async function getOutletPOIs(outletId: string): Promise<POI[]> {
  // 1. Get outlet lat/lon and cluster_id
  const outletRes = await db.execute({ sql: `
    SELECT o.latitude, o.longitude, c.cluster_id
    FROM outlets o
    JOIN outlet_clusters c ON o.outlet_id = c.outlet_id
    WHERE o.outlet_id = ?
  `, args: [outletId] });
  const outletRow = outletRes.rows[0] as unknown as { latitude: number, longitude: number, cluster_id: number } | undefined;

  if (!outletRow) return [];

  // 2. Fetch all POIs for the cluster
  const poisRes = await db.execute({ sql: `
    SELECT * FROM cluster_pois WHERE cluster_id = ?
  `, args: [outletRow.cluster_id] });
  const pois = poisRes.rows as unknown as POI[];

  // 3. Calculate distance and filter to 2km (2000 meters)
  const result: POI[] = [];
  for (const poi of pois) {
    const dist = calculateDistance(outletRow.latitude as number, outletRow.longitude as number, poi.lat, poi.lon);
    if (dist <= 2000) {
      poi.distance_meters = Math.round(dist);
      result.push(poi);
    }
  }

  // Sort by distance ascending
  result.sort((a, b) => (a.distance_meters || 0) - (b.distance_meters || 0));

  return result;
}
