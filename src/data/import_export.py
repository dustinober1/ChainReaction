"""
Data Import/Export Utilities.

Provides functionality for importing and exporting supply chain data
in various formats with validation and error handling.
"""

import json
import csv
from datetime import datetime, timezone
from io import StringIO
from pathlib import Path
from typing import Any, TypeVar
from dataclasses import dataclass, field

from pydantic import BaseModel, ValidationError
import structlog

from src.models import Supplier, Component, Product, SuppliesRelation, PartOfRelation

logger = structlog.get_logger(__name__)


T = TypeVar("T", bound=BaseModel)


@dataclass
class ImportResult:
    """Result of an import operation."""

    success: bool
    total_records: int = 0
    imported_count: int = 0
    failed_count: int = 0
    errors: list[dict[str, Any]] = field(default_factory=list)
    warnings: list[str] = field(default_factory=list)


@dataclass
class ExportResult:
    """Result of an export operation."""

    success: bool
    format: str
    record_count: int
    data: str | bytes
    filename: str


class DataImporter:
    """
    Handles importing supply chain data from various formats.

    Supports JSON and CSV formats with validation and error handling.
    """

    def __init__(self):
        """Initialize the importer."""
        self._suppliers: dict[str, Supplier] = {}
        self._components: dict[str, Component] = {}
        self._products: dict[str, Product] = {}
        self._supplies_relations: list[SuppliesRelation] = []
        self._part_of_relations: list[PartOfRelation] = []

    def import_json(self, data: str | dict) -> ImportResult:
        """
        Import supply chain data from JSON.

        Args:
            data: JSON string or dictionary with supply chain data.

        Returns:
            ImportResult with import statistics.
        """
        result = ImportResult(success=True)

        try:
            if isinstance(data, str):
                parsed = json.loads(data)
            else:
                parsed = data

            # Import suppliers
            if "suppliers" in parsed:
                for i, sup_data in enumerate(parsed["suppliers"]):
                    try:
                        supplier = Supplier(**sup_data)
                        self._suppliers[supplier.id] = supplier
                        result.imported_count += 1
                    except ValidationError as e:
                        result.failed_count += 1
                        result.errors.append({
                            "type": "supplier",
                            "index": i,
                            "data": sup_data,
                            "error": str(e),
                        })
                    result.total_records += 1

            # Import components
            if "components" in parsed:
                for i, comp_data in enumerate(parsed["components"]):
                    try:
                        component = Component(**comp_data)
                        self._components[component.id] = component
                        result.imported_count += 1
                    except ValidationError as e:
                        result.failed_count += 1
                        result.errors.append({
                            "type": "component",
                            "index": i,
                            "data": comp_data,
                            "error": str(e),
                        })
                    result.total_records += 1

            # Import products
            if "products" in parsed:
                for i, prod_data in enumerate(parsed["products"]):
                    try:
                        product = Product(**prod_data)
                        self._products[product.id] = product
                        result.imported_count += 1
                    except ValidationError as e:
                        result.failed_count += 1
                        result.errors.append({
                            "type": "product",
                            "index": i,
                            "data": prod_data,
                            "error": str(e),
                        })
                    result.total_records += 1

            # Import relationships
            if "supplies" in parsed:
                for rel in parsed["supplies"]:
                    supplier_id = rel.get("supplier_id")
                    component_id = rel.get("component_id")
                    if supplier_id in self._suppliers and component_id in self._components:
                        self._supplies_relations.append(
                            SuppliesRelation(
                                supplier_id=supplier_id,
                                component_id=component_id,
                                is_primary=rel.get("is_primary", False),
                            )
                        )
                    else:
                        result.warnings.append(
                            f"Skipped supplies relation {supplier_id} -> {component_id}: entity not found"
                        )

            if "part_of" in parsed:
                for rel in parsed["part_of"]:
                    component_id = rel.get("component_id")
                    product_id = rel.get("product_id")
                    if component_id in self._components and product_id in self._products:
                        self._part_of_relations.append(
                            PartOfRelation(
                                component_id=component_id,
                                product_id=product_id,
                                quantity=rel.get("quantity", 1),
                            )
                        )
                    else:
                        result.warnings.append(
                            f"Skipped part_of relation {component_id} -> {product_id}: entity not found"
                        )

            result.success = result.failed_count == 0

        except json.JSONDecodeError as e:
            result.success = False
            result.errors.append({
                "type": "parse",
                "error": f"Invalid JSON: {e}",
            })

        return result

    def import_csv(
        self,
        entity_type: str,
        csv_data: str,
    ) -> ImportResult:
        """
        Import entities from CSV format.

        Args:
            entity_type: Type of entity ('supplier', 'component', 'product').
            csv_data: CSV string with entity data.

        Returns:
            ImportResult with import statistics.
        """
        result = ImportResult(success=True)

        model_map = {
            "supplier": (Supplier, self._suppliers),
            "component": (Component, self._components),
            "product": (Product, self._products),
        }

        if entity_type not in model_map:
            result.success = False
            result.errors.append({
                "type": "config",
                "error": f"Unknown entity type: {entity_type}",
            })
            return result

        model_class, storage = model_map[entity_type]

        reader = csv.DictReader(StringIO(csv_data))
        for i, row in enumerate(reader):
            result.total_records += 1
            try:
                entity = model_class(**row)
                storage[entity.id] = entity
                result.imported_count += 1
            except ValidationError as e:
                result.failed_count += 1
                result.errors.append({
                    "type": entity_type,
                    "index": i,
                    "data": row,
                    "error": str(e),
                })

        result.success = result.failed_count == 0
        return result

    def get_suppliers(self) -> list[Supplier]:
        """Get all imported suppliers."""
        return list(self._suppliers.values())

    def get_components(self) -> list[Component]:
        """Get all imported components."""
        return list(self._components.values())

    def get_products(self) -> list[Product]:
        """Get all imported products."""
        return list(self._products.values())

    def get_supplies_relations(self) -> list[SuppliesRelation]:
        """Get all supplies relations."""
        return self._supplies_relations

    def get_part_of_relations(self) -> list[PartOfRelation]:
        """Get all part_of relations."""
        return self._part_of_relations

    def clear(self):
        """Clear all imported data."""
        self._suppliers.clear()
        self._components.clear()
        self._products.clear()
        self._supplies_relations.clear()
        self._part_of_relations.clear()


