/**
 * Dashboard Visualization Utilities
 * 
 * Provides utilities for enhanced graph visualization including:
 * - Property 1: Risk Severity Color Mapping
 * - Property 2: Tooltip Content Completeness
 * - Property 3: Impact Path Highlighting
 * - Property 4: Severity Filter Correctness
 * - Property 5: Graph Performance Under Load
 */

// =============================================================================
// Types and Interfaces
// =============================================================================

export type SeverityLevel = 'critical' | 'high' | 'medium' | 'low' | 'none';

export interface RiskColorMapping {
    color: string;
    backgroundColor: string;
    borderColor: string;
    glowColor: string;
    label: string;
}

export interface TooltipContent {
    id: string;
    name: string;
    type: string;
    riskScore: number;
    severityLevel: SeverityLevel;
    location?: string;
    affectedProducts: string[];
    relatedSuppliers: string[];
    relatedComponents: string[];
    lastUpdated: string;
    additionalInfo: Record<string, unknown>;
}

export interface PathHighlight {
    nodes: string[];
    edges: Array<{ source: string; target: string }>;
    animationDuration: number;
    animationDelay: number;
}

export interface SeverityFilter {
    critical: boolean;
    high: boolean;
    medium: boolean;
    low: boolean;
    none: boolean;
}

export interface PerformanceMetrics {
    nodeCount: number;
    edgeCount: number;
    renderTime: number;
    frameRate: number;
    memoryUsage: number;
    isOptimized: boolean;
}

export interface GraphNode {
    id: string;
    label: string;
    type: 'supplier' | 'component' | 'product' | 'risk';
    name: string;
    riskScore?: number;
    location?: string;
    isAtRisk?: boolean;
    isRiskSource?: boolean;
    lat?: number;
    lng?: number;
}

export interface GraphData {
    nodes: GraphNode[];
    links: Array<{ source: string; target: string; type: string }>;
}

// =============================================================================
// Risk Severity Color Mapping (Property 1)
// =============================================================================

/**
 * WCAG 2.1 AA compliant color palette for risk severity levels.
 * All colors meet minimum contrast ratio of 4.5:1 against dark backgrounds.
 */
export const SEVERITY_COLORS: Record<SeverityLevel, RiskColorMapping> = {
    critical: {
        color: '#ef4444',        // Red-500
        backgroundColor: '#fef2f2',
        borderColor: '#dc2626',
        glowColor: 'rgba(239, 68, 68, 0.5)',
        label: 'Critical',
    },
    high: {
        color: '#f97316',        // Orange-500
        backgroundColor: '#fff7ed',
        borderColor: '#ea580c',
        glowColor: 'rgba(249, 115, 22, 0.5)',
        label: 'High',
    },
    medium: {
        color: '#eab308',        // Yellow-500
        backgroundColor: '#fefce8',
        borderColor: '#ca8a04',
        glowColor: 'rgba(234, 179, 8, 0.5)',
        label: 'Medium',
    },
    low: {
        color: '#22c55e',        // Green-500
        backgroundColor: '#f0fdf4',
        borderColor: '#16a34a',
        glowColor: 'rgba(34, 197, 94, 0.5)',
        label: 'Low',
    },
    none: {
        color: '#6b7280',        // Gray-500
        backgroundColor: '#f9fafb',
        borderColor: '#4b5563',
        glowColor: 'rgba(107, 114, 128, 0.3)',
        label: 'None',
    },
};

/**
 * Map a numeric risk score to a severity level.
 * 
 * @param score - Risk score between 0 and 1
 * @returns Corresponding severity level
 */
export function getSeverityFromScore(score: number | undefined): SeverityLevel {
    if (score === undefined || score === null) return 'none';
    if (score >= 0.8) return 'critical';
    if (score >= 0.6) return 'high';
    if (score >= 0.4) return 'medium';
    if (score >= 0.2) return 'low';
    return 'none';
}

/**
 * Get the color mapping for a given severity level.
 * 
 * @param severity - Severity level
 * @returns Color mapping object
 */
