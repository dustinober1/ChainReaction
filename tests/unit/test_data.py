"""
Unit tests for data import/export and entity management.
"""

import pytest
import json

from src.data.import_export import (
    DataImporter,
    DataExporter,
    ImportResult,
    validate_import_data,
)
from src.data.entity_manager import (
    EntityManager,
    OperationResult,
)
from src.models import Supplier, Component, Product


class TestDataImporter:
    """Tests for DataImporter."""

    def test_import_json_suppliers(self):
        """Test importing suppliers from JSON."""
        importer = DataImporter()

        data = {
            "suppliers": [
                {"id": "SUP-001", "name": "Test Supplier", "location": "Taiwan", "tier": 1},
                {"id": "SUP-002", "name": "Another Supplier", "location": "Germany", "tier": 2},
            ]
        }

        result = importer.import_json(data)

        assert result.success
        assert result.imported_count == 2
        assert result.failed_count == 0
        assert len(importer.get_suppliers()) == 2

    def test_import_json_with_validation_errors(self):
        """Test that invalid data is rejected with errors."""
        importer = DataImporter()

        data = {
            "suppliers": [
                {"id": "SUP-001", "name": "Valid", "location": "Taiwan", "tier": 1},
                {"id": "SUP-002"},  # Missing required fields
            ]
        }

        result = importer.import_json(data)

        assert result.imported_count >= 1
        assert result.failed_count >= 1
        assert len(result.errors) > 0

    def test_import_json_string(self):
        """Test importing from JSON string."""
        importer = DataImporter()

        json_str = json.dumps({
            "suppliers": [
                {"id": "SUP-001", "name": "Test", "location": "Taiwan", "tier": 1}
            ]
        })

        result = importer.import_json(json_str)

        assert result.success
        assert result.imported_count == 1

    def test_import_json_invalid_string(self):
        """Test handling of invalid JSON string."""
        importer = DataImporter()

        result = importer.import_json("not valid json {")

        assert not result.success
        assert len(result.errors) > 0

    def test_import_json_with_relationships(self):
        """Test importing with relationships."""
        importer = DataImporter()

        data = {
            "suppliers": [
                {"id": "SUP-001", "name": "Supplier", "location": "Taiwan", "tier": 1}
            ],
            "components": [
                {"id": "COMP-001", "name": "Component", "category": "Electronics"}
            ],
            "products": [
                {"id": "PROD-001", "name": "Product", "product_line": "Consumer"}
            ],
            "supplies": [
                {"supplier_id": "SUP-001", "component_id": "COMP-001", "is_primary": True}
            ],
            "part_of": [
                {"component_id": "COMP-001", "product_id": "PROD-001", "quantity": 2}
            ]
        }

        result = importer.import_json(data)

        assert result.success
        assert len(importer.get_supplies_relations()) == 1
        assert len(importer.get_part_of_relations()) == 1

    def test_import_csv_suppliers(self):
        """Test importing suppliers from CSV."""
        importer = DataImporter()

        csv_data = """id,name,location,tier
SUP-001,Test Supplier,Taiwan,1
SUP-002,Another Supplier,Germany,2"""

        result = importer.import_csv("supplier", csv_data)

        assert result.success
        assert result.imported_count == 2

    def test_import_csv_invalid_type(self):
        """Test handling of invalid entity type."""
        importer = DataImporter()

        result = importer.import_csv("invalid_type", "id,name\n1,test")

        assert not result.success

    def test_clear_imported_data(self):
        """Test clearing imported data."""
        importer = DataImporter()

        importer.import_json({
            "suppliers": [
                {"id": "SUP-001", "name": "Test", "location": "Taiwan", "tier": 1}
            ]
        })

        assert len(importer.get_suppliers()) == 1

        importer.clear()

        assert len(importer.get_suppliers()) == 0


class TestDataExporter:
    """Tests for DataExporter."""

    def test_export_json(self):
        """Test exporting to JSON."""
        exporter = DataExporter()

        suppliers = [
            Supplier(id="SUP-001", name="Test", location="Taiwan", tier=1)
        ]
        components = [
            Component(id="COMP-001", name="Test", category="Electronics")
        ]
        products = [
            Product(id="PROD-001", name="Test", product_line="Consumer")
        ]

        result = exporter.export_json(suppliers, components, products)

        assert result.success
        assert result.format == "json"
        assert result.record_count == 3

        # Verify JSON structure
        data = json.loads(result.data)
        assert "suppliers" in data
        assert "components" in data
        assert "products" in data
        assert len(data["suppliers"]) == 1

    def test_export_json_with_metadata(self):
        """Test exporting with metadata."""
        exporter = DataExporter()

        result = exporter.export_json([], [], [], include_metadata=True)

        data = json.loads(result.data)
        assert "_metadata" in data
        assert "exported_at" in data["_metadata"]
        assert "format_version" in data["_metadata"]

    def test_export_csv_suppliers(self):
        """Test exporting suppliers to CSV."""
        exporter = DataExporter()

        suppliers = [
            Supplier(id="SUP-001", name="Test 1", location="Taiwan", tier=1),
            Supplier(id="SUP-002", name="Test 2", location="Germany", tier=2),
        ]

        result = exporter.export_csv("supplier", suppliers)

        assert result.success
        assert result.format == "csv"
        assert result.record_count == 2
        assert "SUP-001" in result.data
        assert "SUP-002" in result.data

    def test_export_csv_empty(self):
        """Test exporting empty list."""
        exporter = DataExporter()

        result = exporter.export_csv("supplier", [])

        assert result.success
        assert result.record_count == 0


