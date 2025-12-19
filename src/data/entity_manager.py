"""
Supply Chain Entity Management.

Provides CRUD operations for suppliers, components, and products
with relationship management and consistency validation.
"""

from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any, TypeVar
import uuid

import structlog

from src.models import Supplier, Component, Product, SuppliesRelation, PartOfRelation

logger = structlog.get_logger(__name__)


T = TypeVar("T", Supplier, Component, Product)


@dataclass
class OperationResult:
    """Result of a CRUD operation."""

    success: bool
    message: str
    entity_id: str | None = None
    data: Any = None


@dataclass
class BulkOperationResult:
    """Result of a bulk operation."""

    success: bool
    total: int
    succeeded: int
    failed: int
    errors: list[dict[str, Any]] = field(default_factory=list)


class EntityManager:
    """
    Manages supply chain entities with CRUD operations.

    Provides:
    - Create, Read, Update, Delete for suppliers, components, products
    - Relationship management
    - Consistency validation
    - Bulk operations
    """

    def __init__(self):
        """Initialize the entity manager."""
        self._suppliers: dict[str, Supplier] = {}
        self._components: dict[str, Component] = {}
        self._products: dict[str, Product] = {}
        self._supplies_relations: list[SuppliesRelation] = []
        self._part_of_relations: list[PartOfRelation] = []

    # =========================================================================
    # Supplier CRUD
    # =========================================================================

    def create_supplier(
        self,
        name: str,
        location: str,
        tier: int = 1,
        **kwargs,
    ) -> OperationResult:
        """Create a new supplier."""
        supplier_id = f"SUP-{uuid.uuid4().hex[:8].upper()}"

        try:
            supplier = Supplier(
                id=supplier_id,
                name=name,
                location=location,
                tier=tier,
                **kwargs,
            )
            self._suppliers[supplier_id] = supplier

            logger.info("Supplier created", supplier_id=supplier_id, name=name)

            return OperationResult(
                success=True,
                message=f"Supplier {name} created",
                entity_id=supplier_id,
                data=supplier,
            )
        except Exception as e:
            logger.error("Failed to create supplier", error=str(e))
            return OperationResult(
                success=False,
                message=f"Failed to create supplier: {e}",
            )

    def get_supplier(self, supplier_id: str) -> Supplier | None:
        """Get a supplier by ID."""
        return self._suppliers.get(supplier_id)

    def update_supplier(
        self,
        supplier_id: str,
        **updates,
    ) -> OperationResult:
        """Update a supplier."""
        supplier = self._suppliers.get(supplier_id)
        if not supplier:
            return OperationResult(
                success=False,
                message=f"Supplier {supplier_id} not found",
            )

        try:
            # Create updated supplier
            updated_data = supplier.model_dump()
            updated_data.update(updates)
            updated_supplier = Supplier(**updated_data)
            self._suppliers[supplier_id] = updated_supplier

            logger.info("Supplier updated", supplier_id=supplier_id)

            return OperationResult(
                success=True,
                message=f"Supplier {supplier_id} updated",
                entity_id=supplier_id,
                data=updated_supplier,
            )
        except Exception as e:
            logger.error("Failed to update supplier", error=str(e))
            return OperationResult(
                success=False,
                message=f"Failed to update supplier: {e}",
            )

    def delete_supplier(self, supplier_id: str) -> OperationResult:
        """Delete a supplier and its relationships."""
        if supplier_id not in self._suppliers:
            return OperationResult(
                success=False,
                message=f"Supplier {supplier_id} not found",
            )

        # Remove relationships
        self._supplies_relations = [
            r for r in self._supplies_relations if r.supplier_id != supplier_id
        ]

        del self._suppliers[supplier_id]

        logger.info("Supplier deleted", supplier_id=supplier_id)

        return OperationResult(
            success=True,
            message=f"Supplier {supplier_id} deleted",
            entity_id=supplier_id,
        )

    def list_suppliers(
        self,
        location: str | None = None,
        tier: int | None = None,
    ) -> list[Supplier]:
        """List suppliers with optional filtering."""
        suppliers = list(self._suppliers.values())

        if location:
            suppliers = [s for s in suppliers if s.location.lower() == location.lower()]
        if tier:
            suppliers = [s for s in suppliers if s.tier == tier]

        return suppliers

    # =========================================================================
    # Component CRUD
    # =========================================================================

    def create_component(
        self,
        name: str,
        category: str,
        **kwargs,
    ) -> OperationResult:
        """Create a new component."""
        component_id = f"COMP-{uuid.uuid4().hex[:8].upper()}"

        try:
            component = Component(
                id=component_id,
                name=name,
                category=category,
                **kwargs,
            )
            self._components[component_id] = component

            logger.info("Component created", component_id=component_id, name=name)

            return OperationResult(
                success=True,
                message=f"Component {name} created",
                entity_id=component_id,
                data=component,
            )
        except Exception as e:
            logger.error("Failed to create component", error=str(e))
            return OperationResult(
                success=False,
                message=f"Failed to create component: {e}",
            )

    def get_component(self, component_id: str) -> Component | None:
        """Get a component by ID."""
        return self._components.get(component_id)

    def update_component(
        self,
        component_id: str,
        **updates,
    ) -> OperationResult:
        """Update a component."""
        component = self._components.get(component_id)
        if not component:
            return OperationResult(
                success=False,
                message=f"Component {component_id} not found",
            )

        try:
            updated_data = component.model_dump()
            updated_data.update(updates)
            updated_component = Component(**updated_data)
            self._components[component_id] = updated_component

            logger.info("Component updated", component_id=component_id)

            return OperationResult(
                success=True,
                message=f"Component {component_id} updated",
                entity_id=component_id,
                data=updated_component,
            )
        except Exception as e:
            logger.error("Failed to update component", error=str(e))
            return OperationResult(
                success=False,
                message=f"Failed to update component: {e}",
            )

    def delete_component(self, component_id: str) -> OperationResult:
        """Delete a component and its relationships."""
        if component_id not in self._components:
            return OperationResult(
                success=False,
                message=f"Component {component_id} not found",
            )

        # Remove relationships
        self._supplies_relations = [
            r for r in self._supplies_relations if r.component_id != component_id
        ]
        self._part_of_relations = [
            r for r in self._part_of_relations if r.component_id != component_id
        ]

        del self._components[component_id]

        logger.info("Component deleted", component_id=component_id)

        return OperationResult(
            success=True,
            message=f"Component {component_id} deleted",
            entity_id=component_id,
        )

    def list_components(
        self,
        category: str | None = None,
    ) -> list[Component]:
        """List components with optional filtering."""
        components = list(self._components.values())

        if category:
            components = [c for c in components if c.category.lower() == category.lower()]

        return components

    # =========================================================================
    # Product CRUD
    # =========================================================================

    def create_product(
        self,
        name: str,
        product_line: str,
        **kwargs,
    ) -> OperationResult:
        """Create a new product."""
        product_id = f"PROD-{uuid.uuid4().hex[:8].upper()}"

        try:
            product = Product(
                id=product_id,
                name=name,
                product_line=product_line,
                **kwargs,
            )
            self._products[product_id] = product

            logger.info("Product created", product_id=product_id, name=name)

            return OperationResult(
                success=True,
                message=f"Product {name} created",
                entity_id=product_id,
                data=product,
            )
        except Exception as e:
            logger.error("Failed to create product", error=str(e))
            return OperationResult(
                success=False,
                message=f"Failed to create product: {e}",
            )

    def get_product(self, product_id: str) -> Product | None:
        """Get a product by ID."""
        return self._products.get(product_id)

    def update_product(
        self,
        product_id: str,
        **updates,
    ) -> OperationResult:
        """Update a product."""
        product = self._products.get(product_id)
        if not product:
            return OperationResult(
                success=False,
                message=f"Product {product_id} not found",
            )

        try:
            updated_data = product.model_dump()
            updated_data.update(updates)
            updated_product = Product(**updated_data)
            self._products[product_id] = updated_product

            logger.info("Product updated", product_id=product_id)

            return OperationResult(
                success=True,
                message=f"Product {product_id} updated",
                entity_id=product_id,
                data=updated_product,
            )
        except Exception as e:
            logger.error("Failed to update product", error=str(e))
            return OperationResult(
                success=False,
                message=f"Failed to update product: {e}",
            )

    def delete_product(self, product_id: str) -> OperationResult:
        """Delete a product and its relationships."""
        if product_id not in self._products:
            return OperationResult(
                success=False,
                message=f"Product {product_id} not found",
            )

        # Remove relationships
        self._part_of_relations = [
            r for r in self._part_of_relations if r.product_id != product_id
        ]

        del self._products[product_id]

        logger.info("Product deleted", product_id=product_id)

        return OperationResult(
            success=True,
            message=f"Product {product_id} deleted",
            entity_id=product_id,
        )

    def list_products(
        self,
        product_line: str | None = None,
    ) -> list[Product]:
        """List products with optional filtering."""
        products = list(self._products.values())

        if product_line:
            products = [p for p in products if p.product_line.lower() == product_line.lower()]

        return products

    # =========================================================================
    # Relationship Management
    # =========================================================================

    def add_supplies_relation(
        self,
        supplier_id: str,
        component_id: str,
        is_primary: bool = False,
    ) -> OperationResult:
        """Add a supplies relationship between supplier and component."""
        if supplier_id not in self._suppliers:
            return OperationResult(
                success=False,
                message=f"Supplier {supplier_id} not found",
            )
        if component_id not in self._components:
            return OperationResult(
                success=False,
                message=f"Component {component_id} not found",
            )

        # Check for duplicate
        existing = any(
            r.supplier_id == supplier_id and r.component_id == component_id
            for r in self._supplies_relations
        )
        if existing:
            return OperationResult(
                success=False,
                message="Relationship already exists",
            )

        relation = SuppliesRelation(
            supplier_id=supplier_id,
            component_id=component_id,
            is_primary=is_primary,
        )
        self._supplies_relations.append(relation)

        return OperationResult(
            success=True,
            message=f"Added supplies relation: {supplier_id} -> {component_id}",
            data=relation,
        )

    def add_part_of_relation(
        self,
        component_id: str,
        product_id: str,
        quantity: int = 1,
    ) -> OperationResult:
        """Add a part_of relationship between component and product."""
        if component_id not in self._components:
            return OperationResult(
                success=False,
                message=f"Component {component_id} not found",
            )
        if product_id not in self._products:
            return OperationResult(
                success=False,
                message=f"Product {product_id} not found",
            )

        # Check for duplicate
        existing = any(
            r.component_id == component_id and r.product_id == product_id
            for r in self._part_of_relations
        )
        if existing:
            return OperationResult(
                success=False,
                message="Relationship already exists",
            )

        relation = PartOfRelation(
            component_id=component_id,
            product_id=product_id,
            quantity=quantity,
        )
        self._part_of_relations.append(relation)

        return OperationResult(
            success=True,
            message=f"Added part_of relation: {component_id} -> {product_id}",
            data=relation,
        )

    def get_component_suppliers(self, component_id: str) -> list[Supplier]:
        """Get all suppliers for a component."""
        supplier_ids = [
            r.supplier_id
            for r in self._supplies_relations
            if r.component_id == component_id
        ]
        return [self._suppliers[sid] for sid in supplier_ids if sid in self._suppliers]

    def get_product_components(self, product_id: str) -> list[Component]:
        """Get all components for a product."""
        component_ids = [
            r.component_id
            for r in self._part_of_relations
            if r.product_id == product_id
        ]
        return [self._components[cid] for cid in component_ids if cid in self._components]

    # =========================================================================
    # Bulk Operations
    # =========================================================================

    def bulk_create_suppliers(
        self,
        suppliers_data: list[dict],
    ) -> BulkOperationResult:
        """Create multiple suppliers in bulk."""
        result = BulkOperationResult(
            success=True,
            total=len(suppliers_data),
            succeeded=0,
            failed=0,
        )

        for i, data in enumerate(suppliers_data):
            try:
                op_result = self.create_supplier(**data)
                if op_result.success:
                    result.succeeded += 1
                else:
                    result.failed += 1
                    result.errors.append({
                        "index": i,
                        "error": op_result.message,
                    })
            except Exception as e:
                result.failed += 1
                result.errors.append({
                    "index": i,
                    "error": str(e),
                })

        result.success = result.failed == 0
        return result

    def bulk_update(
        self,
        entity_type: str,
        updates: list[dict],
    ) -> BulkOperationResult:
        """
        Update multiple entities in bulk.

        Each update dict should contain 'id' and the fields to update.
        """
        result = BulkOperationResult(
            success=True,
            total=len(updates),
            succeeded=0,
            failed=0,
        )

        update_func = {
            "supplier": self.update_supplier,
            "component": self.update_component,
            "product": self.update_product,
        }.get(entity_type)

        if not update_func:
            result.success = False
            result.errors.append({"error": f"Unknown entity type: {entity_type}"})
            return result

        for i, update in enumerate(updates):
            entity_id = update.pop("id", None)
            if not entity_id:
                result.failed += 1
                result.errors.append({"index": i, "error": "Missing 'id' field"})
                continue

            op_result = update_func(entity_id, **update)
            if op_result.success:
                result.succeeded += 1
            else:
                result.failed += 1
                result.errors.append({
                    "index": i,
                    "id": entity_id,
                    "error": op_result.message,
                })

        result.success = result.failed == 0
        return result

    # =========================================================================
    # Statistics
    # =========================================================================

    def get_statistics(self) -> dict[str, Any]:
        """Get entity statistics."""
        return {
            "suppliers": len(self._suppliers),
            "components": len(self._components),
            "products": len(self._products),
            "supplies_relations": len(self._supplies_relations),
            "part_of_relations": len(self._part_of_relations),
        }

    def validate_consistency(self) -> list[str]:
        """
        Validate data consistency.

        Returns:
            List of consistency issues found.
        """
        issues = []

        # Check for orphaned relationships
        for rel in self._supplies_relations:
            if rel.supplier_id not in self._suppliers:
                issues.append(f"Orphaned supplies relation: supplier {rel.supplier_id} not found")
            if rel.component_id not in self._components:
                issues.append(f"Orphaned supplies relation: component {rel.component_id} not found")

        for rel in self._part_of_relations:
            if rel.component_id not in self._components:
                issues.append(f"Orphaned part_of relation: component {rel.component_id} not found")
            if rel.product_id not in self._products:
                issues.append(f"Orphaned part_of relation: product {rel.product_id} not found")

        # Check for components without suppliers
        for comp_id in self._components:
            has_supplier = any(r.component_id == comp_id for r in self._supplies_relations)
            if not has_supplier:
                issues.append(f"Component {comp_id} has no suppliers")

        # Check for products without components
        for prod_id in self._products:
            has_component = any(r.product_id == prod_id for r in self._part_of_relations)
            if not has_component:
                issues.append(f"Product {prod_id} has no components")

        return issues
