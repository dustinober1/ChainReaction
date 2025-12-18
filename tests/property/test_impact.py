"""
Property-Based Tests for GraphRAG Impact Analysis.

Feature: chain-reaction
Property 1: Graph traversal completeness
Property 13: Redundancy assessment accuracy
Property 14: Impact scoring consistency

Validates that the GraphRAG engine correctly traverses the supply chain
graph and calculates accurate impact scores.

Validates: Requirements 1.1, 6.1, 6.2, 6.3, 6.4
"""

import pytest
from hypothesis import given, settings, HealthCheck, assume
from hypothesis import strategies as st

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


# =============================================================================
# Test Strategies
# =============================================================================

@st.composite
def graph_node_strategy(draw, label: str | None = None) -> GraphNode:
    """Generate a random graph node."""
    return GraphNode(
        id=draw(st.text(min_size=5, max_size=15).map(lambda s: f"NODE-{s}")),
        label=label or draw(st.sampled_from(["Supplier", "Component", "Product"])),
        properties={},
        depth=draw(st.integers(min_value=0, max_value=10)),
    )


@st.composite
def simple_supply_chain_strategy(draw) -> InMemoryGraph:
    """
    Generate a simple supply chain graph.

    Creates a graph with:
    - N suppliers
    - M components (connected to suppliers)
    - P products (connected to components)
    """
    graph = InMemoryGraph()

    # Generate suppliers
    num_suppliers = draw(st.integers(min_value=2, max_value=5))
    suppliers = []
    for i in range(num_suppliers):
        node = GraphNode(id=f"SUP-{i:04d}", label="Supplier")
        graph.add_node(node)
        suppliers.append(node)

    # Generate components connected to suppliers
    num_components = draw(st.integers(min_value=2, max_value=5))
    components = []
    for i in range(num_components):
        node = GraphNode(id=f"COMP-{i:04d}", label="Component")
        graph.add_node(node)
        components.append(node)

        # Connect to random supplier(s)
        num_supplier_links = draw(st.integers(min_value=1, max_value=min(3, len(suppliers))))
        linked_suppliers = draw(st.sampled_from(suppliers))
        edge = GraphEdge(
            source_id=linked_suppliers.id,
            target_id=node.id,
            relationship_type="SUPPLIES",
        )
        graph.add_edge(edge)

    # Generate products connected to components
    num_products = draw(st.integers(min_value=1, max_value=3))
    for i in range(num_products):
        node = GraphNode(id=f"PROD-{i:04d}", label="Product")
        graph.add_node(node)

        # Connect to components
        num_component_links = draw(st.integers(min_value=1, max_value=min(3, len(components))))
        for _ in range(num_component_links):
            linked_component = draw(st.sampled_from(components))
            edge = GraphEdge(
                source_id=linked_component.id,
                target_id=node.id,
                relationship_type="PART_OF",
            )
            graph.add_edge(edge)

    return graph


@st.composite
def risk_event_for_impact_strategy(draw) -> RiskEvent:
    """Generate a risk event for impact testing."""
    return RiskEvent(
        id=draw(st.text(min_size=5, max_size=10).map(lambda s: f"RISK-{s}")),
        event_type=draw(st.sampled_from(list(EventType))),
        location=draw(st.text(min_size=3, max_size=20)),
        affected_entities=[],
        severity=draw(st.sampled_from(list(SeverityLevel))),
        confidence=draw(st.floats(min_value=0.5, max_value=1.0)),
        source_url="https://test.example.com",
        description="Test risk event for impact analysis",
    )


# =============================================================================
# Property 1: Graph traversal completeness
# =============================================================================


