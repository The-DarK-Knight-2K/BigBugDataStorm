import { NextResponse } from 'next/server';
import { getPaginatedOutlets, OutletFilters } from '@/data_access/queries';

export async function GET(request: Request) {
  const { searchParams } = new URL(request.url);
  
  const page = parseInt(searchParams.get('page') || '1');
  const limit = parseInt(searchParams.get('limit') || '50');
  
  const filters: OutletFilters = {
    province: searchParams.get('province') || undefined,
    distributor_id: searchParams.get('distributor_id') || undefined,
    outlet_type: searchParams.get('outlet_type') || undefined,
    tier: searchParams.get('tier') || undefined,
  };

  try {
    const data = getPaginatedOutlets(filters, page, limit);
    return NextResponse.json(data);
  } catch (error) {
    console.error("Failed to fetch outlets:", error);
    return NextResponse.json({ error: "Failed to fetch outlets" }, { status: 500 });
  }
}
