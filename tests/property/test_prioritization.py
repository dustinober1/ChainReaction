"""
Property-Based Tests for Risk Prioritization and Reporting.

Feature: chain-reaction
Property 2: Risk prioritization consistency
Property 15: Impact report completeness

Validates that risk prioritization is consistent and reports are complete.

Validates: Requirements 1.3, 6.5
"""

import pytest
from hypothesis import given, settings, HealthCheck
from hypothesis import strategies as st
from datetime import datetime, timezone, timedelta

from src.models import RiskEvent, SeverityLevel, EventType, ImpactAssessment
from src.analysis.prioritization import (
    RiskPrioritizer,
    PriorityWeights,
    sort_by_severity,
    sort_by_timeline,
)
from src.analysis.reporting import ReportGenerator


# =============================================================================
# Test Data Generators
# =============================================================================


@st.composite
def risk_event_strategy(draw) -> RiskEvent:
    """Generate a random risk event for testing."""
    detected_hours_ago = draw(st.integers(min_value=0, max_value=720))
    detected_at = datetime.now(timezone.utc) - timedelta(hours=detected_hours_ago)

    return RiskEvent(
        id=f"RISK-{draw(st.integers(min_value=1, max_value=9999)):04d}",
        event_type=draw(st.sampled_from(list(EventType))),
        description=draw(st.text(min_size=10, max_size=100)),
        location=draw(st.sampled_from(["Taiwan", "China", "Germany", "USA", "Japan"])),
        severity=draw(st.sampled_from(list(SeverityLevel))),
        confidence=draw(st.floats(min_value=0.5, max_value=1.0)),
        detected_at=detected_at,
        source_url="https://example.com/news",
        affected_entities=draw(st.lists(
            st.text(min_size=3, max_size=10),
            min_size=1,
            max_size=5,
        )),
    )


@st.composite
def impact_assessment_strategy(draw, risk_id: str) -> ImpactAssessment:
    """Generate a random impact assessment for testing."""
    return ImpactAssessment(
        risk_event_id=risk_id,
        affected_suppliers=draw(st.lists(st.text(min_size=3, max_size=10), min_size=1, max_size=3)),
        affected_components=draw(st.lists(st.text(min_size=3, max_size=10), min_size=1, max_size=5)),
        affected_products=draw(st.lists(st.text(min_size=3, max_size=10), min_size=1, max_size=5)),
        impact_paths=[],
        severity_score=draw(st.floats(min_value=1.0, max_value=10.0)),
        redundancy_level=draw(st.floats(min_value=0.0, max_value=1.0)),
        mitigation_options=["Option A", "Option B"],
    )


# =============================================================================
# Property 2: Risk prioritization consistency
# =============================================================================