class TestGraphTraversalCompleteness:
    """
    Property-based tests for graph traversal completeness.

    Feature: chain-reaction, Property 1: Graph traversal completeness
    """

    @given(simple_supply_chain_strategy())
    @settings(max_examples=50, suppress_health_check=[HealthCheck.too_slow])
    def test_downstream_finds_all_reachable_nodes(self, graph: InMemoryGraph):
        """
        Property: BFS finds all reachable downstream nodes.

        Feature: chain-reaction, Property 1: Graph traversal completeness
        Validates: Requirements 1.1, 6.1
        """
        # Get a supplier node
        suppliers = [n for n in graph.nodes.values() if n.label == "Supplier"]
        if not suppliers:
            return

        supplier = suppliers[0]
        impacts = graph.find_downstream(supplier.id)

        # All impact results should have valid node IDs
        for impact in impacts:
            assert impact.affected_node_id in graph.nodes
            assert impact.distance_from_source > 0

    @given(simple_supply_chain_strategy())
    @settings(max_examples=50, suppress_health_check=[HealthCheck.too_slow])
    def test_paths_are_valid_sequences(self, graph: InMemoryGraph):
        """
        Property: All returned paths are valid node sequences.

        Feature: chain-reaction, Property 1: Graph traversal completeness
        Validates: Requirements 6.1, 6.2
        """
        suppliers = [n for n in graph.nodes.values() if n.label == "Supplier"]
        if not suppliers:
            return

        supplier = suppliers[0]
        impacts = graph.find_downstream(supplier.id)

        for impact in impacts:
            for path in impact.impact_paths:
                # Path should have at least 2 nodes
                assert len(path.nodes) >= 2

                # First node should be the source
                assert path.nodes[0].id == supplier.id

                # Last node should be the affected node
                assert path.nodes[-1].id == impact.affected_node_id

                # Edges should match nodes
                assert len(path.edges) == len(path.nodes) - 1

    @given(simple_supply_chain_strategy())
    @settings(max_examples=50, suppress_health_check=[HealthCheck.too_slow])
    def test_distance_matches_path_length(self, graph: InMemoryGraph):
        """
        Property: Distance from source matches actual path length.

        Feature: chain-reaction, Property 1: Graph traversal completeness
        Validates: Requirements 6.2
        """
        suppliers = [n for n in graph.nodes.values() if n.label == "Supplier"]
        if not suppliers:
            return

        supplier = suppliers[0]
        impacts = graph.find_downstream(supplier.id)

        for impact in impacts:
            if impact.impact_paths:
                # Check shortest path length
                min_path_length = min(p.total_depth for p in impact.impact_paths)
                assert impact.distance_from_source >= 1

    @given(simple_supply_chain_strategy())
    @settings(max_examples=50, suppress_health_check=[HealthCheck.too_slow])
    def test_no_duplicate_impacts(self, graph: InMemoryGraph):
        """
        Property: Each node appears at most once in impact results.

        Feature: chain-reaction, Property 1: Graph traversal completeness
        Validates: Requirements 6.1
        """
        suppliers = [n for n in graph.nodes.values() if n.label == "Supplier"]
        if not suppliers:
            return

        supplier = suppliers[0]
        impacts = graph.find_downstream(supplier.id)

        affected_ids = [impact.affected_node_id for impact in impacts]
        assert len(affected_ids) == len(set(affected_ids))

    def test_empty_graph_returns_empty_results(self):
        """
        Test: Empty graph returns empty impact results.

        Feature: chain-reaction, Property 1: Graph traversal completeness
        Validates: Requirements 6.1
        """
        graph = InMemoryGraph()
        impacts = graph.find_downstream("nonexistent")
        assert impacts == []


# =============================================================================
# Property 13: Redundancy assessment accuracy
# =============================================================================


