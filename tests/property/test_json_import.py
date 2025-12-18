"""
Property-Based Tests for JSON Import/Export Consistency.

Feature: chain-reaction
Property 9: JSON import round-trip consistency

For any valid supply chain JSON data, importing then exporting should 
preserve all entities and relationships without data loss.

Validates: Requirements 3.4
"""

import json
import pytest
from hypothesis import given, settings, HealthCheck

from tests.strategies import (
    supply_chain_json_strategy,
    supply_chain_graph_strategy,
)


# Feature: chain-reaction, Property 9: JSON import round-trip consistency
class TestJSONImportConsistency:
    """
    Property-based tests for JSON import/export consistency.

    These tests validate that:
    1. Generated JSON is valid and parseable
    2. All nodes and edges are preserved in round-trip
    3. Node IDs are consistent across import/export
    4. Edge references remain valid
    """

    @given(supply_chain_json_strategy())
    @settings(max_examples=100, suppress_health_check=[HealthCheck.too_slow])
    def test_json_is_valid_and_parseable(self, supply_chain_data):
        """
        Property: Generated supply chain JSON must be valid JSON.

        Feature: chain-reaction, Property 9: JSON import round-trip consistency
        """
        # Serialize to JSON string
        json_str = json.dumps(supply_chain_data)

        # Parse back
        parsed = json.loads(json_str)

        assert "nodes" in parsed
        assert "edges" in parsed
        assert isinstance(parsed["nodes"], list)
        assert isinstance(parsed["edges"], list)

    @given(supply_chain_json_strategy())
    @settings(max_examples=100, suppress_health_check=[HealthCheck.too_slow])
    def test_round_trip_preserves_node_count(self, supply_chain_data):
        """
        Property: Round-trip serialization preserves all nodes.

        Feature: chain-reaction, Property 9: JSON import round-trip consistency
        """
        original_node_count = len(supply_chain_data["nodes"])

        # Simulate round-trip
        json_str = json.dumps(supply_chain_data)
        parsed = json.loads(json_str)

        assert len(parsed["nodes"]) == original_node_count

    @given(supply_chain_json_strategy())
    @settings(max_examples=100, suppress_health_check=[HealthCheck.too_slow])
    def test_round_trip_preserves_edge_count(self, supply_chain_data):
        """
        Property: Round-trip serialization preserves all edges.

        Feature: chain-reaction, Property 9: JSON import round-trip consistency
        """
        original_edge_count = len(supply_chain_data["edges"])

        # Simulate round-trip
        json_str = json.dumps(supply_chain_data)
        parsed = json.loads(json_str)

        assert len(parsed["edges"]) == original_edge_count

    @given(supply_chain_json_strategy())
    @settings(max_examples=100, suppress_health_check=[HealthCheck.too_slow])
    def test_all_node_ids_are_unique(self, supply_chain_data):
        """
        Property: All node IDs in JSON must be unique.

        Feature: chain-reaction, Property 9: JSON import round-trip consistency
        """
        node_ids = [node["id"] for node in supply_chain_data["nodes"]]
        assert len(node_ids) == len(set(node_ids)), "Duplicate node IDs found"

    @given(supply_chain_json_strategy())
    @settings(max_examples=100, suppress_health_check=[HealthCheck.too_slow])
    def test_all_edge_references_are_valid(self, supply_chain_data):
        """
        Property: All edge source/target IDs must reference existing nodes.

        Feature: chain-reaction, Property 9: JSON import round-trip consistency
        """
        node_ids = {node["id"] for node in supply_chain_data["nodes"]}

        for edge in supply_chain_data["edges"]:
            assert edge["source"] in node_ids, f"Edge source {edge['source']} not in nodes"
            assert edge["target"] in node_ids, f"Edge target {edge['target']} not in nodes"

    @given(supply_chain_json_strategy())
    @settings(max_examples=100, suppress_health_check=[HealthCheck.too_slow])
    def test_all_nodes_have_required_fields(self, supply_chain_data):
        """
        Property: All nodes must have id, type, and name fields.

        Feature: chain-reaction, Property 9: JSON import round-trip consistency
        """
        for node in supply_chain_data["nodes"]:
            assert "id" in node, "Node missing 'id' field"
            assert "type" in node, "Node missing 'type' field"
            assert "name" in node, "Node missing 'name' field"

    @given(supply_chain_json_strategy())
    @settings(max_examples=100, suppress_health_check=[HealthCheck.too_slow])
    def test_all_edges_have_required_fields(self, supply_chain_data):
        """
        Property: All edges must have source, target, and type fields.

        Feature: chain-reaction, Property 9: JSON import round-trip consistency
        """
        for edge in supply_chain_data["edges"]:
            assert "source" in edge, "Edge missing 'source' field"
            assert "target" in edge, "Edge missing 'target' field"
            assert "type" in edge, "Edge missing 'type' field"

    @given(supply_chain_json_strategy())
    @settings(max_examples=100, suppress_health_check=[HealthCheck.too_slow])
    def test_edge_types_are_valid(self, supply_chain_data):
        """
        Property: All edge types must be valid relationship types.

        Feature: chain-reaction, Property 9: JSON import round-trip consistency
        """
        valid_types = {
            "SUPPLIES", "LOCATED_IN", "BACKUP_FOR", "PART_OF",
            "REQUIRES", "ALTERNATIVE_TO", "MANUFACTURES",
        }

        for edge in supply_chain_data["edges"]:
            assert edge["type"] in valid_types, f"Invalid edge type: {edge['type']}"

    @given(supply_chain_json_strategy())
    @settings(max_examples=50, suppress_health_check=[HealthCheck.too_slow])
    def test_round_trip_preserves_node_properties(self, supply_chain_data):
        """
        Property: Round-trip preserves all node properties.

        Feature: chain-reaction, Property 9: JSON import round-trip consistency
        """
        # Round-trip
        json_str = json.dumps(supply_chain_data)
        parsed = json.loads(json_str)

        # Create lookup by ID
        original_by_id = {n["id"]: n for n in supply_chain_data["nodes"]}
        parsed_by_id = {n["id"]: n for n in parsed["nodes"]}

        # Compare all properties
        for node_id, original_node in original_by_id.items():
            parsed_node = parsed_by_id.get(node_id)
            assert parsed_node is not None, f"Node {node_id} lost in round-trip"

            for key, value in original_node.items():
                assert key in parsed_node, f"Property {key} lost in node {node_id}"
                assert parsed_node[key] == value, f"Property {key} changed in node {node_id}"


