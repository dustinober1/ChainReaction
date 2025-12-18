"""
Pytest configuration and shared fixtures for ChainReaction tests.
"""

import pytest
from datetime import datetime, timezone

from src.models import (
    Supplier,
    Component,
    Product,
    Location,
    RiskEvent,
    EventType,
    SeverityLevel,
    EntityTier,
)


@pytest.fixture
def sample_supplier() -> Supplier:
    """Create a sample supplier for testing."""
    return Supplier(
        id="SUP-001",
        name="TechCorp Industries",
        location="Taiwan",
        risk_score=25.0,
        country="Taiwan",
        tier=1,
    )


@pytest.fixture
def sample_component() -> Component:
    """Create a sample component for testing."""
    return Component(
        id="COMP-001",
        name="RTX 4090 GPU",
        category="Graphics Processing",
        tier=EntityTier.COMPONENT,
        specifications={"memory": "24GB", "tdp": "450W"},
        lead_time_days=14,
        critical=True,
    )


@pytest.fixture
def sample_product() -> Product:
    """Create a sample product for testing."""
    return Product(
        id="PROD-001",
        name="Gaming Laptop X1",
        product_line="Gaming",
        revenue_impact=1000000.0,
        sku="GL-X1-2024",
    )


@pytest.fixture
def sample_location() -> Location:
    """Create a sample location for testing."""
    return Location(
        id="LOC-001",
        name="Taipei Tech Park",
        country="Taiwan",
        region="East Asia",
        risk_factors=["Earthquake Zone", "Geopolitical Tensions"],
        latitude=25.0330,
        longitude=121.5654,
    )


@pytest.fixture
def sample_risk_event() -> RiskEvent:
    """Create a sample risk event for testing."""
    return RiskEvent(
        id="RISK-001",
        event_type=EventType.WEATHER,
        location="Taiwan",
        affected_entities=["TechCorp Industries", "Semiconductor Plant A"],
        severity=SeverityLevel.HIGH,
        confidence=0.85,
        source_url="https://news.example.com/taiwan-earthquake",
        detected_at=datetime.now(timezone.utc),
        description="6.2 magnitude earthquake near semiconductor manufacturing hub",
    )


@pytest.fixture
def sample_suppliers_list() -> list[Supplier]:
    """Create a list of sample suppliers for testing."""
    locations = ["Taiwan", "Vietnam", "California", "Germany", "South Korea"]
    return [
        Supplier(
            id=f"SUP-{i:03d}",
            name=f"Supplier {i}",
            location=locations[i % len(locations)],
            risk_score=float(i * 10),
            tier=(i % 4) + 1,
        )
        for i in range(10)
    ]
