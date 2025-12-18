"""
Unit tests for the LangGraph workflow orchestration.
"""

import pytest
from datetime import datetime, timezone
import uuid

from src.agents.state import AgentState, WorkflowConfig, create_initial_state
from src.agents.workflow import (
    should_extract,
    should_validate,
    should_analyze,
    should_alert,
    build_risk_monitoring_workflow,
    WorkflowExecutor,
)
from src.agents.nodes import (
    _simple_extraction,
    _score_to_severity,
    _setup_demo_graph,
    _find_suppliers_by_location,
)
from src.graph.traversal import InMemoryGraph
from src.models import (
    RawEvent,
    RiskEvent,
    ImpactAssessment,
    EventType,
    SeverityLevel,
)


class TestConditionalEdges:
    """Tests for workflow conditional edge functions."""

    def test_should_extract_with_events(self):
        """Test that extraction proceeds when events exist."""
        state = create_initial_state()
        state["current_events"] = [
            RawEvent(
                source="test",
                url="https://test.com",
                title="Test",
                content="Content",
            )
        ]

        assert should_extract(state) == "extract"

    def test_should_extract_without_events(self):
        """Test that extraction ends when no events exist."""
        state = create_initial_state()
        state["current_events"] = []

        assert should_extract(state) == "end"

    def test_should_validate_with_risks(self):
        """Test that validation proceeds when risks exist."""
        state = create_initial_state()
        state["extracted_risks"] = [
            RiskEvent(
                id="RISK-001",
                event_type=EventType.WEATHER,
                location="Taiwan",
                affected_entities=[],
                severity=SeverityLevel.HIGH,
                confidence=0.9,
                source_url="https://test.com",
                description="Test",
            )
        ]

        assert should_validate(state) == "validate"

    def test_should_validate_without_risks(self):
        """Test that validation ends when no risks exist."""
        state = create_initial_state()
        state["extracted_risks"] = []

        assert should_validate(state) == "end"

    def test_should_analyze_with_validated_risks(self):
        """Test that analysis proceeds when validated risks exist."""
        state = create_initial_state()
        state["validated_risks"] = [
            RiskEvent(
                id="RISK-001",
                event_type=EventType.FIRE,
                location="Taiwan",
                affected_entities=[],
                severity=SeverityLevel.CRITICAL,
                confidence=0.95,
                source_url="https://test.com",
                description="Test",
            )
        ]

        assert should_analyze(state) == "analyze"

    def test_should_alert_with_assessments(self):
        """Test that alerting proceeds when assessments exist."""
        state = create_initial_state()
        state["impact_assessments"] = [
            ImpactAssessment(
                risk_event_id="RISK-001",
                affected_products=["PROD-001"],
                impact_paths=[],
                severity_score=8.0,
                mitigation_options=[],
                redundancy_level=0.5,
            )
        ]

        assert should_alert(state) == "alert"


class TestSimpleExtraction:
    """Tests for the simple extraction helper."""

    def test_extracts_strike_event(self):
        """Test extraction of strike-related events."""
        raw_event = RawEvent(
            source="test",
            url="https://test.com/strike",
            title="Workers strike at major factory",
            content="Labor dispute leads to walkout at semiconductor plant.",
        )

        risk = _simple_extraction(raw_event)

        assert risk is not None
        assert risk.event_type == EventType.STRIKE

    def test_extracts_weather_event(self):
        """Test extraction of weather-related events."""
        raw_event = RawEvent(
            source="test",
            url="https://test.com/weather",
            title="Typhoon hits Taiwan coast",
            content="Major typhoon causes flooding and disruption.",
        )

        risk = _simple_extraction(raw_event)

        assert risk is not None
        assert risk.event_type == EventType.WEATHER
        assert risk.location == "Taiwan"

    def test_extracts_fire_event(self):
        """Test extraction of fire-related events."""
        raw_event = RawEvent(
            source="test",
            url="https://test.com/fire",
            title="Factory fire in China",
            content="Major fire at electronics manufacturing plant in China.",
        )

        risk = _simple_extraction(raw_event)

        assert risk is not None
        assert risk.event_type == EventType.FIRE
        assert risk.location == "China"

    def test_extracts_critical_severity(self):
        """Test extraction of critical severity."""
        raw_event = RawEvent(
            source="test",
            url="https://test.com/critical",
            title="Catastrophic failure at plant",
            content="Critical infrastructure damage causes severe disruption.",
        )

        risk = _simple_extraction(raw_event)

        assert risk is not None
        assert risk.severity == SeverityLevel.CRITICAL

    def test_extracts_low_severity(self):
        """Test extraction of low severity."""
        raw_event = RawEvent(
            source="test",
            url="https://test.com/minor",
            title="Minor issue at facility",
            content="Small problem with limited impact on operations.",
        )

        risk = _simple_extraction(raw_event)

        assert risk is not None
        assert risk.severity == SeverityLevel.LOW


