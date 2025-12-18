"""
Property-Based Tests for Workflow and Alert Generation.

Feature: chain-reaction
Property 3: Alert generation for monitored products

Validates that the workflow correctly processes events and
generates alerts for high-severity risk events.

Validates: Requirements 1.5, 8.4
"""

import pytest
from hypothesis import given, settings, HealthCheck, assume
from hypothesis import strategies as st
from datetime import datetime, timezone
import uuid

from src.agents.state import AgentState, WorkflowConfig, create_initial_state
from src.agents.workflow import (
    should_extract,
    should_validate,
    should_analyze,
    should_alert,
)
from src.agents.nodes import (
    _simple_extraction,
    _score_to_severity,
)
from src.models import (
    RawEvent,
    RiskEvent,
    Alert,
    ImpactAssessment,
    EventType,
    SeverityLevel,
)


# =============================================================================
# Test Strategies
# =============================================================================

@st.composite
def raw_event_strategy(draw) -> RawEvent:
    """Generate a raw event for testing."""
    keywords = draw(st.sampled_from([
        "strike", "typhoon", "fire", "bankruptcy", "sanction", "ransomware", "port"
    ]))
    location = draw(st.sampled_from([
        "Taiwan", "Vietnam", "China", "Japan", "Germany", "California"
    ]))

    return RawEvent(
        source=draw(st.sampled_from(["tavily", "newsapi"])),
        url=f"https://news.example.com/{draw(st.text(min_size=5, max_size=15))}",
        title=f"Breaking: {keywords} event in {location}",
        content=f"Major {keywords} affecting supply chain in {location}. This is a test article with substantial content.",
        published_at=datetime.now(timezone.utc),
    )


@st.composite
def risk_event_strategy(draw) -> RiskEvent:
    """Generate a risk event for testing."""
    return RiskEvent(
        id=f"RISK-{uuid.uuid4().hex[:8].upper()}",
        event_type=draw(st.sampled_from(list(EventType))),
        location=draw(st.sampled_from(["Taiwan", "Vietnam", "China", "Unknown"])),
        affected_entities=[],
        severity=draw(st.sampled_from(list(SeverityLevel))),
        confidence=draw(st.floats(min_value=0.3, max_value=1.0)),
        source_url="https://test.example.com",
        description="Test risk event",
    )


@st.composite
def impact_assessment_strategy(draw) -> ImpactAssessment:
    """Generate an impact assessment for testing."""
    return ImpactAssessment(
        risk_event_id=f"RISK-{uuid.uuid4().hex[:8].upper()}",
        affected_products=[f"PROD-{i:04d}" for i in range(draw(st.integers(0, 5)))],
        impact_paths=[],
        severity_score=draw(st.floats(min_value=0.0, max_value=10.0)),
        mitigation_options=["Action 1", "Action 2"],
        redundancy_level=draw(st.floats(min_value=0.0, max_value=1.0)),
    )


# =============================================================================
# Property 3: Alert generation for monitored products
# =============================================================================


