"""
LangGraph Workflow Nodes for Supply Chain Risk Processing.

Implements the individual processing nodes for the risk monitoring
workflow: monitor, extract, validate, analyze, and alert.
"""

from datetime import datetime, timezone
from typing import Any
import asyncio
import uuid

import structlog

from src.agents.state import AgentState, WorkflowConfig
from src.agents.scout import ScoutAgent, MonitoringConfig, MonitoringEvent
from src.agents.sources import NewsArticle
from src.analysis.modules import RiskAnalyst
from src.analysis.validation import (
    ExtractionValidator,
    ExtractionErrorHandler,
    ConfidenceScorer,
)
from src.graph.impact import ImpactCalculator, RiskAssessor, InMemoryGraph
from src.graph.traversal import GraphNode, GraphEdge
from src.models import (
    RawEvent,
    RiskEvent,
    Alert,
    ImpactAssessment,
    ProcessingError,
    EventType,
    SeverityLevel,
)

logger = structlog.get_logger(__name__)


# =============================================================================
# Workflow Node Functions
# =============================================================================


async def monitor_node(state: AgentState) -> dict[str, Any]:
    """
    Monitor Node: Fetches news from sources and discovers potential events.

    This is the entry point of the workflow that collects raw events
    from configured news sources.

    Args:
        state: Current workflow state.

    Returns:
        Updated state fields with discovered events.
    """
    logger.info("Starting monitor node")
    start_time = datetime.now(timezone.utc)

    try:
        # Create scout agent with config from state
        config = state.get("workflow_config", WorkflowConfig())
        monitoring_config = MonitoringConfig(
            max_queries_per_run=config.max_events_per_run,
            max_results_per_query=5,
            days_back=7,
            min_relevance_score=0.5,
        )

        scout = ScoutAgent(config=monitoring_config)

        # Collect events
        events: list[MonitoringEvent] = []
        detected_events = await scout.run_once()
        events.extend(detected_events)

        await scout.close()

        # Convert to RawEvents
        raw_events = []
        for event in events:
            raw_event = event.article.to_raw_event()
            raw_events.append(raw_event)

        logger.info(
            "Monitor node complete",
            events_discovered=len(raw_events),
            duration=(datetime.now(timezone.utc) - start_time).total_seconds(),
        )

        return {
            "current_events": raw_events,
            "last_run_at": datetime.now(timezone.utc).isoformat(),
        }

    except Exception as e:
        logger.error("Monitor node failed", error=str(e))
        error = ProcessingError(
            stage="monitor",
            error_type=type(e).__name__,
            message=str(e),
            recoverable=True,
        )
        return {
            "processing_errors": [error],
            "last_run_at": datetime.now(timezone.utc).isoformat(),
        }


async def extract_node(state: AgentState) -> dict[str, Any]:
    """
    Extract Node: Extracts structured risk data from raw events.

    Uses DSPy modules to extract risk information from news content.

    Args:
        state: Current workflow state.

    Returns:
        Updated state fields with extracted risks.
    """
    logger.info("Starting extract node")
    start_time = datetime.now(timezone.utc)

    current_events = state.get("current_events", [])
    if not current_events:
        logger.info("No events to extract")
        return {"extracted_risks": []}

    extracted_risks: list[RiskEvent] = []
    errors: list[ProcessingError] = []

    # Initialize extraction components
    error_handler = ExtractionErrorHandler()

    for raw_event in current_events:
        try:
            # For now, create a simplified extraction without LLM
            # (Full DSPy integration would require API keys)
            risk_event = _simple_extraction(raw_event)

            if risk_event:
                extracted_risks.append(risk_event)

        except Exception as e:
            error_handler.log_error(
                e,
                source_url=raw_event.url,
                content_snippet=raw_event.content[:200] if raw_event.content else "",
            )

            # Create fallback event
            fallback = error_handler.create_fallback_event(
                source_url=raw_event.url,
                content_snippet=raw_event.content[:100] if raw_event.content else "",
                error_message=str(e),
            )
            extracted_risks.append(fallback)

            errors.append(
                ProcessingError(
                    stage="extract",
                    error_type=type(e).__name__,
                    message=str(e),
                    recoverable=True,
                )
            )

    logger.info(
        "Extract node complete",
        events_processed=len(current_events),
        risks_extracted=len(extracted_risks),
        errors=len(errors),
        duration=(datetime.now(timezone.utc) - start_time).total_seconds(),
    )

    return {
        "extracted_risks": extracted_risks,
        "processing_errors": state.get("processing_errors", []) + errors,
    }