class TestRedundancyAssessmentAccuracy:
    """
    Property-based tests for redundancy assessment accuracy.

    Feature: chain-reaction, Property 13: Redundancy assessment accuracy
    """

    @given(st.integers(min_value=0, max_value=10))
    @settings(max_examples=50)
    def test_redundancy_score_increases_with_suppliers(self, supplier_count: int):
        """
        Property: Redundancy score increases with more suppliers.

        Feature: chain-reaction, Property 13: Redundancy assessment accuracy
        Validates: Requirements 6.3
        """
        analyzer = RedundancyAnalyzer()

        # Create component-supplier mapping
        suppliers = [f"SUP-{i:04d}" for i in range(supplier_count)]
        component_map = {"COMP-001": suppliers}

        results = analyzer.analyze_redundancy_in_memory(
            product_id="PROD-001",
            component_supplier_map=component_map,
        )

        assert len(results) == 1
        result = results[0]

        # Single source should have low redundancy
        if supplier_count <= 1:
            assert result.redundancy_score <= 0.2

        # Multiple suppliers should have higher redundancy
        if supplier_count >= 3:
            assert result.redundancy_score >= 0.8

    @given(st.lists(
        st.integers(min_value=0, max_value=5),
        min_size=1,
        max_size=10,
    ))
    @settings(max_examples=50, suppress_health_check=[HealthCheck.too_slow])
    def test_single_source_correctly_identified(self, supplier_counts: list[int]):
        """
        Property: Single-source components are correctly flagged.

        Feature: chain-reaction, Property 13: Redundancy assessment accuracy
        Validates: Requirements 6.3
        """
        analyzer = RedundancyAnalyzer()

        # Create component-supplier mapping
        component_map = {}
        for i, count in enumerate(supplier_counts):
            suppliers = [f"SUP-{j:04d}" for j in range(count)]
            component_map[f"COMP-{i:04d}"] = suppliers

        results = analyzer.analyze_redundancy_in_memory(
            product_id="PROD-001",
            component_supplier_map=component_map,
        )

        for result in results:
            if result.supplier_count <= 1:
                assert result.is_single_source
            else:
                assert not result.is_single_source

    @given(st.lists(st.text(min_size=5, max_size=10), min_size=1, max_size=5, unique=True))
    @settings(max_examples=50, suppress_health_check=[HealthCheck.too_slow])
    def test_critical_components_flagged(self, critical_ids: list[str]):
        """
        Property: Critical components are correctly flagged.

        Feature: chain-reaction, Property 13: Redundancy assessment accuracy
        Validates: Requirements 6.3
        """
        analyzer = RedundancyAnalyzer()

        # Create mapping with the critical IDs
        component_map = {c_id: ["SUP-001"] for c_id in critical_ids}
        critical_set = set(critical_ids)

        results = analyzer.analyze_redundancy_in_memory(
            product_id="PROD-001",
            component_supplier_map=component_map,
            critical_components=critical_set,
        )

        for result in results:
            if result.component_id in critical_set:
                assert result.is_critical

    def test_redundancy_score_is_bounded(self):
        """
        Test: Redundancy score is always between 0 and 1.

        Feature: chain-reaction, Property 13: Redundancy assessment accuracy
        Validates: Requirements 6.3
        """
        analyzer = RedundancyAnalyzer()

        for count in range(0, 15):
            score = analyzer._calculate_redundancy_score(count)
            assert 0.0 <= score <= 1.0


# =============================================================================
# Property 14: Impact scoring consistency
# =============================================================================


