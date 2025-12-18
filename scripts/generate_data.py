"""
Synthetic Supply Chain Data Generator.

Creates realistic supply chain graphs with configurable complexity
for development, testing, and demonstration purposes.

Based on the design in idea.md - generates multi-tier supply chains
with suppliers in realistic risk zones.
"""

import json
import random
from datetime import datetime, timezone, timedelta
from pathlib import Path
from typing import Any

from faker import Faker

from src.models import (
    Supplier,
    Component,
    Product,
    Location,
    RiskEvent,
    EntityTier,
    EventType,
    SeverityLevel,
)

# Initialize Faker for realistic company names
fake = Faker()

# =============================================================================
# Configuration Constants
# =============================================================================

# Geographic locations with associated risk characteristics
LOCATIONS = {
    "Taiwan": {"region": "East Asia", "risk_factors": ["Earthquake Zone", "Geopolitical Tensions"]},
    "Shenzhen": {"region": "East Asia", "risk_factors": ["Trade Restrictions", "Labor Disputes"]},
    "Vietnam": {"region": "Southeast Asia", "risk_factors": ["Flood Risk", "Infrastructure Gaps"]},
    "South Korea": {"region": "East Asia", "risk_factors": ["Geopolitical Tensions"]},
    "Japan": {"region": "East Asia", "risk_factors": ["Earthquake Zone", "Tsunami Risk"]},
    "Singapore": {"region": "Southeast Asia", "risk_factors": ["Port Congestion"]},
    "Malaysia": {"region": "Southeast Asia", "risk_factors": ["Political Instability"]},
    "Thailand": {"region": "Southeast Asia", "risk_factors": ["Flood Risk"]},
    "India": {"region": "South Asia", "risk_factors": ["Infrastructure Gaps", "Labor Disputes"]},
    "Germany": {"region": "Western Europe", "risk_factors": ["Energy Dependency"]},
    "Munich": {"region": "Western Europe", "risk_factors": ["Energy Dependency"]},
    "California": {"region": "North America", "risk_factors": ["Wildfire Risk", "Earthquake Zone"]},
    "Texas": {"region": "North America", "risk_factors": ["Weather Events"]},
    "Mexico": {"region": "Central America", "risk_factors": ["Political Instability", "Border Delays"]},
    "Israel": {"region": "Middle East", "risk_factors": ["Geopolitical Tensions"]},
}

# High-risk locations for more interesting scenarios
HIGH_RISK_LOCATIONS = ["Taiwan", "Shenzhen", "Israel", "Vietnam"]

# Component categories and typical specifications
COMPONENT_CATEGORIES = {
    "Semiconductor": {
        "specs": ["process_nm", "cores", "tdp"],
        "tier": EntityTier.COMPONENT,
        "lead_time_range": (30, 90),
    },
    "Display": {
        "specs": ["resolution", "size_inches", "technology"],
        "tier": EntityTier.COMPONENT,
        "lead_time_range": (14, 45),
    },
    "Battery": {
        "specs": ["capacity_wh", "chemistry", "cycles"],
        "tier": EntityTier.COMPONENT,
        "lead_time_range": (21, 60),
    },
    "Memory": {
        "specs": ["capacity_gb", "speed", "type"],
        "tier": EntityTier.COMPONENT,
        "lead_time_range": (14, 30),
    },
    "Storage": {
        "specs": ["capacity_tb", "interface", "read_speed"],
        "tier": EntityTier.COMPONENT,
        "lead_time_range": (14, 30),
    },
    "Power Supply": {
        "specs": ["wattage", "efficiency", "form_factor"],
        "tier": EntityTier.SUB_ASSEMBLY,
        "lead_time_range": (7, 21),
    },
    "Chassis": {
        "specs": ["material", "weight_kg", "dimensions"],
        "tier": EntityTier.SUB_ASSEMBLY,
        "lead_time_range": (7, 14),
    },
    "PCB": {
        "specs": ["layers", "material", "thickness_mm"],
        "tier": EntityTier.COMPONENT,
        "lead_time_range": (14, 30),
    },
    "Raw Material": {
        "specs": ["purity", "grade", "origin"],
        "tier": EntityTier.RAW_MATERIAL,
        "lead_time_range": (30, 90),
    },
}

