"""
Validation and Confidence Scoring for Risk Extraction.

Provides utilities for validating extracted risk data, checking confidence
thresholds, and handling extraction failures gracefully.
"""

from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Any
import re

import structlog

from src.models import RiskEvent, EventType, SeverityLevel

logger = structlog.get_logger(__name__)


@dataclass
class ValidationResult:
    """Result of validating an extracted risk event."""

    is_valid: bool
    errors: list[str]
    warnings: list[str]
    confidence_adjusted: float
    original_confidence: float


class ExtractionValidator:
    """
    Validates extracted risk events and adjusts confidence scores.

    Performs checks for:
    - Required field presence
    - Field value validity
    - Content plausibility
    - Confidence threshold compliance
    """

    def __init__(
        self,
        confidence_threshold: float = 0.7,
        min_description_length: int = 10,
    ):
        """
        Initialize the validator.

        Args:
            confidence_threshold: Minimum confidence for an event to be accepted.
            min_description_length: Minimum length for event descriptions.
        """
        self.confidence_threshold = confidence_threshold
        self.min_description_length = min_description_length

        # Known valid locations for validation
        self.known_locations = {
            "taiwan", "vietnam", "california", "germany", "south korea",
            "japan", "china", "mexico", "india", "thailand", "malaysia",
            "indonesia", "philippines", "singapore", "united states",
            "shenzhen", "shanghai", "munich", "seoul", "tokyo", "israel",
        }

    def validate(self, event: RiskEvent) -> ValidationResult:
        """
        Validate a RiskEvent and return validation result.

        Args:
            event: The RiskEvent to validate.

        Returns:
            ValidationResult with validation status and details.
        """
        errors = []
        warnings = []
        confidence_adjustment = 0.0

        # Check required fields
        if not event.id:
            errors.append("Missing event ID")

        if not event.location or event.location.lower() in ("unknown", "unspecified", ""):
            warnings.append("Location not identified")
            confidence_adjustment -= 0.1

        if not event.description or len(event.description) < self.min_description_length:
            warnings.append("Description too short or missing")
            confidence_adjustment -= 0.05

        if not event.affected_entities:
            warnings.append("No affected entities identified")
            confidence_adjustment -= 0.05

        # Validate location if provided
        if event.location and event.location.lower() not in self.known_locations:
            # Not in known list - could be valid but unrecognized
            if not self._looks_like_location(event.location):
                warnings.append(f"Unrecognized location format: {event.location}")
                confidence_adjustment -= 0.05

        # Check for suspicious patterns in extraction
        if self._has_suspicious_patterns(event):
            warnings.append("Extraction may contain hallucinated content")
            confidence_adjustment -= 0.15

        # Calculate adjusted confidence
        original_confidence = event.confidence
        adjusted_confidence = max(0.0, min(1.0, original_confidence + confidence_adjustment))

        # Determine overall validity
        is_valid = (
            len(errors) == 0
            and adjusted_confidence >= self.confidence_threshold
        )

        return ValidationResult(
            is_valid=is_valid,
            errors=errors,
            warnings=warnings,
            confidence_adjusted=round(adjusted_confidence, 3),
            original_confidence=original_confidence,
        )

    def _looks_like_location(self, location: str) -> bool:
        """Check if a string looks like a valid location name."""
        # Should be mostly letters and spaces, possibly with some punctuation
        if not location:
            return False

        # Check if it's mostly alphabetic
        alpha_ratio = sum(c.isalpha() for c in location) / len(location)
        return alpha_ratio > 0.7

    def _has_suspicious_patterns(self, event: RiskEvent) -> bool:
        """Check for patterns that suggest hallucinated content."""
        suspicious_patterns = [
            r"as an ai",
            r"i cannot",
            r"i'm unable",
            r"hypothetical",
            r"example scenario",
            r"no actual",
            r"this is not real",
        ]

        text_to_check = f"{event.description} {event.location}".lower()

        for pattern in suspicious_patterns:
            if re.search(pattern, text_to_check):
                return True

        return False

    def validate_batch(self, events: list[RiskEvent]) -> list[tuple[RiskEvent, ValidationResult]]:
        """
        Validate a batch of events.

        Args:
            events: List of RiskEvents to validate.

        Returns:
            List of (event, validation_result) tuples.
        """
        return [(event, self.validate(event)) for event in events]


