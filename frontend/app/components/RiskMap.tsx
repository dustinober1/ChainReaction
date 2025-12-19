"use client";

import { useEffect, useState } from "react";
import { MapContainer, TileLayer, CircleMarker, Popup, useMap, Polygon } from "react-leaflet";
import "leaflet/dist/leaflet.css";
import { GraphNode } from "./SupplyChainGraph";

interface RiskMapProps {
    nodes: GraphNode[];
    onNodeClick?: (node: GraphNode) => void;
}

// Component to handle map view reset
function MapController({ center }: { center: [number, number] }) {
    const map = useMap();
    useEffect(() => {
        map.setView(center);
    }, [center, map]);
    return null;
}

export default function RiskMap({ nodes, onNodeClick }: RiskMapProps) {
    // Default center (Asia)
    const defaultCenter: [number, number] = [25, 110];

    // Filter only nodes with coordinates (typically suppliers)
    // For components without direct coords, we could assign their supplier's coord + offset, 
    // but for "Real World Map" usually we just map the physical entities (suppliers, warehouses).
    const mapNodes = nodes.filter(n => n.lat !== undefined && n.lng !== undefined && n.type === 'supplier');

    const getRiskColor = (score?: number) => {
        if (!score) return "#3b82f6"; // Blue default
        if (score >= 70) return "#ef4444"; // Red high
        if (score >= 40) return "#f59e0b"; // Orange medium
        return "#10b981"; // Green low
    };

    return (
        <div className="w-full h-full rounded-xl overflow-hidden bg-gray-900 relative z-0">
            <MapContainer
                center={defaultCenter}
                zoom={4}
                scrollWheelZoom={true}
                style={{ height: "100%", width: "100%", background: '#1e1e1e' }}
            >
                {/* Dark mode tiles */}
                <TileLayer
                    attribution='&copy; <a href="https://www.openstreetmap.org/copyright">OpenStreetMap</a> contributors &copy; <a href="https://carto.com/attributions">CARTO</a>'
                    url="https://{s}.basemaps.cartocdn.com/dark_all/{z}/{x}/{y}{r}.png"
                />

                {/* Simulated Weather Event: Super Typhoon approaching Taiwan */}
                <Polygon
                    positions={[
                        [21.5, 119.5], [25.5, 120.0], [26.0, 123.5], [22.0, 124.0]
                    ]}
                    pathOptions={{
                        color: '#ef4444',
                        weight: 1,
                        fillColor: '#ef4444',
                        fillOpacity: 0.15,
                        dashArray: '5, 10'
                    }}
                >
                    <Popup>
                        <div className="p-1">
                            <h3 className="font-bold text-sm text-red-600">⚠ Super Typhoon "Indra"</h3>
                            <p className="text-xs text-gray-500">Severity: Critical</p>
                            <p className="text-xs text-gray-500">Impact Radius: 400km</p>
                        </div>
                    </Popup>
                </Polygon>

                {mapNodes.map((node) => (
                    <div key={node.id}>
                        {/* Risk Halo for high risk items */}
                        {node.riskScore && node.riskScore > 40 && (
                            <CircleMarker
                                center={[node.lat!, node.lng!]}
                                radius={node.riskScore > 70 ? 25 : 15}
                                pathOptions={{
                                    color: node.riskScore > 70 ? '#ef4444' : '#f59e0b',
                                    fillColor: node.riskScore > 70 ? '#ef4444' : '#f59e0b',
                                    fillOpacity: 0.2,
                                    stroke: false
                                }}
                            />
                        )}

                        {/* Actual Node Marker */}
                        <CircleMarker
                            center={[node.lat!, node.lng!]}
                            radius={8}
                            pathOptions={{
                                color: '#ffffff',
                                weight: 2,
                                fillColor: getRiskColor(node.riskScore),
                                fillOpacity: 1
                            }}
                            eventHandlers={{
                                click: () => onNodeClick?.(node)
                            }}
                        >
                            <Popup className="glass-popup">
                                <div className="p-1">
                                    <h3 className="font-bold text-sm">{node.name}</h3>
                                    <p className="text-xs text-gray-500 mb-1">{node.location}</p>
                                    <div className="flex items-center gap-2 mt-1">
                                        <span className={`text-xs font-bold px-1.5 py-0.5 rounded ${node.riskScore && node.riskScore >= 70 ? 'bg-red-100 text-red-700' :
                                            node.riskScore && node.riskScore >= 40 ? 'bg-amber-100 text-amber-700' :
                                                'bg-green-100 text-green-700'
                                            }`}>
                                            Risk: {node.riskScore}%
                                        </span>
                                    </div>
                                </div>
                            </Popup>
                        </CircleMarker>
                    </div>
                ))}
            </MapContainer>

            {/* Legend Overlay */}
            <div className="absolute top-4 right-4 bg-gray-900/80 backdrop-blur-md p-3 rounded-lg border border-white/10 z-[1000]">
                <h4 className="text-xs font-bold text-white mb-2 uppercase tracking-wider">Risk Heatmap</h4>
                <div className="space-y-1.5">
                    <div className="flex items-center gap-2">
                        <div className="w-3 h-3 rounded-full bg-red-500 shadow-[0_0_8px_rgba(239,68,68,0.5)]"></div>
                        <span className="text-[10px] text-gray-300">High Risk (&gt;70%)</span>
                    </div>
                    <div className="flex items-center gap-2">
                        <div className="w-3 h-3 rounded-full bg-amber-500 shadow-[0_0_8px_rgba(245,158,11,0.5)]"></div>
                        <span className="text-[10px] text-gray-300">Medium Risk (40-70%)</span>
                    </div>
                    <div className="flex items-center gap-2">
                        <div className="w-3 h-3 rounded-full bg-emerald-500"></div>
                        <span className="text-[10px] text-gray-300">Low Risk (&lt;40%)</span>
                    </div>
                </div>
                <div className="mt-3 pt-2 border-t border-white/10">
                    <div className="flex items-center gap-2">
                        <div className="w-3 h-3 border border-red-500 bg-red-500/20"></div>
                        <span className="text-[10px] text-gray-300">Weather Event Zone</span>
                    </div>
                </div>
            </div>
        </div>
    );
}
