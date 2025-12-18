"""
Cypher Query Generation and Graph Operations.

This module provides typed queries for creating, reading, updating, and deleting
supply chain entities in the Neo4j knowledge graph.
"""

from datetime import datetime, timezone
from typing import Any

from src.models import (
    Supplier,
    Component,
    Product,
    Location,
    RiskEvent,
    RelationshipType,
)


# =============================================================================
# Node Creation Queries
# =============================================================================


def create_supplier_query(supplier: Supplier) -> tuple[str, dict[str, Any]]:
    """
    Generate Cypher query to create a Supplier node.

    Args:
        supplier: Supplier model instance.

    Returns:
        Tuple of (query_string, parameters).
    """
    query = """
    CREATE (s:Supplier {
        id: $id,
        name: $name,
        location: $location,
        risk_score: $risk_score,
        country: $country,
        tier: $tier,
        contact_info: $contact_info,
        created_at: datetime($created_at),
        updated_at: datetime($updated_at)
    })
    RETURN s
    """

    params = {
        "id": supplier.id,
        "name": supplier.name,
        "location": supplier.location,
        "risk_score": supplier.risk_score,
        "country": supplier.country,
        "tier": supplier.tier,
        "contact_info": str(supplier.contact_info) if supplier.contact_info else None,
        "created_at": supplier.created_at.isoformat(),
        "updated_at": supplier.updated_at.isoformat(),
    }

    return query, params


def create_component_query(component: Component) -> tuple[str, dict[str, Any]]:
    """
    Generate Cypher query to create a Component node.

    Args:
        component: Component model instance.

    Returns:
        Tuple of (query_string, parameters).
    """
    query = """
    CREATE (c:Component {
        id: $id,
        name: $name,
        category: $category,
        tier: $tier,
        specifications: $specifications,
        lead_time_days: $lead_time_days,
        critical: $critical,
        created_at: datetime($created_at),
        updated_at: datetime($updated_at)
    })
    RETURN c
    """

    params = {
        "id": component.id,
        "name": component.name,
        "category": component.category,
        "tier": component.tier.value,
        "specifications": str(component.specifications),
        "lead_time_days": component.lead_time_days,
        "critical": component.critical,
        "created_at": component.created_at.isoformat(),
        "updated_at": component.updated_at.isoformat(),
    }

    return query, params


def create_product_query(product: Product) -> tuple[str, dict[str, Any]]:
    """
    Generate Cypher query to create a Product node.

    Args:
        product: Product model instance.

    Returns:
        Tuple of (query_string, parameters).
    """
    query = """
    CREATE (p:Product {
        id: $id,
        name: $name,
        product_line: $product_line,
        revenue_impact: $revenue_impact,
        sku: $sku,
        launch_date: $launch_date,
        created_at: datetime($created_at),
        updated_at: datetime($updated_at)
    })
    RETURN p
    """

    params = {
        "id": product.id,
        "name": product.name,
        "product_line": product.product_line,
        "revenue_impact": product.revenue_impact,
        "sku": product.sku,
        "launch_date": product.launch_date.isoformat() if product.launch_date else None,
        "created_at": product.created_at.isoformat(),
        "updated_at": product.updated_at.isoformat(),
    }

    return query, params


def create_location_query(location: Location) -> tuple[str, dict[str, Any]]:
    """
    Generate Cypher query to create a Location node.

    Args:
        location: Location model instance.

    Returns:
        Tuple of (query_string, parameters).
    """
    query = """
    CREATE (l:Location {
        id: $id,
        name: $name,
        country: $country,
        region: $region,
        risk_factors: $risk_factors,
        latitude: $latitude,
        longitude: $longitude,
        created_at: datetime($created_at),
        updated_at: datetime($updated_at)
    })
    RETURN l
    """

    params = {
        "id": location.id,
        "name": location.name,
        "country": location.country,
        "region": location.region,
        "risk_factors": location.risk_factors,
        "latitude": location.latitude,
        "longitude": location.longitude,
        "created_at": location.created_at.isoformat(),
        "updated_at": location.updated_at.isoformat(),
    }

    return query, params