class ConfidenceScorer:
    """
    Calculates and adjusts confidence scores based on multiple factors.

    Considers:
    - Source reliability
    - Content clarity
    - Entity recognition success
    - Historical accuracy (if available)
    """

    def __init__(self):
        """Initialize the confidence scorer."""
        # Source reliability scores (0-1)
        self.source_reliability = {
            "reuters": 0.95,
            "bloomberg": 0.95,
            "wsj": 0.90,
            "bbc": 0.90,
            "cnn": 0.85,
            "default": 0.7,
        }

    def calculate_confidence(
        self,
        base_confidence: float,
        source_url: str = "",
        entity_count: int = 0,
        location_recognized: bool = False,
        event_type_clear: bool = True,
    ) -> float:
        """
        Calculate adjusted confidence score.

        Args:
            base_confidence: Initial confidence from extraction.
            source_url: URL of the source for reliability scoring.
            entity_count: Number of entities extracted.
            location_recognized: Whether location was successfully identified.
            event_type_clear: Whether event type was clearly identified.

        Returns:
            Adjusted confidence score (0-1).
        """
        score = base_confidence

        # Adjust for source reliability
        source_factor = self._get_source_reliability(source_url)
        score *= source_factor

        # Bonus for multiple entities identified
        if entity_count >= 2:
            score = min(1.0, score + 0.05)
        elif entity_count == 0:
            score = max(0.0, score - 0.1)

        # Penalty for unrecognized location
        if not location_recognized:
            score = max(0.0, score - 0.1)

        # Penalty for unclear event type
        if not event_type_clear:
            score = max(0.0, score - 0.1)

        return round(max(0.0, min(1.0, score)), 3)

    def _get_source_reliability(self, url: str) -> float:
        """Get reliability score for a source URL."""
        url_lower = url.lower()

        for source, reliability in self.source_reliability.items():
            if source in url_lower:
                return reliability

        return self.source_reliability["default"]


class ExtractionErrorHandler:
    """
    Handles errors during the extraction pipeline.

    Provides graceful degradation and logging for failed extractions.
    """

    def __init__(self, max_retries: int = 3):
        """
        Initialize the error handler.

        Args:
            max_retries: Maximum number of retry attempts for transient failures.
        """
        self.max_retries = max_retries
        self.error_log: list[dict[str, Any]] = []

    def log_error(
        self,
        error: Exception,
        source_url: str = "",
        content_snippet: str = "",
        recoverable: bool = True,
    ) -> dict[str, Any]:
        """
        Log an extraction error.

        Args:
            error: The exception that occurred.
            source_url: URL of the source being processed.
            content_snippet: First 200 chars of content for debugging.
            recoverable: Whether the pipeline can continue.

        Returns:
            Error log entry.
        """
        entry = {
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "error_type": type(error).__name__,
            "message": str(error),
            "source_url": source_url,
            "content_snippet": content_snippet[:200] if content_snippet else "",
            "recoverable": recoverable,
        }

        self.error_log.append(entry)
        logger.error(
            "Extraction error",
            error_type=entry["error_type"],
            message=entry["message"],
            source_url=source_url,
            recoverable=recoverable,
        )

        return entry

    def should_retry(self, error: Exception, attempt: int) -> bool:
        """
        Determine if an operation should be retried.

        Args:
            error: The exception that occurred.
            attempt: Current attempt number (1-indexed).

        Returns:
            True if the operation should be retried.
        """
        if attempt >= self.max_retries:
            return False

        # Retry for transient errors
        transient_error_types = (
            ConnectionError,
            TimeoutError,
        )

        return isinstance(error, transient_error_types)

    def create_fallback_event(
        self,
        source_url: str,
        content_snippet: str,
        error_message: str,
    ) -> RiskEvent:
        """
        Create a fallback RiskEvent for failed extractions.

        This ensures the pipeline continues even when extraction fails.

        Args:
            source_url: URL of the source.
            content_snippet: Beginning of the content.
            error_message: The error that caused the fallback.

        Returns:
            A RiskEvent marked with low confidence.
        """
        import uuid

        return RiskEvent(
            id=f"RISK-FALLBACK-{uuid.uuid4().hex[:8].upper()}",
            event_type=EventType.OTHER,
            location="Unknown",
            affected_entities=[],
            severity=SeverityLevel.LOW,
            confidence=0.1,  # Very low confidence for fallback events
            source_url=source_url,
            description=f"[Extraction failed: {error_message}] {content_snippet[:100]}...",
        )

    def get_error_summary(self) -> dict[str, Any]:
        """Get summary of logged errors."""
        if not self.error_log:
            return {"total_errors": 0, "by_type": {}}

        by_type: dict[str, int] = {}
        for entry in self.error_log:
            error_type = entry["error_type"]
            by_type[error_type] = by_type.get(error_type, 0) + 1

        return {
            "total_errors": len(self.error_log),
            "by_type": by_type,
            "recoverable_count": sum(1 for e in self.error_log if e["recoverable"]),
            "recent_errors": self.error_log[-5:],
        }

    def clear_log(self) -> None:
        """Clear the error log."""
        self.error_log = []
