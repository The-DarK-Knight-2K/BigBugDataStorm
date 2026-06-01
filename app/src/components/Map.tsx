"use client";

import React, { useEffect, useState } from 'react';
import { MapContainer, TileLayer, useMap } from 'react-leaflet';
import 'leaflet/dist/leaflet.css';

interface MapProps {
  outlets: any[][]; // [outlet_id, latitude, longitude, outlet_type, predicted_potential_litres, allocation_tier, market_saturation_class]
}

// A sub-component to handle the native Leaflet Canvas integration
function FastMapPoints({ outlets }: { outlets: any[][] }) {
  const map = useMap();

  useEffect(() => {
    // eslint-disable-next-line @typescript-eslint/no-require-imports
    const L = require('leaflet');
    
    // Create a feature group to hold all our canvas markers
    const layerGroup = L.featureGroup();

    outlets.forEach((outlet) => {
      // market_saturation_class is at index 6, but we primarily use tier (index 5) for color
      const [id, lat, lng, type, vol, tier] = outlet;
      
      let color = '#06b6d4'; // cyan default
      if (tier === 'high') color = '#10b981'; // emerald
      else if (tier === 'medium') color = '#f59e0b'; // amber
      else if (tier === 'low') color = '#f43f5e'; // rose
      
      // Native Canvas-based circle marker (bypasses React DOM completely)
      const marker = L.circleMarker([lat, lng], {
        radius: 4,
        color: color, // stroke color
        weight: 1,
        fillColor: color,
        fillOpacity: 0.6,
      });

      // Attach a lightweight click listener for on-demand popups
      marker.on('click', () => {
        // Build popup content natively to avoid rendering thousands of hidden React popups
        const popupContent = `
          <div class="p-2 font-sans min-w-[150px]">
            <h4 class="font-bold text-sm tracking-tight text-slate-800 mb-1 flex items-center gap-1.5">
              <span class="text-xs">🏪</span> ${id}
            </h4>
            <div class="space-y-1 text-[11px] text-slate-600">
              <p><span class="font-semibold">Type:</span> ${type}</p>
              <p><span class="font-semibold">Prediction:</span> ${vol ? Math.round(vol).toLocaleString() : 0} L</p>
              <p class="mt-1 flex items-center gap-1">
                <span class="font-semibold">Tier:</span> 
                <span class="px-1.5 py-0.5 rounded text-[9px] uppercase font-bold text-white shadow-sm" style="background-color: ${color}">
                  ${tier ? tier : 'N/A'}
                </span>
              </p>
            </div>
            <div class="mt-3 pt-2 border-t border-slate-200 text-right">
              <a href="/outlets/${id}" class="text-[10px] text-cyan-600 font-bold hover:text-cyan-700 transition-colors uppercase tracking-wider block">
                View Details &rarr;
              </a>
            </div>
          </div>
        `;
        
        L.popup({ className: 'canvas-popup' })
          .setLatLng([lat, lng])
          .setContent(popupContent)
          .openOn(map);
      });

      layerGroup.addLayer(marker);
    });

    // Add everything to the map in one rapid operation
    layerGroup.addTo(map);

    // Cleanup on unmount or when points change
    return () => {
      map.removeLayer(layerGroup);
    };
  }, [outlets, map]);

  return null;
}

const MapComponent = ({ outlets }: MapProps) => {
  const [isMounted, setIsMounted] = useState(false);

  useEffect(() => {
    setIsMounted(true);
  }, []);

  if (!isMounted) {
    return (
      <div className="w-full h-full min-h-[450px] rounded-2xl bg-slate-900/60 border border-slate-800 flex items-center justify-center">
        <div className="flex flex-col items-center gap-3">
          <div className="w-8 h-8 rounded-full border-2 border-cyan-500 border-t-transparent animate-spin"></div>
          <span className="text-xs text-slate-400 font-mono">Initializing Spatial Map...</span>
        </div>
      </div>
    );
  }

  return (
    <div className="w-full h-full min-h-[450px] rounded-2xl border border-slate-800/80 overflow-hidden shadow-2xl relative z-10">
      <MapContainer 
        center={[7.8731, 80.7718]} 
        zoom={8} 
        style={{ height: '100%', width: '100%', background: '#090d16' }}
        scrollWheelZoom={true}
        preferCanvas={true} // Crucial for rendering 20k points quickly
      >
        {/* Sleek Dark CartoDB Voyager Tile Style */}
        <TileLayer
          attribution='&copy; <a href="https://www.openstreetmap.org/copyright">OpenStreetMap</a> contributors &copy; <a href="https://carto.com/attributions">CARTO</a>'
          url="https://{s}.basemaps.cartocdn.com/dark_all/{z}/{x}/{y}{r}.png"
        />
        
        {/* Native Canvas Injection Component */}
        <FastMapPoints outlets={outlets} />

      </MapContainer>

      {/* Map Overlay Legend */}
      <div className="absolute bottom-4 left-4 z-[400] glass-panel p-3 rounded-xl border border-slate-800 text-[10px] space-y-1.5 pointer-events-auto bg-slate-900/80 backdrop-blur-md shadow-xl">
        <h5 className="font-bold text-white tracking-wider uppercase mb-1">Potential Tier</h5>
        <div className="flex items-center gap-2">
          <span className="w-2 h-2 rounded-full bg-emerald-500 shadow-lg shadow-emerald-500/50"></span>
          <span className="text-slate-300 font-medium">High</span>
        </div>
        <div className="flex items-center gap-2">
          <span className="w-2 h-2 rounded-full bg-amber-500 shadow-lg shadow-amber-500/50"></span>
          <span className="text-slate-300 font-medium">Medium</span>
        </div>
        <div className="flex items-center gap-2">
          <span className="w-2 h-2 rounded-full bg-rose-500 shadow-lg shadow-rose-500/50"></span>
          <span className="text-slate-300 font-medium">Low</span>
        </div>
      </div>
    </div>
  );
};

export default React.memo(MapComponent);