export function getColorForSeverity(severity: SeverityLevel): RiskColorMapping {
    return SEVERITY_COLORS[severity];
}

/**
 * Get the node color based on risk score.
 * 
 * @param riskScore - Numeric risk score (0-1)
 * @returns Hex color string
 */
export function getNodeColorFromScore(riskScore: number | undefined): string {
    const severity = getSeverityFromScore(riskScore);
    return SEVERITY_COLORS[severity].color;
}

/**
 * Apply severity-based colors to graph nodes.
 * 
 * @param nodes - Array of graph nodes
 * @returns Nodes with color information added
 */
export function applyColorMappingToNodes(
    nodes: GraphNode[]
): Array<GraphNode & { severityColor: string; severityLevel: SeverityLevel }> {
    return nodes.map(node => ({
        ...node,
        severityLevel: getSeverityFromScore(node.riskScore),
        severityColor: getNodeColorFromScore(node.riskScore),
    }));
}

// =============================================================================
// Tooltip Content (Property 2)
// =============================================================================

/**
 * Generate complete tooltip content for a node.
 * 
 * @param node - Graph node
 * @param graphData - Full graph data for relationship lookup
 * @returns Complete tooltip content
 */
export function generateTooltipContent(
    node: GraphNode,
    graphData: GraphData
): TooltipContent {
    // Find related entities
    const relatedLinks = graphData.links.filter(
        link => link.source === node.id || link.target === node.id
    );

    const relatedNodeIds = relatedLinks.map(link =>
        link.source === node.id ? link.target : link.source
    );

    const relatedNodes = graphData.nodes.filter(n =>
        relatedNodeIds.includes(n.id)
    );

    return {
        id: node.id,
        name: node.name || node.label,
        type: node.type,
        riskScore: node.riskScore ?? 0,
        severityLevel: getSeverityFromScore(node.riskScore),
        location: node.location,
        affectedProducts: relatedNodes
            .filter(n => n.type === 'product')
            .map(n => n.name),
        relatedSuppliers: relatedNodes
            .filter(n => n.type === 'supplier')
            .map(n => n.name),
        relatedComponents: relatedNodes
            .filter(n => n.type === 'component')
            .map(n => n.name),
        lastUpdated: new Date().toISOString(),
        additionalInfo: {
            isAtRisk: node.isAtRisk ?? false,
            isRiskSource: node.isRiskSource ?? false,
            coordinates: node.lat && node.lng ? { lat: node.lat, lng: node.lng } : null,
        },
    };
}

/**
 * Validate that tooltip content is complete.
 * 
 * @param content - Tooltip content to validate
 * @returns True if all required fields are present
 */
export function validateTooltipContent(content: TooltipContent): boolean {
    const requiredFields: (keyof TooltipContent)[] = [
        'id',
        'name',
        'type',
        'riskScore',
        'severityLevel',
        'affectedProducts',
        'relatedSuppliers',
        'relatedComponents',
        'lastUpdated',
    ];

    return requiredFields.every(field => content[field] !== undefined);
}

// =============================================================================
// Impact Path Highlighting (Property 3)
// =============================================================================

/**
 * Find all impact paths from a source node.
 * Uses BFS to find all connected nodes in the impact chain.
 * 
 * @param sourceId - Starting node ID
 * @param graphData - Graph data
 * @param maxDepth - Maximum path depth
 * @returns PathHighlight with affected nodes and edges
 */
export function findImpactPaths(
    sourceId: string,
    graphData: GraphData,
    maxDepth: number = 5
): PathHighlight {
    const visitedNodes = new Set<string>([sourceId]);
    const impactedEdges: Array<{ source: string; target: string }> = [];
    const queue: Array<{ nodeId: string; depth: number }> = [
        { nodeId: sourceId, depth: 0 },
    ];

    while (queue.length > 0) {
        const current = queue.shift();
        if (!current || current.depth >= maxDepth) continue;

        // Find connected nodes
        const connectedEdges = graphData.links.filter(
            link => link.source === current.nodeId || link.target === current.nodeId
        );

        for (const edge of connectedEdges) {
            const targetId = edge.source === current.nodeId ? edge.target : edge.source;

            if (!visitedNodes.has(targetId)) {
                visitedNodes.add(targetId);
                impactedEdges.push({
                    source: current.nodeId,
                    target: targetId,
                });
                queue.push({ nodeId: targetId, depth: current.depth + 1 });
            }
        }
    }

    return {
        nodes: Array.from(visitedNodes),
        edges: impactedEdges,
        animationDuration: 1500 + (impactedEdges.length * 100),
        animationDelay: 50,
    };
}

