"""
Integration Tests for ChainReaction End-to-End Workflows.

Tests complete workflows from risk detection through alert generation
and API delivery.
"""

import pytest
from datetime import datetime, timezone
from unittest.mock import Mock, AsyncMock, patch
import asyncio

from src.models import (
    RawEvent,
    RiskEvent,
    EventType,
    SeverityLevel,
    ImpactAssessment,
    Alert,
)
from src.analysis.prioritization import RiskPrioritizer
from src.analysis.reporting import ReportGenerator
from src.data import EntityManager


class TestRiskDetectionPipeline:
    """Integration tests for the risk detection pipeline."""

    def test_raw_event_to_risk_event_transformation(self):
        """Test that raw events can be transformed into risk events."""
        # Create a raw event (simulating Scout Agent output)
        raw_event = RawEvent(
            source="tavily",
            url="https://news.example.com/typhoon",
            title="Typhoon Warning for Taiwan",
            content="A major typhoon is approaching Taiwan, threatening semiconductor production facilities.",
            published_at=datetime.now(timezone.utc),
        )

        # Create corresponding risk event (simulating DSPy extraction)
        risk_event = RiskEvent(
            id="RISK-0001",
            event_type=EventType.WEATHER,
            description="Typhoon threatening semiconductor production",
            location="Taiwan",
            severity=SeverityLevel.HIGH,
            confidence=0.85,
            detected_at=datetime.now(timezone.utc),
            source_url=raw_event.url,
            affected_entities=["TSMC", "UMC"],
        )

        assert risk_event.event_type == EventType.WEATHER
        assert risk_event.severity == SeverityLevel.HIGH
        assert len(risk_event.affected_entities) == 2

    def test_risk_to_impact_assessment_flow(self):
        """Test that risk events flow to impact assessments."""
        risk_event = RiskEvent(
            id="RISK-0001",
            event_type=EventType.WEATHER,
            description="Weather event",
            location="Taiwan",
            severity=SeverityLevel.HIGH,
            confidence=0.9,
            detected_at=datetime.now(timezone.utc),
            source_url="https://example.com",
            affected_entities=["Supplier A"],
        )

        # Create impact assessment
        impact = ImpactAssessment(
            risk_event_id=risk_event.id,
            affected_suppliers=["SUP-001", "SUP-002"],
            affected_components=["COMP-001", "COMP-002", "COMP-003"],
            affected_products=["PROD-001", "PROD-002"],
            impact_paths=[],
            severity_score=7.5,
            redundancy_level=0.3,
            mitigation_options=["Activate backup suppliers"],
        )

        assert impact.risk_event_id == risk_event.id
        assert len(impact.affected_products) == 2
        assert impact.severity_score > 0

    def test_prioritization_workflow(self):
        """Test risk prioritization workflow."""
        risks = [
            RiskEvent(
                id="RISK-001",
                event_type=EventType.WEATHER,
                description="Low priority weather",
                location="Location A",
                severity=SeverityLevel.LOW,
                confidence=0.7,
                detected_at=datetime.now(timezone.utc),
                source_url="http://example.com",
                affected_entities=["A"],
            ),
            RiskEvent(
                id="RISK-002",
                event_type=EventType.FIRE,
                description="High priority fire",
                location="Location B",
                severity=SeverityLevel.CRITICAL,
                confidence=0.95,
                detected_at=datetime.now(timezone.utc),
                source_url="http://example.com",
                affected_entities=["B", "C", "D"],
            ),
        ]

        prioritizer = RiskPrioritizer()
        prioritized = prioritizer.prioritize_risks(risks)

        # Critical risk should be first
        assert prioritized[0].risk_event.id == "RISK-002"
        assert prioritized[0].priority_rank == 1
        assert prioritized[1].priority_rank == 2

    def test_report_generation_workflow(self):
        """Test complete report generation workflow."""
        risk = RiskEvent(
            id="RISK-0001",
            event_type=EventType.STRIKE,
            description="Factory strike affecting production",
            location="Germany",
            severity=SeverityLevel.MEDIUM,
            confidence=0.8,
            detected_at=datetime.now(timezone.utc),
            source_url="https://example.com",
            affected_entities=["Factory A"],
        )

        impact = ImpactAssessment(
            risk_event_id=risk.id,
            affected_suppliers=["SUP-001"],
            affected_components=["COMP-001"],
            affected_products=["PROD-001"],
            impact_paths=[],
            severity_score=5.0,
            redundancy_level=0.6,
            mitigation_options=["Negotiate resolution", "Activate backup"],
        )

        generator = ReportGenerator()
        report = generator.generate_report(risk, impact)

        assert report.report_id is not None
        assert report.overall_severity == "Medium"
        assert len(report.mitigation_options) > 0
        assert len(report.recommendations) > 0


