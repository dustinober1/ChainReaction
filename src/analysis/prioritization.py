"""
Risk Prioritization and Scoring.

Provides algorithms for prioritizing and ranking supply chain risks
based on severity, timeline, and business impact.
"""

from dataclasses import dataclass, field
from datetime import datetime, timezone, timedelta
from enum import Enum
from typing import Any

from pydantic import BaseModel, Field
import structlog

from src.models import RiskEvent, SeverityLevel, ImpactAssessment

logger = structlog.get_logger(__name__)


class PriorityFactor(str, Enum):
    """Factors used in risk prioritization."""

    SEVERITY = "severity"
    TIMELINE = "timeline"
    PRODUCTS_AFFECTED = "products_affected"
    REVENUE_IMPACT = "revenue_impact"
    CONFIDENCE = "confidence"


@dataclass
class PriorityWeights:
    """Configurable weights for priority calculation."""

    severity: float = 0.30
    timeline: float = 0.20
    products_affected: float = 0.25
    revenue_impact: float = 0.15
    confidence: float = 0.10

    def validate(self) -> bool:
        """Validate that weights sum to 1.0."""
        total = (
            self.severity
            + self.timeline
            + self.products_affected
            + self.revenue_impact
            + self.confidence
        )
        return 0.99 <= total <= 1.01


@dataclass
class PrioritizedRisk:
    """A risk event with calculated priority score."""

    risk_event: RiskEvent
    priority_score: float
    priority_rank: int
    severity_score: float
    timeline_score: float
    impact_score: float
    factors: dict[str, float] = field(default_factory=dict)


