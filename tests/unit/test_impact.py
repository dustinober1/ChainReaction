"""
Unit tests for the GraphRAG impact analysis engine.
"""

import pytest
from datetime import datetime, timezone

from src.graph.traversal import (
    GraphNode,
    GraphEdge,
    TraversalPath,
    ImpactResult,
    InMemoryGraph,
)
from src.graph.impact import (
    ImpactCalculator,
    RedundancyAnalyzer,
    ImpactScore,
    SupplierRedundancy,
)
from src.models import RiskEvent, EventType, SeverityLevel


class TestGraphNode:
    """Tests for GraphNode class."""

    def test_node_creation(self):
        """Test creating a graph node."""
        node = GraphNode(
            id="SUP-001",
            label="Supplier",
            properties={"name": "Test Supplier"},
            depth=2,
        )

        assert node.id == "SUP-001"
        assert node.label == "Supplier"
        assert node.properties["name"] == "Test Supplier"
        assert node.depth == 2


class TestGraphEdge:
    """Tests for GraphEdge class."""

    def test_edge_creation(self):
        """Test creating a graph edge."""
        edge = GraphEdge(
            source_id="SUP-001",
            target_id="COMP-001",
            relationship_type="SUPPLIES",
            properties={"priority": 1},
        )

        assert edge.source_id == "SUP-001"
        assert edge.target_id == "COMP-001"
        assert edge.relationship_type == "SUPPLIES"
        assert edge.properties["priority"] == 1


class TestTraversalPath:
    """Tests for TraversalPath class."""

    def test_path_creation(self):
        """Test creating a traversal path."""
        nodes = [
            GraphNode(id="SUP-001", label="Supplier", depth=0),
            GraphNode(id="COMP-001", label="Component", depth=1),
            GraphNode(id="PROD-001", label="Product", depth=2),
        ]
        edges = [
            GraphEdge(source_id="SUP-001", target_id="COMP-001", relationship_type="SUPPLIES"),
            GraphEdge(source_id="COMP-001", target_id="PROD-001", relationship_type="PART_OF"),
        ]

        path = TraversalPath(nodes=nodes, edges=edges, total_depth=2)

        assert path.start_node.id == "SUP-001"
        assert path.end_node.id == "PROD-001"
        assert path.relationship_types == ["SUPPLIES", "PART_OF"]
        assert path.total_depth == 2

    def test_empty_path(self):
        """Test empty path handling."""
        path = TraversalPath(nodes=[], edges=[], total_depth=0)

        assert path.start_node is None
        assert path.end_node is None
        assert path.relationship_types == []


class TestInMemoryGraph:
    """Tests for InMemoryGraph class."""

    def test_add_node(self):
        """Test adding nodes to the graph."""
        graph = InMemoryGraph()
        node = GraphNode(id="TEST-001", label="Test")
        graph.add_node(node)

        assert graph.get_node_count() == 1
        assert "TEST-001" in graph.nodes

    def test_add_edge(self):
        """Test adding edges to the graph."""
        graph = InMemoryGraph()
        node1 = GraphNode(id="NODE-001", label="Test")
        node2 = GraphNode(id="NODE-002", label="Test")
        edge = GraphEdge(source_id="NODE-001", target_id="NODE-002", relationship_type="CONNECTS")

        graph.add_node(node1)
        graph.add_node(node2)
        graph.add_edge(edge)

        assert graph.get_edge_count() == 1

    def test_find_downstream_simple(self):
        """Test finding downstream nodes in a simple chain."""
        graph = InMemoryGraph()

        # Create a simple chain: SUP -> COMP -> PROD
        supplier = GraphNode(id="SUP-001", label="Supplier")
        component = GraphNode(id="COMP-001", label="Component")
        product = GraphNode(id="PROD-001", label="Product")

        graph.add_node(supplier)
        graph.add_node(component)
        graph.add_node(product)

        graph.add_edge(GraphEdge(source_id="SUP-001", target_id="COMP-001", relationship_type="SUPPLIES"))
        graph.add_edge(GraphEdge(source_id="COMP-001", target_id="PROD-001", relationship_type="PART_OF"))

        impacts = graph.find_downstream("SUP-001")

        assert len(impacts) == 2
        affected_ids = {i.affected_node_id for i in impacts}
        assert "COMP-001" in affected_ids
        assert "PROD-001" in affected_ids

    def test_find_downstream_branching(self):
        """Test finding downstream nodes with branching."""
        graph = InMemoryGraph()

        # Create branching: SUP -> COMP1 -> PROD1
        #                       -> COMP2 -> PROD2
        supplier = GraphNode(id="SUP-001", label="Supplier")
        comp1 = GraphNode(id="COMP-001", label="Component")
        comp2 = GraphNode(id="COMP-002", label="Component")
        prod1 = GraphNode(id="PROD-001", label="Product")
        prod2 = GraphNode(id="PROD-002", label="Product")

        for node in [supplier, comp1, comp2, prod1, prod2]:
            graph.add_node(node)

        graph.add_edge(GraphEdge(source_id="SUP-001", target_id="COMP-001", relationship_type="SUPPLIES"))
        graph.add_edge(GraphEdge(source_id="SUP-001", target_id="COMP-002", relationship_type="SUPPLIES"))
        graph.add_edge(GraphEdge(source_id="COMP-001", target_id="PROD-001", relationship_type="PART_OF"))
        graph.add_edge(GraphEdge(source_id="COMP-002", target_id="PROD-002", relationship_type="PART_OF"))

        impacts = graph.find_downstream("SUP-001")

        assert len(impacts) == 4
        affected_ids = {i.affected_node_id for i in impacts}
        assert "COMP-001" in affected_ids
        assert "COMP-002" in affected_ids
        assert "PROD-001" in affected_ids
        assert "PROD-002" in affected_ids

    def test_find_all_paths(self):
        """Test finding all paths between nodes."""
        graph = InMemoryGraph()

        # Create graph with multiple paths
        nodes = [
            GraphNode(id="A", label="Start"),
            GraphNode(id="B", label="Middle"),
            GraphNode(id="C", label="Middle"),
            GraphNode(id="D", label="End"),
        ]
        for node in nodes:
            graph.add_node(node)

        # A -> B -> D and A -> C -> D
        graph.add_edge(GraphEdge(source_id="A", target_id="B", relationship_type="CONNECTS"))
        graph.add_edge(GraphEdge(source_id="A", target_id="C", relationship_type="CONNECTS"))
        graph.add_edge(GraphEdge(source_id="B", target_id="D", relationship_type="CONNECTS"))
        graph.add_edge(GraphEdge(source_id="C", target_id="D", relationship_type="CONNECTS"))

        paths = graph.find_all_paths("A", "D")

        assert len(paths) == 2
        for path in paths:
            assert path.nodes[0].id == "A"
            assert path.nodes[-1].id == "D"


