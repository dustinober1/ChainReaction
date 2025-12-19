"""
Impact Reporting.

Generates comprehensive impact reports for stakeholders with
timeline estimates and mitigation recommendations.
"""

from dataclasses import dataclass, field
from datetime import datetime, timezone, timedelta
from enum import Enum
from typing import Any
import json

from pydantic import BaseModel, Field
import structlog

from src.models import RiskEvent, SeverityLevel, ImpactAssessment

logger = structlog.get_logger(__name__)


class ReportFormat(str, Enum):
    """Available report output formats."""

    JSON = "json"
    MARKDOWN = "markdown"
    HTML = "html"


@dataclass
class TimelineEstimate:
    """Estimated timeline for risk impact and recovery."""

    impact_start: datetime
    peak_impact: datetime
    expected_resolution: datetime
    confidence: float  # 0-1
    notes: str = ""


@dataclass
class MitigationOption:
    """A mitigation option for addressing a risk."""

    title: str
    description: str
    estimated_cost: str  # Low, Medium, High
    time_to_implement: str  # e.g., "2-3 days"
    effectiveness: float  # 0-1
    priority: int


@dataclass
class AffectedProduct:
    """Details about an affected product."""

    product_id: str
    product_name: str
    impact_severity: str
    estimated_delay_days: int
    revenue_at_risk: float
    alternative_sources: int


@dataclass
class ImpactReport:
    """Comprehensive impact report for a risk event."""

    report_id: str
    risk_event_id: str
    generated_at: datetime
    title: str
    executive_summary: str
    timeline: TimelineEstimate
    affected_products: list[AffectedProduct]
    mitigation_options: list[MitigationOption]
    total_revenue_impact: float
    overall_severity: str
    recommendations: list[str]
    metadata: dict[str, Any] = field(default_factory=dict)