class TestValidateImportData:
    """Tests for validate_import_data."""

    def test_valid_data(self):
        """Test validation of valid data."""
        data = {
            "suppliers": [{"id": "SUP-001"}],
            "components": [{"id": "COMP-001"}],
            "supplies": [{"supplier_id": "SUP-001", "component_id": "COMP-001"}]
        }

        errors = validate_import_data(data)

        assert len(errors) == 0

    def test_missing_entities(self):
        """Test validation catches missing entities."""
        data = {}

        errors = validate_import_data(data)

        assert len(errors) > 0

    def test_orphaned_relationship(self):
        """Test validation catches orphaned relationships."""
        data = {
            "suppliers": [{"id": "SUP-001"}],
            "supplies": [{"supplier_id": "SUP-001", "component_id": "COMP-MISSING"}]
        }

        errors = validate_import_data(data)

        assert any("unknown component" in e.lower() for e in errors)


class TestEntityManager:
    """Tests for EntityManager."""

    def test_create_supplier(self):
        """Test creating a supplier."""
        manager = EntityManager()

        result = manager.create_supplier(
            name="Test Supplier",
            location="Taiwan",
            tier=1,
        )

        assert result.success
        assert result.entity_id is not None
        assert result.entity_id.startswith("SUP-")

    def test_get_supplier(self):
        """Test getting a supplier."""
        manager = EntityManager()

        create_result = manager.create_supplier(
            name="Test",
            location="Taiwan",
        )

        supplier = manager.get_supplier(create_result.entity_id)

        assert supplier is not None
        assert supplier.name == "Test"

    def test_update_supplier(self):
        """Test updating a supplier."""
        manager = EntityManager()

        create_result = manager.create_supplier(
            name="Original",
            location="Taiwan",
        )

        update_result = manager.update_supplier(
            create_result.entity_id,
            name="Updated",
        )

        assert update_result.success
        assert manager.get_supplier(create_result.entity_id).name == "Updated"

    def test_delete_supplier(self):
        """Test deleting a supplier."""
        manager = EntityManager()

        create_result = manager.create_supplier(
            name="To Delete",
            location="Taiwan",
        )

        delete_result = manager.delete_supplier(create_result.entity_id)

        assert delete_result.success
        assert manager.get_supplier(create_result.entity_id) is None

    def test_list_suppliers_with_filter(self):
        """Test listing suppliers with filter."""
        manager = EntityManager()

        manager.create_supplier(name="Taiwan 1", location="Taiwan")
        manager.create_supplier(name="Taiwan 2", location="Taiwan")
        manager.create_supplier(name="Germany 1", location="Germany")

        taiwan_suppliers = manager.list_suppliers(location="Taiwan")

        assert len(taiwan_suppliers) == 2

    def test_create_component(self):
        """Test creating a component."""
        manager = EntityManager()

        result = manager.create_component(
            name="Test Component",
            category="Electronics",
        )

        assert result.success
        assert result.entity_id.startswith("COMP-")

    def test_create_product(self):
        """Test creating a product."""
        manager = EntityManager()

        result = manager.create_product(
            name="Test Product",
            product_line="Consumer",
        )

        assert result.success
        assert result.entity_id.startswith("PROD-")

    def test_add_supplies_relation(self):
        """Test adding a supplies relation."""
        manager = EntityManager()

        sup_result = manager.create_supplier(name="Sup", location="Taiwan")
        comp_result = manager.create_component(name="Comp", category="Electronics")

        rel_result = manager.add_supplies_relation(
            supplier_id=sup_result.entity_id,
            component_id=comp_result.entity_id,
            is_primary=True,
        )

        assert rel_result.success

    def test_add_supplies_relation_invalid_supplier(self):
        """Test adding relation with invalid supplier."""
        manager = EntityManager()

        comp_result = manager.create_component(name="Comp", category="Electronics")

        rel_result = manager.add_supplies_relation(
            supplier_id="INVALID",
            component_id=comp_result.entity_id,
        )

        assert not rel_result.success

    def test_get_component_suppliers(self):
        """Test getting component suppliers."""
        manager = EntityManager()

        sup1 = manager.create_supplier(name="Sup1", location="Taiwan")
        sup2 = manager.create_supplier(name="Sup2", location="Germany")
        comp = manager.create_component(name="Comp", category="Electronics")

        manager.add_supplies_relation(sup1.entity_id, comp.entity_id)
        manager.add_supplies_relation(sup2.entity_id, comp.entity_id)

        suppliers = manager.get_component_suppliers(comp.entity_id)

        assert len(suppliers) == 2

    def test_bulk_create_suppliers(self):
        """Test bulk creating suppliers."""
        manager = EntityManager()

        suppliers_data = [
            {"name": "Supplier 1", "location": "Taiwan"},
            {"name": "Supplier 2", "location": "Germany"},
            {"name": "Supplier 3", "location": "USA"},
        ]

        result = manager.bulk_create_suppliers(suppliers_data)

        assert result.success
        assert result.succeeded == 3
        assert result.failed == 0

    def test_get_statistics(self):
        """Test getting statistics."""
        manager = EntityManager()

        manager.create_supplier(name="Sup", location="Taiwan")
        manager.create_component(name="Comp", category="Electronics")
        manager.create_product(name="Prod", product_line="Consumer")

        stats = manager.get_statistics()

        assert stats["suppliers"] == 1
        assert stats["components"] == 1
        assert stats["products"] == 1

    def test_validate_consistency(self):
        """Test consistency validation."""
        manager = EntityManager()

        # Create component without supplier (inconsistency)
        manager.create_component(name="Orphan", category="Electronics")

        issues = manager.validate_consistency()

        assert len(issues) > 0
        assert any("no suppliers" in i.lower() for i in issues)
