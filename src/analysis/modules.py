"""
DSPy Modules for Supply Chain Risk Analysis.

Implements the risk extraction and analysis pipeline using DSPy's
optimizable modules with Chain of Thought reasoning.
"""

from datetime import datetime, timezone
from typing import Any
import uuid

import dspy
import structlog

from src.analysis.signatures import RiskExtractor, EntityExtractor, ImpactAssessor
from src.models import RiskEvent, EventType, SeverityLevel

logger = structlog.get_logger(__name__)


class RiskAnalyst(dspy.Module):
    """
    DSPy module for extracting structured risk data from news content.

    Uses Chain of Thought reasoning to improve extraction accuracy
    and can be compiled with training examples for optimization.
    """

    def __init__(self):
        """Initialize the RiskAnalyst module."""
        super().__init__()
        self.extractor = dspy.ChainOfThought(RiskExtractor)

    def forward(self, news_content: str) -> dspy.Prediction:
        """
        Extract risk information from news content.

        Args:
            news_content: The text content of a news article.

        Returns:
            dspy.Prediction with extracted risk fields.
        """
        return self.extractor(news_content=news_content)

    def extract_to_model(
        self,
        news_content: str,
        source_url: str = "unknown",
    ) -> tuple[RiskEvent | None, dict[str, Any]]:
        """
        Extract risk information and convert to RiskEvent model.

        Args:
            news_content: The text content of a news article.
            source_url: URL of the source article.

        Returns:
            Tuple of (RiskEvent or None if extraction failed, metadata dict)
        """
        metadata = {
            "extraction_time": datetime.now(timezone.utc).isoformat(),
            "raw_output": None,
            "validation_errors": [],
            "success": False,
        }

        try:
            # Run extraction
            result = self.forward(news_content)
            metadata["raw_output"] = {
                "location": result.location,
                "company": result.company,
                "event_type": result.event_type,
                "severity": result.severity,
                "confidence": result.confidence,
                "summary": result.summary,
            }

            # Parse and validate event type
            event_type = self._parse_event_type(result.event_type)
            if event_type is None:
                metadata["validation_errors"].append(
                    f"Invalid event_type: {result.event_type}"
                )
                event_type = EventType.OTHER

            # Parse and validate severity
            severity = self._parse_severity(result.severity)
            if severity is None:
                metadata["validation_errors"].append(
                    f"Invalid severity: {result.severity}"
                )
                severity = SeverityLevel.MEDIUM

            # Parse confidence
            confidence = self._parse_confidence(result.confidence)
            if confidence is None:
                metadata["validation_errors"].append(
                    f"Invalid confidence: {result.confidence}"
                )
                confidence = 0.5

            # Parse affected entities
            affected_entities = []
            if result.company and result.company.lower() != "unknown":
                affected_entities = [
                    e.strip() for e in result.company.split(",") if e.strip()
                ]

            # Create RiskEvent
            risk_event = RiskEvent(
                id=f"RISK-{uuid.uuid4().hex[:8].upper()}",
                event_type=event_type,
                location=result.location if result.location.lower() != "unknown" else "Unspecified",
                affected_entities=affected_entities,
                severity=severity,
                confidence=confidence,
                source_url=source_url,
                description=result.summary,
            )

            metadata["success"] = True
            return risk_event, metadata

        except Exception as e:
            logger.error("Extraction failed", error=str(e))
            metadata["validation_errors"].append(f"Extraction error: {str(e)}")
            return None, metadata

    def _parse_event_type(self, value: str) -> EventType | None:
        """Parse event type string to enum."""
        value_normalized = value.strip().lower().replace(" ", "").replace("_", "")

        mapping = {
            "strike": EventType.STRIKE,
            "weather": EventType.WEATHER,
            "bankruptcy": EventType.BANKRUPTCY,
            "geopolitical": EventType.GEOPOLITICAL,
            "fire": EventType.FIRE,
            "pandemic": EventType.PANDEMIC,
            "cyberattack": EventType.CYBER_ATTACK,
            "cyber": EventType.CYBER_ATTACK,
            "transport": EventType.TRANSPORT,
            "transportation": EventType.TRANSPORT,
            "logistics": EventType.TRANSPORT,
            "other": EventType.OTHER,
        }

        return mapping.get(value_normalized)

    def _parse_severity(self, value: str) -> SeverityLevel | None:
        """Parse severity string to enum."""
        value_normalized = value.strip().lower()

        mapping = {
            "low": SeverityLevel.LOW,
            "medium": SeverityLevel.MEDIUM,
            "high": SeverityLevel.HIGH,
            "critical": SeverityLevel.CRITICAL,
        }

        return mapping.get(value_normalized)

    def _parse_confidence(self, value: str) -> float | None:
        """Parse confidence string to float."""
        try:
            # Handle various formats: "0.85", "85%", "0.85 (high)"
            value_clean = value.strip().split()[0].replace("%", "")
            conf = float(value_clean)

            # If given as percentage, convert to decimal
            if conf > 1.0:
                conf = conf / 100.0

            return max(0.0, min(1.0, conf))
        except (ValueError, IndexError):
            return None