# Product lines for generated products
PRODUCT_LINES = [
    "Gaming Laptop",
    "Enterprise Server",
    "Consumer Tablet",
    "Industrial Controller",
    "Medical Device",
    "Smart Display",
    "Edge Computing Node",
    "Telecommunications Equipment",
]


# =============================================================================
# Generator Classes
# =============================================================================


class SupplyChainGenerator:
    """
    Generates synthetic supply chain data with realistic characteristics.

    Creates a multi-tier supply chain with:
    - Suppliers distributed across global locations
    - Components with tiered dependencies
    - Products assembled from multiple components
    - Realistic risk scores based on location
    """

    def __init__(self, seed: int | None = None):
        """
        Initialize the generator.

        Args:
            seed: Optional random seed for reproducibility.
        """
        if seed is not None:
            random.seed(seed)
            Faker.seed(seed)

        self.suppliers: list[Supplier] = []
        self.components: list[Component] = []
        self.products: list[Product] = []
        self.locations: list[Location] = []

        # Relationship tracking
        self.supplier_component_links: list[tuple[str, str, int]] = []
        self.component_product_links: list[tuple[str, str, int]] = []
        self.component_component_links: list[tuple[str, str, int]] = []  # Sub-assemblies
        self.supplier_location_links: list[tuple[str, str]] = []

    def generate(
        self,
        num_suppliers: int = 50,
        num_components: int = 100,
        num_products: int = 5,
        supplier_redundancy: float = 0.3,  # Probability of multiple suppliers per component
    ) -> dict[str, Any]:
        """
        Generate a complete supply chain graph.

        Args:
            num_suppliers: Number of supplier entities to create.
            num_components: Number of component entities to create.
            num_products: Number of final product entities to create.
            supplier_redundancy: Probability of having backup suppliers.

        Returns:
            Dictionary containing all entities and relationships.
        """
        # Clear previous data
        self._reset()

        # Generate entities in order
        self._generate_locations()
        self._generate_suppliers(num_suppliers)
        self._generate_components(num_components)
        self._generate_products(num_products)

        # Generate relationships
        self._link_suppliers_to_locations()
        self._link_suppliers_to_components(supplier_redundancy)
        self._build_component_hierarchies()
        self._link_components_to_products()

        return self.to_dict()

    def _reset(self) -> None:
        """Reset all generated data."""
        self.suppliers = []
        self.components = []
        self.products = []
        self.locations = []
        self.supplier_component_links = []
        self.component_product_links = []
        self.component_component_links = []
        self.supplier_location_links = []

    def _generate_locations(self) -> None:
        """Generate location entities from configured locations."""
        for i, (name, info) in enumerate(LOCATIONS.items()):
            location = Location(
                id=f"LOC-{i:04d}",
                name=name,
                country=name,  # Simplified - using location name as country
                region=info["region"],
                risk_factors=info["risk_factors"],
            )
            self.locations.append(location)

    def _generate_suppliers(self, count: int) -> None:
        """Generate supplier entities with realistic characteristics."""
        location_names = list(LOCATIONS.keys())

        for i in range(count):
            location = random.choice(location_names)
            location_info = LOCATIONS[location]

            # Higher base risk for high-risk locations
            base_risk = random.uniform(20, 60)
            if location in HIGH_RISK_LOCATIONS:
                base_risk += random.uniform(15, 35)
            base_risk = min(base_risk, 95)

            supplier = Supplier(
                id=f"SUP-{i:04d}",
                name=fake.company(),
                location=location,
                risk_score=round(base_risk, 2),
                country=location,
                tier=random.choice([1, 2, 2, 3]),  # More tier 2 suppliers
            )
            self.suppliers.append(supplier)

    def _generate_components(self, count: int) -> None:
        """Generate component entities across different categories."""
        categories = list(COMPONENT_CATEGORIES.keys())

        for i in range(count):
            category = random.choice(categories)
            cat_info = COMPONENT_CATEGORIES[category]

            # Generate specifications
            specs = {}
            for spec in cat_info["specs"]:
                specs[spec] = fake.word()

            lead_time = random.randint(*cat_info["lead_time_range"])

            component = Component(
                id=f"COMP-{i:04d}",
                name=f"{fake.word().capitalize()} {category}",
                category=category,
                tier=cat_info["tier"],
                specifications=specs,
                lead_time_days=lead_time,
                critical=random.random() < 0.2,  # 20% are critical
            )
            self.components.append(component)

    def _generate_products(self, count: int) -> None:
        """Generate final product entities."""
        for i in range(count):
            product_line = random.choice(PRODUCT_LINES)

            product = Product(
                id=f"PROD-{i:04d}",
                name=f"Nexus {product_line} {fake.random_uppercase_letter()}{random.randint(1, 9)}",
                product_line=product_line,
                revenue_impact=round(random.uniform(100000, 5000000), 2),
                sku=f"SKU-{fake.hexify('????').upper()}",
            )
            self.products.append(product)

    def _link_suppliers_to_locations(self) -> None:
        """Create LOCATED_IN relationships between suppliers and locations."""
        location_by_name = {loc.name: loc for loc in self.locations}

        for supplier in self.suppliers:
            if supplier.location in location_by_name:
                self.supplier_location_links.append(
                    (supplier.id, location_by_name[supplier.location].id)
                )

    def _link_suppliers_to_components(self, redundancy: float) -> None:
        """Create SUPPLIES relationships between suppliers and components."""
        for component in self.components:
            # At least one supplier per component
            num_suppliers = 1
            if random.random() < redundancy:
                num_suppliers = random.randint(2, 3)

            # Select suppliers (prefer those in matching regions for realism)
            selected_suppliers = random.sample(
                self.suppliers, min(num_suppliers, len(self.suppliers))
            )

            for i, supplier in enumerate(selected_suppliers):
                priority = i + 1  # Primary supplier has priority 1
                self.supplier_component_links.append(
                    (supplier.id, component.id, priority)
                )

    def _build_component_hierarchies(self) -> None:
        """Create PART_OF relationships for sub-assemblies."""
        # Group components by tier
        raw_materials = [c for c in self.components if c.tier == EntityTier.RAW_MATERIAL]
        base_components = [c for c in self.components if c.tier == EntityTier.COMPONENT]
        sub_assemblies = [c for c in self.components if c.tier == EntityTier.SUB_ASSEMBLY]

        # Raw materials feed into base components
        for component in base_components:
            if raw_materials:
                num_materials = random.randint(1, 2)
                materials = random.sample(raw_materials, min(num_materials, len(raw_materials)))
                for material in materials:
                    self.component_component_links.append(
                        (material.id, component.id, random.randint(1, 5))
                    )

        # Base components feed into sub-assemblies
        for sub_assembly in sub_assemblies:
            if base_components:
                num_components = random.randint(2, 4)
                parts = random.sample(base_components, min(num_components, len(base_components)))
                for part in parts:
                    self.component_component_links.append(
                        (part.id, sub_assembly.id, random.randint(1, 3))
                    )

    def _link_components_to_products(self) -> None:
        """Create PART_OF relationships between components and products."""
        sub_assemblies = [c for c in self.components if c.tier == EntityTier.SUB_ASSEMBLY]
        base_components = [c for c in self.components if c.tier == EntityTier.COMPONENT]

        for product in self.products:
            # Each product needs several sub-assemblies
            num_sub_assemblies = random.randint(3, 5)
            selected_subs = random.sample(
                sub_assemblies, min(num_sub_assemblies, len(sub_assemblies))
            )
            for sub in selected_subs:
                self.component_product_links.append(
                    (sub.id, product.id, 1)
                )

            # Plus some direct components
            num_direct = random.randint(3, 6)
            selected_comps = random.sample(
                base_components, min(num_direct, len(base_components))
            )
            for comp in selected_comps:
                self.component_product_links.append(
                    (comp.id, product.id, random.randint(1, 4))
                )

    def to_dict(self) -> dict[str, Any]:
        """Convert all data to a dictionary format suitable for JSON export."""
        return {
            "suppliers": [s.model_dump() for s in self.suppliers],
            "components": [c.model_dump() for c in self.components],
            "products": [p.model_dump() for p in self.products],
            "locations": [loc.model_dump() for loc in self.locations],
            "relationships": {
                "supplier_component": [
                    {"supplier_id": s, "component_id": c, "priority": p}
                    for s, c, p in self.supplier_component_links
                ],
                "component_product": [
                    {"component_id": c, "product_id": p, "quantity": q}
                    for c, p, q in self.component_product_links
                ],
                "component_component": [
                    {"child_id": ch, "parent_id": pa, "quantity": q}
                    for ch, pa, q in self.component_component_links
                ],
                "supplier_location": [
                    {"supplier_id": s, "location_id": l}
                    for s, l in self.supplier_location_links
                ],
            },
            "metadata": {
                "generated_at": datetime.now(timezone.utc).isoformat(),
                "counts": {
                    "suppliers": len(self.suppliers),
                    "components": len(self.components),
                    "products": len(self.products),
                    "locations": len(self.locations),
                    "supplier_component_links": len(self.supplier_component_links),
                    "component_product_links": len(self.component_product_links),
                    "component_component_links": len(self.component_component_links),
                },
            },
        }

    def to_json(self, indent: int = 2) -> str:
        """Export data as JSON string."""
        return json.dumps(self.to_dict(), indent=indent, default=str)

    def save_to_file(self, filepath: str | Path) -> None:
        """Save generated data to a JSON file."""
        filepath = Path(filepath)
        filepath.parent.mkdir(parents=True, exist_ok=True)

        with open(filepath, "w") as f:
            f.write(self.to_json())

    def to_graph_json(self) -> dict[str, list[dict]]:
        """
        Export in the format expected by the graph import utilities.

        This matches the format from idea.md for Neo4j ingestion.
        """
        nodes = []
        edges = []

        # Add suppliers as nodes
        for s in self.suppliers:
            nodes.append({
                "id": s.id,
                "type": "Supplier",
                "name": s.name,
                "location": s.location,
                "risk_score": s.risk_score,
            })

        # Add components as nodes
        for c in self.components:
            nodes.append({
                "id": c.id,
                "type": c.tier.value,
                "name": c.name,
                "category": c.category,
            })

        # Add products as nodes
        for p in self.products:
            nodes.append({
                "id": p.id,
                "type": "Final Product",
                "name": p.name,
                "product_line": p.product_line,
            })

        # Add locations as nodes
        for loc in self.locations:
            nodes.append({
                "id": loc.id,
                "type": "Location",
                "name": loc.name,
                "country": loc.country,
                "region": loc.region,
            })

        # Add all edges
        for s_id, c_id, priority in self.supplier_component_links:
            edges.append({
                "source": s_id,
                "target": c_id,
                "type": "SUPPLIES",
                "priority": priority,
            })

        for c_id, p_id, qty in self.component_product_links:
            edges.append({
                "source": c_id,
                "target": p_id,
                "type": "PART_OF",
                "quantity": qty,
            })

        for child_id, parent_id, qty in self.component_component_links:
            edges.append({
                "source": child_id,
                "target": parent_id,
                "type": "PART_OF",
                "quantity": qty,
            })

        for s_id, l_id in self.supplier_location_links:
            edges.append({
                "source": s_id,
                "target": l_id,
                "type": "LOCATED_IN",
            })

        return {"nodes": nodes, "edges": edges}


