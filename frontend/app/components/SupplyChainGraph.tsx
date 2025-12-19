"use client";

import { useCallback, useEffect, useRef, useState } from "react";
import dynamic from "next/dynamic";

// Dynamically import ForceGraph2D to avoid SSR issues
const ForceGraph2D = dynamic(() => import("react-force-graph-2d"), {
    ssr: false,
    loading: () => (
        <div className="flex items-center justify-center h-full">
            <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-blue-500"></div>
        </div>
    ),
});

export interface GraphNode {
    id: string;
    label: string;
    type: "supplier" | "component" | "product" | "risk";
    name: string;
    riskScore?: number;
    location?: string;
    isAtRisk?: boolean;
    isRiskSource?: boolean;
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

// Color mapping for node types
const NODE_COLORS: Record<string, string> = {
    supplier: "#3b82f6",
    component: "#8b5cf6",
    product: "#10b981",
    risk: "#ef4444",
};

const getNodeColor = (node: GraphNode): string => {
    if (node.isRiskSource) return "#ef4444"; // Red for risk source
    if (node.isAtRisk) return "#f59e0b"; // Orange for at-risk
    return NODE_COLORS[node.type] || "#6b7280";
};

const getNodeSize = (node: GraphNode): number => {
    if (node.type === "risk") return 12;
    if (node.type === "product") return 10;
    if (node.type === "component") return 8;
    return 6;
};

export default function SupplyChainGraph({
    data,
    onNodeClick,
    onNodeHover,
    selectedNode,
    highlightedNodes = new Set(),
}: SupplyChainGraphProps) {
    const graphRef = useRef<any>(null);
    const containerRef = useRef<HTMLDivElement>(null);
    const [dimensions, setDimensions] = useState({ width: 800, height: 600 });

    // Update dimensions on resize
    useEffect(() => {
        const updateDimensions = () => {
            if (containerRef.current) {
                setDimensions({
                    width: containerRef.current.offsetWidth,
                    height: containerRef.current.offsetHeight,
                });
            }
        };

        updateDimensions();
        window.addEventListener("resize", updateDimensions);
        return () => window.removeEventListener("resize", updateDimensions);
    }, []);

    // Center graph on load
    useEffect(() => {
        if (graphRef.current && data.nodes.length > 0) {
            setTimeout(() => {
                graphRef.current?.zoomToFit(400, 50);
            }, 500);
        }
    }, [data]);

    const handleNodeClick = useCallback(
        (node: any) => {
            if (onNodeClick) {
                onNodeClick(node as GraphNode);
            }
            // Zoom to node
            if (graphRef.current) {
                graphRef.current.centerAt(node.x, node.y, 1000);
                graphRef.current.zoom(2, 1000);
            }
        },
        [onNodeClick]
    );

    const handleNodeHover = useCallback(
        (node: any) => {
            if (onNodeHover) {
                onNodeHover(node as GraphNode | null);
            }
        },
        [onNodeHover]
    );

    // Custom node rendering
    const nodeCanvasObject = useCallback(
        (node: any, ctx: CanvasRenderingContext2D, globalScale: number) => {
            const size = getNodeSize(node);
            const isSelected = selectedNode === node.id;
            const isHighlighted = highlightedNodes.has(node.id);

            // Draw glow for selected/highlighted nodes
            if (isSelected || isHighlighted) {
                ctx.beginPath();
                ctx.arc(node.x, node.y, size + 4, 0, 2 * Math.PI);
                ctx.fillStyle = isSelected
                    ? "rgba(59, 130, 246, 0.3)"
                    : "rgba(245, 158, 11, 0.3)";
                ctx.fill();
            }

            // Draw node
            ctx.beginPath();
            ctx.arc(node.x, node.y, size, 0, 2 * Math.PI);
            ctx.fillStyle = getNodeColor(node);
            ctx.fill();

            // Draw border
            if (isSelected) {
                ctx.strokeStyle = "#fff";
                ctx.lineWidth = 2;
                ctx.stroke();
            }

            // Draw label if zoomed in
            if (globalScale > 1) {
                const label = node.name || node.id;
                const fontSize = 10 / globalScale;
                ctx.font = `${fontSize}px Inter, sans-serif`;
                ctx.textAlign = "center";
                ctx.textBaseline = "top";
                ctx.fillStyle = "#fff";
                ctx.fillText(label, node.x, node.y + size + 2);
            }
        },
        [selectedNode, highlightedNodes]
    );

    // Custom link rendering
    const linkCanvasObject = useCallback(
        (link: any, ctx: CanvasRenderingContext2D) => {
            const start = link.source;
            const end = link.target;

            // Draw link
            ctx.beginPath();
            ctx.moveTo(start.x, start.y);
            ctx.lineTo(end.x, end.y);
            ctx.strokeStyle = "rgba(255, 255, 255, 0.1)";
            ctx.lineWidth = 1;
            ctx.stroke();
        },
        []
    );

    return (
        <div ref={containerRef} className="w-full h-full graph-container relative">
            {/* World Map Background */}
            <div className="absolute inset-0 overflow-hidden">
                <svg
                    viewBox="0 0 1000 500"
                    className="w-full h-full"
                    preserveAspectRatio="xMidYMid slice"
                >
                    {/* Background gradient */}
                    <defs>
                        <linearGradient id="mapGradient" x1="0%" y1="0%" x2="100%" y2="100%">
                            <stop offset="0%" stopColor="#1e3a5f" stopOpacity="0.8" />
                            <stop offset="100%" stopColor="#1a1a2e" stopOpacity="0.8" />
                        </linearGradient>
                        <linearGradient id="landGradient" x1="0%" y1="0%" x2="100%" y2="100%">
                            <stop offset="0%" stopColor="#3b82f6" stopOpacity="0.4" />
                            <stop offset="100%" stopColor="#6366f1" stopOpacity="0.3" />
                        </linearGradient>
                        <filter id="glow">
                            <feGaussianBlur stdDeviation="3" result="coloredBlur" />
                            <feMerge>
                                <feMergeNode in="coloredBlur" />
                                <feMergeNode in="SourceGraphic" />
                            </feMerge>
                        </filter>
                    </defs>

                    {/* Ocean background */}
                    <rect x="0" y="0" width="1000" height="500" fill="url(#mapGradient)" />

                    {/* Grid lines - latitude */}
                    {[...Array(9)].map((_, i) => (
                        <line
                            key={`lat-${i}`}
                            x1="0"
                            y1={(i + 1) * 50}
                            x2="1000"
                            y2={(i + 1) * 50}
                            stroke="#3b82f6"
                            strokeOpacity="0.15"
                            strokeWidth="0.5"
                            strokeDasharray="5,5"
                        />
                    ))}
                    {/* Grid lines - longitude */}
                    {[...Array(19)].map((_, i) => (
                        <line
                            key={`lon-${i}`}
                            x1={(i + 1) * 50}
                            y1="0"
                            x2={(i + 1) * 50}
                            y2="500"
                            stroke="#3b82f6"
                            strokeOpacity="0.15"
                            strokeWidth="0.5"
                            strokeDasharray="5,5"
                        />
                    ))}

                    {/* Simplified continent shapes */}
                    {/* North America */}
                    <path
                        d="M80,70 L120,50 L180,55 L220,70 L250,90 L270,120 L260,160 L240,190 L200,210 L160,200 L130,180 L100,150 L80,120 L75,95 Z"
                        fill="url(#landGradient)"
                        stroke="#60a5fa"
                        strokeWidth="1.5"
                        strokeOpacity="0.6"
                    />

                    {/* South America */}
                    <path
                        d="M200,230 L230,220 L260,240 L280,280 L285,330 L275,380 L250,420 L220,430 L195,400 L185,350 L190,290 L195,250 Z"
                        fill="url(#landGradient)"
                        stroke="#60a5fa"
                        strokeWidth="1.5"
                        strokeOpacity="0.6"
                    />

                    {/* Europe */}
                    <path
                        d="M440,60 L480,50 L530,55 L570,70 L590,100 L580,130 L550,150 L510,145 L470,135 L445,115 L435,85 Z"
                        fill="url(#landGradient)"
                        stroke="#60a5fa"
                        strokeWidth="1.5"
                        strokeOpacity="0.6"
                    />

                    {/* Africa */}
                    <path
                        d="M460,160 L510,150 L560,170 L590,220 L600,280 L585,340 L550,390 L500,400 L460,370 L440,320 L435,260 L445,200 Z"
                        fill="url(#landGradient)"
                        stroke="#60a5fa"
                        strokeWidth="1.5"
                        strokeOpacity="0.6"
                    />

                    {/* Asia */}
                    <path
                        d="M580,50 L650,40 L740,50 L820,80 L880,120 L920,170 L900,220 L840,250 L760,240 L680,210 L620,170 L590,120 L575,80 Z"
                        fill="url(#landGradient)"
                        stroke="#60a5fa"
                        strokeWidth="1.5"
                        strokeOpacity="0.6"
                    />

                    {/* Australia */}
                    <path
                        d="M760,310 L820,290 L880,310 L910,360 L890,410 L840,430 L780,420 L750,380 L755,340 Z"
                        fill="url(#landGradient)"
                        stroke="#60a5fa"
                        strokeWidth="1.5"
                        strokeOpacity="0.6"
                    />

                    {/* Connection lines between supplier locations */}
                    <line x1="510" y1="95" x2="780" y2="150" stroke="#60a5fa" strokeWidth="0.5" strokeOpacity="0.3" strokeDasharray="4,4" />
                    <line x1="780" y1="150" x2="800" y2="175" stroke="#60a5fa" strokeWidth="0.5" strokeOpacity="0.3" strokeDasharray="4,4" />
                    <line x1="800" y1="175" x2="760" y2="200" stroke="#60a5fa" strokeWidth="0.5" strokeOpacity="0.3" strokeDasharray="4,4" />

                    {/* Location markers for suppliers */}
                    {/* Taiwan - pulsing danger */}
                    <circle cx="800" cy="175" r="8" fill="#ef4444" opacity="0.2" filter="url(#glow)">
                        <animate attributeName="r" values="8;12;8" dur="2s" repeatCount="indefinite" />
                        <animate attributeName="opacity" values="0.2;0.4;0.2" dur="2s" repeatCount="indefinite" />
                    </circle>
                    <circle cx="800" cy="175" r="5" fill="#ef4444" opacity="0.9">
                        <animate attributeName="opacity" values="0.9;1;0.9" dur="1.5s" repeatCount="indefinite" />
                    </circle>

                    {/* Germany - stable */}
                    <circle cx="510" cy="95" r="6" fill="#10b981" opacity="0.2" filter="url(#glow)" />
                    <circle cx="510" cy="95" r="4" fill="#10b981" opacity="0.9" />

                    {/* Vietnam */}
                    <circle cx="760" cy="200" r="5" fill="#3b82f6" opacity="0.2" filter="url(#glow)" />
                    <circle cx="760" cy="200" r="3" fill="#3b82f6" opacity="0.9" />

                    {/* China/Shanghai - warning */}
                    <circle cx="780" cy="150" r="6" fill="#f59e0b" opacity="0.2" filter="url(#glow)" />
                    <circle cx="780" cy="150" r="4" fill="#f59e0b" opacity="0.9" />

                    {/* Korea */}
                    <circle cx="820" cy="135" r="5" fill="#3b82f6" opacity="0.2" filter="url(#glow)" />
                    <circle cx="820" cy="135" r="3" fill="#3b82f6" opacity="0.9" />

                    {/* Location labels */}
                    <text x="800" y="160" fill="#ef4444" fontSize="8" textAnchor="middle" opacity="0.8">Taiwan</text>
                    <text x="510" y="82" fill="#10b981" fontSize="8" textAnchor="middle" opacity="0.8">Germany</text>
                    <text x="760" y="215" fill="#3b82f6" fontSize="8" textAnchor="middle" opacity="0.8">Vietnam</text>
                    <text x="780" y="138" fill="#f59e0b" fontSize="8" textAnchor="middle" opacity="0.8">Shanghai</text>
                    <text x="820" y="150" fill="#3b82f6" fontSize="8" textAnchor="middle" opacity="0.8">Korea</text>
                </svg>
            </div>

            {/* Graph overlay */}
            <div className="relative z-10 w-full h-full">
                <ForceGraph2D
                    ref={graphRef}
                    graphData={data}
                    width={dimensions.width}
                    height={dimensions.height}
                    nodeRelSize={6}
                    nodeCanvasObject={nodeCanvasObject}
                    linkCanvasObject={linkCanvasObject}
                    onNodeClick={handleNodeClick}
                    onNodeHover={handleNodeHover}
                    cooldownTicks={100}
                    linkDirectionalArrowLength={4}
                    linkDirectionalArrowRelPos={1}
                    backgroundColor="transparent"
                    d3AlphaDecay={0.02}
                    d3VelocityDecay={0.3}
                />
            </div>
        </div>
    );
}

