"""
Property-Based Tests for Extraction Pipeline.

Feature: chain-reaction
Property 5: Extraction pipeline completeness
Property 6: Error handling continuity

Validates that the extraction pipeline correctly processes all input types
and continues execution even when encountering errors.

Validates: Requirements 2.2, 2.3, 2.4, 5.1, 5.2, 5.3
"""

import pytest
from hypothesis import given, settings, HealthCheck
from hypothesis import strategies as st

from src.analysis.validation import (
    ExtractionValidator,
    ConfidenceScorer,
    ExtractionErrorHandler,
    ValidationResult,
)
from src.analysis.training import (
    TrainingExample,
    TrainingDataset,
    TrainingDataManager,
)
from src.models import RiskEvent, EventType, SeverityLevel

# Import strategies for generating test data
from tests.strategies import risk_event_strategy


# =============================================================================
# Test Strategies
# =============================================================================

# Strategy for generating news content
news_content_strategy = st.text(min_size=50, max_size=500).filter(
    lambda s: len(s.strip()) >= 50
)

# Strategy for generating source URLs
source_url_strategy = st.text(min_size=10, max_size=50).map(
    lambda s: f"https://news.example.com/{s.replace(' ', '-')}"
)


# =============================================================================
# Property 5: Extraction pipeline completeness
# =============================================================================


class TestExtractionPipelineCompleteness:
    """
    Property-based tests for extraction pipeline completeness.

    Feature: chain-reaction, Property 5: Extraction pipeline completeness
    """

    @given(risk_event_strategy())
    @settings(max_examples=100, suppress_health_check=[HealthCheck.too_slow])
    def test_validator_returns_result_for_any_event(self, event: RiskEvent):
        """
        Property: Validator always returns a ValidationResult for any event.

        Feature: chain-reaction, Property 5: Extraction pipeline completeness
        Validates: Requirements 5.1, 5.3
        """
        validator = ExtractionValidator()
        result = validator.validate(event)

        assert isinstance(result, ValidationResult)
        assert isinstance(result.is_valid, bool)
        assert isinstance(result.errors, list)
        assert isinstance(result.warnings, list)
        assert 0.0 <= result.confidence_adjusted <= 1.0

    @given(risk_event_strategy())
    @settings(max_examples=100, suppress_health_check=[HealthCheck.too_slow])
    def test_confidence_adjustment_is_bounded(self, event: RiskEvent):
        """
        Property: Adjusted confidence is always within [0, 1] range.

        Feature: chain-reaction, Property 5: Extraction pipeline completeness
        Validates: Requirements 5.3
        """
        validator = ExtractionValidator(confidence_threshold=0.0)
        result = validator.validate(event)

        assert 0.0 <= result.confidence_adjusted <= 1.0
        assert 0.0 <= result.original_confidence <= 1.0

    @given(st.lists(risk_event_strategy(), min_size=1, max_size=10))
    @settings(max_examples=50, suppress_health_check=[HealthCheck.too_slow])
    def test_batch_validation_processes_all_events(self, events: list[RiskEvent]):
        """
        Property: Batch validation returns result for every input event.

        Feature: chain-reaction, Property 5: Extraction pipeline completeness
        Validates: Requirements 2.2, 5.1
        """
        validator = ExtractionValidator()
        results = validator.validate_batch(events)

        assert len(results) == len(events)
        for event, result in results:
            assert isinstance(result, ValidationResult)

    @given(
        st.floats(min_value=0.0, max_value=1.0),
        source_url_strategy,
        st.integers(min_value=0, max_value=10),
        st.booleans(),
        st.booleans(),
    )
    @settings(max_examples=100, suppress_health_check=[HealthCheck.too_slow])
    def test_confidence_scorer_always_returns_valid_score(
        self,
        base_confidence: float,
        source_url: str,
        entity_count: int,
        location_recognized: bool,
        event_type_clear: bool,
    ):
        """
        Property: ConfidenceScorer always returns a score in [0, 1].

        Feature: chain-reaction, Property 5: Extraction pipeline completeness
        Validates: Requirements 5.3
        """
        scorer = ConfidenceScorer()
        score = scorer.calculate_confidence(
            base_confidence=base_confidence,
            source_url=source_url,
            entity_count=entity_count,
            location_recognized=location_recognized,
            event_type_clear=event_type_clear,
        )

        assert 0.0 <= score <= 1.0

    @given(st.sampled_from(list(EventType)))
    @settings(max_examples=20)
    def test_all_event_types_are_valid_for_extraction(self, event_type: EventType):
        """
        Property: All defined event types can be processed by the pipeline.

        Feature: chain-reaction, Property 5: Extraction pipeline completeness
        Validates: Requirements 2.3, 5.2
        """
        event = RiskEvent(
            id="TEST-001",
            event_type=event_type,
            location="Test Location",
            affected_entities=["Test Company"],
            severity=SeverityLevel.MEDIUM,
            confidence=0.8,
            source_url="https://test.com",
            description=f"Test event of type {event_type.value}",
        )

        validator = ExtractionValidator()
        result = validator.validate(event)

        # Should not have type-related errors
        assert not any("event_type" in str(e).lower() for e in result.errors)