# =============================================================================
# Risk Event Generator
# =============================================================================


class RiskEventGenerator:
    """Generates synthetic risk events for testing."""

    def __init__(self, seed: int | None = None):
        if seed is not None:
            random.seed(seed)
            Faker.seed(seed)

    def generate_events(
        self,
        count: int = 10,
        locations: list[str] | None = None,
        companies: list[str] | None = None,
    ) -> list[RiskEvent]:
        """
        Generate synthetic risk events.

        Args:
            count: Number of events to generate.
            locations: Optional list of locations to use.
            companies: Optional list of company names to reference.

        Returns:
            List of RiskEvent instances.
        """
        if locations is None:
            locations = list(LOCATIONS.keys())
        if companies is None:
            companies = [fake.company() for _ in range(20)]

        events = []
        event_templates = self._get_event_templates()

        for i in range(count):
            template = random.choice(event_templates)
            location = random.choice(locations)
            affected = random.sample(companies, min(random.randint(1, 3), len(companies)))

            event = RiskEvent(
                id=f"RISK-{i:04d}",
                event_type=template["type"],
                location=location,
                affected_entities=affected,
                severity=random.choice(list(SeverityLevel)),
                confidence=round(random.uniform(0.6, 0.95), 3),
                source_url=f"https://news.example.com/{fake.slug()}",
                detected_at=datetime.now(timezone.utc) - timedelta(hours=random.randint(0, 72)),
                description=template["description"].format(
                    location=location,
                    company=affected[0] if affected else "Unknown"
                ),
            )
            events.append(event)

        return events

    def _get_event_templates(self) -> list[dict[str, Any]]:
        """Get event description templates."""
        return [
            {
                "type": EventType.STRIKE,
                "description": "Workers at {company} facilities in {location} have announced plans to strike.",
            },
            {
                "type": EventType.WEATHER,
                "description": "Severe weather conditions affecting operations in {location} region.",
            },
            {
                "type": EventType.FIRE,
                "description": "Fire reported at major manufacturing facility in {location}.",
            },
            {
                "type": EventType.BANKRUPTCY,
                "description": "{company} has filed for bankruptcy protection.",
            },
            {
                "type": EventType.GEOPOLITICAL,
                "description": "New trade sanctions announced affecting {location}.",
            },
            {
                "type": EventType.PANDEMIC,
                "description": "Health restrictions implemented in {location} affecting manufacturing.",
            },
            {
                "type": EventType.TRANSPORT,
                "description": "Port congestion causing significant delays at {location}.",
            },
            {
                "type": EventType.CYBER_ATTACK,
                "description": "Cyber attack disrupts operations at {company}.",
            },
        ]


# =============================================================================
# Convenience Functions
# =============================================================================


def generate_small_dataset(seed: int = 42) -> dict[str, Any]:
    """Generate a small dataset for development and unit testing (~100 nodes)."""
    generator = SupplyChainGenerator(seed=seed)
    return generator.generate(
        num_suppliers=20,
        num_components=50,
        num_products=3,
        supplier_redundancy=0.3,
    )


def generate_medium_dataset(seed: int = 42) -> dict[str, Any]:
    """Generate a medium dataset for integration testing (~5000 nodes)."""
    generator = SupplyChainGenerator(seed=seed)
    return generator.generate(
        num_suppliers=500,
        num_components=2000,
        num_products=20,
        supplier_redundancy=0.4,
    )


def generate_large_dataset(seed: int = 42) -> dict[str, Any]:
    """Generate a large dataset for performance testing (~50000 nodes)."""
    generator = SupplyChainGenerator(seed=seed)
    return generator.generate(
        num_suppliers=5000,
        num_components=20000,
        num_products=100,
        supplier_redundancy=0.5,
    )
