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
            <div className="absolute inset-0 overflow-hidden opacity-20">
                <svg
                    viewBox="0 0 1000 500"
                    className="w-full h-full"
                    preserveAspectRatio="xMidYMid slice"
                >
                    {/* Simplified world map paths */}
                    <defs>
                        <linearGradient id="mapGradient" x1="0%" y1="0%" x2="100%" y2="100%">
                            <stop offset="0%" stopColor="#3b82f6" stopOpacity="0.3" />
                            <stop offset="100%" stopColor="#8b5cf6" stopOpacity="0.3" />
                        </linearGradient>
                    </defs>

                    {/* Grid lines */}
                    {[...Array(10)].map((_, i) => (
                        <line
                            key={`h-${i}`}
                            x1="0"
                            y1={i * 50}
                            x2="1000"
                            y2={i * 50}
                            stroke="#3b82f6"
                            strokeOpacity="0.1"
                            strokeWidth="0.5"
                        />
                    ))}
                    {[...Array(20)].map((_, i) => (
                        <line
                            key={`v-${i}`}
                            x1={i * 50}
                            y1="0"
                            x2={i * 50}
                            y2="500"
                            stroke="#3b82f6"
                            strokeOpacity="0.1"
                            strokeWidth="0.5"
                        />
                    ))}

                    {/* Simplified continent shapes */}
                    {/* North America */}
                    <path
                        d="M150,80 Q200,60 250,80 Q300,100 280,150 Q260,200 200,220 Q150,200 120,150 Q100,120 150,80"
                        fill="url(#mapGradient)"
                        stroke="#3b82f6"
                        strokeWidth="0.5"
                        strokeOpacity="0.3"
                    />

                    {/* South America */}
                    <path
                        d="M220,250 Q260,230 280,260 Q300,320 280,380 Q260,420 230,400 Q200,360 210,300 Q210,260 220,250"
                        fill="url(#mapGradient)"
                        stroke="#3b82f6"
                        strokeWidth="0.5"
                        strokeOpacity="0.3"
                    />

                    {/* Europe */}
                    <path
                        d="M450,80 Q500,60 550,80 Q580,100 560,140 Q540,160 500,150 Q460,140 450,120 Q440,100 450,80"
                        fill="url(#mapGradient)"
                        stroke="#3b82f6"
                        strokeWidth="0.5"
                        strokeOpacity="0.3"
                    />

                    {/* Africa */}
                    <path
                        d="M480,180 Q530,160 560,200 Q580,260 560,320 Q530,380 490,360 Q450,320 460,260 Q470,200 480,180"
                        fill="url(#mapGradient)"
                        stroke="#3b82f6"
                        strokeWidth="0.5"
                        strokeOpacity="0.3"
                    />

                    {/* Asia */}
                    <path
                        d="M580,80 Q700,60 820,100 Q880,140 860,200 Q800,240 720,220 Q640,200 600,160 Q560,120 580,80"
                        fill="url(#mapGradient)"
                        stroke="#3b82f6"
                        strokeWidth="0.5"
                        strokeOpacity="0.3"
                    />

                    {/* Australia */}
                    <path
                        d="M780,320 Q840,300 880,340 Q900,380 860,400 Q820,410 780,380 Q760,350 780,320"
                        fill="url(#mapGradient)"
                        stroke="#3b82f6"
                        strokeWidth="0.5"
                        strokeOpacity="0.3"
                    />

                    {/* Location markers for suppliers */}
                    {/* Taiwan */}
                    <circle cx="800" cy="180" r="4" fill="#ef4444" opacity="0.6">
                        <animate attributeName="opacity" values="0.6;1;0.6" dur="2s" repeatCount="indefinite" />
                    </circle>

                    {/* Germany */}
                    <circle cx="510" cy="100" r="3" fill="#10b981" opacity="0.6" />

                    {/* Vietnam */}
                    <circle cx="760" cy="210" r="3" fill="#3b82f6" opacity="0.6" />

                    {/* China/Shanghai */}
                    <circle cx="780" cy="160" r="3" fill="#f59e0b" opacity="0.6" />

                    {/* Korea */}
                    <circle cx="820" cy="140" r="3" fill="#3b82f6" opacity="0.6" />
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

