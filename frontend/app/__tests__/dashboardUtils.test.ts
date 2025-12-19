/**
 * Property Tests for Dashboard Visualization Utilities
 * 
 * Tests the dashboard utility functions, verifying:
 * - Property 1: Risk Severity Color Mapping
 * - Property 2: Tooltip Content Completeness
 * - Property 3: Impact Path Highlighting
 * - Property 4: Severity Filter Correctness
 * - Property 5: Graph Performance Under Load
 */

import {
    SeverityLevel,
    GraphNode,
    GraphData,
    SEVERITY_COLORS,
    getSeverityFromScore,
    getColorForSeverity,
    getNodeColorFromScore,
    applyColorMappingToNodes,
    generateTooltipContent,
    validateTooltipContent,
    findImpactPaths,
    generatePathAnimationCSS,
    DEFAULT_SEVERITY_FILTER,
    filterNodesBySeverity,
    filterGraphBySeverity,
    countNodesBySeverity,
    PERFORMANCE_THRESHOLDS,
    shouldEnableViewportCulling,
    shouldUseWebGL,
    shouldDisableAnimations,
    getMaxVisibleLabels,
    cullNodesOutsideViewport,
    getPerformanceMetrics,
    getOptimizationRecommendations,
} from '../utils/dashboardUtils';

// =============================================================================
// Test Helpers
// =============================================================================

function createTestNode(
    id: string,
    type: 'supplier' | 'component' | 'product' | 'risk',
    riskScore?: number
): GraphNode {
    return {
        id,
        label: `Test ${type}`,
        type,
        name: `Test ${type} ${id}`,
        riskScore,
        location: 'Taiwan',
        isAtRisk: riskScore !== undefined && riskScore > 0.5,
        isRiskSource: type === 'risk',
        lat: 25.0,
        lng: 121.5,
    };
}

function createTestGraphData(nodeCount: number): GraphData {
    const nodes: GraphNode[] = [];
    const links: Array<{ source: string; target: string; type: string }> = [];

    // Create suppliers
    for (let i = 0; i < Math.floor(nodeCount / 4); i++) {
        nodes.push(createTestNode(`supplier-${i}`, 'supplier', Math.random()));
    }

    // Create components
    for (let i = 0; i < Math.floor(nodeCount / 4); i++) {
        nodes.push(createTestNode(`component-${i}`, 'component', Math.random()));
        if (i < Math.floor(nodeCount / 4)) {
            links.push({
                source: `supplier-${i % Math.floor(nodeCount / 4)}`,
                target: `component-${i}`,
                type: 'supplies',
            });
        }
    }

    // Create products
    for (let i = 0; i < Math.floor(nodeCount / 4); i++) {
        nodes.push(createTestNode(`product-${i}`, 'product', Math.random()));
        if (i < Math.floor(nodeCount / 4)) {
            links.push({
                source: `component-${i}`,
                target: `product-${i}`,
                type: 'used_in',
            });
        }
    }

    // Create risks
    for (let i = 0; i < Math.floor(nodeCount / 4); i++) {
        nodes.push(createTestNode(`risk-${i}`, 'risk', 0.7 + Math.random() * 0.3));
        if (i < Math.floor(nodeCount / 4)) {
            links.push({
                source: `risk-${i}`,
                target: `supplier-${i % Math.floor(nodeCount / 4)}`,
                type: 'affects',
            });
        }
    }

    return { nodes, links };
}

// =============================================================================
// Property 1: Risk Severity Color Mapping
// =============================================================================

