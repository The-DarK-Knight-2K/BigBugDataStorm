import { getPaginatedOutlets, getDashboardStats, getFilterOptions } from '@/data_access/queries';
import DashboardClient from '@/components/DashboardClient';

export default async function Dashboard() {
  const { outlets: initialOutlets, total: totalOutlets } = await getPaginatedOutlets(undefined, 1, 50);
  const initialStats = await getDashboardStats();
  const filterOptions = await getFilterOptions();

  return (
    <DashboardClient 
      initialOutlets={initialOutlets} 
      initialTotalOutlets={totalOutlets}
      initialStats={initialStats} 
      filterOptions={filterOptions}
    />
  );
}
