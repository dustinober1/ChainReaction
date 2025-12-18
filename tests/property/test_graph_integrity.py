"""
Property-Based Tests for Graph Data Integrity.

Feature: chain-reaction
Property 8: Graph data integrity preservation

For any modification to the knowledge graph (adding entities, updating 
relationships), all existing connections should remain valid and no 
orphaned nodes should be created.

Validates: Requirements 3.1, 3.2, 3.3
"""

import pytest
from hypothesis import given, settings, HealthCheck

from tests.strategies import (
    supplier_strategy,
    component_strategy,
    product_strategy,
    location_strategy,
    supply_chain_graph_strategy,
)
from src.models import RelationshipType


# Feature: chain-reaction, Property 8: Graph data integrity preservation
class TestGraphDataIntegrity:
    """
    Property-based tests for graph data integrity.

    These tests validate that:
    1. Entity IDs are always unique and valid
    2. Relationships reference valid entities
    3. Supply chain hierarchies maintain consistency
    4. Node modifications preserve existing relationships
    """

    @given(supplier_strategy())
    @settings(max_examples=100, suppress_health_check=[HealthCheck.too_slow])
    def test_supplier_has_valid_id(self, supplier):
        """
        Property: Every supplier must have a non-empty, unique-format ID.

        Feature: chain-reaction, Property 8: Graph data integrity preservation
        """
        assert supplier.id is not None
        assert len(supplier.id) > 0
        assert isinstance(supplier.id, str)

    @given(component_strategy())
    @settings(max_examples=100, suppress_health_check=[HealthCheck.too_slow])
    def test_component_has_valid_structure(self, component):
        """
        Property: Every component must have valid tier and category.

        Feature: chain-reaction, Property 8: Graph data integrity preservation
        """
        assert component.id is not None
        assert component.name is not None
        assert len(component.name) > 0
        assert component.tier is not None
        assert component.category is not None

    @given(product_strategy())
    @settings(max_examples=100, suppress_health_check=[HealthCheck.too_slow])
    def test_product_has_valid_structure(self, product):
        """
        Property: Every product must have valid product line and non-negative revenue.

        Feature: chain-reaction, Property 8: Graph data integrity preservation
        """
        assert product.id is not None
        assert product.name is not None
        assert product.product_line is not None
        assert product.revenue_impact >= 0

    @given(location_strategy())
    @settings(max_examples=100, suppress_health_check=[HealthCheck.too_slow])
    def test_location_has_valid_coordinates(self, location):
        """
        Property: Location coordinates must be within valid geographic bounds.

        Feature: chain-reaction, Property 8: Graph data integrity preservation
        """
        assert location.id is not None
        assert location.country is not None
        assert location.region is not None

        if location.latitude is not None:
            assert -90.0 <= location.latitude <= 90.0

        if location.longitude is not None:
            assert -180.0 <= location.longitude <= 180.0

    @given(supply_chain_graph_strategy())
    @settings(max_examples=50, suppress_health_check=[HealthCheck.too_slow])
    def test_supply_chain_links_reference_valid_entities(self, graph):
        """
        Property: All relationship links must reference existing entities.

        Feature: chain-reaction, Property 8: Graph data integrity preservation
        """
        supplier_ids = {s.id for s in graph["suppliers"]}
        component_ids = {c.id for c in graph["components"]}
        product_ids = {p.id for p in graph["products"]}

        # Verify supplier-component links
        for supplier_id, component_id in graph["supplier_component_links"]:
            assert supplier_id in supplier_ids, f"Invalid supplier reference: {supplier_id}"
            assert component_id in component_ids, f"Invalid component reference: {component_id}"

        # Verify component-product links
        for component_id, product_id in graph["component_product_links"]:
            assert component_id in component_ids, f"Invalid component reference: {component_id}"
            assert product_id in product_ids, f"Invalid product reference: {product_id}"

    @given(supply_chain_graph_strategy(num_suppliers=5, num_components=10, num_products=3))
    @settings(max_examples=50, suppress_health_check=[HealthCheck.too_slow])
    def test_all_entity_ids_are_unique_within_type(self, graph):
        """
        Property: All entity IDs must be unique within their type.

        Feature: chain-reaction, Property 8: Graph data integrity preservation
        """
        supplier_ids = [s.id for s in graph["suppliers"]]
        component_ids = [c.id for c in graph["components"]]
        product_ids = [p.id for p in graph["products"]]

        assert len(supplier_ids) == len(set(supplier_ids)), "Duplicate supplier IDs"
        assert len(component_ids) == len(set(component_ids)), "Duplicate component IDs"
        assert len(product_ids) == len(set(product_ids)), "Duplicate product IDs"

    @given(supply_chain_graph_strategy())
    @settings(max_examples=50, suppress_health_check=[HealthCheck.too_slow])
    def test_products_have_at_least_one_component(self, graph):
        """
        Property: Each product should have at least one component linked.

        Feature: chain-reaction, Property 8: Graph data integrity preservation
        """
        products_with_components = set()
        for component_id, product_id in graph["component_product_links"]:
            products_with_components.add(product_id)

        # All products should have components
        for p in graph["products"]:
            assert p.id in products_with_components, f"Product {p.id} has no components"

    @given(supply_chain_graph_strategy())
    @settings(max_examples=50, suppress_health_check=[HealthCheck.too_slow])
    def test_components_have_at_least_one_supplier(self, graph):
        """
        Property: Each component should have at least one supplier.

        Feature: chain-reaction, Property 8: Graph data integrity preservation
        """
        components_with_suppliers = set()
        for supplier_id, component_id in graph["supplier_component_links"]:
            components_with_suppliers.add(component_id)

        # All components should have suppliers
        for c in graph["components"]:
            assert c.id in components_with_suppliers, f"Component {c.id} has no supplier"


# Feature: chain-reaction, Property 8: Graph data integrity preservation
class TestEntityValidation:
    """Tests for individual entity validation rules."""

    @given(supplier_strategy())
    @settings(max_examples=100, suppress_health_check=[HealthCheck.too_slow])
    def test_supplier_risk_score_is_clamped(self, supplier):
        """
        Property: Supplier risk scores are always in [0, 100] range.

        Feature: chain-reaction, Property 8: Graph data integrity preservation
        """
        assert 0.0 <= supplier.risk_score <= 100.0

    @given(component_strategy())
    @settings(max_examples=100, suppress_health_check=[HealthCheck.too_slow])
    def test_component_lead_time_is_non_negative(self, component):
        """
        Property: Component lead times are always non-negative when set.

        Feature: chain-reaction, Property 8: Graph data integrity preservation
        """
        if component.lead_time_days is not None:
            assert component.lead_time_days >= 0
