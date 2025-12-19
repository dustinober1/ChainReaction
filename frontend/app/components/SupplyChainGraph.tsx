"use client";

import { useCallback, useEffect, useRef, useState, useMemo } from "react";
import {
    ComposableMap,
    Geographies,
    Geography,
    Marker,
    Line,
    ZoomableGroup,
} from "react-simple-maps";

// World map TopoJSON
const geoUrl = "https://cdn.jsdelivr.net/npm/world-atlas@2/countries-110m.json";

export interface GraphNode {
    id: string;
    label: string;
    type: "supplier" | "component" | "product" | "risk";
    name: string;
    riskScore?: number;
    location?: string;
    isAtRisk?: boolean;
    isRiskSource?: boolean;
    lat?: number;
    lng?: number;
}

export interface GraphLink {
    source: string;
    target: string;
    type: string;
}

export interface GraphData {
    nodes: GraphNode[];
    links: GraphLink[];
}

interface SupplyChainGraphProps {
    data: GraphData;
    onNodeClick?: (node: GraphNode) => void;
    onNodeHover?: (node: GraphNode | null) => void;
    selectedNode?: string | null;
    highlightedNodes?: Set<string>;
}

// Geographic coordinates [longitude, latitude] for supplier locations
const LOCATION_COORDS: Record<string, [number, number]> = {
    "Taiwan": [121.5654, 25.0330],
    "Vietnam": [105.8342, 21.0278],
    "Germany": [10.4515, 51.1657],
    "China": [121.4737, 31.2304], // Shanghai
    "Korea": [126.9780, 37.5665], // Seoul
    "USA": [-95.7129, 37.0902],
    "Japan": [139.6917, 35.6895],
    "India": [78.9629, 20.5937],
};

// Color mapping for node types
const NODE_COLORS: Record<string, string> = {
    supplier: "#3b82f6",
    component: "#8b5cf6",
    product: "#10b981",
    risk: "#ef4444",
};

const getNodeColor = (node: GraphNode, isSelected: boolean, isHighlighted: boolean): string => {
    if (isSelected) return "#ffffff";
    if (node.isRiskSource) return "#ef4444";
    if (node.isAtRisk) return "#f59e0b";
    return NODE_COLORS[node.type] || "#6b7280";
};

const getNodeSize = (node: GraphNode): number => {
    if (node.type === "risk") return 12;
    if (node.type === "supplier") return 10;
    if (node.type === "product") return 8;
    if (node.type === "component") return 6;
    return 5;
};