class TestRiskPrioritizationConsistency:
    """
    Property-based tests for risk prioritization consistency.

    Feature: chain-reaction, Property 2: Risk prioritization consistency
    """

    @given(st.sampled_from(list(SeverityLevel)), st.sampled_from(list(SeverityLevel)))
    @settings(max_examples=50)
    def test_higher_severity_has_higher_score(
        self,
        severity1: SeverityLevel,
        severity2: SeverityLevel,
    ):
        """
        Property: Higher severity always results in higher severity score.

        Feature: chain-reaction, Property 2: Risk prioritization consistency
        Validates: Requirements 1.3
        """
        prioritizer = RiskPrioritizer()

        score1 = prioritizer.SEVERITY_SCORES[severity1]
        score2 = prioritizer.SEVERITY_SCORES[severity2]

        severity_order = [SeverityLevel.LOW, SeverityLevel.MEDIUM, SeverityLevel.HIGH, SeverityLevel.CRITICAL]

        if severity_order.index(severity1) > severity_order.index(severity2):
            assert score1 > score2
        elif severity_order.index(severity1) < severity_order.index(severity2):
            assert score1 < score2
        else:
            assert score1 == score2

    @given(st.floats(min_value=0.0, max_value=0.25), st.floats(min_value=0.0, max_value=0.25))
    @settings(max_examples=30)
    def test_weights_must_sum_to_one(self, w1: float, w2: float):
        """
        Property: Priority weights must sum to 1.0 to be valid.

        Feature: chain-reaction, Property 2: Risk prioritization consistency
        Validates: Requirements 1.3
        """
        # Create weights that don't sum to 1.0
        invalid_weights = PriorityWeights(
            severity=w1,
            timeline=w2,
            products_affected=0.2,
            revenue_impact=0.1,
            confidence=0.1,
        )

        expected_sum = w1 + w2 + 0.4
        is_valid = invalid_weights.validate()

        # Should only be valid if sum is close to 1.0
        assert is_valid == (0.99 <= expected_sum <= 1.01)

    def test_same_risk_always_gets_same_priority(self):
        """
        Test: Same risk should always receive the same priority score.

        Feature: chain-reaction, Property 2: Risk prioritization consistency
        Validates: Requirements 1.3
        """
        prioritizer = RiskPrioritizer()

        risk = RiskEvent(
            id="RISK-0001",
            event_type=EventType.WEATHER,
            description="Test weather event",
            location="Taiwan",
            severity=SeverityLevel.HIGH,
            confidence=0.9,
            detected_at=datetime.now(timezone.utc),
            source_url="https://example.com",
            affected_entities=["Product A"],
        )

        score1 = prioritizer.calculate_priority(risk).priority_score
        score2 = prioritizer.calculate_priority(risk).priority_score

        assert score1 == score2

    def test_sort_by_severity_order(self):
        """
        Test: Sorting by severity maintains proper order.

        Feature: chain-reaction, Property 2: Risk prioritization consistency
        Validates: Requirements 1.3
        """
        now = datetime.now(timezone.utc)
        risks = [
            RiskEvent(
                id="RISK-1", event_type=EventType.WEATHER, description="Low",
                location="A", severity=SeverityLevel.LOW, confidence=0.9,
                detected_at=now, source_url="http://x", affected_entities=[],
            ),
            RiskEvent(
                id="RISK-2", event_type=EventType.WEATHER, description="Critical",
                location="B", severity=SeverityLevel.CRITICAL, confidence=0.9,
                detected_at=now, source_url="http://x", affected_entities=[],
            ),
            RiskEvent(
                id="RISK-3", event_type=EventType.WEATHER, description="Medium",
                location="C", severity=SeverityLevel.MEDIUM, confidence=0.9,
                detected_at=now, source_url="http://x", affected_entities=[],
            ),
        ]

        sorted_risks = sort_by_severity(risks)

        assert sorted_risks[0].severity == SeverityLevel.CRITICAL
        assert sorted_risks[1].severity == SeverityLevel.MEDIUM
        assert sorted_risks[2].severity == SeverityLevel.LOW

    def test_sort_by_timeline_order(self):
        """
        Test: Sorting by timeline puts most recent first.

        Feature: chain-reaction, Property 2: Risk prioritization consistency
        Validates: Requirements 1.3
        """
        now = datetime.now(timezone.utc)
        risks = [
            RiskEvent(
                id="RISK-OLD", event_type=EventType.WEATHER, description="Old",
                location="A", severity=SeverityLevel.HIGH, confidence=0.9,
                detected_at=now - timedelta(days=30), source_url="http://x",
                affected_entities=[],
            ),
            RiskEvent(
                id="RISK-NEW", event_type=EventType.WEATHER, description="New",
                location="B", severity=SeverityLevel.HIGH, confidence=0.9,
                detected_at=now, source_url="http://x", affected_entities=[],
            ),
        ]

        sorted_risks = sort_by_timeline(risks)

        assert sorted_risks[0].id == "RISK-NEW"
        assert sorted_risks[1].id == "RISK-OLD"

    def test_no_risk_response_structure(self):
        """
        Test: No-risk response has required structure.

        Feature: chain-reaction, Property 2: Risk prioritization consistency
        Validates: Requirements 1.4
        """
        prioritizer = RiskPrioritizer()
        response = prioritizer.get_no_risk_response()

        assert response["status"] == "stable"
        assert response["risk_count"] == 0
        assert "message" in response
        assert "recommendations" in response
        assert len(response["recommendations"]) > 0


# =============================================================================
# Property 15: Impact report completeness
# =============================================================================