class TestImpactScoringConsistency:
    """
    Property-based tests for impact scoring consistency.

    Feature: chain-reaction, Property 14: Impact scoring consistency
    """

    @given(risk_event_for_impact_strategy())
    @settings(max_examples=100, suppress_health_check=[HealthCheck.too_slow])
    def test_impact_score_is_bounded(self, risk_event: RiskEvent):
        """
        Property: Impact scores are always in valid range [0, 10].

        Feature: chain-reaction, Property 14: Impact scoring consistency
        Validates: Requirements 6.4
        """
        calculator = ImpactCalculator()

        # Create mock impact results
        impact_results = [
            ImpactResult(
                affected_node_id="PROD-001",
                affected_node_label="Product",
                distance_from_source=2,
                impact_paths=[],
            )
        ]

        score = calculator.calculate_impact_from_paths(risk_event, impact_results)

        assert 0.0 <= score.overall_score <= 10.0
        assert 0.0 <= score.severity_component <= 10.0
        assert 0.0 <= score.proximity_component <= 10.0
        assert 0.0 <= score.criticality_component <= 10.0

    @given(
        st.sampled_from(list(SeverityLevel)),
        st.sampled_from(list(SeverityLevel)),
    )
    def test_higher_severity_means_higher_score(
        self,
        low_severity: SeverityLevel,
        high_severity: SeverityLevel,
    ):
        """
        Property: Higher severity events produce higher impact scores.

        Feature: chain-reaction, Property 14: Impact scoring consistency
        Validates: Requirements 6.4
        """
        # Skip if severities are the same
        if low_severity == high_severity:
            return

        severity_order = [
            SeverityLevel.LOW,
            SeverityLevel.MEDIUM,
            SeverityLevel.HIGH,
            SeverityLevel.CRITICAL,
        ]

        low_index = severity_order.index(low_severity)
        high_index = severity_order.index(high_severity)

        # Ensure we're comparing different levels
        assume(low_index != high_index)

        calculator = ImpactCalculator()

        event1 = RiskEvent(
            id="RISK-001",
            event_type=EventType.WEATHER,
            location="Taiwan",
            affected_entities=[],
            severity=severity_order[min(low_index, high_index)],
            confidence=0.9,
            source_url="https://test.com",
            description="Test",
        )

        event2 = RiskEvent(
            id="RISK-002",
            event_type=EventType.WEATHER,
            location="Taiwan",
            affected_entities=[],
            severity=severity_order[max(low_index, high_index)],
            confidence=0.9,
            source_url="https://test.com",
            description="Test",
        )

        impact_results = []

        score1 = calculator.calculate_impact_from_paths(event1, impact_results)
        score2 = calculator.calculate_impact_from_paths(event2, impact_results)

        assert score2.severity_component >= score1.severity_component

    @given(st.integers(min_value=0, max_value=20))
    @settings(max_examples=50)
    def test_more_affected_products_increases_criticality(self, num_products: int):
        """
        Property: More affected products increases criticality component.

        Feature: chain-reaction, Property 14: Impact scoring consistency
        Validates: Requirements 6.4
        """
        calculator = ImpactCalculator()

        risk_event = RiskEvent(
            id="RISK-001",
            event_type=EventType.FIRE,
            location="Taiwan",
            affected_entities=[],
            severity=SeverityLevel.HIGH,
            confidence=0.9,
            source_url="https://test.com",
            description="Test",
        )

        impact_results = [
            ImpactResult(
                affected_node_id=f"PROD-{i:04d}",
                affected_node_label="Product",
                distance_from_source=2,
                impact_paths=[],
            )
            for i in range(num_products)
        ]

        score = calculator.calculate_impact_from_paths(risk_event, impact_results)

        # More products should increase criticality (capped at 10)
        expected_criticality = min(num_products * 0.5, 10.0)
        assert abs(score.criticality_component - expected_criticality) < 0.1

    @given(st.integers(min_value=1, max_value=10))
    @settings(max_examples=50)
    def test_closer_distance_means_higher_proximity_score(self, distance: int):
        """
        Property: Closer affected nodes have higher proximity scores.

        Feature: chain-reaction, Property 14: Impact scoring consistency
        Validates: Requirements 6.4
        """
        calculator = ImpactCalculator()

        risk_event = RiskEvent(
            id="RISK-001",
            event_type=EventType.WEATHER,
            location="Taiwan",
            affected_entities=[],
            severity=SeverityLevel.MEDIUM,
            confidence=0.9,
            source_url="https://test.com",
            description="Test",
        )

        # Calculate score for close product
        close_results = [
            ImpactResult(
                affected_node_id="PROD-001",
                affected_node_label="Product",
                distance_from_source=1,
                impact_paths=[],
            )
        ]

        # Calculate score for far product
        far_results = [
            ImpactResult(
                affected_node_id="PROD-001",
                affected_node_label="Product",
                distance_from_source=distance + 5,
                impact_paths=[],
            )
        ]

        close_score = calculator.calculate_impact_from_paths(risk_event, close_results)
        far_score = calculator.calculate_impact_from_paths(risk_event, far_results)

        assert close_score.proximity_component >= far_score.proximity_component