export default function SupplyChainGraph({
    data,
    onNodeClick,
    onNodeHover,
    selectedNode,
    highlightedNodes = new Set(),
}: SupplyChainGraphProps) {
    const [hoveredNode, setHoveredNode] = useState<string | null>(null);
    const containerRef = useRef<HTMLDivElement>(null);

    // Process nodes to get their coordinates
    const nodePositions = useMemo(() => {
        const positions: Record<string, { coords: [number, number]; offset: [number, number] }> = {};

        // First: Position suppliers at their geographic locations
        data.nodes.forEach((node) => {
            if (node.type === "supplier" && node.location && LOCATION_COORDS[node.location]) {
                positions[node.id] = {
                    coords: LOCATION_COORDS[node.location],
                    offset: [0, 0],
                };
            }
        });

        // Second: Position components near their suppliers
        data.nodes.forEach((node, index) => {
            if (node.type === "component") {
                const connectedSuppliers = data.links
                    .filter(link => link.target === node.id || link.source === node.id)
                    .map(link => link.source === node.id ? link.target : link.source)
                    .filter(id => positions[id]);

                if (connectedSuppliers.length > 0) {
                    let avgLon = 0, avgLat = 0;
                    connectedSuppliers.forEach(supplierId => {
                        avgLon += positions[supplierId].coords[0];
                        avgLat += positions[supplierId].coords[1];
                    });
                    avgLon /= connectedSuppliers.length;
                    avgLat /= connectedSuppliers.length;

                    // Offset to avoid overlap
                    const angle = (index * 0.7) + Math.PI / 3;
                    const distance = 5 + (index % 3) * 3;
                    positions[node.id] = {
                        coords: [
                            avgLon + Math.cos(angle) * distance,
                            avgLat + Math.sin(angle) * distance,
                        ],
                        offset: [0, 0],
                    };
                }
            }
        });

        // Third: Position products and risks
        data.nodes.forEach((node, index) => {
            if ((node.type === "product" || node.type === "risk") && !positions[node.id]) {
                const connectedNodes = data.links
                    .filter(link => link.target === node.id || link.source === node.id)
                    .map(link => link.source === node.id ? link.target : link.source)
                    .filter(id => positions[id]);

                if (connectedNodes.length > 0) {
                    let avgLon = 0, avgLat = 0;
                    connectedNodes.forEach(nodeId => {
                        avgLon += positions[nodeId].coords[0];
                        avgLat += positions[nodeId].coords[1];
                    });
                    avgLon /= connectedNodes.length;
                    avgLat /= connectedNodes.length;

                    const yOffset = node.type === "risk" ? 8 : -8;
                    const xOffset = (index % 4 - 2) * 4;
                    positions[node.id] = {
                        coords: [avgLon + xOffset, avgLat + yOffset],
                        offset: [0, 0],
                    };
                }
            }
        });

        return positions;
    }, [data]);

    // Get connections for drawing lines
    const connections = useMemo(() => {
        return data.links
            .filter(link => {
                const sourcePos = nodePositions[typeof link.source === 'object' ? (link.source as any).id : link.source];
                const targetPos = nodePositions[typeof link.target === 'object' ? (link.target as any).id : link.target];
                return sourcePos && targetPos;
            })
            .map(link => ({
                source: nodePositions[typeof link.source === 'object' ? (link.source as any).id : link.source].coords,
                target: nodePositions[typeof link.target === 'object' ? (link.target as any).id : link.target].coords,
                type: link.type,
            }));
    }, [data.links, nodePositions]);

    const handleNodeClick = useCallback((node: GraphNode) => {
        if (onNodeClick) {
            onNodeClick(node);
        }
    }, [onNodeClick]);

    return (
        <div ref={containerRef} className="w-full h-full graph-container relative bg-gray-900 rounded-xl overflow-hidden">
            <ComposableMap
                projection="geoMercator"
                projectionConfig={{
                    scale: 140,
                    center: [80, 25], // Center on Asia
                }}
                style={{ width: "100%", height: "100%" }}
            >
                <ZoomableGroup center={[80, 25]} zoom={1}>
                    {/* Map background */}
                    <Geographies geography={geoUrl}>
                        {({ geographies }) =>
                            geographies.map((geo) => (
                                <Geography
                                    key={geo.rsmKey}
                                    geography={geo}
                                    fill="#1e3a5f"
                                    stroke="#3b82f6"
                                    strokeWidth={0.5}
                                    style={{
                                        default: { outline: "none" },
                                        hover: { fill: "#2d4a6f", outline: "none" },
                                        pressed: { outline: "none" },
                                    }}
                                />
                            ))
                        }
                    </Geographies>

                    {/* Connection lines */}
                    {connections.map((conn, index) => (
                        <Line
                            key={`line-${index}`}
                            from={conn.source}
                            to={conn.target}
                            stroke="#60a5fa"
                            strokeWidth={1}
                            strokeOpacity={0.4}
                            strokeLinecap="round"
                        />
                    ))}

                    {/* Node markers */}
                    {data.nodes.map((node) => {
                        const position = nodePositions[node.id];
                        if (!position) return null;

                        const isSelected = selectedNode === node.id;
                        const isHighlighted = highlightedNodes.has(node.id);
                        const isHovered = hoveredNode === node.id;
                        const size = getNodeSize(node);
                        const color = getNodeColor(node, isSelected, isHighlighted);

                        return (
                            <Marker
                                key={node.id}
                                coordinates={position.coords}
                                onClick={() => handleNodeClick(node)}
                                onMouseEnter={() => {
                                    setHoveredNode(node.id);
                                    onNodeHover?.(node);
                                }}
                                onMouseLeave={() => {
                                    setHoveredNode(null);
                                    onNodeHover?.(null);
                                }}
                                style={{ cursor: "pointer" }}
                            >
                                {/* Glow effect for highlighted/selected nodes */}
                                {(isSelected || isHighlighted || node.isRiskSource) && (
                                    <circle
                                        r={size + 6}
                                        fill={node.isRiskSource ? "#ef4444" : isSelected ? "#3b82f6" : "#f59e0b"}
                                        opacity={0.3}
                                    >
                                        {node.isRiskSource && (
                                            <animate
                                                attributeName="r"
                                                values={`${size + 4};${size + 10};${size + 4}`}
                                                dur="2s"
                                                repeatCount="indefinite"
                                            />
                                        )}
                                    </circle>
                                )}

                                {/* Main node circle */}
                                <circle
                                    r={isHovered ? size + 2 : size}
                                    fill={color}
                                    stroke={isSelected ? "#fff" : "rgba(255,255,255,0.3)"}
                                    strokeWidth={isSelected ? 2 : 1}
                                    style={{
                                        transition: "all 0.2s ease",
                                    }}
                                />

                                {/* Node label */}
                                <text
                                    textAnchor="middle"
                                    y={size + 12}
                                    style={{
                                        fontFamily: "Inter, system-ui, sans-serif",
                                        fontSize: "8px",
                                        fill: "#fff",
                                        fontWeight: isSelected ? 600 : 400,
                                        opacity: isHovered || isSelected ? 1 : 0.7,
                                        pointerEvents: "none",
                                    }}
                                >
                                    {node.name}
                                </text>
                            </Marker>
                        );
                    })}
                </ZoomableGroup>
            </ComposableMap>

            {/* Legend */}
            <div className="absolute bottom-4 left-4 glass-card px-3 py-2">
                <div className="flex items-center gap-4 text-xs">
                    <div className="flex items-center gap-1.5">
                        <div className="w-3 h-3 rounded-full bg-blue-500" />
                        <span className="text-gray-400">Supplier</span>
                    </div>
                    <div className="flex items-center gap-1.5">
                        <div className="w-3 h-3 rounded-full bg-purple-500" />
                        <span className="text-gray-400">Component</span>
                    </div>
                    <div className="flex items-center gap-1.5">
                        <div className="w-3 h-3 rounded-full bg-emerald-500" />
                        <span className="text-gray-400">Product</span>
                    </div>
                    <div className="flex items-center gap-1.5">
                        <div className="w-3 h-3 rounded-full bg-red-500" />
                        <span className="text-gray-400">Risk</span>
                    </div>
                    <div className="flex items-center gap-1.5">
                        <div className="w-3 h-3 rounded-full bg-amber-500" />
                        <span className="text-gray-400">At Risk</span>
                    </div>
                </div>
            </div>
        </div>
    );
}
