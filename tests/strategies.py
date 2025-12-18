"""
Hypothesis Strategies for ChainReaction Property-Based Tests.

Provides data generators for supply chain entities, risk events,
and graph structures used in property-based testing.
"""

from datetime import datetime, timezone, timedelta
import string

from hypothesis import strategies as st

from src.models import (
    Supplier,
    Component,
    Product,
    Location,
    RiskEvent,
    ImpactAssessment,
    ImpactPath,
    EventType,
    SeverityLevel,
    EntityTier,
    RelationshipType,
)


# =============================================================================
# Basic Strategies
# =============================================================================

# Valid ID format
entity_id = st.text(
    alphabet=string.ascii_uppercase + string.digits + "-",
    min_size=4,
    max_size=20,
).map(lambda s: f"ID-{s}")

# Company/entity names
company_name = st.text(
    alphabet=string.ascii_letters + " ",
    min_size=3,
    max_size=50,
).filter(lambda s: s.strip() != "").map(lambda s: s.strip())

# Location names
location_name = st.sampled_from([
    "Taiwan", "Vietnam", "California", "Germany", "South Korea",
    "Japan", "China", "Mexico", "India", "Thailand", "Malaysia",
    "Indonesia", "Philippines", "Singapore", "United States",
    "Shenzhen", "Shanghai", "Munich", "Seoul", "Tokyo",
])

# Region names
region_name = st.sampled_from([
    "East Asia", "Southeast Asia", "North America", "Europe",
    "South Asia", "Central America", "Western Europe",
])

# Risk score (0-100)
risk_score = st.floats(min_value=0.0, max_value=100.0, allow_nan=False)

# Confidence score (0-1)
confidence_score = st.floats(min_value=0.0, max_value=1.0, allow_nan=False)

# Tier level (1-4)
tier_level = st.integers(min_value=1, max_value=4)

# Positive integers
positive_int = st.integers(min_value=1, max_value=1000)

# URL format
source_url = st.text(
    alphabet=string.ascii_lowercase + string.digits + "-",
    min_size=5,
    max_size=30,
).map(lambda s: f"https://news.example.com/{s}")

# Datetime within reasonable range
recent_datetime = st.datetimes(
    min_value=datetime(2020, 1, 1),
    max_value=datetime(2030, 12, 31),
).map(lambda dt: dt.replace(tzinfo=timezone.utc))


# =============================================================================
# Entity Strategies
# =============================================================================

@st.composite
def supplier_strategy(draw) -> Supplier:
    """Generate a random Supplier entity."""
    return Supplier(
        id=draw(st.text(min_size=3, max_size=10).map(lambda s: f"SUP-{s}")),
        name=draw(company_name),
        location=draw(location_name),
        risk_score=draw(risk_score),
        country=draw(location_name),
        tier=draw(tier_level),
    )


@st.composite
def component_strategy(draw) -> Component:
    """Generate a random Component entity."""
    categories = ["Electronics", "Mechanical", "Chemical", "Raw Material", "Packaging"]
    return Component(
        id=draw(st.text(min_size=3, max_size=10).map(lambda s: f"COMP-{s}")),
        name=draw(company_name),
        category=draw(st.sampled_from(categories)),
        tier=draw(st.sampled_from(list(EntityTier))),
        specifications=draw(st.dictionaries(
            keys=st.text(alphabet=string.ascii_lowercase, min_size=3, max_size=10),
            values=st.text(min_size=1, max_size=20),
            max_size=5,
        )),
        lead_time_days=draw(st.integers(min_value=1, max_value=90) | st.none()),
        critical=draw(st.booleans()),
    )


@st.composite
def product_strategy(draw) -> Product:
    """Generate a random Product entity."""
    product_lines = ["Gaming", "Enterprise", "Consumer", "Industrial", "Medical"]
    return Product(
        id=draw(st.text(min_size=3, max_size=10).map(lambda s: f"PROD-{s}")),
        name=draw(company_name),
        product_line=draw(st.sampled_from(product_lines)),
        revenue_impact=draw(st.floats(min_value=0.0, max_value=10000000.0, allow_nan=False)),
        sku=draw(st.text(min_size=5, max_size=15).map(lambda s: f"SKU-{s}") | st.none()),
    )


@st.composite
def location_strategy(draw) -> Location:
    """Generate a random Location entity."""
    risk_factors_list = [
        "Earthquake Zone", "Flood Risk", "Political Instability",
        "Trade Restrictions", "Port Congestion", "Labor Disputes",
        "Pandemic History", "Extreme Weather",
    ]
    return Location(
        id=draw(st.text(min_size=3, max_size=10).map(lambda s: f"LOC-{s}")),
        name=draw(company_name),
        country=draw(location_name),
        region=draw(region_name),
        risk_factors=draw(st.lists(st.sampled_from(risk_factors_list), max_size=4)),
        latitude=draw(st.floats(min_value=-90.0, max_value=90.0, allow_nan=False) | st.none()),
        longitude=draw(st.floats(min_value=-180.0, max_value=180.0, allow_nan=False) | st.none()),
    )


@st.composite
def risk_event_strategy(draw) -> RiskEvent:
    """Generate a random RiskEvent."""
    descriptions = [
        "Factory fire reported",
        "Workers announce strike",
        "Severe flooding in region",
        "Port operations suspended",
        "Company files for bankruptcy",
        "Trade sanctions announced",
        "Earthquake damages facilities",
        "Cyber attack disrupts operations",
    ]
    return RiskEvent(
        id=draw(st.text(min_size=3, max_size=10).map(lambda s: f"RISK-{s}")),
        event_type=draw(st.sampled_from(list(EventType))),
        location=draw(location_name),
        affected_entities=draw(st.lists(company_name, min_size=1, max_size=5)),
        severity=draw(st.sampled_from(list(SeverityLevel))),
        confidence=draw(confidence_score),
        source_url=draw(source_url),
        detected_at=draw(recent_datetime),
        description=draw(st.sampled_from(descriptions)),
    )


