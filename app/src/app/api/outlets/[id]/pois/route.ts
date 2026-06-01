import { NextResponse } from 'next/server';
import { getOutletPOIs } from '@/data_access/queries';

export async function GET(
  request: Request,
  { params }: { params: Promise<{ id: string }> }
) {
  try {
    const { id } = await params;
    const pois = getOutletPOIs(id);
    
    if (!pois) {
      return NextResponse.json({ error: 'Failed to fetch POIs' }, { status: 500 });
    }
    
    return NextResponse.json({ pois });
  } catch (error: any) {
    console.error("Error in /api/outlets/[id]/pois:", error);
    return NextResponse.json(
      { error: error.message || 'Internal Server Error' },
      { status: 500 }
    );
  }
}