class TestImpactCalculator:
    """Tests for ImpactCalculator class."""

    def test_severity_weight_mapping(self):
        """Test that severity levels map to correct weights."""
        calculator = ImpactCalculator()

        assert calculator.SEVERITY_WEIGHTS[SeverityLevel.LOW] == 0.25
        assert calculator.SEVERITY_WEIGHTS[SeverityLevel.MEDIUM] == 0.50
        assert calculator.SEVERITY_WEIGHTS[SeverityLevel.HIGH] == 0.75
        assert calculator.SEVERITY_WEIGHTS[SeverityLevel.CRITICAL] == 1.0

    def test_impact_score_from_empty_paths(self):
        """Test impact calculation with no affected nodes."""
        calculator = ImpactCalculator()

        risk_event = RiskEvent(
            id="RISK-001",
            event_type=EventType.WEATHER,
            location="Taiwan",
            affected_entities=[],
            severity=SeverityLevel.HIGH,
            confidence=0.9,
            source_url="https://test.com",
            description="Test event",
        )

        score = calculator.calculate_impact_from_paths(risk_event, [])

        assert score.overall_score >= 0
        assert score.affected_products_count == 0

    def test_impact_score_with_products(self):
        """Test impact calculation with affected products."""
        calculator = ImpactCalculator()

        risk_event = RiskEvent(
            id="RISK-001",
            event_type=EventType.FIRE,
            location="Taiwan",
            affected_entities=["TSMC"],
            severity=SeverityLevel.CRITICAL,
            confidence=0.95,
            source_url="https://test.com",
            description="Factory fire",
        )

        impact_results = [
            ImpactResult(
                affected_node_id="PROD-001",
                affected_node_label="Product",
                distance_from_source=2,
                impact_paths=[],
            ),
            ImpactResult(
                affected_node_id="PROD-002",
                affected_node_label="Product",
                distance_from_source=3,
                impact_paths=[],
            ),
        ]

        score = calculator.calculate_impact_from_paths(risk_event, impact_results)

        assert score.affected_products_count == 2
        assert score.severity_component > 0
        assert score.criticality_component > 0


class TestRedundancyAnalyzer:
    """Tests for RedundancyAnalyzer class."""

    def test_single_source_detection(self):
        """Test detection of single-source components."""
        analyzer = RedundancyAnalyzer()

        component_map = {
            "COMP-001": ["SUP-001"],  # Single source
            "COMP-002": ["SUP-001", "SUP-002"],  # Dual source
        }

        results = analyzer.analyze_redundancy_in_memory(
            product_id="PROD-001",
            component_supplier_map=component_map,
        )

        single_source = [r for r in results if r.component_id == "COMP-001"][0]
        dual_source = [r for r in results if r.component_id == "COMP-002"][0]

        assert single_source.is_single_source
        assert not dual_source.is_single_source

    def test_redundancy_score_calculation(self):
        """Test redundancy score calculation."""
        analyzer = RedundancyAnalyzer()

        assert analyzer._calculate_redundancy_score(0) == 0.0
        assert analyzer._calculate_redundancy_score(1) == 0.2
        assert analyzer._calculate_redundancy_score(2) == 0.5
        assert analyzer._calculate_redundancy_score(3) == 0.8
        assert analyzer._calculate_redundancy_score(5) == 1.0

    def test_backup_suppliers_identified(self):
        """Test that backup suppliers are correctly identified."""
        analyzer = RedundancyAnalyzer()

        component_map = {
            "COMP-001": ["SUP-001", "SUP-002", "SUP-003"],
        }

        results = analyzer.analyze_redundancy_in_memory(
            product_id="PROD-001",
            component_supplier_map=component_map,
        )

        result = results[0]
        assert result.primary_supplier_id == "SUP-001"
        assert "SUP-002" in result.backup_suppliers
        assert "SUP-003" in result.backup_suppliers

    def test_critical_component_flagging(self):
        """Test flagging of critical components."""
        analyzer = RedundancyAnalyzer()

        component_map = {
            "COMP-001": ["SUP-001"],
            "COMP-002": ["SUP-002"],
        }

        results = analyzer.analyze_redundancy_in_memory(
            product_id="PROD-001",
            component_supplier_map=component_map,
            critical_components={"COMP-001"},
        )

        comp1 = [r for r in results if r.component_id == "COMP-001"][0]
        comp2 = [r for r in results if r.component_id == "COMP-002"][0]

        assert comp1.is_critical
        assert not comp2.is_critical
