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
        <div ref={containerRef} className="w-full h-full graph-container">
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
    );
}
