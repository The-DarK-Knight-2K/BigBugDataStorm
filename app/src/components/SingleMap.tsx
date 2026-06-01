"use client";

import { useEffect, useState } from 'react';
import { MapContainer, TileLayer, Marker, Popup } from 'react-leaflet';
import 'leaflet/dist/leaflet.css';

interface SingleMapProps {
  outlet: {
    outlet_id: string;
    latitude: number;
    longitude: number;
    outlet_type: string;
    allocation_tier?: string;
  };
}

export default function SingleMap({ outlet }: SingleMapProps) {
  const [isMounted, setIsMounted] = useState(false);

  useEffect(() => {
    setIsMounted(true);
  }, []);

  if (!isMounted) {
    return (
      <div className="w-full h-full min-h-[300px] rounded-xl bg-slate-900/60 border border-slate-800 flex items-center justify-center">
        <div className="flex flex-col items-center gap-3">
          <div className="w-8 h-8 rounded-full border-2 border-cyan-500 border-t-transparent animate-spin"></div>
          <span className="text-xs text-slate-400 font-mono">Initializing Spatial Map...</span>
        </div>
      </div>
    );
  }

  // Helper to create glowing markers by potential tier
  const createGlowingIcon = (tier?: string) => {
    // eslint-disable-next-line @typescript-eslint/no-require-imports
    const L = require('leaflet');
    let colorClass = 'bg-cyan-500 shadow-cyan-500/80'; // fallback
    if (tier === 'high') colorClass = 'bg-emerald-500 shadow-emerald-500/80';
    else if (tier === 'medium') colorClass = 'bg-amber-500 shadow-amber-500/80';
    else if (tier === 'low') colorClass = 'bg-rose-500 shadow-rose-500/80';

    return L.divIcon({
      className: 'custom-leaflet-icon',
      html: `<div class="relative w-4 h-4 flex items-center justify-center">
        <div class="absolute w-4 h-4 rounded-full ${colorClass} shadow-[0_0_12px_2px] animate-ping opacity-40"></div>
        <div class="w-2.5 h-2.5 rounded-full ${colorClass} shadow-[0_0_8px_1px] border border-white/20"></div>
      </div>`,
      iconSize: [16, 16],
      iconAnchor: [8, 8]
    });
  };

  return (
    <div className="w-full h-full min-h-[300px] rounded-xl border border-slate-800/80 overflow-hidden shadow-2xl relative z-10">
      <MapContainer 
        center={[outlet.latitude, outlet.longitude]} 
        zoom={15} 
        style={{ height: '100%', width: '100%', background: '#090d16' }}
        scrollWheelZoom={true}
      >
        {/* Sleek Dark CartoDB Voyager Tile Style */}
        <TileLayer
          attribution='&copy; <a href="https://www.openstreetmap.org/copyright">OpenStreetMap</a> contributors &copy; <a href="https://carto.com/attributions">CARTO</a>'
          url="https://{s}.basemaps.cartocdn.com/dark_all/{z}/{x}/{y}{r}.png"
        />
        
        <Marker 
          position={[outlet.latitude, outlet.longitude]}
          icon={createGlowingIcon(outlet.allocation_tier)}
        >
          <Popup className="custom-popup">
            <div className="p-2 text-slate-100 font-sans min-w-[120px]">
              <h4 className="font-bold text-sm tracking-tight text-white mb-1 flex items-center gap-1.5">
                <span className="text-xs">🏪</span> {outlet.outlet_id}
              </h4>
              <div className="space-y-1 text-[11px] text-slate-300">
                <p><span className="text-slate-400 font-semibold">Type:</span> {outlet.outlet_type}</p>
                {outlet.allocation_tier && (
                  <p className="flex items-center gap-1.5 mt-2">
                    <span className="text-slate-400">Tier:</span> 
                    <span className={`px-1.5 py-0.5 rounded text-[9px] uppercase font-bold tracking-wider ${
                      outlet.allocation_tier === 'high' ? 'bg-emerald-500/20 text-emerald-300 border border-emerald-500/30' :
                      outlet.allocation_tier === 'medium' ? 'bg-amber-500/20 text-amber-300 border border-amber-500/30' :
                      outlet.allocation_tier === 'low' ? 'bg-rose-500/20 text-rose-300 border border-rose-500/30' :
                      'bg-slate-700/20 text-slate-300'
                    }`}>{outlet.allocation_tier}</span>
                  </p>
                )}
              </div>
            </div>
          </Popup>
        </Marker>
      </MapContainer>
    </div>
  );
}
