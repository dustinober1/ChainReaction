import pytest
import dspy
from src.analysis.modules import MitigationCoPilotModule
from src.models import RiskEvent, EventType, SeverityLevel
from datetime import datetime, timezone

class TestMitigationCoPilot:
    """Tests for MitigationCoPilotModule."""

    @pytest.fixture
    def module(self):
        """Initialize module for testing."""
        # Use a mock or local LM for testing if needed, but here we'll assume dspy.settings
        return MitigationCoPilotModule()

    @pytest.fixture
    def sample_risk(self):
        """Create a sample risk event."""
        return RiskEvent(
            id="RISK-TEST",
            event_type=EventType.WEATHER,
            location="Taiwan",
            description="Major typhoon approaching manufacturing hubs",
            severity=SeverityLevel.HIGH,
            confidence=0.9,
            detected_at=datetime.now(timezone.utc),
            source_url="https://example.com",
            affected_entities=["TSMC", "ASE Group"]
        )

    def test_parse_list_newline(self, module):
        """Test parsing newline-separated suggestions."""
        input_str = "1. Action one\n2. Action two\n- Action three"
        parsed = module._parse_list(input_str)
        assert len(parsed) == 3
        assert parsed[0] == "Action one"
        assert parsed[1] == "Action two"
        assert parsed[2] == "Action three"

    def test_parse_list_comma(self, module):
        """Test parsing comma-separated suggestions."""
        input_str = "Action A, Action B, Action C"
        parsed = module._parse_list(input_str)
        assert len(parsed) == 3
        assert parsed[0] == "Action A"
        assert parsed[1] == "Action B"
        assert parsed[2] == "Action C"

    def test_parse_list_empty(self, module):
        """Test parsing empty or None values."""
        assert module._parse_list("") == []
        assert module._parse_list("None") == []
        assert module._parse_list(None) == []

    @pytest.mark.asyncio
    async def test_get_recommendations_structure(self, module, sample_risk):
        """
        Test that get_recommendations returns the correct structure.
        Note: This might call the LLM if not mocked.
        """
        # For unit testing without LLM, we should ideally mock self.forward
        # But since dspy modules are intended to be tested with the configured LM:
        
        # Mocking forward to avoid LLM dependency in unit tests
        class MockPrediction:
            top_priority_actions = "Action 1, Action 2"
            strategic_mitigations = "Strategic 1"
            rationale = "Test rationale"
            estimated_risk_reduction = "Medium"

        module.forward = lambda **kwargs: MockPrediction()
        
        results = module.get_recommendations(
            risk_event=sample_risk,
            affected_entities=sample_risk.affected_entities,
            graph_context="Test context"
        )
        
        assert results["success"] is True
        assert len(results["top_priority_actions"]) == 2
        assert results["rationale"] == "Test rationale"
        assert results["estimated_risk_reduction"] == "Medium"