@st.composite
def impact_path_strategy(draw) -> ImpactPath:
    """Generate a random ImpactPath."""
    num_nodes = draw(st.integers(min_value=2, max_value=6))
    node_ids = [
        draw(st.text(min_size=3, max_size=8).map(lambda s: f"NODE-{s}"))
        for _ in range(num_nodes)
    ]
    rel_types = [
        draw(st.sampled_from(list(RelationshipType)))
        for _ in range(num_nodes - 1)
    ]
    return ImpactPath(
        nodes=node_ids,
        relationship_types=rel_types,
        total_hops=num_nodes - 1,
        criticality_score=draw(confidence_score),
    )


@st.composite
def impact_assessment_strategy(draw) -> ImpactAssessment:
    """Generate a random ImpactAssessment."""
    return ImpactAssessment(
        risk_event_id=draw(st.text(min_size=3, max_size=10).map(lambda s: f"RISK-{s}")),
        affected_products=draw(st.lists(
            st.text(min_size=3, max_size=10).map(lambda s: f"PROD-{s}"),
            min_size=1,
            max_size=5,
        )),
        impact_paths=draw(st.lists(impact_path_strategy(), max_size=3)),
        severity_score=draw(st.floats(min_value=0.0, max_value=10.0, allow_nan=False)),
        mitigation_options=draw(st.lists(
            st.sampled_from([
                "Alternative Supplier", "Increase Inventory",
                "Expedited Shipping", "Substitute Component",
                "Production Delay", "Customer Communication",
            ]),
            max_size=3,
        )),
        redundancy_level=draw(confidence_score),
    )


# =============================================================================
# Supply Chain Graph Strategies
# =============================================================================

@st.composite
def supply_chain_graph_strategy(
    draw,
    num_suppliers: int = 5,
    num_components: int = 10,
    num_products: int = 3,
):
    """
    Generate a complete supply chain graph structure.

    Returns a dictionary with:
    - suppliers: list of Supplier entities
    - components: list of Component entities
    - products: list of Product entities
    - supplier_component_links: list of (supplier_id, component_id) tuples
    - component_product_links: list of (component_id, product_id) tuples
    """
    suppliers = [draw(supplier_strategy()) for _ in range(num_suppliers)]
    components = [draw(component_strategy()) for _ in range(num_components)]
    products = [draw(product_strategy()) for _ in range(num_products)]

    # Make IDs unique
    for i, s in enumerate(suppliers):
        s.id = f"SUP-{i:04d}"
    for i, c in enumerate(components):
        c.id = f"COMP-{i:04d}"
    for i, p in enumerate(products):
        p.id = f"PROD-{i:04d}"

    # Generate links (each component has 1-2 suppliers, each product has 2-4 components)
    supplier_component_links = []
    for c in components:
        num_links = draw(st.integers(min_value=1, max_value=min(2, len(suppliers))))
        # Use indices for sampling to avoid hashability issues with Pydantic models
        supplier_indices = draw(st.lists(
            st.sampled_from(range(len(suppliers))),
            min_size=num_links,
            max_size=num_links,
            unique=True,
        ))
        for idx in supplier_indices:
            supplier_component_links.append((suppliers[idx].id, c.id))

    component_product_links = []
    for p in products:
        num_comps = draw(st.integers(min_value=2, max_value=min(4, len(components))))
        # Use indices for sampling to avoid hashability issues with Pydantic models
        component_indices = draw(st.lists(
            st.sampled_from(range(len(components))),
            min_size=num_comps,
            max_size=num_comps,
            unique=True,
        ))
        for idx in component_indices:
            component_product_links.append((components[idx].id, p.id))

    return {
        "suppliers": suppliers,
        "components": components,
        "products": products,
        "supplier_component_links": supplier_component_links,
        "component_product_links": component_product_links,
    }


# =============================================================================
# JSON Export Strategies
# =============================================================================

@st.composite  
def supply_chain_json_strategy(draw):
    """Generate supply chain data in JSON-importable format."""
    graph = draw(supply_chain_graph_strategy(
        num_suppliers=draw(st.integers(min_value=3, max_value=10)),
        num_components=draw(st.integers(min_value=5, max_value=15)),
        num_products=draw(st.integers(min_value=2, max_value=5)),
    ))

    nodes = []
    edges = []

    # Convert suppliers to JSON nodes
    for s in graph["suppliers"]:
        nodes.append({
            "id": s.id,
            "type": "Supplier",
            "name": s.name,
            "location": s.location,
            "risk_score": s.risk_score,
        })

    # Convert components to JSON nodes
    for c in graph["components"]:
        nodes.append({
            "id": c.id,
            "type": c.tier.value,
            "name": c.name,
            "category": c.category,
        })

    # Convert products to JSON nodes
    for p in graph["products"]:
        nodes.append({
            "id": p.id,
            "type": "Final Product",
            "name": p.name,
            "product_line": p.product_line,
        })

    # Add supplier->component edges
    for supplier_id, component_id in graph["supplier_component_links"]:
        edges.append({
            "source": supplier_id,
            "target": component_id,
            "type": "SUPPLIES",
        })

    # Add component->product edges
    for component_id, product_id in graph["component_product_links"]:
        edges.append({
            "source": component_id,
            "target": product_id,
            "type": "PART_OF",
        })

    return {"nodes": nodes, "edges": edges}