# =============================================================================
# Property 6: Error handling continuity
# =============================================================================


class TestErrorHandlingContinuity:
    """
    Property-based tests for error handling continuity.

    Feature: chain-reaction, Property 6: Error handling continuity
    """

    @given(
        st.text(min_size=1, max_size=100),
        source_url_strategy,
        st.text(min_size=10, max_size=200),
    )
    @settings(max_examples=100, suppress_health_check=[HealthCheck.too_slow])
    def test_fallback_event_always_created(
        self,
        error_message: str,
        source_url: str,
        content_snippet: str,
    ):
        """
        Property: Fallback event is always created for any error.

        Feature: chain-reaction, Property 6: Error handling continuity
        Validates: Requirements 2.4
        """
        handler = ExtractionErrorHandler()
        fallback = handler.create_fallback_event(
            source_url=source_url,
            content_snippet=content_snippet,
            error_message=error_message,
        )

        assert fallback is not None
        assert isinstance(fallback, RiskEvent)
        assert fallback.id.startswith("RISK-FALLBACK-")
        assert fallback.confidence == 0.1  # Low confidence for fallbacks
        assert fallback.event_type == EventType.OTHER

    @given(st.lists(st.sampled_from([
        ValueError("Test error"),
        TypeError("Type mismatch"),
        KeyError("missing_key"),
        RuntimeError("Runtime failure"),
    ]), min_size=1, max_size=10))
    @settings(max_examples=50, suppress_health_check=[HealthCheck.too_slow])
    def test_error_handler_logs_all_errors(self, errors: list[Exception]):
        """
        Property: All errors are logged and tracked.

        Feature: chain-reaction, Property 6: Error handling continuity
        Validates: Requirements 2.4
        """
        handler = ExtractionErrorHandler()

        for error in errors:
            handler.log_error(error, source_url="test://url")

        summary = handler.get_error_summary()

        assert summary["total_errors"] == len(errors)
        assert len(handler.error_log) == len(errors)

    @given(
        st.integers(min_value=1, max_value=10),
        st.integers(min_value=1, max_value=5),
    )
    @settings(max_examples=50)
    def test_retry_logic_respects_max_attempts(
        self,
        max_retries: int,
        attempt: int,
    ):
        """
        Property: Retry logic correctly enforces max attempts.

        Feature: chain-reaction, Property 6: Error handling continuity
        Validates: Requirements 2.4
        """
        handler = ExtractionErrorHandler(max_retries=max_retries)
        error = ConnectionError("Network failure")

        should_retry = handler.should_retry(error, attempt)

        if attempt >= max_retries:
            assert not should_retry
        # If under max, ConnectionError should retry
        elif attempt < max_retries:
            assert should_retry

    @given(risk_event_strategy())
    @settings(max_examples=50, suppress_health_check=[HealthCheck.too_slow])
    def test_error_log_can_be_cleared(self, event: RiskEvent):
        """
        Property: Error log can be cleared without affecting operation.

        Feature: chain-reaction, Property 6: Error handling continuity
        Validates: Requirements 2.4
        """
        handler = ExtractionErrorHandler()

        # Log some errors
        handler.log_error(ValueError("test"))
        handler.log_error(TypeError("test"))

        assert handler.get_error_summary()["total_errors"] == 2

        # Clear and verify
        handler.clear_log()

        assert handler.get_error_summary()["total_errors"] == 0

        # Should still be able to log new errors
        handler.log_error(RuntimeError("new error"))
        assert handler.get_error_summary()["total_errors"] == 1

    @given(st.floats(min_value=0.0, max_value=1.0))
    @settings(max_examples=50)
    def test_high_confidence_threshold_still_validates(
        self,
        threshold: float,
    ):
        """
        Property: Pipeline continues even with high confidence thresholds.

        Feature: chain-reaction, Property 6: Error handling continuity
        Validates: Requirements 2.4
        """
        validator = ExtractionValidator(confidence_threshold=threshold)

        event = RiskEvent(
            id="TEST-001",
            event_type=EventType.WEATHER,
            location="Taiwan",
            affected_entities=["TSMC"],
            severity=SeverityLevel.HIGH,
            confidence=0.95,
            source_url="https://test.com",
            description="Major weather event affecting operations",
        )

        result = validator.validate(event)

        # Should always produce a result, even if marked invalid
        assert isinstance(result, ValidationResult)


