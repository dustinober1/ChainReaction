"""
Unit tests for core data models.
"""

import pytest
from datetime import datetime, timedelta

from src.models import (
    Supplier,
    Component,
    Product,
    Location,
    RiskEvent,
    ImpactAssessment,
    ImpactPath,
    Alert,
    EventType,
    SeverityLevel,
    EntityTier,
    RelationshipType,
)


class TestSupplierModel:
    """Tests for the Supplier model."""

    def test_supplier_creation(self, sample_supplier):
        """Test basic supplier creation."""
        assert sample_supplier.id == "SUP-001"
        assert sample_supplier.name == "TechCorp Industries"
        assert sample_supplier.location == "Taiwan"
        assert sample_supplier.risk_score == 25.0

    def test_risk_score_validation_clamps_high(self):
        """Test that risk scores above 100 are clamped."""
        supplier = Supplier(
            id="SUP-HIGH",
            name="High Risk",
            location="Test",
            risk_score=150.0,
        )
        assert supplier.risk_score == 100.0

    def test_risk_score_validation_clamps_low(self):
        """Test that risk scores below 0 are clamped."""
        supplier = Supplier(
            id="SUP-LOW",
            name="Low Risk",
            location="Test",
            risk_score=-10.0,
        )
        assert supplier.risk_score == 0.0

    def test_risk_score_rounds_to_two_decimals(self):
        """Test that risk score is rounded to 2 decimal places."""
        supplier = Supplier(
            id="SUP-ROUND",
            name="Rounded Risk",
            location="Test",
            risk_score=33.333333,
        )
        assert supplier.risk_score == 33.33

    def test_supplier_tier_validation(self):
        """Test tier validation."""
        with pytest.raises(ValueError):
            Supplier(
                id="SUP-BAD",
                name="Bad Tier",
                location="Test",
                tier=5,  # Invalid tier
            )


class TestComponentModel:
    """Tests for the Component model."""

    def test_component_creation(self, sample_component):
        """Test basic component creation."""
        assert sample_component.id == "COMP-001"
        assert sample_component.name == "RTX 4090 GPU"
        assert sample_component.tier == EntityTier.COMPONENT
        assert sample_component.critical is True

    def test_component_with_specifications(self):
        """Test component with detailed specifications."""
        comp = Component(
            id="COMP-SPEC",
            name="Memory Module",
            category="RAM",
            specifications={
                "capacity": "16GB",
                "speed": "DDR5-4800",
                "latency": "CL40",
            },
        )
        assert comp.specifications["capacity"] == "16GB"


class TestProductModel:
    """Tests for the Product model."""

    def test_product_creation(self, sample_product):
        """Test basic product creation."""
        assert sample_product.id == "PROD-001"
        assert sample_product.name == "Gaming Laptop X1"
        assert sample_product.product_line == "Gaming"
        assert sample_product.revenue_impact == 1000000.0


class TestLocationModel:
    """Tests for the Location model."""

    def test_location_creation(self, sample_location):
        """Test basic location creation."""
        assert sample_location.id == "LOC-001"
        assert sample_location.country == "Taiwan"
        assert "Earthquake Zone" in sample_location.risk_factors

    def test_location_coordinates_validation(self):
        """Test coordinate validation."""
        with pytest.raises(ValueError):
            Location(
                id="LOC-BAD",
                name="Invalid",
                country="Nowhere",
                region="Unknown",
                latitude=100.0,  # Invalid latitude
            )


class TestRiskEventModel:
    """Tests for the RiskEvent model."""

    def test_risk_event_creation(self, sample_risk_event):
        """Test basic risk event creation."""
        assert sample_risk_event.id == "RISK-001"
        assert sample_risk_event.event_type == EventType.WEATHER
        assert sample_risk_event.severity == SeverityLevel.HIGH
        assert sample_risk_event.confidence == 0.85

    def test_confidence_validation(self):
        """Test confidence score validation."""
        with pytest.raises(ValueError):
            RiskEvent(
                id="RISK-BAD",
                event_type=EventType.OTHER,
                location="Test",
                severity=SeverityLevel.LOW,
                confidence=1.5,  # Invalid confidence
                source_url="http://test.com",
            )

    def test_all_event_types(self):
        """Test all event types can be used."""
        for event_type in EventType:
            event = RiskEvent(
                id=f"RISK-{event_type.value}",
                event_type=event_type,
                location="Test",
                severity=SeverityLevel.LOW,
                confidence=0.5,
                source_url="http://test.com",
            )
            assert event.event_type == event_type


class TestImpactAssessmentModel:
    """Tests for the ImpactAssessment model."""

    def test_impact_assessment_creation(self):
        """Test impact assessment creation."""
        assessment = ImpactAssessment(
            risk_event_id="RISK-001",
            affected_products=["PROD-001", "PROD-002"],
            severity_score=7.5,
            mitigation_options=["Alternative Supplier", "Increase Inventory"],
            redundancy_level=0.3,
        )
        assert len(assessment.affected_products) == 2
        assert assessment.severity_score == 7.5
        assert assessment.redundancy_level == 0.3

    def test_impact_path_creation(self):
        """Test impact path creation."""
        path = ImpactPath(
            nodes=["SUP-001", "COMP-001", "PROD-001"],
            relationship_types=[RelationshipType.SUPPLIES, RelationshipType.PART_OF],
            total_hops=2,
            criticality_score=0.8,
        )
        assert path.total_hops == 2
        assert len(path.nodes) == 3


class TestAlertModel:
    """Tests for the Alert model."""

    def test_alert_creation(self):
        """Test alert creation."""
        alert = Alert(
            id="ALERT-001",
            risk_event_id="RISK-001",
            product_ids=["PROD-001"],
            severity=SeverityLevel.HIGH,
            title="Supply Chain Risk Detected",
            message="Critical supplier affected by earthquake",
        )
        assert alert.acknowledged is False
        assert alert.acknowledged_at is None