class EntityAnalyst(dspy.Module):
    """
    DSPy module for extracting named entities from text.

    Useful for pre-processing text to identify relevant supply chain entities.
    """

    def __init__(self):
        """Initialize the EntityAnalyst module."""
        super().__init__()
        self.extractor = dspy.ChainOfThought(EntityExtractor)

    def forward(self, text: str) -> dspy.Prediction:
        """Extract entities from text."""
        return self.extractor(text=text)

    def extract_entities(self, text: str) -> dict[str, list[str]]:
        """
        Extract entities and return as structured dict.

        Args:
            text: Text to extract entities from.

        Returns:
            Dict with 'companies', 'locations', and 'products' lists.
        """
        try:
            result = self.forward(text)

            def parse_list(value: str) -> list[str]:
                if not value or value.lower() == "none":
                    return []
                return [item.strip() for item in value.split(",") if item.strip()]

            return {
                "companies": parse_list(result.companies),
                "locations": parse_list(result.locations),
                "products": parse_list(result.products),
            }
        except Exception as e:
            logger.error("Entity extraction failed", error=str(e))
            return {"companies": [], "locations": [], "products": []}


class ImpactAnalyst(dspy.Module):
    """
    DSPy module for assessing supply chain impact of risk events.

    Takes extracted risk information and supply chain context to
    assess downstream impacts and suggest mitigations.
    """

    def __init__(self):
        """Initialize the ImpactAnalyst module."""
        super().__init__()
        self.assessor = dspy.ChainOfThought(ImpactAssessor)

    def forward(
        self,
        event_description: str,
        affected_entities: str,
        supply_chain_context: str,
    ) -> dspy.Prediction:
        """Assess impact of a risk event."""
        return self.assessor(
            event_description=event_description,
            affected_entities=affected_entities,
            supply_chain_context=supply_chain_context,
        )

    def assess_impact(
        self,
        risk_event: RiskEvent,
        supply_chain_context: str = "",
    ) -> dict[str, Any]:
        """
        Assess the impact of a RiskEvent.

        Args:
            risk_event: The risk event to assess.
            supply_chain_context: Description of relevant supply chain relationships.

        Returns:
            Dict with impact assessment, timeline, and mitigation suggestions.
        """
        event_description = (
            f"{risk_event.event_type.value} event in {risk_event.location}: "
            f"{risk_event.description}"
        )
        affected_entities = ", ".join(risk_event.affected_entities) or "Unknown"

        try:
            result = self.forward(
                event_description=event_description,
                affected_entities=affected_entities,
                supply_chain_context=supply_chain_context or "No specific context provided",
            )

            return {
                "impact_assessment": result.impact_assessment,
                "timeline_estimate": result.timeline_estimate,
                "mitigation_suggestions": result.mitigation_suggestions,
                "success": True,
            }
        except Exception as e:
            logger.error("Impact assessment failed", error=str(e))
            return {
                "impact_assessment": "Assessment failed",
                "timeline_estimate": "Unknown",
                "mitigation_suggestions": "Unable to generate suggestions",
                "success": False,
                "error": str(e),
            }