# =============================================================================
# Training Data Tests
# =============================================================================


class TestTrainingDataIntegrity:
    """Tests for training data management."""

    @given(st.lists(
        st.builds(
            TrainingExample,
            news_content=st.text(min_size=50, max_size=200),
            expected_location=st.text(min_size=3, max_size=30),
            expected_company=st.text(min_size=3, max_size=50),
            expected_event_type=st.sampled_from([
                "Strike", "Weather", "Bankruptcy", "Fire", "Geopolitical"
            ]),
            expected_severity=st.sampled_from(["Low", "Medium", "High", "Critical"]),
        ),
        min_size=1,
        max_size=5,
    ))
    @settings(max_examples=50, suppress_health_check=[HealthCheck.too_slow])
    def test_dataset_version_is_deterministic(self, examples: list[TrainingExample]):
        """
        Property: Same examples produce same version hash.

        Feature: chain-reaction
        Validates: Requirements 5.5
        """
        dataset1 = TrainingDataset(name="test", examples=examples)
        dataset2 = TrainingDataset(name="test", examples=examples)

        assert dataset1.version == dataset2.version

    @given(st.text(min_size=3, max_size=20))
    @settings(max_examples=50, suppress_health_check=[HealthCheck.too_slow])
    def test_dataset_name_preserved(self, name: str):
        """
        Property: Dataset name is preserved through creation.

        Feature: chain-reaction
        Validates: Requirements 5.5
        """
        # Filter out names with only whitespace
        if not name.strip():
            return

        dataset = TrainingDataset(name=name, examples=[])
        assert dataset.name == name

    def test_default_examples_are_valid(self):
        """
        Test: Default training examples have correct structure.

        Feature: chain-reaction
        Validates: Requirements 5.1, 5.4
        """
        manager = TrainingDataManager()
        examples = manager.create_default_examples()

        assert len(examples) >= 5  # Should have multiple examples

        for example in examples:
            assert len(example.news_content) > 0
            assert len(example.expected_location) > 0
            assert example.expected_event_type in [
                "Strike", "Weather", "Bankruptcy", "Fire",
                "Geopolitical", "CyberAttack", "Transport",
            ]
            assert example.expected_severity in ["Low", "Medium", "High", "Critical"]
