"""
Unit tests for the DSPy analysis module.
"""

import pytest
import tempfile
from pathlib import Path

from src.analysis.validation import (
    ExtractionValidator,
    ConfidenceScorer,
    ExtractionErrorHandler,
)
from src.analysis.training import (
    TrainingExample,
    TrainingDataset,
    TrainingDataManager,
)
from src.models import RiskEvent, EventType, SeverityLevel


class TestExtractionValidator:
    """Tests for the ExtractionValidator class."""

    def test_valid_event_passes_validation(self):
        """Test that a complete, valid event passes validation."""
        event = RiskEvent(
            id="RISK-001",
            event_type=EventType.WEATHER,
            location="Taiwan",
            affected_entities=["TSMC", "MediaTek"],
            severity=SeverityLevel.HIGH,
            confidence=0.9,
            source_url="https://example.com/news",
            description="Major typhoon causes factory shutdowns across Taiwan.",
        )

        validator = ExtractionValidator(confidence_threshold=0.7)
        result = validator.validate(event)

        assert result.is_valid is True
        assert len(result.errors) == 0

    def test_low_confidence_fails_validation(self):
        """Test that events with low confidence fail validation."""
        event = RiskEvent(
            id="RISK-002",
            event_type=EventType.STRIKE,
            location="California",
            affected_entities=["Port Workers"],
            severity=SeverityLevel.MEDIUM,
            confidence=0.3,
            source_url="https://example.com/news",
            description="Possible strike action being discussed.",
        )

        validator = ExtractionValidator(confidence_threshold=0.7)
        result = validator.validate(event)

        assert result.is_valid is False

    def test_unknown_location_adds_warning(self):
        """Test that unknown location generates a warning."""
        event = RiskEvent(
            id="RISK-003",
            event_type=EventType.FIRE,
            location="Unknown",
            affected_entities=["Factory A"],
            severity=SeverityLevel.HIGH,
            confidence=0.9,
            source_url="https://example.com/news",
            description="Fire at manufacturing facility.",
        )

        validator = ExtractionValidator()
        result = validator.validate(event)

        assert any("location" in w.lower() for w in result.warnings)

    def test_suspicious_pattern_lowers_confidence(self):
        """Test that suspicious patterns lower confidence."""
        event = RiskEvent(
            id="RISK-004",
            event_type=EventType.OTHER,
            location="Test City",
            affected_entities=[],
            severity=SeverityLevel.LOW,
            confidence=0.9,
            source_url="https://example.com",
            description="As an AI, I cannot provide real information.",
        )

        validator = ExtractionValidator()
        result = validator.validate(event)

        assert result.confidence_adjusted < result.original_confidence
        assert any("hallucinated" in w.lower() for w in result.warnings)

    def test_batch_validation(self):
        """Test batch validation of multiple events."""
        events = [
            RiskEvent(
                id=f"RISK-{i:03d}",
                event_type=EventType.WEATHER,
                location="Taiwan",
                affected_entities=["Company"],
                severity=SeverityLevel.MEDIUM,
                confidence=0.8,
                source_url="https://test.com",
                description="Test event",
            )
            for i in range(5)
        ]

        validator = ExtractionValidator()
        results = validator.validate_batch(events)

        assert len(results) == 5
        assert all(isinstance(r[1].is_valid, bool) for r in results)


class TestConfidenceScorer:
    """Tests for the ConfidenceScorer class."""

    def test_reliable_source_increases_confidence(self):
        """Test that reliable sources get higher confidence."""
        scorer = ConfidenceScorer()

        reuters_score = scorer.calculate_confidence(
            base_confidence=0.7,
            source_url="https://reuters.com/article",
            entity_count=2,
            location_recognized=True,
            event_type_clear=True,
        )

        unknown_score = scorer.calculate_confidence(
            base_confidence=0.7,
            source_url="https://unknown-blog.com/post",
            entity_count=2,
            location_recognized=True,
            event_type_clear=True,
        )

        assert reuters_score > unknown_score

    def test_multiple_entities_increases_confidence(self):
        """Test that multiple entities increase confidence."""
        scorer = ConfidenceScorer()

        multi_entity = scorer.calculate_confidence(
            base_confidence=0.7,
            entity_count=3,
            location_recognized=True,
            event_type_clear=True,
        )

        single_entity = scorer.calculate_confidence(
            base_confidence=0.7,
            entity_count=1,
            location_recognized=True,
            event_type_clear=True,
        )

        assert multi_entity >= single_entity

    def test_unrecognized_location_decreases_confidence(self):
        """Test that unrecognized location decreases confidence."""
        scorer = ConfidenceScorer()

        recognized = scorer.calculate_confidence(
            base_confidence=0.7,
            location_recognized=True,
        )

        unrecognized = scorer.calculate_confidence(
            base_confidence=0.7,
            location_recognized=False,
        )

        assert recognized > unrecognized