/**
 * Generate CSS animation keyframes for path highlighting.
 * 
 * @param pathHighlight - Path highlight data
 * @returns CSS keyframes string
 */
export function generatePathAnimationCSS(pathHighlight: PathHighlight): string {
    const { animationDuration, animationDelay } = pathHighlight;

    return `
        @keyframes pulse-glow {
            0%, 100% { 
                filter: drop-shadow(0 0 4px currentColor);
                opacity: 1;
            }
            50% { 
                filter: drop-shadow(0 0 12px currentColor);
                opacity: 0.8;
            }
        }
        
        @keyframes path-flow {
            0% { stroke-dashoffset: 20; }
            100% { stroke-dashoffset: 0; }
        }
        
        .highlighted-node {
            animation: pulse-glow ${animationDuration}ms ease-in-out infinite;
        }
        
        .highlighted-edge {
            stroke-dasharray: 5, 5;
            animation: path-flow 1s linear infinite;
            animation-delay: ${animationDelay}ms;
        }
    `;
}

// =============================================================================
// Severity Filtering (Property 4)
// =============================================================================

/**
 * Default filter state with all severities visible.
 */
export const DEFAULT_SEVERITY_FILTER: SeverityFilter = {
    critical: true,
    high: true,
    medium: true,
    low: true,
    none: true,
};

/**
 * Filter nodes based on severity filter settings.
 * 
 * @param nodes - Nodes to filter
 * @param filter - Severity filter settings
 * @returns Filtered nodes
 */
export function filterNodesBySeverity(
    nodes: GraphNode[],
    filter: SeverityFilter
): GraphNode[] {
    return nodes.filter(node => {
        const severity = getSeverityFromScore(node.riskScore);
        return filter[severity];
    });
}

/**
 * Filter graph data based on severity filter.
 * Also removes edges connected to filtered-out nodes.
 * 
 * @param graphData - Original graph data
 * @param filter - Severity filter settings
 * @returns Filtered graph data
 */
export function filterGraphBySeverity(
    graphData: GraphData,
    filter: SeverityFilter
): GraphData {
    const filteredNodes = filterNodesBySeverity(graphData.nodes, filter);
    const filteredNodeIds = new Set(filteredNodes.map(n => n.id));

    const filteredLinks = graphData.links.filter(
        link =>
            filteredNodeIds.has(link.source) && filteredNodeIds.has(link.target)
    );

    return {
        nodes: filteredNodes,
        links: filteredLinks,
    };
}

/**
 * Get count of nodes by severity level.
 * 
 * @param nodes - Nodes to count
 * @returns Record of severity to count
 */
export function countNodesBySeverity(
    nodes: GraphNode[]
): Record<SeverityLevel, number> {
    const counts: Record<SeverityLevel, number> = {
        critical: 0,
        high: 0,
        medium: 0,
        low: 0,
        none: 0,
    };

    for (const node of nodes) {
        const severity = getSeverityFromScore(node.riskScore);
        counts[severity]++;
    }

    return counts;
}

// =============================================================================
// Performance Optimization (Property 5)
// =============================================================================

/**
 * Thresholds for performance optimization decisions.
 */
export const PERFORMANCE_THRESHOLDS = {
    ENABLE_VIEWPORT_CULLING: 1000,    // Node count
    ENABLE_WEBGL: 50000,              // Node count
    DISABLE_ANIMATIONS: 10000,        // Node count
    MAX_VISIBLE_LABELS: 200,          // Label count
    TARGET_FRAME_RATE: 30,            // FPS
    MAX_RENDER_TIME: 16,              // Milliseconds
};

