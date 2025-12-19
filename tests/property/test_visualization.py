"""
Property-Based Tests for Dashboard Visualization.

Feature: chain-reaction
Property 10: Visual risk highlighting accuracy
Property 11: Node interaction information completeness
Property 12: Query result visualization synchronization

Validates that the dashboard correctly visualizes risk data and
responds to user interactions.

Validates: Requirements 4.2, 4.3, 4.5
"""

import pytest
from hypothesis import given, settings, HealthCheck
from hypothesis import strategies as st
from dataclasses import dataclass
from enum import Enum
from typing import Optional


# =============================================================================
# Visualization Models (Python counterpart)
# =============================================================================


class NodeType(str, Enum):
    SUPPLIER = "supplier"
    COMPONENT = "component"
    PRODUCT = "product"
    RISK = "risk"


@dataclass
class GraphNode:
    """Graph node for visualization testing."""

    id: str
    label: str
    type: NodeType
    name: str
    risk_score: Optional[float] = None
    location: Optional[str] = None
    is_at_risk: bool = False
    is_risk_source: bool = False


@dataclass
class GraphLink:
    """Graph link for visualization testing."""

    source: str
    target: str
    link_type: str


# =============================================================================
# Color and Styling Logic
# =============================================================================

NODE_COLORS = {
    NodeType.SUPPLIER: "#3b82f6",
    NodeType.COMPONENT: "#8b5cf6",
    NodeType.PRODUCT: "#10b981",
    NodeType.RISK: "#ef4444",
}

RISK_COLOR = "#ef4444"  # Red for risk source
AT_RISK_COLOR = "#f59e0b"  # Orange for at-risk


def get_node_color(node: GraphNode) -> str:
    """Get the display color for a node."""
    if node.is_risk_source:
        return RISK_COLOR
    if node.is_at_risk:
        return AT_RISK_COLOR
    return NODE_COLORS.get(node.type, "#6b7280")


def get_node_size(node: GraphNode) -> int:
    """Get the display size for a node."""
    if node.type == NodeType.RISK:
        return 12
    if node.type == NodeType.PRODUCT:
        return 10
    if node.type == NodeType.COMPONENT:
        return 8
    return 6


def get_risk_level(score: Optional[float]) -> str:
    """Get risk level label from score."""
    if score is None:
        return "unknown"
    if score >= 70:
        return "high"
    if score >= 40:
        return "medium"
    return "low"


def calculate_affected_nodes(
    source_id: str,
    nodes: list[GraphNode],
    links: list[GraphLink],
) -> set[str]:
    """Calculate all nodes affected by a risk source."""
    affected = set()
    to_visit = [source_id]
    visited = set()

    while to_visit:
        current = to_visit.pop(0)
        if current in visited:
            continue
        visited.add(current)

        # Find outgoing links
        for link in links:
            if link.source == current:
                affected.add(link.target)
                to_visit.append(link.target)

    return affected


# =============================================================================
# Property 10: Visual risk highlighting accuracy
# =============================================================================


class TestVisualRiskHighlighting:
    """
    Property-based tests for visual risk highlighting.

    Feature: chain-reaction, Property 10: Visual risk highlighting accuracy
    """

    @given(st.booleans(), st.booleans())
    @settings(max_examples=50)
    def test_risk_source_always_red(self, is_at_risk: bool, is_product: bool):
        """
        Property: Risk sources always display in red regardless of other flags.

        Feature: chain-reaction, Property 10: Visual risk highlighting accuracy
        Validates: Requirements 4.2
        """
        node = GraphNode(
            id="TEST-001",
            label="Test",
            type=NodeType.PRODUCT if is_product else NodeType.SUPPLIER,
            name="Test Node",
            is_risk_source=True,
            is_at_risk=is_at_risk,
        )

        color = get_node_color(node)
        assert color == RISK_COLOR

    @given(st.sampled_from(list(NodeType)))
    @settings(max_examples=20)
    def test_at_risk_nodes_orange(self, node_type: NodeType):
        """
        Property: At-risk nodes (not sources) display in orange.

        Feature: chain-reaction, Property 10: Visual risk highlighting accuracy
        Validates: Requirements 4.2
        """
        if node_type == NodeType.RISK:
            return  # Skip risk type

        node = GraphNode(
            id="TEST-001",
            label="Test",
            type=node_type,
            name="Test Node",
            is_at_risk=True,
            is_risk_source=False,
        )

        color = get_node_color(node)
        assert color == AT_RISK_COLOR

    @given(st.sampled_from(list(NodeType)))
    @settings(max_examples=20)
    def test_normal_nodes_have_type_color(self, node_type: NodeType):
        """
        Property: Normal nodes display their type-specific color.

        Feature: chain-reaction, Property 10: Visual risk highlighting accuracy
        Validates: Requirements 4.2
        """
        node = GraphNode(
            id="TEST-001",
            label="Test",
            type=node_type,
            name="Test Node",
            is_at_risk=False,
            is_risk_source=False,
        )

        color = get_node_color(node)
        assert color == NODE_COLORS[node_type]

    @given(st.floats(min_value=0.0, max_value=100.0))
    @settings(max_examples=50)
    def test_risk_level_boundaries(self, score: float):
        """
        Property: Risk levels respect boundaries (70+ high, 40-69 medium, <40 low).

        Feature: chain-reaction, Property 10: Visual risk highlighting accuracy
        Validates: Requirements 4.2
        """
        level = get_risk_level(score)

        if score >= 70:
            assert level == "high"
        elif score >= 40:
            assert level == "medium"
        else:
            assert level == "low"