class TestAlertGeneration:
    """
    Property-based tests for alert generation.

    Feature: chain-reaction, Property 3: Alert generation for monitored products
    """

    @given(st.floats(min_value=0.0, max_value=10.0))
    @settings(max_examples=50)
    def test_severity_score_to_level_is_valid(self, score: float):
        """
        Property: Score to severity conversion always returns valid level.

        Feature: chain-reaction, Property 3: Alert generation
        Validates: Requirements 1.5
        """
        severity = _score_to_severity(score)
        assert severity in list(SeverityLevel)

    @given(st.floats(min_value=8.0, max_value=10.0))
    @settings(max_examples=20)
    def test_high_scores_produce_critical_severity(self, score: float):
        """
        Property: Scores >= 8.0 produce CRITICAL severity.

        Feature: chain-reaction, Property 3: Alert generation
        Validates: Requirements 1.5
        """
        severity = _score_to_severity(score)
        assert severity == SeverityLevel.CRITICAL

    @given(st.floats(min_value=0.0, max_value=3.99))
    @settings(max_examples=20)
    def test_low_scores_produce_low_severity(self, score: float):
        """
        Property: Scores < 4.0 produce LOW severity.

        Feature: chain-reaction, Property 3: Alert generation
        Validates: Requirements 1.5
        """
        severity = _score_to_severity(score)
        assert severity == SeverityLevel.LOW

    @given(raw_event_strategy())
    @settings(max_examples=50, suppress_health_check=[HealthCheck.too_slow])
    def test_extraction_always_produces_risk_event(self, raw_event: RawEvent):
        """
        Property: Simple extraction always produces a valid RiskEvent.

        Feature: chain-reaction, Property 3: Alert generation
        Validates: Requirements 1.5
        """
        risk_event = _simple_extraction(raw_event)

        assert risk_event is not None
        assert risk_event.id.startswith("RISK-")
        assert risk_event.event_type in list(EventType)
        assert risk_event.severity in list(SeverityLevel)
        assert risk_event.source_url == raw_event.url

    @given(st.lists(raw_event_strategy(), min_size=0, max_size=5))
    @settings(max_examples=30, suppress_health_check=[HealthCheck.too_slow])
    def test_workflow_state_determines_next_step(self, events: list[RawEvent]):
        """
        Property: Workflow routing depends on state contents.

        Feature: chain-reaction, Property 3: Alert generation
        Validates: Requirements 8.4
        """
        state: AgentState = create_initial_state()
        state["current_events"] = events

        result = should_extract(state)

        if len(events) > 0:
            assert result == "extract"
        else:
            assert result == "end"

    @given(st.lists(risk_event_strategy(), min_size=0, max_size=5))
    @settings(max_examples=30, suppress_health_check=[HealthCheck.too_slow])
    def test_validate_routing_based_on_risks(self, risks: list[RiskEvent]):
        """
        Property: Validation routing depends on extracted risks.

        Feature: chain-reaction, Property 3: Alert generation
        Validates: Requirements 8.4
        """
        state: AgentState = create_initial_state()
        state["extracted_risks"] = risks

        result = should_validate(state)

        if len(risks) > 0:
            assert result == "validate"
        else:
            assert result == "end"

    @given(st.lists(impact_assessment_strategy(), min_size=0, max_size=5))
    @settings(max_examples=30, suppress_health_check=[HealthCheck.too_slow])
    def test_alert_routing_based_on_assessments(self, assessments: list[ImpactAssessment]):
        """
        Property: Alert routing depends on impact assessments.

        Feature: chain-reaction, Property 3: Alert generation
        Validates: Requirements 8.4
        """
        state: AgentState = create_initial_state()
        state["impact_assessments"] = assessments

        result = should_alert(state)

        if len(assessments) > 0:
            assert result == "alert"
        else:
            assert result == "end"


# =============================================================================
# Workflow State Tests
# =============================================================================


class TestWorkflowState:
    """Tests for workflow state management."""

    def test_initial_state_has_required_fields(self):
        """
        Test: Initial state contains all required fields.

        Feature: chain-reaction
        Validates: Requirements 8.4
        """
        state = create_initial_state()

        assert "current_events" in state
        assert "extracted_risks" in state
        assert "validated_risks" in state
        assert "impact_assessments" in state
        assert "alerts_generated" in state
        assert "processing_errors" in state

    @given(st.integers(min_value=1, max_value=100))
    @settings(max_examples=20)
    def test_config_max_events_respected(self, max_events: int):
        """
        Property: WorkflowConfig max_events_per_run is respected.

        Feature: chain-reaction
        Validates: Requirements 8.4
        """
        config = WorkflowConfig(max_events_per_run=max_events)

        assert config.max_events_per_run == max_events

    @given(st.floats(min_value=0.0, max_value=1.0))
    @settings(max_examples=20)
    def test_config_confidence_threshold_valid(self, threshold: float):
        """
        Property: WorkflowConfig confidence threshold is valid.

        Feature: chain-reaction
        Validates: Requirements 8.4
        """
        config = WorkflowConfig(confidence_threshold=threshold)

        assert config.confidence_threshold == threshold

    @given(st.floats(min_value=0.0, max_value=10.0))
    @settings(max_examples=20)
    def test_config_alert_threshold_valid(self, threshold: float):
        """
        Property: WorkflowConfig alert threshold is valid.

        Feature: chain-reaction
        Validates: Requirements 1.5
        """
        config = WorkflowConfig(alert_threshold=threshold)

        assert config.alert_threshold == threshold
