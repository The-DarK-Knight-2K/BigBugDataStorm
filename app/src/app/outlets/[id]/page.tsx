import { notFound } from 'next/navigation';
import { getOutletDetails } from '@/data_access/queries';
import OutletDetailClient from '@/components/OutletDetailClient';

export default async function OutletDetailPage({ params }: { params: Promise<{ id: string }> }) {
  const { id } = await params;
  
  const outlet = await getOutletDetails(id);

  if (!outlet) {
    notFound();
  }

  return <OutletDetailClient outlet={outlet} />;
}