def create_risk_event_query(risk_event: RiskEvent) -> tuple[str, dict[str, Any]]:
    """
    Generate Cypher query to create a RiskEvent node.

    Args:
        risk_event: RiskEvent model instance.

    Returns:
        Tuple of (query_string, parameters).
    """
    query = """
    CREATE (r:RiskEvent {
        id: $id,
        event_type: $event_type,
        location: $location,
        affected_entities: $affected_entities,
        severity: $severity,
        confidence: $confidence,
        source_url: $source_url,
        detected_at: datetime($detected_at),
        description: $description
    })
    RETURN r
    """

    params = {
        "id": risk_event.id,
        "event_type": risk_event.event_type.value,
        "location": risk_event.location,
        "affected_entities": risk_event.affected_entities,
        "severity": risk_event.severity.value,
        "confidence": risk_event.confidence,
        "source_url": risk_event.source_url,
        "detected_at": risk_event.detected_at.isoformat(),
        "description": risk_event.description,
    }

    return query, params


# =============================================================================
# Relationship Creation Queries
# =============================================================================


def create_relationship_query(
    source_id: str,
    target_id: str,
    relationship_type: RelationshipType,
    properties: dict[str, Any] | None = None,
) -> tuple[str, dict[str, Any]]:
    """
    Generate Cypher query to create a relationship between two nodes.

    Args:
        source_id: ID of the source node.
        target_id: ID of the target node.
        relationship_type: Type of relationship to create.
        properties: Optional relationship properties.

    Returns:
        Tuple of (query_string, parameters).
    """
    props_str = ""
    if properties:
        props_list = [f"{k}: ${k}" for k in properties.keys()]
        props_str = " {" + ", ".join(props_list) + "}"

    query = f"""
    MATCH (a), (b)
    WHERE a.id = $source_id AND b.id = $target_id
    CREATE (a)-[r:{relationship_type.value}{props_str}]->(b)
    RETURN type(r) as relationship_type, a.id as source, b.id as target
    """

    params = {
        "source_id": source_id,
        "target_id": target_id,
        **(properties or {}),
    }

    return query, params


def create_supplier_supplies_component_query(
    supplier_id: str,
    component_id: str,
    priority: int = 1,
) -> tuple[str, dict[str, Any]]:
    """Create SUPPLIES relationship from Supplier to Component."""
    query = """
    MATCH (s:Supplier {id: $supplier_id})
    MATCH (c:Component {id: $component_id})
    CREATE (s)-[r:SUPPLIES {priority: $priority, created_at: datetime()}]->(c)
    RETURN s.id as supplier, c.id as component
    """
    return query, {"supplier_id": supplier_id, "component_id": component_id, "priority": priority}


def create_component_part_of_product_query(
    component_id: str,
    product_id: str,
    quantity: int = 1,
) -> tuple[str, dict[str, Any]]:
    """Create PART_OF relationship from Component to Product."""
    query = """
    MATCH (c:Component {id: $component_id})
    MATCH (p:Product {id: $product_id})
    CREATE (c)-[r:PART_OF {quantity: $quantity, created_at: datetime()}]->(p)
    RETURN c.id as component, p.id as product
    """
    return query, {"component_id": component_id, "product_id": product_id, "quantity": quantity}


def create_supplier_located_in_query(
    supplier_id: str,
    location_id: str,
) -> tuple[str, dict[str, Any]]:
    """Create LOCATED_IN relationship from Supplier to Location."""
    query = """
    MATCH (s:Supplier {id: $supplier_id})
    MATCH (l:Location {id: $location_id})
    CREATE (s)-[r:LOCATED_IN {created_at: datetime()}]->(l)
    RETURN s.id as supplier, l.id as location
    """
    return query, {"supplier_id": supplier_id, "location_id": location_id}


def create_component_part_of_component_query(
    child_component_id: str,
    parent_component_id: str,
    quantity: int = 1,
) -> tuple[str, dict[str, Any]]:
    """Create PART_OF relationship between Components (sub-assembly)."""
    query = """
    MATCH (child:Component {id: $child_id})
    MATCH (parent:Component {id: $parent_id})
    CREATE (child)-[r:PART_OF {quantity: $quantity, created_at: datetime()}]->(parent)
    RETURN child.id as child_component, parent.id as parent_component
    """
    return query, {
        "child_id": child_component_id,
        "parent_id": parent_component_id,
        "quantity": quantity,
    }


# =============================================================================
# Query Queries (Read Operations)
# =============================================================================


def find_suppliers_by_location_query(location: str) -> tuple[str, dict[str, Any]]:
    """Find all suppliers in a specific location."""
    query = """
    MATCH (s:Supplier)
    WHERE s.location = $location OR s.country = $location
    RETURN s
    ORDER BY s.risk_score DESC
    """
    return query, {"location": location}