class RiskPrioritizer:
    """
    Calculates priority scores for risk events.

    Provides multi-criteria prioritization with configurable weights
    and risk aggregation for products with multiple threats.
    """

    # Severity level to score mapping
    SEVERITY_SCORES = {
        SeverityLevel.LOW: 0.25,
        SeverityLevel.MEDIUM: 0.50,
        SeverityLevel.HIGH: 0.75,
        SeverityLevel.CRITICAL: 1.0,
    }

    def __init__(self, weights: PriorityWeights | None = None):
        """Initialize the prioritizer with optional custom weights."""
        self.weights = weights or PriorityWeights()
        if not self.weights.validate():
            raise ValueError("Priority weights must sum to 1.0")

    def calculate_priority(
        self,
        risk: RiskEvent,
        impact: ImpactAssessment | None = None,
        revenue_data: dict[str, float] | None = None,
    ) -> PrioritizedRisk:
        """
        Calculate priority score for a single risk event.

        Args:
            risk: The risk event to prioritize.
            impact: Optional impact assessment data.
            revenue_data: Optional revenue impact by product ID.

        Returns:
            PrioritizedRisk with calculated scores.
        """
        factors = {}

        # Severity score
        severity_score = self.SEVERITY_SCORES.get(risk.severity, 0.5)
        factors["severity"] = severity_score

        # Timeline score (more recent = higher priority)
        timeline_score = self._calculate_timeline_score(risk.detected_at)
        factors["timeline"] = timeline_score

        # Products affected score
        products_count = 0
        if impact:
            products_count = len(impact.affected_products)
        elif risk.affected_entities:
            products_count = len(risk.affected_entities)

        products_score = min(products_count / 10, 1.0)  # Normalize to max 10 products
        factors["products_affected"] = products_score

        # Revenue impact score
        revenue_score = 0.0
        if revenue_data and impact:
            total_revenue = sum(
                revenue_data.get(pid, 0) for pid in impact.affected_products
            )
            revenue_score = min(total_revenue / 1_000_000, 1.0)  # Normalize to 1M
        factors["revenue_impact"] = revenue_score

        # Confidence score
        confidence_score = risk.confidence
        factors["confidence"] = confidence_score

        # Calculate weighted priority
        priority_score = (
            factors["severity"] * self.weights.severity
            + factors["timeline"] * self.weights.timeline
            + factors["products_affected"] * self.weights.products_affected
            + factors["revenue_impact"] * self.weights.revenue_impact
            + factors["confidence"] * self.weights.confidence
        )

        return PrioritizedRisk(
            risk_event=risk,
            priority_score=priority_score,
            priority_rank=0,  # Set during batch prioritization
            severity_score=severity_score,
            timeline_score=timeline_score,
            impact_score=products_score,
            factors=factors,
        )

    def prioritize_risks(
        self,
        risks: list[RiskEvent],
        impacts: dict[str, ImpactAssessment] | None = None,
        revenue_data: dict[str, float] | None = None,
    ) -> list[PrioritizedRisk]:
        """
        Prioritize a list of risk events.

        Args:
            risks: List of risk events to prioritize.
            impacts: Optional dict mapping risk ID to impact assessment.
            revenue_data: Optional revenue data by product ID.

        Returns:
            List of PrioritizedRisk sorted by priority (highest first).
        """
        if not risks:
            return []

        prioritized = []
        for risk in risks:
            impact = impacts.get(risk.id) if impacts else None
            p_risk = self.calculate_priority(risk, impact, revenue_data)
            prioritized.append(p_risk)

        # Sort by priority score descending
        prioritized.sort(key=lambda x: x.priority_score, reverse=True)

        # Assign ranks
        for i, p_risk in enumerate(prioritized):
            p_risk.priority_rank = i + 1

        return prioritized

    def _calculate_timeline_score(self, detected_at: datetime) -> float:
        """Calculate timeline score based on recency."""
        now = datetime.now(timezone.utc)
        age = now - detected_at

        # More recent = higher score
        if age < timedelta(hours=1):
            return 1.0
        elif age < timedelta(hours=24):
            return 0.9
        elif age < timedelta(days=7):
            return 0.7
        elif age < timedelta(days=30):
            return 0.5
        else:
            return 0.3

    def aggregate_product_risks(
        self,
        prioritized_risks: list[PrioritizedRisk],
    ) -> dict[str, float]:
        """
        Aggregate risk scores for products with multiple threats.

        Args:
            prioritized_risks: List of prioritized risks.

        Returns:
            Dict mapping product ID to aggregated risk score.
        """
        product_scores: dict[str, list[float]] = {}

        for p_risk in prioritized_risks:
            for entity in p_risk.risk_event.affected_entities:
                if entity not in product_scores:
                    product_scores[entity] = []
                product_scores[entity].append(p_risk.priority_score)

        # Aggregate using max + 10% of others
        aggregated = {}
        for product_id, scores in product_scores.items():
            if not scores:
                continue
            scores.sort(reverse=True)
            max_score = scores[0]
            other_contribution = sum(scores[1:]) * 0.1
            aggregated[product_id] = min(max_score + other_contribution, 1.0)

        return aggregated

    def get_no_risk_response(self) -> dict[str, Any]:
        """
        Get a response for when no risks are found.

        Returns:
            Response dict confirming stable supply chain.
        """
        return {
            "status": "stable",
            "message": "No active supply chain risks detected",
            "risk_count": 0,
            "last_checked": datetime.now(timezone.utc).isoformat(),
            "recommendations": [
                "Continue normal monitoring",
                "Review backup supplier qualifications",
                "Update risk thresholds if needed",
            ],
        }


def sort_by_severity(risks: list[RiskEvent]) -> list[RiskEvent]:
    """Sort risks by severity (highest first)."""
    severity_order = {
        SeverityLevel.CRITICAL: 4,
        SeverityLevel.HIGH: 3,
        SeverityLevel.MEDIUM: 2,
        SeverityLevel.LOW: 1,
    }
    return sorted(
        risks,
        key=lambda r: severity_order.get(r.severity, 0),
        reverse=True,
    )


def sort_by_timeline(risks: list[RiskEvent]) -> list[RiskEvent]:
    """Sort risks by detection time (most recent first)."""
    return sorted(risks, key=lambda r: r.detected_at, reverse=True)


def sort_by_affected_count(
    risks: list[RiskEvent],
    impacts: dict[str, ImpactAssessment],
) -> list[RiskEvent]:
    """Sort risks by number of affected products (highest first)."""
    def get_affected_count(risk: RiskEvent) -> int:
        if risk.id in impacts:
            return len(impacts[risk.id].affected_products)
        return len(risk.affected_entities)

    return sorted(risks, key=get_affected_count, reverse=True)