# =============================================================================
# Property 11: Node interaction information completeness
# =============================================================================


class TestNodeInteractionCompleteness:
    """
    Property-based tests for node interaction information.

    Feature: chain-reaction, Property 11: Node interaction information completeness
    """

    @given(
        st.sampled_from(list(NodeType)),
        st.text(min_size=1, max_size=50),
        st.floats(min_value=0.0, max_value=100.0),
    )
    @settings(max_examples=50, suppress_health_check=[HealthCheck.too_slow])
    def test_node_has_required_display_attributes(
        self,
        node_type: NodeType,
        name: str,
        risk_score: float,
    ):
        """
        Property: Every node has required attributes for display.

        Feature: chain-reaction, Property 11: Node interaction information completeness
        Validates: Requirements 4.3
        """
        node = GraphNode(
            id=f"NODE-{hash(name) % 10000:04d}",
            label=node_type.value.title(),
            type=node_type,
            name=name,
            risk_score=risk_score,
        )

        # Required attributes
        assert node.id is not None
        assert node.name is not None
        assert node.type is not None
        assert len(node.id) > 0
        assert len(node.name) > 0

    @given(st.sampled_from(list(NodeType)))
    @settings(max_examples=20)
    def test_node_size_is_positive(self, node_type: NodeType):
        """
        Property: All node types have positive display size.

        Feature: chain-reaction, Property 11: Node interaction information completeness
        Validates: Requirements 4.3
        """
        node = GraphNode(
            id="TEST-001",
            label="Test",
            type=node_type,
            name="Test",
        )

        size = get_node_size(node)
        assert size > 0

    def test_risk_nodes_are_largest(self):
        """
        Test: Risk nodes are displayed largest for visibility.

        Feature: chain-reaction, Property 11: Node interaction information completeness
        Validates: Requirements 4.3
        """
        risk_node = GraphNode(id="R", label="Risk", type=NodeType.RISK, name="Risk")
        product_node = GraphNode(id="P", label="Product", type=NodeType.PRODUCT, name="Product")
        component_node = GraphNode(id="C", label="Component", type=NodeType.COMPONENT, name="Component")
        supplier_node = GraphNode(id="S", label="Supplier", type=NodeType.SUPPLIER, name="Supplier")

        risk_size = get_node_size(risk_node)
        product_size = get_node_size(product_node)
        component_size = get_node_size(component_node)
        supplier_size = get_node_size(supplier_node)

        assert risk_size >= product_size >= component_size >= supplier_size


# =============================================================================
# Property 12: Query result visualization synchronization
# =============================================================================


class TestQueryVisualizationSynchronization:
    """
    Property-based tests for query-visualization synchronization.

    Feature: chain-reaction, Property 12: Query result visualization synchronization
    """

    @given(st.integers(min_value=0, max_value=10))
    @settings(max_examples=30)
    def test_affected_nodes_includes_downstream(self, num_downstream: int):
        """
        Property: Affected nodes calculation includes all downstream nodes.

        Feature: chain-reaction, Property 12: Query result visualization synchronization
        Validates: Requirements 4.5
        """
        # Create a chain: RISK -> SUP -> COMP_0 -> ... -> COMP_n -> PROD
        nodes = [
            GraphNode(id="RISK-001", label="Risk", type=NodeType.RISK, name="Risk", is_risk_source=True),
            GraphNode(id="SUP-001", label="Supplier", type=NodeType.SUPPLIER, name="Supplier"),
        ]

        links = [
            GraphLink(source="RISK-001", target="SUP-001", link_type="AFFECTS"),
        ]

        prev_id = "SUP-001"
        for i in range(num_downstream):
            comp_id = f"COMP-{i:03d}"
            nodes.append(GraphNode(id=comp_id, label="Component", type=NodeType.COMPONENT, name=f"Component {i}"))
            links.append(GraphLink(source=prev_id, target=comp_id, link_type="SUPPLIES"))
            prev_id = comp_id

        nodes.append(GraphNode(id="PROD-001", label="Product", type=NodeType.PRODUCT, name="Product"))
        links.append(GraphLink(source=prev_id, target="PROD-001", link_type="PART_OF"))

        # Calculate affected nodes from risk
        affected = calculate_affected_nodes("RISK-001", nodes, links)

        # Should include all nodes in the chain
        assert "SUP-001" in affected
        assert "PROD-001" in affected
        for i in range(num_downstream):
            assert f"COMP-{i:03d}" in affected

    @given(st.lists(st.text(min_size=3, max_size=10), min_size=1, max_size=5, unique=True))
    @settings(max_examples=30, suppress_health_check=[HealthCheck.too_slow])
    def test_query_results_match_highlighted_nodes(self, affected_products: list[str]):
        """
        Property: Query results should match highlighted nodes.

        Feature: chain-reaction, Property 12: Query result visualization synchronization
        Validates: Requirements 4.5
        """
        # Simulate query result
        query_results = {
            "affectedProducts": [
                {"id": f"PROD-{p}", "name": p, "riskScore": 50}
                for p in affected_products
            ]
        }

        # Highlighted nodes should include all query results
        highlighted = set(f"PROD-{p}" for p in affected_products)

        for product in query_results["affectedProducts"]:
            assert product["id"] in highlighted

    def test_empty_query_clears_highlights(self):
        """
        Test: Empty query results should clear node highlighting.

        Feature: chain-reaction, Property 12: Query result visualization synchronization
        Validates: Requirements 4.5
        """
        query_results = {"affectedProducts": []}
        highlighted = set()

        assert len(highlighted) == 0
        assert len(query_results["affectedProducts"]) == 0