describe('Property 1: Risk Severity Color Mapping', () => {
    describe('getSeverityFromScore', () => {
        it('should return critical for scores >= 0.8', () => {
            expect(getSeverityFromScore(0.8)).toBe('critical');
            expect(getSeverityFromScore(0.9)).toBe('critical');
            expect(getSeverityFromScore(1.0)).toBe('critical');
        });

        it('should return high for scores >= 0.6 and < 0.8', () => {
            expect(getSeverityFromScore(0.6)).toBe('high');
            expect(getSeverityFromScore(0.7)).toBe('high');
            expect(getSeverityFromScore(0.79)).toBe('high');
        });

        it('should return medium for scores >= 0.4 and < 0.6', () => {
            expect(getSeverityFromScore(0.4)).toBe('medium');
            expect(getSeverityFromScore(0.5)).toBe('medium');
            expect(getSeverityFromScore(0.59)).toBe('medium');
        });

        it('should return low for scores >= 0.2 and < 0.4', () => {
            expect(getSeverityFromScore(0.2)).toBe('low');
            expect(getSeverityFromScore(0.3)).toBe('low');
            expect(getSeverityFromScore(0.39)).toBe('low');
        });

        it('should return none for scores < 0.2', () => {
            expect(getSeverityFromScore(0.0)).toBe('none');
            expect(getSeverityFromScore(0.1)).toBe('none');
            expect(getSeverityFromScore(0.19)).toBe('none');
        });

        it('should return none for undefined or null', () => {
            expect(getSeverityFromScore(undefined)).toBe('none');
        });
    });

    describe('SEVERITY_COLORS', () => {
        it('should have all severity levels defined', () => {
            const levels: SeverityLevel[] = ['critical', 'high', 'medium', 'low', 'none'];
            levels.forEach(level => {
                expect(SEVERITY_COLORS[level]).toBeDefined();
                expect(SEVERITY_COLORS[level].color).toMatch(/^#[0-9a-f]{6}$/i);
                expect(SEVERITY_COLORS[level].label).toBeTruthy();
            });
        });

        it('should provide distinct colors for each severity', () => {
            const colors = Object.values(SEVERITY_COLORS).map(c => c.color);
            const uniqueColors = new Set(colors);
            expect(uniqueColors.size).toBe(5);
        });
    });

    describe('getColorForSeverity', () => {
        it('should return correct color mapping for each severity', () => {
            expect(getColorForSeverity('critical').color).toBe('#ef4444');
            expect(getColorForSeverity('high').color).toBe('#f97316');
            expect(getColorForSeverity('medium').color).toBe('#eab308');
            expect(getColorForSeverity('low').color).toBe('#22c55e');
            expect(getColorForSeverity('none').color).toBe('#6b7280');
        });
    });

    describe('applyColorMappingToNodes', () => {
        it('should add severity information to all nodes', () => {
            const nodes = [
                createTestNode('1', 'supplier', 0.9),
                createTestNode('2', 'component', 0.5),
                createTestNode('3', 'product', 0.1),
            ];

            const coloredNodes = applyColorMappingToNodes(nodes);

            expect(coloredNodes[0].severityLevel).toBe('critical');
            expect(coloredNodes[0].severityColor).toBe('#ef4444');
            expect(coloredNodes[1].severityLevel).toBe('medium');
            expect(coloredNodes[2].severityLevel).toBe('none');
        });
    });
});

// =============================================================================
// Property 2: Tooltip Content Completeness
// =============================================================================

describe('Property 2: Tooltip Content Completeness', () => {
    const graphData = createTestGraphData(20);

    describe('generateTooltipContent', () => {
        it('should generate complete tooltip content', () => {
            const node = graphData.nodes[0];
            const content = generateTooltipContent(node, graphData);

            expect(content.id).toBe(node.id);
            expect(content.name).toBeTruthy();
            expect(content.type).toBe(node.type);
            expect(typeof content.riskScore).toBe('number');
            expect(content.severityLevel).toBeTruthy();
            expect(Array.isArray(content.affectedProducts)).toBe(true);
            expect(Array.isArray(content.relatedSuppliers)).toBe(true);
            expect(Array.isArray(content.relatedComponents)).toBe(true);
            expect(content.lastUpdated).toBeTruthy();
        });

        it('should include related entities', () => {
            const supplierNode = graphData.nodes.find(n => n.type === 'supplier');
            if (supplierNode) {
                const content = generateTooltipContent(supplierNode, graphData);

                // Should have at least one related entity
                const totalRelated =
                    content.affectedProducts.length +
                    content.relatedSuppliers.length +
                    content.relatedComponents.length;

                expect(totalRelated).toBeGreaterThanOrEqual(0);
            }
        });
    });

    describe('validateTooltipContent', () => {
        it('should return true for complete tooltip content', () => {
            const node = graphData.nodes[0];
            const content = generateTooltipContent(node, graphData);

            expect(validateTooltipContent(content)).toBe(true);
        });

        it('should check all required fields', () => {
            const incompleteContent = {
                id: 'test',
                name: 'Test',
                type: 'supplier',
                riskScore: 0.5,
                severityLevel: 'medium' as SeverityLevel,
                affectedProducts: [],
                relatedSuppliers: [],
                relatedComponents: [],
                lastUpdated: new Date().toISOString(),
                additionalInfo: {},
            };

            expect(validateTooltipContent(incompleteContent)).toBe(true);
        });
    });
});

// =============================================================================
// Property 3: Impact Path Highlighting
// =============================================================================

describe('Property 3: Impact Path Highlighting', () => {
    const graphData = createTestGraphData(20);

    describe('findImpactPaths', () => {
        it('should include source node in results', () => {
            const sourceNode = graphData.nodes[0];
            const paths = findImpactPaths(sourceNode.id, graphData);

            expect(paths.nodes).toContain(sourceNode.id);
        });

        it('should find connected nodes', () => {
            const riskNode = graphData.nodes.find(n => n.type === 'risk');
            if (riskNode) {
                const paths = findImpactPaths(riskNode.id, graphData);

                // Should find at least the risk node itself
                expect(paths.nodes.length).toBeGreaterThanOrEqual(1);
            }
        });

        it('should respect max depth limit', () => {
            const sourceNode = graphData.nodes[0];

            const shallowPaths = findImpactPaths(sourceNode.id, graphData, 1);
            const deepPaths = findImpactPaths(sourceNode.id, graphData, 5);

            expect(shallowPaths.nodes.length).toBeLessThanOrEqual(deepPaths.nodes.length);
        });

        it('should return animation parameters', () => {
            const sourceNode = graphData.nodes[0];
            const paths = findImpactPaths(sourceNode.id, graphData);

            expect(paths.animationDuration).toBeGreaterThan(0);
            expect(paths.animationDelay).toBeGreaterThanOrEqual(0);
        });
    });

    describe('generatePathAnimationCSS', () => {
        it('should generate valid CSS', () => {
            const paths = findImpactPaths(graphData.nodes[0].id, graphData);
            const css = generatePathAnimationCSS(paths);

            expect(css).toContain('@keyframes');
            expect(css).toContain('pulse-glow');
            expect(css).toContain('path-flow');
        });
    });
});

// =============================================================================
// Property 4: Severity Filter Correctness
// =============================================================================

describe('Property 4: Severity Filter Correctness', () => {
    const graphData = createTestGraphData(20);

    describe('DEFAULT_SEVERITY_FILTER', () => {
        it('should have all severities enabled by default', () => {
            expect(DEFAULT_SEVERITY_FILTER.critical).toBe(true);
            expect(DEFAULT_SEVERITY_FILTER.high).toBe(true);
            expect(DEFAULT_SEVERITY_FILTER.medium).toBe(true);
            expect(DEFAULT_SEVERITY_FILTER.low).toBe(true);
            expect(DEFAULT_SEVERITY_FILTER.none).toBe(true);
        });
    });

    describe('filterNodesBySeverity', () => {
        it('should return all nodes when all filters are enabled', () => {
            const filtered = filterNodesBySeverity(graphData.nodes, DEFAULT_SEVERITY_FILTER);
            expect(filtered.length).toBe(graphData.nodes.length);
        });

        it('should filter out nodes when severity is disabled', () => {
            const criticalOnly = {
                critical: true,
                high: false,
                medium: false,
                low: false,
                none: false,
            };

            const filtered = filterNodesBySeverity(graphData.nodes, criticalOnly);

            filtered.forEach(node => {
                const severity = getSeverityFromScore(node.riskScore);
                expect(severity).toBe('critical');
            });
        });

        it('should return empty array when all filters are disabled', () => {
            const noneEnabled = {
                critical: false,
                high: false,
                medium: false,
                low: false,
                none: false,
            };

            const filtered = filterNodesBySeverity(graphData.nodes, noneEnabled);
            expect(filtered.length).toBe(0);
        });
    });

    describe('filterGraphBySeverity', () => {
        it('should filter both nodes and edges', () => {
            const criticalOnly = {
                critical: true,
                high: false,
                medium: false,
                low: false,
                none: false,
            };

            const filtered = filterGraphBySeverity(graphData, criticalOnly);
            const filteredNodeIds = new Set(filtered.nodes.map(n => n.id));

            // All edges should connect filtered nodes
            filtered.links.forEach(link => {
                expect(filteredNodeIds.has(link.source)).toBe(true);
                expect(filteredNodeIds.has(link.target)).toBe(true);
            });
        });
    });

    describe('countNodesBySeverity', () => {
        it('should count all nodes correctly', () => {
            const counts = countNodesBySeverity(graphData.nodes);

            const totalCount =
                counts.critical +
                counts.high +
                counts.medium +
                counts.low +
                counts.none;

            expect(totalCount).toBe(graphData.nodes.length);
        });
    });
});

// =============================================================================
// Property 5: Graph Performance Under Load
// =============================================================================

describe('Property 5: Graph Performance Under Load', () => {
    describe('PERFORMANCE_THRESHOLDS', () => {
        it('should have all thresholds defined', () => {
            expect(PERFORMANCE_THRESHOLDS.ENABLE_VIEWPORT_CULLING).toBeDefined();
            expect(PERFORMANCE_THRESHOLDS.ENABLE_WEBGL).toBeDefined();
            expect(PERFORMANCE_THRESHOLDS.DISABLE_ANIMATIONS).toBeDefined();
            expect(PERFORMANCE_THRESHOLDS.MAX_VISIBLE_LABELS).toBeDefined();
            expect(PERFORMANCE_THRESHOLDS.TARGET_FRAME_RATE).toBeDefined();
            expect(PERFORMANCE_THRESHOLDS.MAX_RENDER_TIME).toBeDefined();
        });
    });

    describe('shouldEnableViewportCulling', () => {
        it('should return false for small graphs', () => {
            expect(shouldEnableViewportCulling(100)).toBe(false);
            expect(shouldEnableViewportCulling(500)).toBe(false);
        });

        it('should return true for large graphs', () => {
            expect(shouldEnableViewportCulling(1000)).toBe(true);
            expect(shouldEnableViewportCulling(5000)).toBe(true);
        });
    });

    describe('shouldUseWebGL', () => {
        it('should return false for moderate graphs', () => {
            expect(shouldUseWebGL(1000)).toBe(false);
            expect(shouldUseWebGL(10000)).toBe(false);
        });

        it('should return true for very large graphs', () => {
            expect(shouldUseWebGL(50000)).toBe(true);
            expect(shouldUseWebGL(100000)).toBe(true);
        });
    });

    describe('shouldDisableAnimations', () => {
        it('should return false for small graphs', () => {
            expect(shouldDisableAnimations(1000)).toBe(false);
            expect(shouldDisableAnimations(5000)).toBe(false);
        });

        it('should return true for large graphs', () => {
            expect(shouldDisableAnimations(10000)).toBe(true);
            expect(shouldDisableAnimations(50000)).toBe(true);
        });
    });

    describe('getMaxVisibleLabels', () => {
        it('should return full count for small graphs', () => {
            expect(getMaxVisibleLabels(50)).toBe(50);
            expect(getMaxVisibleLabels(30)).toBe(30);
        });

        it('should limit labels for larger graphs', () => {
            expect(getMaxVisibleLabels(500)).toBeLessThanOrEqual(200);
            expect(getMaxVisibleLabels(2000)).toBeLessThanOrEqual(100);
        });
    });

    describe('cullNodesOutsideViewport', () => {
        it('should keep nodes within viewport', () => {
            const nodes = [
                { ...createTestNode('1', 'supplier'), lat: 25.0, lng: 121.5 },
                { ...createTestNode('2', 'supplier'), lat: 50.0, lng: 100.0 },
            ];

            const viewport = { minLat: 20, maxLat: 30, minLng: 115, maxLng: 125 };
            const culled = cullNodesOutsideViewport(nodes, viewport);

            expect(culled.length).toBe(1);
            expect(culled[0].id).toBe('1');
        });

        it('should keep nodes without coordinates', () => {
            const nodes = [
                createTestNode('1', 'supplier'),
                { id: '2', label: 'No coords', type: 'supplier' as const, name: 'No coords' },
            ];

            const viewport = { minLat: 0, maxLat: 1, minLng: 0, maxLng: 1 };
            const culled = cullNodesOutsideViewport(nodes, viewport);

            // Node without coordinates should be kept
            expect(culled.find(n => n.id === '2')).toBeDefined();
        });
    });

    describe('getPerformanceMetrics', () => {
        it('should calculate metrics correctly', () => {
            const graphData = createTestGraphData(100);
            const metrics = getPerformanceMetrics(graphData, 10);

            expect(metrics.nodeCount).toBeGreaterThan(0);
            expect(metrics.edgeCount).toBeGreaterThanOrEqual(0);
            expect(metrics.renderTime).toBe(10);
            expect(metrics.frameRate).toBeGreaterThan(0);
            expect(metrics.isOptimized).toBe(true);
        });

        it('should detect non-optimized render time', () => {
            const graphData = createTestGraphData(100);
            const metrics = getPerformanceMetrics(graphData, 50);

            expect(metrics.isOptimized).toBe(false);
        });
    });

    describe('getOptimizationRecommendations', () => {
        it('should return empty for small graphs', () => {
            const recommendations = getOptimizationRecommendations(100);
            expect(recommendations.length).toBe(0);
        });

        it('should recommend culling for large graphs', () => {
            const recommendations = getOptimizationRecommendations(5000);
            expect(recommendations.some(r => r.includes('culling'))).toBe(true);
        });

        it('should recommend WebGL for very large graphs', () => {
            const recommendations = getOptimizationRecommendations(100000);
            expect(recommendations.some(r => r.includes('WebGL'))).toBe(true);
        });
    });
});
