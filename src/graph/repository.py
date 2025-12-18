"""
Graph Repository for Supply Chain Entity Operations.

Provides a high-level interface for managing supply chain entities
in the Neo4j knowledge graph with full CRUD support.
"""

from typing import Any

import structlog

from src.graph.connection import Neo4jConnection, get_connection
from src.graph.queries import (
    create_supplier_query,
    create_component_query,
    create_product_query,
    create_location_query,
    create_risk_event_query,
    create_supplier_supplies_component_query,
    create_component_part_of_product_query,
    create_supplier_located_in_query,
    create_component_part_of_component_query,
    find_suppliers_by_location_query,
    find_products_by_supplier_query,
    find_supply_chain_path_query,
    get_product_dependencies_query,
    find_downstream_impact_query,
    find_alternative_suppliers_query,
    calculate_supplier_redundancy_query,
)
from src.models import (
    Supplier,
    Component,
    Product,
    Location,
    RiskEvent,
    EntityTier,
    SeverityLevel,
    EventType,
)

logger = structlog.get_logger(__name__)


class SupplyChainRepository:
    """
    Repository for supply chain entity operations.

    Provides methods for creating, reading, updating, and deleting
    supply chain entities in the Neo4j graph database.
    """

    def __init__(self, connection: Neo4jConnection | None = None):
        """
        Initialize the repository.

        Args:
            connection: Optional Neo4j connection. If None, uses global connection.
        """
        self._connection = connection

    async def _get_connection(self) -> Neo4jConnection:
        """Get the database connection."""
        if self._connection is not None:
            return self._connection
        return await get_connection()

    # =========================================================================
    # Create Operations
    # =========================================================================

    async def create_supplier(self, supplier: Supplier) -> dict[str, Any]:
        """
        Create a new supplier in the graph.

        Args:
            supplier: Supplier model instance.

        Returns:
            Created node data.
        """
        conn = await self._get_connection()
        query, params = create_supplier_query(supplier)
        result = await conn.execute_query(query, params)

        logger.info("Created supplier", supplier_id=supplier.id, name=supplier.name)
        return result[0] if result else {}

    async def create_component(self, component: Component) -> dict[str, Any]:
        """Create a new component in the graph."""
        conn = await self._get_connection()
        query, params = create_component_query(component)
        result = await conn.execute_query(query, params)

        logger.info("Created component", component_id=component.id, name=component.name)
        return result[0] if result else {}

    async def create_product(self, product: Product) -> dict[str, Any]:
        """Create a new product in the graph."""
        conn = await self._get_connection()
        query, params = create_product_query(product)
        result = await conn.execute_query(query, params)

        logger.info("Created product", product_id=product.id, name=product.name)
        return result[0] if result else {}

    async def create_location(self, location: Location) -> dict[str, Any]:
        """Create a new location in the graph."""
        conn = await self._get_connection()
        query, params = create_location_query(location)
        result = await conn.execute_query(query, params)

        logger.info("Created location", location_id=location.id, name=location.name)
        return result[0] if result else {}

    async def create_risk_event(self, risk_event: RiskEvent) -> dict[str, Any]:
        """Create a new risk event in the graph."""
        conn = await self._get_connection()
        query, params = create_risk_event_query(risk_event)
        result = await conn.execute_query(query, params)

        logger.info(
            "Created risk event",
            event_id=risk_event.id,
            event_type=risk_event.event_type.value,
        )
        return result[0] if result else {}

    # =========================================================================
    # Relationship Operations
    # =========================================================================

    async def link_supplier_to_component(
        self,
        supplier_id: str,
        component_id: str,
        priority: int = 1,
    ) -> dict[str, Any]:
        """Create SUPPLIES relationship from supplier to component."""
        conn = await self._get_connection()
        query, params = create_supplier_supplies_component_query(
            supplier_id, component_id, priority
        )
        result = await conn.execute_query(query, params)

        logger.debug(
            "Linked supplier to component",
            supplier_id=supplier_id,
            component_id=component_id,
        )
        return result[0] if result else {}

    async def link_component_to_product(
        self,
        component_id: str,
        product_id: str,
        quantity: int = 1,
    ) -> dict[str, Any]:
        """Create PART_OF relationship from component to product."""
        conn = await self._get_connection()
        query, params = create_component_part_of_product_query(
            component_id, product_id, quantity
        )
        result = await conn.execute_query(query, params)

        logger.debug(
            "Linked component to product",
            component_id=component_id,
            product_id=product_id,
        )
        return result[0] if result else {}

    async def link_supplier_to_location(
        self,
        supplier_id: str,
        location_id: str,
    ) -> dict[str, Any]:
        """Create LOCATED_IN relationship from supplier to location."""
        conn = await self._get_connection()
        query, params = create_supplier_located_in_query(supplier_id, location_id)
        result = await conn.execute_query(query, params)

        logger.debug(
            "Linked supplier to location",
            supplier_id=supplier_id,
            location_id=location_id,
        )
        return result[0] if result else {}

    async def link_component_to_component(
        self,
        child_id: str,
        parent_id: str,
        quantity: int = 1,
    ) -> dict[str, Any]:
        """Create PART_OF relationship between components (sub-assembly)."""
        conn = await self._get_connection()
        query, params = create_component_part_of_component_query(
            child_id, parent_id, quantity
        )
        result = await conn.execute_query(query, params)

        logger.debug(
            "Linked child component to parent",
            child_id=child_id,
            parent_id=parent_id,
        )
        return result[0] if result else {}

    # =========================================================================
    # Query Operations
    # =========================================================================

    async def find_suppliers_by_location(self, location: str) -> list[dict[str, Any]]:
        """Find all suppliers in a specific location."""
        conn = await self._get_connection()
        query, params = find_suppliers_by_location_query(location)
        return await conn.execute_query(query, params)

    async def find_products_affected_by_supplier(
        self, supplier_id: str
    ) -> list[dict[str, Any]]:
        """Find all products that depend on a specific supplier."""
        conn = await self._get_connection()
        query, params = find_products_by_supplier_query(supplier_id)
        return await conn.execute_query(query, params)

    async def get_supply_chain_path(
        self, product_id: str, max_depth: int = 10
    ) -> list[dict[str, Any]]:
        """Get the complete supply chain path for a product."""
        conn = await self._get_connection()
        query, params = find_supply_chain_path_query(product_id, max_depth)
        return await conn.execute_query(query, params)

    async def get_product_dependencies(self, product_id: str) -> dict[str, Any]:
        """Get all components and suppliers a product depends on."""
        conn = await self._get_connection()
        query, params = get_product_dependencies_query(product_id)
        results = await conn.execute_query(query, params)
        return results[0] if results else {}

    # =========================================================================
    # Impact Analysis Operations
    # =========================================================================

    async def find_downstream_impact(
        self, affected_node_id: str, max_depth: int = 10
    ) -> list[dict[str, Any]]:
        """Find all downstream nodes affected by an issue at a specific node."""
        conn = await self._get_connection()
        query, params = find_downstream_impact_query(affected_node_id, max_depth)
        return await conn.execute_query(query, params)

    async def find_alternative_suppliers(
        self, component_id: str
    ) -> list[dict[str, Any]]:
        """Find alternative suppliers for a component."""
        conn = await self._get_connection()
        query, params = find_alternative_suppliers_query(component_id)
        return await conn.execute_query(query, params)

    async def calculate_product_redundancy(
        self, product_id: str
    ) -> list[dict[str, Any]]:
        """Calculate supplier redundancy for all components of a product."""
        conn = await self._get_connection()
        query, params = calculate_supplier_redundancy_query(product_id)
        return await conn.execute_query(query, params)

    # =========================================================================
    # Read Operations
    # =========================================================================

    async def get_supplier(self, supplier_id: str) -> dict[str, Any] | None:
        """Get a supplier by ID."""
        conn = await self._get_connection()
        query = "MATCH (s:Supplier {id: $id}) RETURN s"
        results = await conn.execute_query(query, {"id": supplier_id})
        return results[0] if results else None

    async def get_component(self, component_id: str) -> dict[str, Any] | None:
        """Get a component by ID."""
        conn = await self._get_connection()
        query = "MATCH (c:Component {id: $id}) RETURN c"
        results = await conn.execute_query(query, {"id": component_id})
        return results[0] if results else None

    async def get_product(self, product_id: str) -> dict[str, Any] | None:
        """Get a product by ID."""
        conn = await self._get_connection()
        query = "MATCH (p:Product {id: $id}) RETURN p"
        results = await conn.execute_query(query, {"id": product_id})
        return results[0] if results else None

    async def get_all_products(self) -> list[dict[str, Any]]:
        """Get all products."""
        conn = await self._get_connection()
        query = "MATCH (p:Product) RETURN p ORDER BY p.name"
        return await conn.execute_query(query)

    async def get_all_suppliers(self) -> list[dict[str, Any]]:
        """Get all suppliers."""
        conn = await self._get_connection()
        query = "MATCH (s:Supplier) RETURN s ORDER BY s.risk_score DESC"
        return await conn.execute_query(query)

    async def get_graph_stats(self) -> dict[str, int]:
        """Get statistics about the graph."""
        conn = await self._get_connection()
        query = """
        MATCH (n)
        WITH labels(n) as node_labels
        UNWIND node_labels as label
        RETURN label, count(*) as count
        ORDER BY count DESC
        """
        results = await conn.execute_query(query)

        stats = {}
        for r in results:
            stats[r["label"]] = r["count"]

        # Get relationship count
        rel_query = "MATCH ()-[r]->() RETURN count(r) as rel_count"
        rel_result = await conn.execute_query(rel_query)
        stats["_relationships"] = rel_result[0]["rel_count"] if rel_result else 0

        return stats

    # =========================================================================
    # Delete Operations
    # =========================================================================

    async def delete_supplier(self, supplier_id: str) -> bool:
        """Delete a supplier and its relationships."""
        conn = await self._get_connection()
        result = await conn.execute_write(
            "MATCH (s:Supplier {id: $id}) DETACH DELETE s",
            {"id": supplier_id},
        )
        deleted = result["nodes_deleted"] > 0
        if deleted:
            logger.info("Deleted supplier", supplier_id=supplier_id)
        return deleted

    async def delete_product(self, product_id: str) -> bool:
        """Delete a product and its relationships."""
        conn = await self._get_connection()
        result = await conn.execute_write(
            "MATCH (p:Product {id: $id}) DETACH DELETE p",
            {"id": product_id},
        )
        return result["nodes_deleted"] > 0