/**
 * Check if viewport culling should be enabled.
 * 
 * @param nodeCount - Number of nodes in the graph
 * @returns True if viewport culling should be enabled
 */
export function shouldEnableViewportCulling(nodeCount: number): boolean {
    return nodeCount >= PERFORMANCE_THRESHOLDS.ENABLE_VIEWPORT_CULLING;
}

/**
 * Check if WebGL rendering should be used.
 * 
 * @param nodeCount - Number of nodes
 * @returns True if WebGL should be used
 */
export function shouldUseWebGL(nodeCount: number): boolean {
    return nodeCount >= PERFORMANCE_THRESHOLDS.ENABLE_WEBGL;
}

/**
 * Check if animations should be disabled for performance.
 * 
 * @param nodeCount - Number of nodes
 * @returns True if animations should be disabled
 */
export function shouldDisableAnimations(nodeCount: number): boolean {
    return nodeCount >= PERFORMANCE_THRESHOLDS.DISABLE_ANIMATIONS;
}

/**
 * Calculate the number of visible labels based on node count.
 * 
 * @param nodeCount - Total node count
 * @returns Maximum number of labels to show
 */
export function getMaxVisibleLabels(nodeCount: number): number {
    if (nodeCount <= 50) return nodeCount;
    if (nodeCount <= 200) return PERFORMANCE_THRESHOLDS.MAX_VISIBLE_LABELS;
    if (nodeCount <= 1000) return Math.floor(PERFORMANCE_THRESHOLDS.MAX_VISIBLE_LABELS / 2);
    return 50;
}

/**
 * Cull nodes outside the viewport.
 * 
 * @param nodes - All nodes
 * @param viewportBounds - Viewport boundaries
 * @returns Nodes within viewport
 */
export function cullNodesOutsideViewport(
    nodes: GraphNode[],
    viewportBounds: { minLat: number; maxLat: number; minLng: number; maxLng: number }
): GraphNode[] {
    return nodes.filter(node => {
        if (!node.lat || !node.lng) return true;  // Keep nodes without coordinates
        return (
            node.lat >= viewportBounds.minLat &&
            node.lat <= viewportBounds.maxLat &&
            node.lng >= viewportBounds.minLng &&
            node.lng <= viewportBounds.maxLng
        );
    });
}

/**
 * Get performance metrics for the graph.
 * 
 * @param graphData - Graph data
 * @param renderTime - Time to render in ms
 * @returns Performance metrics
 */
export function getPerformanceMetrics(
    graphData: GraphData,
    renderTime: number
): PerformanceMetrics {
    const nodeCount = graphData.nodes.length;
    const edgeCount = graphData.links.length;

    return {
        nodeCount,
        edgeCount,
        renderTime,
        frameRate: renderTime > 0 ? Math.min(60, 1000 / renderTime) : 60,
        memoryUsage: (nodeCount * 0.5) + (edgeCount * 0.1),  // Estimate in KB
        isOptimized: renderTime <= PERFORMANCE_THRESHOLDS.MAX_RENDER_TIME,
    };
}

/**
 * Get optimization recommendations based on graph size.
 * 
 * @param nodeCount - Number of nodes
 * @returns Array of optimization recommendations
 */
export function getOptimizationRecommendations(nodeCount: number): string[] {
    const recommendations: string[] = [];

    if (shouldEnableViewportCulling(nodeCount)) {
        recommendations.push('Enable viewport culling for better performance');
    }
    if (shouldUseWebGL(nodeCount)) {
        recommendations.push('Switch to WebGL rendering for large graph');
    }
    if (shouldDisableAnimations(nodeCount)) {
        recommendations.push('Disable animations to improve responsiveness');
    }
    if (nodeCount > PERFORMANCE_THRESHOLDS.MAX_VISIBLE_LABELS * 2) {
        recommendations.push('Limit visible labels to improve render time');
    }

    return recommendations;
}