class TestEntityManagementIntegration:
    """Integration tests for entity management workflows."""

    def test_create_full_supply_chain(self):
        """Test creating a complete supply chain structure."""
        manager = EntityManager()

        # Create suppliers
        sup1 = manager.create_supplier(name="Taiwan Semi", location="Taiwan")
        sup2 = manager.create_supplier(name="German Parts", location="Germany")

        # Create components
        comp1 = manager.create_component(name="CPU Chip", category="Semiconductors")
        comp2 = manager.create_component(name="Power Unit", category="Electronics")

        # Create products
        prod1 = manager.create_product(name="Smartphone Pro", product_line="Mobile")
        prod2 = manager.create_product(name="Laptop Elite", product_line="Computing")

        # Create relationships
        manager.add_supplies_relation(sup1.entity_id, comp1.entity_id)
        manager.add_supplies_relation(sup2.entity_id, comp2.entity_id)
        manager.add_part_of_relation(comp1.entity_id, prod1.entity_id)
        manager.add_part_of_relation(comp1.entity_id, prod2.entity_id)
        manager.add_part_of_relation(comp2.entity_id, prod2.entity_id)

        # Verify structure
        stats = manager.get_statistics()
        assert stats["suppliers"] == 2
        assert stats["components"] == 2
        assert stats["products"] == 2
        assert stats["supplies_relations"] == 2
        assert stats["part_of_relations"] == 3

    def test_query_supply_chain_relationships(self):
        """Test querying supply chain relationships."""
        manager = EntityManager()

        # Create entities
        sup = manager.create_supplier(name="Supplier", location="Taiwan")
        comp = manager.create_component(name="Component", category="Electronics")
        prod = manager.create_product(name="Product", product_line="Consumer")

        # Create relationships
        manager.add_supplies_relation(sup.entity_id, comp.entity_id)
        manager.add_part_of_relation(comp.entity_id, prod.entity_id)

        # Query relationships
        suppliers = manager.get_component_suppliers(comp.entity_id)
        components = manager.get_product_components(prod.entity_id)

        assert len(suppliers) == 1
        assert suppliers[0].name == "Supplier"
        assert len(components) == 1
        assert components[0].name == "Component"

    def test_consistency_validation(self):
        """Test supply chain consistency validation."""
        manager = EntityManager()

        # Create orphaned component (no supplier)
        manager.create_component(name="Orphan", category="Test")

        issues = manager.validate_consistency()

        assert len(issues) > 0
        assert any("no suppliers" in issue.lower() for issue in issues)