class TestExtractionErrorHandler:
    """Tests for the ExtractionErrorHandler class."""

    def test_error_logging(self):
        """Test that errors are properly logged."""
        handler = ExtractionErrorHandler()

        handler.log_error(
            ValueError("Test error"),
            source_url="https://test.com",
            content_snippet="Some content...",
        )

        summary = handler.get_error_summary()

        assert summary["total_errors"] == 1
        assert "ValueError" in summary["by_type"]

    def test_fallback_event_creation(self):
        """Test that fallback events are created correctly."""
        handler = ExtractionErrorHandler()

        fallback = handler.create_fallback_event(
            source_url="https://test.com/article",
            content_snippet="Breaking news about supply chain disruption...",
            error_message="Extraction timeout",
        )

        assert fallback.id.startswith("RISK-FALLBACK-")
        assert fallback.confidence == 0.1
        assert fallback.event_type == EventType.OTHER
        assert "Extraction failed" in fallback.description

    def test_retry_logic_for_transient_errors(self):
        """Test retry logic for different error types."""
        handler = ExtractionErrorHandler(max_retries=3)

        # Connection errors should retry
        assert handler.should_retry(ConnectionError("Network issue"), attempt=1)
        assert handler.should_retry(ConnectionError("Network issue"), attempt=2)
        assert not handler.should_retry(ConnectionError("Network issue"), attempt=3)

        # Value errors should not retry
        assert not handler.should_retry(ValueError("Bad data"), attempt=1)

    def test_error_log_clear(self):
        """Test clearing the error log."""
        handler = ExtractionErrorHandler()

        handler.log_error(ValueError("Error 1"))
        handler.log_error(TypeError("Error 2"))

        assert handler.get_error_summary()["total_errors"] == 2

        handler.clear_log()

        assert handler.get_error_summary()["total_errors"] == 0


class TestTrainingDataManager:
    """Tests for the TrainingDataManager class."""

    def test_create_default_examples(self):
        """Test that default examples are created correctly."""
        manager = TrainingDataManager()
        examples = manager.create_default_examples()

        assert len(examples) > 0
        for example in examples:
            assert example.news_content
            assert example.expected_location
            assert example.expected_event_type

    def test_dataset_versioning(self):
        """Test that dataset versions are computed correctly."""
        examples = [
            TrainingExample(
                news_content="Test content",
                expected_location="Test Location",
                expected_company="Test Company",
                expected_event_type="Strike",
                expected_severity="High",
            )
        ]

        dataset1 = TrainingDataset(name="test", examples=examples)
        dataset2 = TrainingDataset(name="test", examples=examples)

        # Same examples should produce same version
        assert dataset1.version == dataset2.version

    def test_dataset_save_and_load(self):
        """Test saving and loading datasets."""
        with tempfile.TemporaryDirectory() as tmpdir:
            manager = TrainingDataManager(data_dir=tmpdir)

            examples = manager.create_default_examples()[:3]
            dataset = TrainingDataset(
                name="test_dataset",
                examples=examples,
                description="Test dataset for unit testing",
            )

            # Save
            filepath = manager.save_dataset(dataset)
            assert filepath.exists()

            # Load
            loaded = manager.load_dataset(filepath)

            assert loaded.name == dataset.name
            assert loaded.version == dataset.version
            assert len(loaded.examples) == len(dataset.examples)

    def test_needs_recompilation(self):
        """Test recompilation detection."""
        with tempfile.TemporaryDirectory() as tmpdir:
            manager = TrainingDataManager(data_dir=tmpdir)

            examples = [
                TrainingExample(
                    news_content="Test",
                    expected_location="Location",
                    expected_company="Company",
                    expected_event_type="Strike",
                    expected_severity="High",
                )
            ]

            dataset = TrainingDataset(name="test", examples=examples)

            # No previous version, should need compilation
            assert manager.needs_recompilation(dataset)

            # Save dataset
            manager.save_dataset(dataset)

            # Same version, should not need recompilation
            assert not manager.needs_recompilation(dataset)

            # New version should need recompilation
            new_examples = examples + [
                TrainingExample(
                    news_content="New content",
                    expected_location="New Location",
                    expected_company="New Company",
                    expected_event_type="Fire",
                    expected_severity="Medium",
                )
            ]
            new_dataset = TrainingDataset(name="test", examples=new_examples)

            assert manager.needs_recompilation(new_dataset)

    def test_convert_to_dspy_examples(self):
        """Test conversion to DSPy format."""
        manager = TrainingDataManager()

        examples = [
            TrainingExample(
                news_content="Port strike in LA",
                expected_location="Los Angeles",
                expected_company="Port of LA",
                expected_event_type="Strike",
                expected_severity="High",
                expected_summary="Port workers strike affects shipping",
            )
        ]

        dataset = TrainingDataset(name="test", examples=examples)
        dspy_examples = manager.convert_to_dspy_examples(dataset)

        assert len(dspy_examples) == 1
        assert dspy_examples[0]["news_content"] == "Port strike in LA"
        assert dspy_examples[0]["location"] == "Los Angeles"
        assert dspy_examples[0]["event_type"] == "Strike"

    def test_performance_tracking(self):
        """Test performance metrics recording."""
        manager = TrainingDataManager()

        manager.record_performance(
            dataset_version="v1",
            accuracy=0.85,
            extraction_count=100,
            avg_confidence=0.88,
        )

        manager.record_performance(
            dataset_version="v2",
            accuracy=0.90,
            extraction_count=150,
            avg_confidence=0.91,
        )

        trend = manager.get_performance_trend()

        assert len(trend) == 2
        assert trend[0]["version"] == "v1"
        assert trend[1]["version"] == "v2"
        assert trend[1]["accuracy"] > trend[0]["accuracy"]