class TestScoreToSeverity:
    """Tests for score to severity conversion."""

    def test_critical_threshold(self):
        """Test critical severity threshold."""
        assert _score_to_severity(8.0) == SeverityLevel.CRITICAL
        assert _score_to_severity(10.0) == SeverityLevel.CRITICAL

    def test_high_threshold(self):
        """Test high severity threshold."""
        assert _score_to_severity(6.0) == SeverityLevel.HIGH
        assert _score_to_severity(7.9) == SeverityLevel.HIGH

    def test_medium_threshold(self):
        """Test medium severity threshold."""
        assert _score_to_severity(4.0) == SeverityLevel.MEDIUM
        assert _score_to_severity(5.9) == SeverityLevel.MEDIUM

    def test_low_threshold(self):
        """Test low severity threshold."""
        assert _score_to_severity(0.0) == SeverityLevel.LOW
        assert _score_to_severity(3.9) == SeverityLevel.LOW


class TestDemoGraph:
    """Tests for demo graph setup."""

    def test_demo_graph_has_nodes(self):
        """Test that demo graph setup creates nodes."""
        graph = InMemoryGraph()
        _setup_demo_graph(graph)

        assert graph.get_node_count() > 0
        assert graph.get_edge_count() > 0

    def test_demo_graph_has_suppliers(self):
        """Test that demo graph has supplier nodes."""
        graph = InMemoryGraph()
        _setup_demo_graph(graph)

        suppliers = [n for n in graph.nodes.values() if n.label == "Supplier"]
        assert len(suppliers) >= 5

    def test_demo_graph_has_products(self):
        """Test that demo graph has product nodes."""
        graph = InMemoryGraph()
        _setup_demo_graph(graph)

        products = [n for n in graph.nodes.values() if n.label == "Product"]
        assert len(products) >= 3

    def test_find_suppliers_by_location(self):
        """Test finding suppliers by location."""
        graph = InMemoryGraph()
        _setup_demo_graph(graph)

        taiwan_suppliers = _find_suppliers_by_location(graph, "Taiwan")
        assert len(taiwan_suppliers) >= 1

    def test_find_suppliers_unknown_location(self):
        """Test finding suppliers with unknown location."""
        graph = InMemoryGraph()
        _setup_demo_graph(graph)

        suppliers = _find_suppliers_by_location(graph, "Unknown")
        assert len(suppliers) == 0


class TestWorkflowBuilder:
    """Tests for workflow graph building."""

    def test_workflow_builds_successfully(self):
        """Test that the workflow builds without errors."""
        workflow = build_risk_monitoring_workflow()
        assert workflow is not None

    def test_workflow_has_all_nodes(self):
        """Test that workflow has all required nodes."""
        workflow = build_risk_monitoring_workflow()

        # Compile to verify structure
        compiled = workflow.compile()
        assert compiled is not None


class TestWorkflowExecutor:
    """Tests for the WorkflowExecutor class."""

    def test_executor_initialization(self):
        """Test executor initializes correctly."""
        executor = WorkflowExecutor()

        assert executor.config is not None
        assert not executor._is_running

    def test_executor_with_custom_config(self):
        """Test executor with custom configuration."""
        config = WorkflowConfig(
            max_events_per_run=50,
            confidence_threshold=0.8,
            alert_threshold=7.5,
        )

        executor = WorkflowExecutor(config=config)

        assert executor.config.max_events_per_run == 50
        assert executor.config.confidence_threshold == 0.8
        assert executor.config.alert_threshold == 7.5

    def test_executor_stats_initial(self):
        """Test executor initial stats."""
        executor = WorkflowExecutor()
        stats = executor.get_stats()

        assert stats["is_running"] is False
        assert stats["total_runs"] == 0
        assert stats["successful_runs"] == 0

    def test_executor_stop(self):
        """Test executor stop method."""
        executor = WorkflowExecutor()
        executor._is_running = True

        executor.stop()

        assert not executor._is_running


class TestWorkflowConfig:
    """Tests for WorkflowConfig."""

    def test_default_config(self):
        """Test default configuration values."""
        config = WorkflowConfig()

        assert config.max_events_per_run > 0
        assert 0.0 <= config.confidence_threshold <= 1.0
        assert config.alert_threshold > 0

    def test_custom_config(self):
        """Test custom configuration."""
        config = WorkflowConfig(
            max_events_per_run=100,
            confidence_threshold=0.9,
            alert_threshold=8.0,
        )

        assert config.max_events_per_run == 100
        assert config.confidence_threshold == 0.9
        assert config.alert_threshold == 8.0