class TestAlertGenerationWorkflow:
    """Integration tests for alert generation workflow."""

    def test_alert_payload_generation(self):
        """Test generating alert payloads from risk events."""
        risk = RiskEvent(
            id="RISK-0001",
            event_type=EventType.PANDEMIC,
            description="Health emergency affecting supply chain",
            location="Global",
            severity=SeverityLevel.CRITICAL,
            confidence=0.95,
            detected_at=datetime.now(timezone.utc),
            source_url="https://example.com",
            affected_entities=["Multiple regions"],
        )

        alert = Alert(
            id="ALERT-0001",
            risk_event_id=risk.id,
            product_ids=["PROD-001", "PROD-002", "PROD-003"],
            severity=risk.severity,
            title=f"{risk.severity.value} Alert: {risk.event_type.value}",
            message=risk.description,
        )

        assert alert.severity == SeverityLevel.CRITICAL
        assert len(alert.product_ids) == 3
        assert "Critical" in alert.title

    def test_alert_acknowledgment_workflow(self):
        """Test alert acknowledgment workflow."""
        alert = Alert(
            id="ALERT-0001",
            risk_event_id="RISK-0001",
            product_ids=["PROD-001"],
            severity=SeverityLevel.HIGH,
            title="High Alert",
            message="Test alert",
        )

        # Initially not acknowledged
        assert alert.acknowledged is False

        # Acknowledge the alert
        alert.acknowledged = True
        alert.acknowledged_at = datetime.now(timezone.utc)
        alert.acknowledged_by = "user@example.com"

        assert alert.acknowledged is True
        assert alert.acknowledged_by == "user@example.com"


class TestDataPipelineIntegration:
    """Integration tests for data import/export workflows."""

    def test_import_then_export_roundtrip(self):
        """Test that data can be imported and exported without loss."""
        from src.data import DataImporter, DataExporter

        # Create and import data
        import_data = {
            "suppliers": [
                {"id": "SUP-001", "name": "Supplier 1", "location": "Taiwan", "tier": 1},
                {"id": "SUP-002", "name": "Supplier 2", "location": "Germany", "tier": 2},
            ],
            "components": [
                {"id": "COMP-001", "name": "Component 1", "category": "Electronics"},
            ],
            "products": [
                {"id": "PROD-001", "name": "Product 1", "product_line": "Consumer"},
            ],
        }

        importer = DataImporter()
        result = importer.import_json(import_data)
        assert result.success

        # Export the data
        exporter = DataExporter()
        export_result = exporter.export_json(
            importer.get_suppliers(),
            importer.get_components(),
            importer.get_products(),
        )

        assert export_result.success
        assert export_result.record_count == 4  # 2 suppliers + 1 component + 1 product

        # Verify export contains original data
        import json
        exported = json.loads(export_result.data)
        assert len(exported["suppliers"]) == 2
        assert len(exported["components"]) == 1
        assert len(exported["products"]) == 1


class TestConcurrentOperations:
    """Tests for concurrent operation handling."""

    def test_concurrent_entity_creation(self):
        """Test that entities can be created concurrently without conflict."""
        manager = EntityManager()

        # Create multiple suppliers rapidly
        results = []
        for i in range(10):
            result = manager.create_supplier(
                name=f"Supplier {i}",
                location=f"Location {i}",
            )
            results.append(result)

        # All should succeed
        assert all(r.success for r in results)

        # All IDs should be unique
        ids = [r.entity_id for r in results]
        assert len(ids) == len(set(ids))

    def test_multiple_risk_prioritization(self):
        """Test prioritizing large risk batches."""
        prioritizer = RiskPrioritizer()

        # Create many risks
        risks = []
        for i in range(100):
            severity = list(SeverityLevel)[i % 4]
            risks.append(RiskEvent(
                id=f"RISK-{i:04d}",
                event_type=EventType.OTHER,
                description=f"Risk {i}",
                location="Location",
                severity=severity,
                confidence=0.8,
                detected_at=datetime.now(timezone.utc),
                source_url="http://example.com",
                affected_entities=[f"Entity-{i}"],
            ))

        prioritized = prioritizer.prioritize_risks(risks)

        # Should handle all risks
        assert len(prioritized) == 100

        # Should be properly ranked
        for i, p in enumerate(prioritized):
            assert p.priority_rank == i + 1

        # Higher severity risks should tend to be first
        critical_positions = [
            p.priority_rank for p in prioritized
            if p.risk_event.severity == SeverityLevel.CRITICAL
        ]
        low_positions = [
            p.priority_rank for p in prioritized
            if p.risk_event.severity == SeverityLevel.LOW
        ]

        # Average critical position should be lower (better) than average low position
        if critical_positions and low_positions:
            assert sum(critical_positions) / len(critical_positions) < sum(low_positions) / len(low_positions)