async def validate_node(state: AgentState) -> dict[str, Any]:
    """
    Validate Node: Validates extracted risks and filters low-confidence ones.

    Applies validation rules and confidence thresholds to filter
    unreliable extractions.

    Args:
        state: Current workflow state.

    Returns:
        Updated state fields with validated risks.
    """
    logger.info("Starting validate node")
    start_time = datetime.now(timezone.utc)

    extracted_risks = state.get("extracted_risks", [])
    if not extracted_risks:
        logger.info("No risks to validate")
        return {"validated_risks": []}

    config = state.get("workflow_config", WorkflowConfig())
    validator = ExtractionValidator(
        confidence_threshold=config.confidence_threshold,
    )

    validated_risks: list[RiskEvent] = []
    validation_count = 0

    for risk in extracted_risks:
        result = validator.validate(risk)
        validation_count += 1

        if result.is_valid:
            validated_risks.append(risk)
        else:
            logger.debug(
                "Risk failed validation",
                risk_id=risk.id,
                errors=result.errors,
                warnings=result.warnings,
            )

    logger.info(
        "Validate node complete",
        risks_validated=validation_count,
        risks_passed=len(validated_risks),
        duration=(datetime.now(timezone.utc) - start_time).total_seconds(),
    )

    return {"validated_risks": validated_risks}


async def analyze_node(state: AgentState) -> dict[str, Any]:
    """
    Analyze Node: Analyzes validated risks for supply chain impact.

    Uses GraphRAG to determine downstream impact and affected products.

    Args:
        state: Current workflow state.

    Returns:
        Updated state fields with impact assessments.
    """
    logger.info("Starting analyze node")
    start_time = datetime.now(timezone.utc)

    validated_risks = state.get("validated_risks", [])
    if not validated_risks:
        logger.info("No risks to analyze")
        return {"impact_assessments": []}

    # Create in-memory graph for analysis
    # (In production, would use Neo4j connection)
    graph = InMemoryGraph()

    # Add some sample nodes for demonstration
    _setup_demo_graph(graph)

    assessor = RiskAssessor(graph=graph)
    impact_assessments: list[ImpactAssessment] = []

    for risk in validated_risks:
        # Find affected suppliers based on location
        affected_suppliers = _find_suppliers_by_location(graph, risk.location)

        result = await assessor.assess_risk(
            risk_event=risk,
            affected_suppliers=affected_suppliers,
        )

        # Convert to model
        assessment = assessor.to_impact_assessment_model(result)
        impact_assessments.append(assessment)

    logger.info(
        "Analyze node complete",
        risks_analyzed=len(validated_risks),
        assessments_created=len(impact_assessments),
        duration=(datetime.now(timezone.utc) - start_time).total_seconds(),
    )

    return {"impact_assessments": impact_assessments}


async def alert_node(state: AgentState) -> dict[str, Any]:
    """
    Alert Node: Generates alerts for high-severity impact assessments.

    Creates alerts for risk events that exceed configured thresholds.

    Args:
        state: Current workflow state.

    Returns:
        Updated state fields with generated alerts.
    """
    logger.info("Starting alert node")
    start_time = datetime.now(timezone.utc)

    impact_assessments = state.get("impact_assessments", [])
    validated_risks = state.get("validated_risks", [])

    if not impact_assessments:
        logger.info("No assessments to alert on")
        return {"alerts_generated": []}

    config = state.get("workflow_config", WorkflowConfig())
    alerts: list[Alert] = []

    # Create a mapping of risk_event_id to risk
    risk_map = {r.id: r for r in validated_risks}

    for assessment in impact_assessments:
        # Check if severity exceeds threshold
        if assessment.severity_score >= config.alert_threshold:
            risk = risk_map.get(assessment.risk_event_id)

            alert = Alert(
                id=f"ALERT-{uuid.uuid4().hex[:8].upper()}",
                risk_event_id=assessment.risk_event_id,
                severity=_score_to_severity(assessment.severity_score),
                affected_products=assessment.affected_products,
                recommended_actions=assessment.mitigation_options[:3],
                notified=False,
            )
            alerts.append(alert)

            logger.info(
                "Alert generated",
                alert_id=alert.id,
                severity=alert.severity.value,
                affected_products=len(alert.affected_products),
            )

    logger.info(
        "Alert node complete",
        assessments_checked=len(impact_assessments),
        alerts_generated=len(alerts),
        duration=(datetime.now(timezone.utc) - start_time).total_seconds(),
    )

    return {"alerts_generated": alerts}


