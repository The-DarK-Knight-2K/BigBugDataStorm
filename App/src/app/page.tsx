import { getOutlets, getDashboardStats } from '@/data_access/queries';
import DashboardClient from '@/components/DashboardClient';

export default function Dashboard() {
  const outlets = getOutlets();
  const stats = getDashboardStats();

  return <DashboardClient initialOutlets={outlets} initialStats={stats} />;
}