class DataExporter:
    """
    Handles exporting supply chain data to various formats.

    Supports JSON and CSV formats.
    """

    def export_json(
        self,
        suppliers: list[Supplier],
        components: list[Component],
        products: list[Product],
        supplies: list[SuppliesRelation] | None = None,
        part_of: list[PartOfRelation] | None = None,
        include_metadata: bool = True,
    ) -> ExportResult:
        """
        Export supply chain data to JSON format.

        Args:
            suppliers: List of suppliers.
            components: List of components.
            products: List of products.
            supplies: Optional list of supplies relations.
            part_of: Optional list of part_of relations.
            include_metadata: Whether to include export metadata.

        Returns:
            ExportResult with JSON data.
        """
        data: dict[str, Any] = {}

        if include_metadata:
            data["_metadata"] = {
                "exported_at": datetime.now(timezone.utc).isoformat(),
                "format_version": "1.0",
                "record_count": {
                    "suppliers": len(suppliers),
                    "components": len(components),
                    "products": len(products),
                },
            }

        data["suppliers"] = [s.model_dump(mode="json") for s in suppliers]
        data["components"] = [c.model_dump(mode="json") for c in components]
        data["products"] = [p.model_dump(mode="json") for p in products]

        if supplies:
            data["supplies"] = [r.model_dump(mode="json") for r in supplies]
        if part_of:
            data["part_of"] = [r.model_dump(mode="json") for r in part_of]

        json_data = json.dumps(data, indent=2, default=str)
        record_count = len(suppliers) + len(components) + len(products)

        return ExportResult(
            success=True,
            format="json",
            record_count=record_count,
            data=json_data,
            filename=f"supply_chain_export_{datetime.now(timezone.utc).strftime('%Y%m%d_%H%M%S')}.json",
        )

    def export_csv(
        self,
        entity_type: str,
        entities: list[Supplier] | list[Component] | list[Product],
    ) -> ExportResult:
        """
        Export entities to CSV format.

        Args:
            entity_type: Type of entity being exported.
            entities: List of entities to export.

        Returns:
            ExportResult with CSV data.
        """
        if not entities:
            return ExportResult(
                success=True,
                format="csv",
                record_count=0,
                data="",
                filename=f"{entity_type}_export.csv",
            )

        output = StringIO()
        
        # Get field names from first entity
        first = entities[0]
        fieldnames = list(first.model_dump().keys())

        writer = csv.DictWriter(output, fieldnames=fieldnames)
        writer.writeheader()

        for entity in entities:
            row = entity.model_dump(mode="json")
            # Flatten any nested structures
            flattened = {}
            for k, v in row.items():
                if isinstance(v, (list, dict)):
                    flattened[k] = json.dumps(v)
                else:
                    flattened[k] = v
            writer.writerow(flattened)

        csv_data = output.getvalue()

        return ExportResult(
            success=True,
            format="csv",
            record_count=len(entities),
            data=csv_data,
            filename=f"{entity_type}_export_{datetime.now(timezone.utc).strftime('%Y%m%d_%H%M%S')}.csv",
        )


def validate_import_data(data: dict) -> list[str]:
    """
    Validate import data structure.

    Args:
        data: Parsed import data.

    Returns:
        List of validation errors.
    """
    errors = []

    # Check for required fields
    has_entities = any(
        key in data for key in ["suppliers", "components", "products"]
    )
    if not has_entities:
        errors.append("No entity data found (suppliers, components, or products)")

    # Check for referenced entities in relationships
    supplier_ids = {s.get("id") for s in data.get("suppliers", [])}
    component_ids = {c.get("id") for c in data.get("components", [])}
    product_ids = {p.get("id") for p in data.get("products", [])}

    for rel in data.get("supplies", []):
        if rel.get("supplier_id") not in supplier_ids:
            errors.append(f"Supplies relation references unknown supplier: {rel.get('supplier_id')}")
        if rel.get("component_id") not in component_ids:
            errors.append(f"Supplies relation references unknown component: {rel.get('component_id')}")

    for rel in data.get("part_of", []):
        if rel.get("component_id") not in component_ids:
            errors.append(f"Part_of relation references unknown component: {rel.get('component_id')}")
        if rel.get("product_id") not in product_ids:
            errors.append(f"Part_of relation references unknown product: {rel.get('product_id')}")

    return errors