# =============================================================================
# Helper Functions
# =============================================================================


def _simple_extraction(raw_event: RawEvent) -> RiskEvent | None:
    """
    Simple rule-based extraction for demonstration.

    In production, this would use the DSPy RiskAnalyst module.
    """
    content = (raw_event.content or "").lower()
    title = (raw_event.title or "").lower()
    combined = f"{title} {content}"

    # Detect event type based on keywords
    event_type = EventType.OTHER
    if any(word in combined for word in ["strike", "walkout", "labor"]):
        event_type = EventType.STRIKE
    elif any(word in combined for word in ["typhoon", "earthquake", "flood", "weather"]):
        event_type = EventType.WEATHER
    elif any(word in combined for word in ["fire", "explosion", "blaze"]):
        event_type = EventType.FIRE
    elif any(word in combined for word in ["bankrupt", "insolvency", "liquidation"]):
        event_type = EventType.BANKRUPTCY
    elif any(word in combined for word in ["sanction", "tariff", "trade war"]):
        event_type = EventType.GEOPOLITICAL
    elif any(word in combined for word in ["cyber", "ransomware", "hack"]):
        event_type = EventType.CYBER_ATTACK
    elif any(word in combined for word in ["port", "shipping", "container"]):
        event_type = EventType.TRANSPORT

    # Detect location
    location = "Unknown"
    locations = ["taiwan", "china", "vietnam", "japan", "korea", "germany", "california"]
    for loc in locations:
        if loc in combined:
            location = loc.title()
            break

    # Detect severity based on keywords
    severity = SeverityLevel.MEDIUM
    if any(word in combined for word in ["catastroph", "critical", "severe", "major"]):
        severity = SeverityLevel.CRITICAL
    elif any(word in combined for word in ["significant", "substantial"]):
        severity = SeverityLevel.HIGH
    elif any(word in combined for word in ["minor", "small", "limited"]):
        severity = SeverityLevel.LOW

    return RiskEvent(
        id=f"RISK-{uuid.uuid4().hex[:8].upper()}",
        event_type=event_type,
        location=location,
        affected_entities=[],
        severity=severity,
        confidence=0.7,
        source_url=raw_event.url,
        description=raw_event.title or "Extracted risk event",
    )


def _setup_demo_graph(graph: InMemoryGraph) -> None:
    """Set up a demo graph for testing."""
    # Add suppliers
    for i in range(5):
        locations = ["Taiwan", "Vietnam", "China", "Germany", "California"]
        graph.add_node(
            GraphNode(
                id=f"SUP-{i:04d}",
                label="Supplier",
                properties={"location": locations[i]},
            )
        )

    # Add components
    for i in range(10):
        graph.add_node(GraphNode(id=f"COMP-{i:04d}", label="Component"))

    # Add products
    for i in range(3):
        graph.add_node(GraphNode(id=f"PROD-{i:04d}", label="Product"))

    # Add edges
    for i in range(10):
        graph.add_edge(
            GraphEdge(
                source_id=f"SUP-{i % 5:04d}",
                target_id=f"COMP-{i:04d}",
                relationship_type="SUPPLIES",
            )
        )

    for i in range(10):
        graph.add_edge(
            GraphEdge(
                source_id=f"COMP-{i:04d}",
                target_id=f"PROD-{i % 3:04d}",
                relationship_type="PART_OF",
            )
        )


def _find_suppliers_by_location(graph: InMemoryGraph, location: str) -> list[str]:
    """Find suppliers in the graph by location."""
    if not location or location.lower() == "unknown":
        return []

    matching = []
    location_lower = location.lower()

    for node_id, node in graph.nodes.items():
        if node.label == "Supplier":
            node_location = node.properties.get("location", "").lower()
            if location_lower in node_location or node_location in location_lower:
                matching.append(node_id)

    return matching


def _score_to_severity(score: float) -> SeverityLevel:
    """Convert numeric score to severity level."""
    if score >= 8.0:
        return SeverityLevel.CRITICAL
    elif score >= 6.0:
        return SeverityLevel.HIGH
    elif score >= 4.0:
        return SeverityLevel.MEDIUM
    else:
        return SeverityLevel.LOW