class ReportGenerator:
    """
    Generates comprehensive impact reports.

    Provides detailed reports for various stakeholder needs
    with multiple output format support.
    """

    def generate_report(
        self,
        risk: RiskEvent,
        impact: ImpactAssessment,
        product_data: dict[str, dict[str, Any]] | None = None,
    ) -> ImpactReport:
        """
        Generate a comprehensive impact report.

        Args:
            risk: The risk event to report on.
            impact: Impact assessment for the risk.
            product_data: Optional product metadata (name, revenue, etc).

        Returns:
            Complete ImpactReport.
        """
        report_id = f"RPT-{risk.id}"
        product_data = product_data or {}

        # Generate timeline estimate
        timeline = self._estimate_timeline(risk, impact)

        # Process affected products
        affected_products = self._process_affected_products(
            impact.affected_products,
            product_data,
            impact.severity_score,
        )

        # Generate mitigation options
        mitigations = self._generate_mitigations(risk, impact)

        # Calculate total revenue impact
        total_revenue = sum(p.revenue_at_risk for p in affected_products)

        # Generate executive summary
        summary = self._generate_executive_summary(risk, impact, len(affected_products))

        # Generate recommendations
        recommendations = self._generate_recommendations(risk, impact, mitigations)

        return ImpactReport(
            report_id=report_id,
            risk_event_id=risk.id,
            generated_at=datetime.now(timezone.utc),
            title=f"Impact Report: {risk.description[:50]}...",
            executive_summary=summary,
            timeline=timeline,
            affected_products=affected_products,
            mitigation_options=mitigations,
            total_revenue_impact=total_revenue,
            overall_severity=risk.severity.value,
            recommendations=recommendations,
            metadata={
                "confidence": risk.confidence,
                "impact_paths_count": len(impact.impact_paths),
                "redundancy_level": impact.redundancy_level,
            },
        )

    def _estimate_timeline(
        self,
        risk: RiskEvent,
        impact: ImpactAssessment,
    ) -> TimelineEstimate:
        """Estimate timeline based on risk severity and type."""
        now = datetime.now(timezone.utc)

        # Base durations by severity
        duration_map = {
            SeverityLevel.LOW: (1, 3, 7),
            SeverityLevel.MEDIUM: (2, 7, 21),
            SeverityLevel.HIGH: (3, 14, 45),
            SeverityLevel.CRITICAL: (1, 30, 90),
        }

        start_days, peak_days, resolution_days = duration_map.get(
            risk.severity, (2, 7, 21)
        )

        return TimelineEstimate(
            impact_start=now + timedelta(days=start_days),
            peak_impact=now + timedelta(days=peak_days),
            expected_resolution=now + timedelta(days=resolution_days),
            confidence=0.7 + (impact.redundancy_level * 0.3),
            notes=f"Based on {risk.event_type.value} event historical patterns",
        )

    def _process_affected_products(
        self,
        product_ids: list[str],
        product_data: dict[str, dict[str, Any]],
        severity_score: float,
    ) -> list[AffectedProduct]:
        """Process and enrich affected product data."""
        products = []

        for pid in product_ids:
            data = product_data.get(pid, {})
            products.append(
                AffectedProduct(
                    product_id=pid,
                    product_name=data.get("name", f"Product {pid}"),
                    impact_severity=self._score_to_severity(severity_score),
                    estimated_delay_days=int(severity_score * 14) + 1,
                    revenue_at_risk=data.get("revenue", 0.0),
                    alternative_sources=data.get("backup_suppliers", 0),
                )
            )

        return products

    def _generate_mitigations(
        self,
        risk: RiskEvent,
        impact: ImpactAssessment,
    ) -> list[MitigationOption]:
        """Generate mitigation options based on impact data."""
        mitigations = []

        # Always suggest monitoring
        mitigations.append(
            MitigationOption(
                title="Enhanced Monitoring",
                description="Increase monitoring frequency for affected suppliers",
                estimated_cost="Low",
                time_to_implement="Immediate",
                effectiveness=0.3,
                priority=1,
            )
        )

        # Add mitigation options from impact assessment
        for i, option in enumerate(impact.mitigation_options[:3]):
            mitigations.append(
                MitigationOption(
                    title=f"Mitigation {i+1}",
                    description=option,
                    estimated_cost="Medium" if i < 2 else "High",
                    time_to_implement=f"{(i+1)*2}-{(i+2)*2} days",
                    effectiveness=0.6 - (i * 0.1),
                    priority=i + 2,
                )
            )

        # Suggest backup supplier activation if available
        if impact.redundancy_level < 0.5:
            mitigations.append(
                MitigationOption(
                    title="Qualify Backup Suppliers",
                    description="Fast-track qualification of alternative suppliers",
                    estimated_cost="High",
                    time_to_implement="2-4 weeks",
                    effectiveness=0.8,
                    priority=len(mitigations) + 1,
                )
            )

        return mitigations

    def _generate_executive_summary(
        self,
        risk: RiskEvent,
        impact: ImpactAssessment,
        affected_count: int,
    ) -> str:
        """Generate executive summary paragraph."""
        return (
            f"A {risk.severity.value.lower()} severity {risk.event_type.value.lower()} "
            f"event has been detected at {risk.location}. This event affects "
            f"{affected_count} product(s) in the supply chain with an estimated severity "
            f"score of {impact.severity_score:.1f}/10. The current redundancy level is "
            f"{impact.redundancy_level:.0%}, which {'provides some protection' if impact.redundancy_level > 0.5 else 'indicates significant vulnerability'}. "
            f"Immediate attention is {'required' if risk.severity in [SeverityLevel.HIGH, SeverityLevel.CRITICAL] else 'recommended'}."
        )

    def _generate_recommendations(
        self,
        risk: RiskEvent,
        impact: ImpactAssessment,
        mitigations: list[MitigationOption],
    ) -> list[str]:
        """Generate prioritized recommendations."""
        recommendations = []

        # High priority actions
        if risk.severity in [SeverityLevel.HIGH, SeverityLevel.CRITICAL]:
            recommendations.append("Activate emergency response team")
            recommendations.append("Notify key stakeholders immediately")

        # Mitigation-based recommendations
        for m in mitigations[:3]:
            recommendations.append(f"{m.title}: {m.description}")

        # General recommendations
        recommendations.append("Continue monitoring for updates")
        recommendations.append("Document all actions taken for post-incident review")

        return recommendations

    def _score_to_severity(self, score: float) -> str:
        """Convert numeric score to severity label."""
        if score >= 8:
            return "Critical"
        elif score >= 6:
            return "High"
        elif score >= 4:
            return "Medium"
        else:
            return "Low"

    def export_json(self, report: ImpactReport) -> str:
        """Export report to JSON format."""
        def serialize(obj):
            if isinstance(obj, datetime):
                return obj.isoformat()
            if hasattr(obj, "__dict__"):
                return {k: serialize(v) for k, v in obj.__dict__.items()}
            if isinstance(obj, list):
                return [serialize(item) for item in obj]
            if isinstance(obj, dict):
                return {k: serialize(v) for k, v in obj.items()}
            return obj

        return json.dumps(serialize(report), indent=2)

    def export_markdown(self, report: ImpactReport) -> str:
        """Export report to Markdown format."""
        lines = [
            f"# {report.title}",
            "",
            f"**Report ID:** {report.report_id}",
            f"**Generated:** {report.generated_at.strftime('%Y-%m-%d %H:%M UTC')}",
            f"**Severity:** {report.overall_severity}",
            "",
            "## Executive Summary",
            "",
            report.executive_summary,
            "",
            "## Timeline",
            "",
            f"- **Impact Start:** {report.timeline.impact_start.strftime('%Y-%m-%d')}",
            f"- **Peak Impact:** {report.timeline.peak_impact.strftime('%Y-%m-%d')}",
            f"- **Expected Resolution:** {report.timeline.expected_resolution.strftime('%Y-%m-%d')}",
            f"- **Confidence:** {report.timeline.confidence:.0%}",
            "",
            "## Affected Products",
            "",
        ]

        for p in report.affected_products:
            lines.append(f"### {p.product_name}")
            lines.append(f"- **ID:** {p.product_id}")
            lines.append(f"- **Impact Severity:** {p.impact_severity}")
            lines.append(f"- **Estimated Delay:** {p.estimated_delay_days} days")
            lines.append(f"- **Revenue at Risk:** ${p.revenue_at_risk:,.2f}")
            lines.append("")

        lines.extend([
            "## Mitigation Options",
            "",
        ])

        for m in report.mitigation_options:
            lines.append(f"### {m.priority}. {m.title}")
            lines.append(f"- **Description:** {m.description}")
            lines.append(f"- **Cost:** {m.estimated_cost}")
            lines.append(f"- **Time:** {m.time_to_implement}")
            lines.append(f"- **Effectiveness:** {m.effectiveness:.0%}")
            lines.append("")

        lines.extend([
            "## Recommendations",
            "",
        ])
        for r in report.recommendations:
            lines.append(f"- {r}")

        return "\n".join(lines)
