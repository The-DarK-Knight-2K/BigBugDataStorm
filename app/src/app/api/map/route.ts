import { NextResponse } from 'next/server';
import { getMapPoints, OutletFilters } from '@/data_access/queries';

export async function GET(request: Request) {
  const { searchParams } = new URL(request.url);
  
  const filters: OutletFilters = {
    province: searchParams.get('province') || undefined,
    distributor_id: searchParams.get('distributor_id') || undefined,
    outlet_type: searchParams.get('outlet_type') || undefined,
    tier: searchParams.get('tier') || undefined,
  };

  try {
    const data = getMapPoints(filters);
    return NextResponse.json(data);
  } catch (error) {
    console.error("Failed to fetch map points:", error);
    return NextResponse.json({ error: "Failed to fetch map points" }, { status: 500 });
  }
}
