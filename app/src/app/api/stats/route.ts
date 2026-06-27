import { NextResponse } from 'next/server';
import { getDashboardStats, OutletFilters } from '@/data_access/queries';

export async function GET(request: Request) {
  const { searchParams } = new URL(request.url);
  
  const filters: OutletFilters = {
    province: searchParams.get('province') || undefined,
    distributor_id: searchParams.get('distributor_id') || undefined,
    outlet_type: searchParams.get('outlet_type') || undefined,
    tier: searchParams.get('tier') || undefined,
    market_saturation_class: searchParams.get('market_saturation_class') || undefined,
  };

  try {
    const data = await getDashboardStats(filters);
    return NextResponse.json(data);
  } catch (error) {
    console.error("Failed to fetch dashboard stats:", error);
    return NextResponse.json({ error: "Failed to fetch dashboard stats" }, { status: 500 });
  }
}
