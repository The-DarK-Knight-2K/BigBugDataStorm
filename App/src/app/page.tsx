import { getPaginatedOutlets, getDashboardStats, getFilterOptions } from '@/data_access/queries';
import DashboardClient from '@/components/DashboardClient';

export default function Dashboard() {
  const { outlets: initialOutlets, total: totalOutlets } = getPaginatedOutlets(undefined, 1, 50);
  const initialStats = getDashboardStats();
  const filterOptions = getFilterOptions();

  return (
    <DashboardClient 
      initialOutlets={initialOutlets} 
      initialTotalOutlets={totalOutlets}
      initialStats={initialStats} 
      filterOptions={filterOptions}
    />
  );
}