class TestImpactReportCompleteness:
    """
    Property-based tests for impact report completeness.

    Feature: chain-reaction, Property 15: Impact report completeness
    """

    def test_report_has_all_required_sections(self):
        """
        Test: Generated report contains all required sections.

        Feature: chain-reaction, Property 15: Impact report completeness
        Validates: Requirements 6.5
        """
        generator = ReportGenerator()

        risk = RiskEvent(
            id="RISK-0001",
            event_type=EventType.WEATHER,
            description="Test typhoon affecting semiconductor production",
            location="Taiwan",
            severity=SeverityLevel.HIGH,
            confidence=0.85,
            detected_at=datetime.now(timezone.utc),
            source_url="https://example.com",
            affected_entities=["TSMC"],
        )

        impact = ImpactAssessment(
            risk_event_id="RISK-0001",
            affected_suppliers=["SUP-001"],
            affected_components=["COMP-001", "COMP-002"],
            affected_products=["PROD-001", "PROD-002", "PROD-003"],
            impact_paths=[],
            severity_score=7.5,
            redundancy_level=0.3,
            mitigation_options=["Activate backup suppliers", "Increase safety stock"],
        )

        report = generator.generate_report(risk, impact)

        # Verify required fields
        assert report.report_id is not None
        assert report.risk_event_id == risk.id
        assert report.generated_at is not None
        assert report.title is not None
        assert report.executive_summary is not None
        assert report.timeline is not None
        assert report.affected_products is not None
        assert report.mitigation_options is not None
        assert report.recommendations is not None

    def test_timeline_estimate_is_valid(self):
        """
        Test: Timeline estimate has valid dates in proper order.

        Feature: chain-reaction, Property 15: Impact report completeness
        Validates: Requirements 6.5
        """
        generator = ReportGenerator()

        risk = RiskEvent(
            id="RISK-0001",
            event_type=EventType.STRIKE,
            description="Factory strike",
            location="Germany",
            severity=SeverityLevel.MEDIUM,
            confidence=0.9,
            detected_at=datetime.now(timezone.utc),
            source_url="https://example.com",
            affected_entities=["Factory A"],
        )

        impact = ImpactAssessment(
            risk_event_id="RISK-0001",
            affected_suppliers=["SUP-001"],
            affected_components=["COMP-001"],
            affected_products=["PROD-001"],
            impact_paths=[],
            severity_score=5.0,
            redundancy_level=0.6,
            mitigation_options=["Negotiate resolution"],
        )

        report = generator.generate_report(risk, impact)
        timeline = report.timeline

        # Timeline should be in order
        assert timeline.impact_start <= timeline.peak_impact
        assert timeline.peak_impact <= timeline.expected_resolution
        assert 0.0 <= timeline.confidence <= 1.0

    @given(st.sampled_from(list(SeverityLevel)))
    @settings(max_examples=10)
    def test_report_severity_matches_risk(self, severity: SeverityLevel):
        """
        Property: Report severity matches input risk severity.

        Feature: chain-reaction, Property 15: Impact report completeness
        Validates: Requirements 6.5
        """
        generator = ReportGenerator()

        risk = RiskEvent(
            id="RISK-0001",
            event_type=EventType.FIRE,
            description="Factory fire",
            location="Japan",
            severity=severity,
            confidence=0.9,
            detected_at=datetime.now(timezone.utc),
            source_url="https://example.com",
            affected_entities=["Factory"],
        )

        impact = ImpactAssessment(
            risk_event_id="RISK-0001",
            affected_suppliers=["SUP-001"],
            affected_components=["COMP-001"],
            affected_products=["PROD-001"],
            impact_paths=[],
            severity_score=5.0,
            redundancy_level=0.5,
            mitigation_options=[],
        )

        report = generator.generate_report(risk, impact)

        assert report.overall_severity == severity.value

    def test_json_export_is_valid(self):
        """
        Test: JSON export produces valid JSON.

        Feature: chain-reaction, Property 15: Impact report completeness
        Validates: Requirements 6.5
        """
        import json

        generator = ReportGenerator()

        risk = RiskEvent(
            id="RISK-0001",
            event_type=EventType.PANDEMIC,
            description="Health emergency",
            location="Global",
            severity=SeverityLevel.CRITICAL,
            confidence=0.95,
            detected_at=datetime.now(timezone.utc),
            source_url="https://example.com",
            affected_entities=["All regions"],
        )

        impact = ImpactAssessment(
            risk_event_id="RISK-0001",
            affected_suppliers=["SUP-001", "SUP-002"],
            affected_components=["COMP-001"],
            affected_products=["PROD-001"],
            impact_paths=[],
            severity_score=9.0,
            redundancy_level=0.2,
            mitigation_options=["Emergency protocols"],
        )

        report = generator.generate_report(risk, impact)
        json_output = generator.export_json(report)

        # Should be valid JSON
        parsed = json.loads(json_output)
        assert "report_id" in parsed
        assert "executive_summary" in parsed

    def test_markdown_export_has_sections(self):
        """
        Test: Markdown export contains all sections.

        Feature: chain-reaction, Property 15: Impact report completeness
        Validates: Requirements 6.5
        """
        generator = ReportGenerator()

        risk = RiskEvent(
            id="RISK-0001",
            event_type=EventType.GEOPOLITICAL,
            description="Trade restrictions",
            location="China",
            severity=SeverityLevel.HIGH,
            confidence=0.8,
            detected_at=datetime.now(timezone.utc),
            source_url="https://example.com",
            affected_entities=["Suppliers"],
        )

        impact = ImpactAssessment(
            risk_event_id="RISK-0001",
            affected_suppliers=["SUP-001"],
            affected_components=["COMP-001"],
            affected_products=["PROD-001"],
            impact_paths=[],
            severity_score=7.0,
            redundancy_level=0.4,
            mitigation_options=["Alternative sourcing"],
        )

        report = generator.generate_report(risk, impact)
        markdown = generator.export_markdown(report)

        # Check for required sections
        assert "# " in markdown  # Title
        assert "## Executive Summary" in markdown
        assert "## Timeline" in markdown
        assert "## Affected Products" in markdown
        assert "## Mitigation Options" in markdown
        assert "## Recommendations" in markdown