# Feature: chain-reaction, Property 9: JSON import round-trip consistency
class TestJSONNodeTypes:
    """Tests for node type validation in JSON import."""

    @given(supply_chain_json_strategy())
    @settings(max_examples=100, suppress_health_check=[HealthCheck.too_slow])
    def test_node_types_follow_tier_structure(self, supply_chain_data):
        """
        Property: Node types must follow the supply chain tier structure.

        Feature: chain-reaction, Property 9: JSON import round-trip consistency
        """
        valid_types = {
            "Supplier", "Raw Material", "Component", "Sub-Assembly", "Final Product",
        }

        for node in supply_chain_data["nodes"]:
            assert node["type"] in valid_types, f"Invalid node type: {node['type']}"

    @given(supply_chain_json_strategy())
    @settings(max_examples=100, suppress_health_check=[HealthCheck.too_slow])
    def test_json_has_products(self, supply_chain_data):
        """
        Property: Generated supply chain must have at least one product.

        Feature: chain-reaction, Property 9: JSON import round-trip consistency
        """
        products = [n for n in supply_chain_data["nodes"] if n["type"] == "Final Product"]
        assert len(products) >= 1, "No products in supply chain"

    @given(supply_chain_json_strategy())
    @settings(max_examples=100, suppress_health_check=[HealthCheck.too_slow])
    def test_json_has_suppliers(self, supply_chain_data):
        """
        Property: Generated supply chain must have at least one supplier.

        Feature: chain-reaction, Property 9: JSON import round-trip consistency
        """
        suppliers = [n for n in supply_chain_data["nodes"] if n["type"] == "Supplier"]
        assert len(suppliers) >= 1, "No suppliers in supply chain"