def find_products_by_supplier_query(supplier_id: str) -> tuple[str, dict[str, Any]]:
    """Find all products that depend on a specific supplier."""
    query = """
    MATCH (s:Supplier {id: $supplier_id})-[:SUPPLIES|MANUFACTURES*1..]->(c)-[:PART_OF*1..]->(p:Product)
    RETURN DISTINCT p as product, 
           length(shortestPath((s)-[*]->(p))) as distance
    ORDER BY distance
    """
    return query, {"supplier_id": supplier_id}


def find_supply_chain_path_query(
    product_id: str,
    max_depth: int = 10,
) -> tuple[str, dict[str, Any]]:
    """Find the complete supply chain path for a product."""
    query = """
    MATCH path = (start)-[*1..$max_depth]->(p:Product {id: $product_id})
    WHERE NOT (start)<--()
    RETURN path, 
           [node in nodes(path) | node.id] as node_ids,
           [rel in relationships(path) | type(rel)] as rel_types,
           length(path) as path_length
    ORDER BY path_length
    """
    return query, {"product_id": product_id, "max_depth": max_depth}


def find_nodes_by_location_query(location: str) -> tuple[str, dict[str, Any]]:
    """Find all nodes (suppliers, locations) associated with a location."""
    query = """
    MATCH (n)
    WHERE (n:Supplier AND (n.location = $location OR n.country = $location))
       OR (n:Location AND (n.name = $location OR n.country = $location))
    RETURN n, labels(n) as labels
    """
    return query, {"location": location}


def get_product_dependencies_query(product_id: str) -> tuple[str, dict[str, Any]]:
    """Get all components and suppliers a product depends on."""
    query = """
    MATCH (p:Product {id: $product_id})
    OPTIONAL MATCH (c:Component)-[:PART_OF*1..]->(p)
    OPTIONAL MATCH (s:Supplier)-[:SUPPLIES|MANUFACTURES]->(c)
    RETURN p as product,
           collect(DISTINCT c) as components,
           collect(DISTINCT s) as suppliers
    """
    return query, {"product_id": product_id}


# =============================================================================
# Impact Analysis Queries
# =============================================================================


def find_downstream_impact_query(
    affected_node_id: str,
    max_depth: int = 10,
) -> tuple[str, dict[str, Any]]:
    """
    Find all downstream nodes affected by an issue at a specific node.

    This traverses the graph to find all products that may be impacted
    by a disruption at the specified node.
    """
    query = """
    MATCH path = (affected {id: $node_id})-[:SUPPLIES|MANUFACTURES|PART_OF*1..$max_depth]->(downstream)
    WHERE downstream:Product OR downstream:Component
    RETURN DISTINCT downstream,
           labels(downstream) as node_type,
           length(path) as distance,
           [node in nodes(path) | node.id] as impact_path
    ORDER BY distance
    """
    return query, {"node_id": affected_node_id, "max_depth": max_depth}


def find_alternative_suppliers_query(component_id: str) -> tuple[str, dict[str, Any]]:
    """Find alternative suppliers for a component."""
    query = """
    MATCH (s:Supplier)-[:SUPPLIES|MANUFACTURES]->(c:Component {id: $component_id})
    RETURN s as supplier, s.risk_score as risk_score
    ORDER BY s.risk_score ASC
    """
    return query, {"component_id": component_id}


def calculate_supplier_redundancy_query(product_id: str) -> tuple[str, dict[str, Any]]:
    """
    Calculate supplier redundancy for a product.

    Returns each component with its supplier count and criticality.
    """
    query = """
    MATCH (c:Component)-[:PART_OF*1..]->(p:Product {id: $product_id})
    OPTIONAL MATCH (s:Supplier)-[:SUPPLIES|MANUFACTURES]->(c)
    WITH c, count(DISTINCT s) as supplier_count, c.critical as is_critical
    RETURN c.id as component_id,
           c.name as component_name,
           supplier_count,
           is_critical,
           CASE 
               WHEN supplier_count = 0 THEN 0.0
               WHEN supplier_count = 1 THEN 0.2
               WHEN supplier_count = 2 THEN 0.5
               ELSE 1.0
           END as redundancy_score
    ORDER BY redundancy_score ASC
    """
    return query, {"product_id": product_id}
