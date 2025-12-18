"""
Unit tests for synthetic data generation.
"""

import json
import sys
from pathlib import Path

import pytest

# Add scripts to path
sys.path.insert(0, str(Path(__file__).parent.parent.parent / "scripts"))

from scripts.generate_data import (
    SupplyChainGenerator,
    RiskEventGenerator,
    generate_small_dataset,
    generate_medium_dataset,
)


class TestSupplyChainGenerator:
    """Tests for the SupplyChainGenerator class."""

    def test_generator_creates_correct_counts(self):
        """Test that generator creates the expected number of entities."""
        generator = SupplyChainGenerator(seed=42)
        data = generator.generate(
            num_suppliers=10,
            num_components=20,
            num_products=3,
        )

        assert len(data["suppliers"]) == 10
        assert len(data["components"]) == 20
        assert len(data["products"]) == 3

    def test_generator_is_deterministic_with_seed(self):
        """Test that the same seed produces identical results."""
        gen1 = SupplyChainGenerator(seed=123)
        data1 = gen1.generate(num_suppliers=5, num_components=10, num_products=2)

        gen2 = SupplyChainGenerator(seed=123)
        data2 = gen2.generate(num_suppliers=5, num_components=10, num_products=2)

        # Compare supplier IDs and names
        assert [s["id"] for s in data1["suppliers"]] == [s["id"] for s in data2["suppliers"]]
        assert [s["name"] for s in data1["suppliers"]] == [s["name"] for s in data2["suppliers"]]

    def test_generator_creates_valid_relationships(self):
        """Test that all relationships reference valid entities."""
        generator = SupplyChainGenerator(seed=42)
        data = generator.generate(num_suppliers=10, num_components=20, num_products=3)

        supplier_ids = {s["id"] for s in data["suppliers"]}
        component_ids = {c["id"] for c in data["components"]}
        product_ids = {p["id"] for p in data["products"]}

        # Check supplier-component relationships
        for rel in data["relationships"]["supplier_component"]:
            assert rel["supplier_id"] in supplier_ids
            assert rel["component_id"] in component_ids

        # Check component-product relationships
        for rel in data["relationships"]["component_product"]:
            assert rel["component_id"] in component_ids
            assert rel["product_id"] in product_ids

    def test_generator_assigns_risk_scores(self):
        """Test that suppliers have valid risk scores."""
        generator = SupplyChainGenerator(seed=42)
        data = generator.generate(num_suppliers=20, num_components=10, num_products=2)

        for supplier in data["suppliers"]:
            assert 0 <= supplier["risk_score"] <= 100

    def test_generator_includes_metadata(self):
        """Test that generated data includes metadata."""
        generator = SupplyChainGenerator(seed=42)
        data = generator.generate(num_suppliers=5, num_components=10, num_products=2)

        assert "metadata" in data
        assert "generated_at" in data["metadata"]
        assert "counts" in data["metadata"]

    def test_graph_format_export(self):
        """Test that graph format export works correctly."""
        generator = SupplyChainGenerator(seed=42)
        generator.generate(num_suppliers=5, num_components=10, num_products=2)

        graph_data = generator.to_graph_json()

        assert "nodes" in graph_data
        assert "edges" in graph_data
        assert len(graph_data["nodes"]) > 0
        assert len(graph_data["edges"]) > 0

        # Check node structure
        for node in graph_data["nodes"]:
            assert "id" in node
            assert "type" in node
            assert "name" in node

        # Check edge structure
        for edge in graph_data["edges"]:
            assert "source" in edge
            assert "target" in edge
            assert "type" in edge

    def test_json_export(self):
        """Test that JSON export produces valid JSON."""
        generator = SupplyChainGenerator(seed=42)
        generator.generate(num_suppliers=5, num_components=10, num_products=2)

        json_str = generator.to_json()

        # Should be valid JSON
        parsed = json.loads(json_str)
        assert "suppliers" in parsed
        assert "components" in parsed
        assert "products" in parsed


class TestRiskEventGenerator:
    """Tests for the RiskEventGenerator class."""

    def test_generates_correct_count(self):
        """Test that generator creates the expected number of events."""
        generator = RiskEventGenerator(seed=42)
        events = generator.generate_events(count=10)

        assert len(events) == 10

    def test_events_have_required_fields(self):
        """Test that events have all required fields."""
        generator = RiskEventGenerator(seed=42)
        events = generator.generate_events(count=5)

        for event in events:
            assert event.id is not None
            assert event.event_type is not None
            assert event.location is not None
            assert event.severity is not None
            assert event.confidence >= 0.6
            assert event.confidence <= 0.95

    def test_uses_provided_locations(self):
        """Test that generator uses provided locations."""
        generator = RiskEventGenerator(seed=42)
        custom_locations = ["TestCity1", "TestCity2"]
        events = generator.generate_events(count=10, locations=custom_locations)

        for event in events:
            assert event.location in custom_locations


class TestConvenienceFunctions:
    """Tests for convenience dataset generation functions."""

    def test_small_dataset(self):
        """Test small dataset generation."""
        data = generate_small_dataset()

        # Should have approximately 100 total nodes
        total_nodes = (
            len(data["suppliers"])
            + len(data["components"])
            + len(data["products"])
            + len(data["locations"])
        )
        assert total_nodes < 200  # Small dataset should be around 88 nodes

    def test_small_dataset_is_deterministic(self):
        """Test that small dataset is deterministic."""
        data1 = generate_small_dataset(seed=42)
        data2 = generate_small_dataset(seed=42)

        assert data1["suppliers"][0]["id"] == data2["suppliers"][0]["id"]
