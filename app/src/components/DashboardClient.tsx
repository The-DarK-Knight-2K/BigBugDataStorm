"use client";

import { useState, useEffect, useCallback, useRef } from 'react';
import dynamic from 'next/dynamic';
import Link from 'next/link';
import { Outlet, DashboardStats, FilterOptions } from '@/data_access/queries';

// Dynamically import the Leaflet map with SSR disabled to avoid window reference errors in Next.js
const MapComponent = dynamic(() => import('@/components/Map'), {
  ssr: false,
  loading: () => (
    <div className="w-full h-full min-h-[450px] rounded-2xl bg-slate-900/60 border border-slate-800 flex items-center justify-center">
      <div className="flex flex-col items-center gap-3">
        <div className="w-8 h-8 rounded-full border-2 border-cyan-500 border-t-transparent animate-spin"></div>
        <span className="text-xs text-slate-400 font-mono">Loading Map Coordinates...</span>
      </div>
    </div>
  )
});

interface DashboardClientProps {
  initialOutlets: (Outlet & { allocation_tier?: string, trade_spend_allocation_lkr?: number })[];
  initialTotalOutlets: number;
  initialStats: DashboardStats;
  filterOptions: FilterOptions;
}

export default function DashboardClient({ initialOutlets, initialTotalOutlets, initialStats, filterOptions }: DashboardClientProps) {
  // State for interactive filters
  const [selectedProvince, setSelectedProvince] = useState('');
  const [selectedDistributor, setSelectedDistributor] = useState('');
  const [selectedType, setSelectedType] = useState('');
  const [selectedTier, setSelectedTier] = useState('');
  const [selectedSaturation, setSelectedSaturation] = useState('');
  
  const [page, setPage] = useState(1);
  const limit = 50;

  // Data state
  const [outlets, setOutlets] = useState(initialOutlets);
  const [totalOutlets, setTotalOutlets] = useState(initialTotalOutlets);
  const [stats, setStats] = useState(initialStats);
  const [mapPoints, setMapPoints] = useState<any[]>([]); // Array of arrays
  
  const [isLoadingTable, setIsLoadingTable] = useState(false);
  const [isLoadingMap, setIsLoadingMap] = useState(true);
  
  const isInitialMount = useRef(true);

  // Sync props to state if parent re-renders with new initial data
  useEffect(() => {
    setOutlets(initialOutlets);
    setTotalOutlets(initialTotalOutlets);
    setStats(initialStats);
  }, [initialOutlets, initialTotalOutlets, initialStats]);

  // Helper to build query string
  const buildQueryString = useCallback((currentPage: number, includePage: boolean = true) => {
    const params = new URLSearchParams();
    if (includePage) {
      params.set('page', currentPage.toString());
      params.set('limit', limit.toString());
    }
    if (selectedProvince) params.set('province', selectedProvince);
    if (selectedDistributor) params.set('distributor_id', selectedDistributor);
    if (selectedType) params.set('outlet_type', selectedType);
    if (selectedTier) params.set('tier', selectedTier);
    if (selectedSaturation) params.set('market_saturation_class', selectedSaturation);
    return params.toString();
  }, [selectedProvince, selectedDistributor, selectedType, selectedTier, selectedSaturation]);

  // Fetch Table Data when filters or page change
  useEffect(() => {
    if (isInitialMount.current) {
      isInitialMount.current = false;
      return;
    }
    
    const fetchTableData = async () => {
      setIsLoadingTable(true);
      const qs = buildQueryString(page);
      try {
        const outletsRes = await fetch(`/api/outlets?${qs}`);
        if (outletsRes.ok) {
          const data = await outletsRes.json();
          setOutlets(data.outlets);
          setTotalOutlets(data.total);
        }
      } catch (error) {
        console.error("Error fetching data:", error);
      } finally {
        setIsLoadingTable(false);
      }
    };
    
    fetchTableData();
  }, [buildQueryString, page]);

  // Fetch Map Data and Stats (on mount and when filters change)
  useEffect(() => {
    const fetchMapAndStats = async () => {
      setIsLoadingMap(true);
      const qs = buildQueryString(1, false); // Map doesn't care about page
      try {
        const [mapRes, statsRes] = await Promise.all([
          fetch(`/api/map?${qs}`),
          fetch(`/api/stats?${qs}`)
        ]);
        
        if (mapRes.ok) {
          const data = await mapRes.json();
          setMapPoints(data);
        }
        if (statsRes.ok) {
          const data = await statsRes.json();
          setStats(data);
        }
      } catch (error) {
        console.error("Error fetching map/stats points:", error);
      } finally {
        setIsLoadingMap(false);
      }
    };
    
    fetchMapAndStats();
  }, [selectedProvince, selectedDistributor, selectedType, selectedTier, selectedSaturation, buildQueryString]);

  // Reset page to 1 when filters change (except first load)
  useEffect(() => {
    if (!isInitialMount.current) {
      setPage(1);
    }
  }, [selectedProvince, selectedDistributor, selectedType, selectedTier, selectedSaturation]);

  const resetFilters = () => {
    setSelectedProvince('');
    setSelectedDistributor('');
    setSelectedType('');
    setSelectedTier('');
    setSelectedSaturation('');
    setPage(1);
  };
  
  const totalPages = Math.ceil(totalOutlets / limit);

  return (
    <div className="space-y-8 animate-fade-in">
      {/* Title & Description */}
      <div className="flex flex-col md:flex-row justify-between md:items-center gap-4">
        <div>
          <h2 className="font-heading font-extrabold text-3xl tracking-tight text-white">Outlet Intelligence Dashboard</h2>
          <p className="text-slate-400 text-sm mt-1">Real-time beverage volume predictions, geospatial intelligence, and trade spend optimization.</p>
        </div>
      </div>

      {/* KPI Cards Grid */}
      <div className={`grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-5 gap-6 transition-opacity duration-300 ${isLoadingTable ? 'opacity-50' : 'opacity-100'}`}>
        {/* Total Outlets */}
        <div className="glass-panel p-6 rounded-2xl border-l-4 border-l-cyan-500 relative overflow-hidden group hover:scale-[1.02] transition-all duration-300">
          <div className="absolute right-4 bottom-4 text-4xl opacity-10 group-hover:scale-110 transition-transform">🏪</div>
          <p className="text-xs font-semibold uppercase tracking-wider text-slate-400">Total Outlets</p>
          <p className="text-3xl font-heading font-extrabold text-white text-glow-cyan mt-2">{stats.total_outlets}</p>
          <span className="text-[10px] text-emerald-400 flex items-center gap-1 mt-1 font-mono">
            <span>●</span> Active Sri Lankan Outlets
          </span>
        </div>

        {/* Total Predicted Liters */}
        <div className="glass-panel p-6 rounded-2xl border-l-4 border-l-violet-500 relative overflow-hidden group hover:scale-[1.02] transition-all duration-300">
          <div className="absolute right-4 bottom-4 text-4xl opacity-10 group-hover:scale-110 transition-transform">🛢️</div>
          <p className="text-xs font-semibold uppercase tracking-wider text-slate-400">Max Monthly Potential</p>
          <p className="text-3xl font-heading font-extrabold text-white mt-2">
            {Math.round(stats.total_predicted_volume).toLocaleString()} <span className="text-xs text-slate-400">L</span>
          </p>
          <span className="text-[10px] text-cyan-400 flex items-center gap-1 mt-1 font-mono">
            <span>⚡</span> January 2026 Prediction
          </span>
        </div>

        {/* Allocated Budget */}
        <div className={`glass-panel p-6 rounded-2xl border-l-4 relative overflow-hidden group hover:scale-[1.02] transition-all duration-300 ${stats.total_budget > 0 ? 'border-l-emerald-500' : 'border-l-slate-700'}`}>
          <div className="absolute right-4 bottom-4 text-4xl opacity-10 group-hover:scale-110 transition-transform">💰</div>
          <p className="text-xs font-semibold uppercase tracking-wider text-slate-400">Western Province Budget</p>
          {stats.total_budget > 0 ? (
            <>
              <p className="text-3xl font-heading font-extrabold text-white text-glow-emerald mt-2">
                LKR {Math.round(stats.total_budget).toLocaleString()}
              </p>
              <span className="text-[10px] text-emerald-400 flex items-center gap-1 mt-1 font-mono">
                <span>↗</span> Trade Spend Allocation
              </span>
            </>
          ) : (
            <>
              <p className="text-2xl font-heading font-bold text-slate-500 mt-3">
                LKR 0
              </p>
              <span className="text-[10px] text-amber-500/80 flex items-center gap-1 mt-1.5 font-mono">
                <span>ⓘ</span> Allocation Restricted to Western Province
              </span>
            </>
          )}
        </div>

        {/* High Potential Tier */}
        <div className="glass-panel p-6 rounded-2xl border-l-4 border-l-amber-500 relative overflow-hidden group hover:scale-[1.02] transition-all duration-300">
          <div className="absolute right-4 bottom-4 text-4xl opacity-10 group-hover:scale-110 transition-transform">🔥</div>
          <p className="text-xs font-semibold uppercase tracking-wider text-slate-400">High Potential Outlets</p>
          <p className="text-3xl font-heading font-extrabold text-white mt-2">{stats.high_potential_outlets}</p>
          <span className="text-[10px] text-amber-400 flex items-center gap-1 mt-1 font-mono">
            <span>★</span> T1 Priority Targets
          </span>
        </div>

        {/* Avg Capacity Utilization */}
        <div className="glass-panel p-6 rounded-2xl border-l-4 border-l-pink-500 relative overflow-hidden group hover:scale-[1.02] transition-all duration-300">
          <div className="absolute right-4 bottom-4 text-4xl opacity-10 group-hover:scale-110 transition-transform">⚙️</div>
          <p className="text-xs font-semibold uppercase tracking-wider text-slate-400">Avg Capacity Utilization</p>
          <p className="text-3xl font-heading font-extrabold text-white mt-2">
            {Math.round((stats.avg_capacity_utilization || 0) * 100)}%
          </p>
          <span className="text-[10px] text-pink-400 flex items-center gap-1 mt-1 font-mono">
            <span>📈</span> Physics-based Ceiling
          </span>
        </div>
      </div>

      {/* Filter Toolbar Component */}
      <div className="glass-panel p-5 rounded-2xl flex flex-wrap gap-4 items-end justify-between border border-slate-800">
        <div className="flex flex-wrap gap-4 items-center flex-1">
          {/* Province */}
          <div className="flex flex-col gap-1.5 min-w-[140px] flex-1 sm:flex-initial">
            <label className="text-[10px] font-semibold tracking-wider text-slate-400 uppercase">Province</label>
            <select 
              value={selectedProvince}
              onChange={(e) => setSelectedProvince(e.target.value)}
              className="bg-slate-900/80 border border-slate-800 text-slate-200 text-xs rounded-xl p-2.5 outline-none focus:border-cyan-500 transition-colors"
            >
              <option value="">All Provinces</option>
              {filterOptions.provinces.map(prov => (
                <option key={prov} value={prov}>{prov}</option>
              ))}
            </select>
          </div>

          {/* Distributor */}
          <div className="flex flex-col gap-1.5 min-w-[140px] flex-1 sm:flex-initial">
            <label className="text-[10px] font-semibold tracking-wider text-slate-400 uppercase">Distributor</label>
            <select 
              value={selectedDistributor}
              onChange={(e) => setSelectedDistributor(e.target.value)}
              className="bg-slate-900/80 border border-slate-800 text-slate-200 text-xs rounded-xl p-2.5 outline-none focus:border-cyan-500 transition-colors"
            >
              <option value="">All Distributors</option>
              {filterOptions.distributors.map(dist => (
                <option key={dist} value={dist}>{dist}</option>
              ))}
            </select>
          </div>

          {/* Type */}
          <div className="flex flex-col gap-1.5 min-w-[140px] flex-1 sm:flex-initial">
            <label className="text-[10px] font-semibold tracking-wider text-slate-400 uppercase">Outlet Type</label>
            <select 
              value={selectedType}
              onChange={(e) => setSelectedType(e.target.value)}
              className="bg-slate-900/80 border border-slate-800 text-slate-200 text-xs rounded-xl p-2.5 outline-none focus:border-cyan-500 transition-colors"
            >
              <option value="">All Types</option>
              {filterOptions.types.map(type => (
                <option key={type} value={type}>{type}</option>
              ))}
            </select>
          </div>

          {/* Tier */}
          <div className="flex flex-col gap-1.5 min-w-[140px] flex-1 sm:flex-initial">
            <label className="text-[10px] font-semibold tracking-wider text-slate-400 uppercase">Spend Tier</label>
            <select 
              value={selectedTier}
              onChange={(e) => setSelectedTier(e.target.value)}
              className="bg-slate-900/80 border border-slate-800 text-slate-200 text-xs rounded-xl p-2.5 outline-none focus:border-cyan-500 transition-colors"
            >
              <option value="">All Tiers</option>
              {filterOptions.tiers.map(tier => (
                <option key={tier} value={tier}>{tier.toUpperCase()}</option>
              ))}
            </select>
          </div>

          {/* Market Saturation */}
          <div className="flex flex-col gap-1.5 min-w-[140px] flex-1 sm:flex-initial">
            <label className="text-[10px] font-semibold tracking-wider text-slate-400 uppercase">Market Saturation</label>
            <select 
              value={selectedSaturation}
              onChange={(e) => setSelectedSaturation(e.target.value)}
              className="bg-slate-900/80 border border-slate-800 text-slate-200 text-xs rounded-xl p-2.5 outline-none focus:border-cyan-500 transition-colors"
            >
              <option value="">All Classes</option>
              {filterOptions.saturation_classes?.map(cls => (
                <option key={cls} value={cls}>{cls ? cls.charAt(0).toUpperCase() + cls.slice(1) : ''}</option>
              ))}
            </select>
          </div>
        </div>

        {/* Reset Action */}
        {(selectedProvince || selectedDistributor || selectedType || selectedTier || selectedSaturation) && (
          <button 
            onClick={resetFilters}
            className="text-xs text-rose-400 font-semibold border border-rose-500/20 hover:border-rose-500 hover:bg-rose-500/10 px-4 py-2.5 rounded-xl transition-all"
          >
            Clear Filters
          </button>
        )}
      </div>

      {/* Geospatial Map Grid */}
      <div className="grid grid-cols-1 gap-6">
        <div className="glass-panel p-5 rounded-2xl border border-slate-800/80 flex flex-col gap-4">
          <div className="flex justify-between items-center">
            <h3 className="font-heading font-bold text-lg text-white flex items-center gap-2">
              🗺️ Spatial Coverage Mapping
            </h3>
            <span className="text-[10px] font-mono text-cyan-400 tracking-wider">
              {isLoadingMap ? 'Loading points...' : `${mapPoints.length} Markers Plotted`}
            </span>
          </div>
          <div className="h-[450px] relative">
            {isLoadingMap && (
              <div className="absolute inset-0 z-50 bg-slate-900/60 flex flex-col items-center justify-center rounded-2xl">
                 <div className="w-8 h-8 rounded-full border-2 border-cyan-500 border-t-transparent animate-spin mb-3"></div>
                 <span className="text-xs text-slate-400 font-mono">Fetching Map Points...</span>
              </div>
            )}
            <MapComponent outlets={mapPoints} />
          </div>
        </div>
      </div>

      {/* Data Table Grid */}
      <div className="glass-panel rounded-2xl border border-slate-800 overflow-hidden shadow-2xl relative">
        <div className="p-6 border-b border-slate-800 flex justify-between items-center">
          <h3 className="font-heading font-bold text-lg text-white">Outlets Predicted Metrics Table</h3>
          <div className="flex items-center gap-4">
            <span className="text-xs bg-slate-800 text-slate-300 px-3 py-1 rounded-full font-mono">
              Total Records: {totalOutlets}
            </span>
            <div className="flex items-center gap-2">
              <button 
                onClick={() => setPage(p => Math.max(1, p - 1))}
                disabled={page === 1 || isLoadingTable}
                className="px-3 py-1 bg-slate-800 text-slate-300 rounded text-xs disabled:opacity-50 hover:bg-slate-700 transition-colors"
              >
                &larr; Prev
              </button>
              <span className="text-xs text-slate-400 font-mono">
                Page {page} of {totalPages || 1}
              </span>
              <button 
                onClick={() => setPage(p => Math.min(totalPages, p + 1))}
                disabled={page >= totalPages || isLoadingTable}
                className="px-3 py-1 bg-slate-800 text-slate-300 rounded text-xs disabled:opacity-50 hover:bg-slate-700 transition-colors"
              >
                Next &rarr;
              </button>
            </div>
          </div>
        </div>

        <div className="overflow-x-auto relative min-h-[300px]">
          {isLoadingTable && (
            <div className="absolute inset-0 z-10 bg-slate-900/50 flex flex-col items-center justify-center backdrop-blur-sm">
               <div className="w-8 h-8 rounded-full border-2 border-cyan-500 border-t-transparent animate-spin mb-3"></div>
            </div>
          )}
          <table className="w-full text-left text-xs border-collapse">
            <thead>
              <tr className="bg-slate-900/80 border-b border-slate-800 text-slate-400 font-semibold tracking-wider uppercase text-[10px]">
                <th className="px-6 py-4">Outlet ID</th>
                <th className="px-6 py-4">Province</th>
                <th className="px-6 py-4">Outlet Type</th>
                <th className="px-6 py-4">Distributor ID</th>
                <th className="px-6 py-4 text-right">Potential (L)</th>
                <th className="px-6 py-4 text-right">Recent 3M Avg (L)</th>
                <th className="px-6 py-4 text-center">T1 Potential Tier</th>
                <th className="px-6 py-4 text-center">Saturation</th>
                <th className="px-6 py-4 text-center">Actions</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-slate-800/50">
              {outlets.length > 0 ? (
                outlets.map((outlet) => (
                  <tr key={outlet.outlet_id} className="hover:bg-slate-900/40 transition-colors">
                    <td className="px-6 py-4 font-mono font-bold text-white tracking-wider">{outlet.outlet_id}</td>
                    <td className="px-6 py-4 text-slate-300">{outlet.province}</td>
                    <td className="px-6 py-4 text-slate-300">
                      <span className="px-2 py-0.5 rounded bg-slate-800 text-slate-400 border border-slate-700/50 text-[10px]">
                        {outlet.outlet_type}
                      </span>
                    </td>
                    <td className="px-6 py-4 text-slate-400 font-mono">{outlet.distributor_id}</td>
                    <td className="px-6 py-4 text-right text-white font-semibold font-mono">
                      {Math.round(outlet.predicted_potential_litres || 0).toLocaleString()}
                    </td>
                    <td className="px-6 py-4 text-right text-slate-400 font-mono">
                      {Math.round(outlet.recent_3m_avg || 0).toLocaleString()}
                    </td>
                    <td className="px-6 py-4 text-center">
                      <span className={`px-2 py-0.5 rounded text-[9px] uppercase font-extrabold tracking-wider ${
                        outlet.allocation_tier === 'high' ? 'bg-emerald-500/20 text-emerald-400 border border-emerald-500/30' :
                        outlet.allocation_tier === 'medium' ? 'bg-amber-500/20 text-amber-400 border border-amber-500/30' :
                        outlet.allocation_tier === 'low' ? 'bg-rose-500/20 text-rose-400 border border-rose-500/30' :
                        'bg-slate-800 text-slate-500'
                      }`}>
                        {outlet.allocation_tier && outlet.allocation_tier !== 'none' ? outlet.allocation_tier : 'NONE'}
                      </span>
                    </td>
                    <td className="px-6 py-4 text-center">
                      <span className={`px-2 py-0.5 rounded text-[9px] uppercase font-extrabold tracking-wider ${
                        outlet.market_saturation_class === 'isolated' ? 'bg-emerald-500/20 text-emerald-400 border border-emerald-500/30' :
                        outlet.market_saturation_class === 'moderate' ? 'bg-amber-500/20 text-amber-400 border border-amber-500/30' :
                        outlet.market_saturation_class === 'dense' ? 'bg-rose-500/20 text-rose-400 border border-rose-500/30' :
                        'bg-slate-800 text-slate-500'
                      }`}>
                        {outlet.market_saturation_class || 'UNKNOWN'}
                      </span>
                    </td>
                    <td className="px-6 py-4 text-center">
                      <Link 
                        href={`/outlets/${outlet.outlet_id}`}
                        className="inline-flex items-center gap-1.5 px-3 py-1.5 rounded-lg bg-cyan-500/10 text-cyan-400 font-semibold border border-cyan-500/20 hover:bg-cyan-500 hover:text-slate-950 transition-all text-[11px]"
                      >
                        Details &rarr;
                      </Link>
                    </td>
                  </tr>
                ))
              ) : (
                <tr>
                  <td colSpan={8} className="px-6 py-12 text-center text-slate-500 font-mono">
                    ⚠️ No outlets match the selected filters.
                  </td>
                </tr>
              )}
            </tbody>
          </table>
        </div>
      </div>
    </div>
  );
}
