"""
Enhanced API v2 Routes for Supply Chain Risk Management.

Implements REST endpoints for resilience metrics, advanced search,
mitigation management, alert rules, and predictive analytics.
"""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Any
import uuid

from fastapi import APIRouter, Query, HTTPException, Depends, Body
from pydantic import BaseModel, Field

from src.models import (
    EventType,
    SeverityLevel,
    AlertChannel,
    AlertRuleStatus,
)
from src.api.auth import RequireReader, RequireWriter, RequireAdmin
from src.api.schemas import APIResponse, PaginationMeta, PaginatedResponse


# =============================================================================
# Enhanced Request/Response Schemas
# =============================================================================


class ResilienceScoreResponse(BaseModel):
    """Response for resilience score endpoint."""

    entity_id: str
    entity_type: str
    overall_score: float = Field(ge=0.0, le=1.0)
    supplier_diversity: float = Field(ge=0.0, le=1.0)
    geographic_distribution: float = Field(ge=0.0, le=1.0)
    redundancy_level: float = Field(ge=0.0, le=1.0)
    calculated_at: datetime


class ResilienceHistoryResponse(BaseModel):
    """Response for resilience history endpoint."""

    entity_id: str
    history: list[dict[str, Any]]
    trend: str  # "improving", "declining", "stable"


class PortfolioResilienceResponse(BaseModel):
    """Response for portfolio resilience endpoint."""

    overall_score: float
    entity_scores: list[ResilienceScoreResponse]
    risk_distribution: dict[str, int]
    recommendations: list[str]


class SearchRequest(BaseModel):
    """Request for full-text search."""

    query: str = Field(..., min_length=1, description="Search query")
    filters: dict | None = Field(default=None, description="Filter conditions")
    limit: int = Field(default=100, ge=1, le=500)
    offset: int = Field(default=0, ge=0)


class SearchResponse(BaseModel):
    """Response for search endpoint."""

    query: str
    total_count: int
    returned_count: int
    results: list[dict[str, Any]]
    search_time_ms: int


class SavedSearchRequest(BaseModel):
    """Request for saving a search."""

    name: str = Field(..., min_length=1, max_length=100)
    query: str
    filters: dict | None = None


class SavedSearchResponse(BaseModel):
    """Response for saved search."""

    id: str
    name: str
    query: str
    filters: dict | None = None
    created_at: datetime
    last_executed: datetime | None = None
    execution_count: int = 0


class MitigationOptionResponse(BaseModel):
    """Response for mitigation options."""

    id: str
    risk_id: str
    action: str
    mitigation_type: str
    cost_estimate: float
    time_to_implement: str
    effectiveness_score: float
    feasibility: str


class SimulationRequest(BaseModel):
    """Request for mitigation simulation."""

    mitigation_id: str
    parameters: dict = Field(default_factory=dict)


class SimulationResponse(BaseModel):
    """Response for mitigation simulation."""

    mitigation_id: str
    original_risk_score: float
    projected_risk_score: float
    risk_reduction: float
    affected_entities: list[str]
    simulation_details: dict


class OutcomeTrackingRequest(BaseModel):
    """Request for tracking mitigation outcome."""

    mitigation_id: str
    actual_risk_reduction: float = Field(ge=0.0, le=1.0)
    notes: str = ""
    completed_at: datetime | None = None


class AlertRuleCreateRequest(BaseModel):
    """Request for creating an alert rule."""

    name: str = Field(..., min_length=1, max_length=100)
    channels: list[AlertChannel]
    event_types: list[EventType] | None = None
    locations: list[str] | None = None
    entity_ids: list[str] | None = None
    min_severity: SeverityLevel = SeverityLevel.LOW


class AlertRuleUpdateRequest(BaseModel):
    """Request for updating an alert rule."""

    name: str | None = None
    channels: list[AlertChannel] | None = None
    event_types: list[EventType] | None = None
    locations: list[str] | None = None
    entity_ids: list[str] | None = None
    min_severity: SeverityLevel | None = None
    status: AlertRuleStatus | None = None


class AlertRuleResponse(BaseModel):
    """Response for alert rule."""

    id: str
    name: str
    status: str
    channels: list[str]
    event_types: list[str]
    locations: list[str]
    entity_ids: list[str]
    created_at: datetime
    updated_at: datetime | None = None


class PatternResponse(BaseModel):
    """Response for risk pattern detection."""

    pattern_id: str
    pattern_type: str
    description: str
    severity: str
    confidence: float
    entity_ids: list[str]
    detected_at: datetime


class ForecastResponse(BaseModel):
    """Response for risk forecast."""

    forecast_id: str
    entity_id: str
    risk_type: str
    predicted_probability: float
    time_horizon: str
    confidence_interval: dict[str, float]
    contributing_factors: list[str]
    generated_at: datetime


class EarlyWarningResponse(BaseModel):
    """Response for early warning."""

    warning_id: str
    risk_type: str
    severity: str
    description: str
    affected_entities: list[str]
    recommended_actions: list[str]
    detected_at: datetime


# =============================================================================
# Router Setup
# =============================================================================

router = APIRouter(prefix="/v2", tags=["v2"])

resilience_router = APIRouter(prefix="/resilience", tags=["resilience"])
search_router = APIRouter(prefix="/search", tags=["search"])
mitigation_router = APIRouter(prefix="/mitigations", tags=["mitigations"])
alert_rules_router = APIRouter(prefix="/alerts/rules", tags=["alert-rules"])
analytics_router = APIRouter(prefix="/analytics", tags=["analytics"])


# =============================================================================
# In-Memory Stores (for demonstration)
# =============================================================================

_resilience_scores: dict[str, ResilienceScoreResponse] = {}
_resilience_history: dict[str, list[dict]] = {}
_saved_searches: dict[str, SavedSearchResponse] = {}
_mitigation_options: dict[str, list[MitigationOptionResponse]] = {}
_simulation_results: dict[str, SimulationResponse] = {}
_alert_rules: dict[str, AlertRuleResponse] = {}
_patterns: list[PatternResponse] = []
_forecasts: list[ForecastResponse] = []
_early_warnings: list[EarlyWarningResponse] = []


def _init_demo_data():
    """Initialize demo data for v2 API."""
    # Demo resilience scores
    for entity_id in ["supplier-1", "supplier-2", "product-1"]:
        _resilience_scores[entity_id] = ResilienceScoreResponse(
            entity_id=entity_id,
            entity_type="supplier" if "supplier" in entity_id else "product",
            overall_score=0.75,
            supplier_diversity=0.8,
            geographic_distribution=0.6,
            redundancy_level=0.85,
            calculated_at=datetime.now(timezone.utc),
        )
        _resilience_history[entity_id] = [
            {"date": "2024-01-01", "score": 0.7},
            {"date": "2024-02-01", "score": 0.72},
            {"date": "2024-03-01", "score": 0.75},
        ]

    # Demo alert rules
    _alert_rules["rule-demo-1"] = AlertRuleResponse(
        id="rule-demo-1",
        name="Critical Alerts",
        status="Active",
        channels=["Email", "Slack"],
        event_types=["Natural Disaster", "Strike"],
        locations=["Asia", "Europe"],
        entity_ids=[],
        created_at=datetime.now(timezone.utc),
    )

    # Demo patterns
    _patterns.append(PatternResponse(
        pattern_id="pattern-1",
        pattern_type="supplier_concentration",
        description="High concentration of critical components from single region",
        severity="high",
        confidence=0.85,
        entity_ids=["supplier-1", "supplier-2"],
        detected_at=datetime.now(timezone.utc),
    ))

    # Demo forecasts
    _forecasts.append(ForecastResponse(
        forecast_id="forecast-1",
        entity_id="supplier-1",
        risk_type="supply_disruption",
        predicted_probability=0.35,
        time_horizon="30_days",
        confidence_interval={"lower": 0.25, "upper": 0.45},
        contributing_factors=["seasonal_demand", "logistics_constraints"],
        generated_at=datetime.now(timezone.utc),
    ))

    # Demo warnings
    _early_warnings.append(EarlyWarningResponse(
        warning_id="warning-1",
        risk_type="capacity_shortage",
        severity="medium",
        description="Potential capacity shortage detected for Q2",
        affected_entities=["supplier-1", "component-a"],
        recommended_actions=["Increase safety stock", "Identify backup suppliers"],
        detected_at=datetime.now(timezone.utc),
    ))


_init_demo_data()


# =============================================================================
# Resilience Endpoints (8.1)
# =============================================================================


@resilience_router.get(
    "/{entity_id}",
    response_model=APIResponse[ResilienceScoreResponse],
)
async def get_resilience_score(
    entity_id: str,
    api_key: RequireReader,
):
    """Get resilience score for a specific entity."""
    if entity_id not in _resilience_scores:
        raise HTTPException(status_code=404, detail=f"Entity {entity_id} not found")

    return APIResponse(
        success=True,
        data=_resilience_scores[entity_id],
    )


@resilience_router.get(
    "/{entity_id}/history",
    response_model=APIResponse[ResilienceHistoryResponse],
)
async def get_resilience_history(
    entity_id: str,
    api_key: RequireReader,
    days: int = Query(default=90, ge=1, le=365),
):
    """Get resilience score history for an entity."""
    if entity_id not in _resilience_history:
        raise HTTPException(status_code=404, detail=f"Entity {entity_id} not found")

    history = _resilience_history[entity_id]
    
    # Calculate trend
    if len(history) >= 2:
        first_score = history[0]["score"]
        last_score = history[-1]["score"]
        if last_score > first_score + 0.05:
            trend = "improving"
        elif last_score < first_score - 0.05:
            trend = "declining"
        else:
            trend = "stable"
    else:
        trend = "stable"

    return APIResponse(
        success=True,
        data=ResilienceHistoryResponse(
            entity_id=entity_id,
            history=history,
            trend=trend,
        ),
    )


@resilience_router.get(
    "/portfolio",
    response_model=APIResponse[PortfolioResilienceResponse],
)
async def get_portfolio_resilience(
    api_key: RequireReader,
):
    """Get portfolio-level resilience metrics."""
    scores = list(_resilience_scores.values())
    
    if not scores:
        overall = 0.0
    else:
        overall = sum(s.overall_score for s in scores) / len(scores)

    return APIResponse(
        success=True,
        data=PortfolioResilienceResponse(
            overall_score=overall,
            entity_scores=scores,
            risk_distribution={"low": 2, "medium": 1, "high": 0},
            recommendations=[
                "Increase supplier diversity in Asia region",
                "Establish backup logistics routes",
            ],
        ),
    )


# =============================================================================
# Search Endpoints (8.2)
# =============================================================================


@search_router.post(
    "",
    response_model=APIResponse[SearchResponse],
)
async def search(
    request: SearchRequest,
    api_key: RequireReader,
):
    """Perform full-text search with optional filters."""
    from src.analysis.search import SearchManager
    
    manager = SearchManager()
    
    # For demo, return mock results
    results: list[dict[str, Any]] = [
        {
            "id": "result-1",
            "type": "risk_event",
            "title": f"Result matching '{request.query}'",
            "score": 0.95,
        },
    ]

    return APIResponse(
        success=True,
        data=SearchResponse(
            query=request.query,
            total_count=len(results),
            returned_count=len(results),
            results=results,
            search_time_ms=15,
        ),
    )


@search_router.get(
    "/saved",
    response_model=APIResponse[list[SavedSearchResponse]],
)
async def list_saved_searches(
    api_key: RequireReader,
):
    """List all saved searches."""
    return APIResponse(
        success=True,
        data=list(_saved_searches.values()),
    )


@search_router.post(
    "/save",
    response_model=APIResponse[SavedSearchResponse],
)
async def save_search(
    request: SavedSearchRequest,
    api_key: RequireWriter,
):
    """Save a search query for later use."""
    search_id = f"search-{uuid.uuid4().hex[:8]}"
    
    saved = SavedSearchResponse(
        id=search_id,
        name=request.name,
        query=request.query,
        filters=request.filters,
        created_at=datetime.now(timezone.utc),
    )
    
    _saved_searches[search_id] = saved
    
    return APIResponse(
        success=True,
        data=saved,
        message=f"Search '{request.name}' saved successfully",
    )


@search_router.post(
    "/saved/{search_id}/execute",
    response_model=APIResponse[SearchResponse],
)
async def execute_saved_search(
    search_id: str,
    api_key: RequireReader,
):
    """Execute a saved search."""
    if search_id not in _saved_searches:
        raise HTTPException(status_code=404, detail=f"Saved search {search_id} not found")

    saved = _saved_searches[search_id]
    saved.last_executed = datetime.now(timezone.utc)
    saved.execution_count += 1

    # Execute the search
    return APIResponse(
        success=True,
        data=SearchResponse(
            query=saved.query,
            total_count=0,
            returned_count=0,
            results=[],
            search_time_ms=5,
        ),
    )


# =============================================================================
# Mitigation Endpoints (8.3)
# =============================================================================


@mitigation_router.get(
    "/risks/{risk_id}",
    response_model=APIResponse[list[MitigationOptionResponse]],
)
async def get_risk_mitigations(
    risk_id: str,
    api_key: RequireReader,
):
    """Get mitigation options for a specific risk."""
    # Generate demo options
    options = [
        MitigationOptionResponse(
            id=f"mitigation-{uuid.uuid4().hex[:8]}",
            risk_id=risk_id,
            action="Diversify supplier base",
            mitigation_type="strategic",
            cost_estimate=50000.0,
            time_to_implement="3-6 months",
            effectiveness_score=0.75,
            feasibility="high",
        ),
        MitigationOptionResponse(
            id=f"mitigation-{uuid.uuid4().hex[:8]}",
            risk_id=risk_id,
            action="Increase safety stock",
            mitigation_type="tactical",
            cost_estimate=15000.0,
            time_to_implement="1-2 weeks",
            effectiveness_score=0.5,
            feasibility="high",
        ),
    ]

    return APIResponse(
        success=True,
        data=options,
    )


@mitigation_router.post(
    "/{mitigation_id}/simulate",
    response_model=APIResponse[SimulationResponse],
)
async def simulate_mitigation(
    mitigation_id: str,
    request: SimulationRequest,
    api_key: RequireWriter,
):
    """Simulate the impact of a mitigation action."""
    simulation = SimulationResponse(
        mitigation_id=mitigation_id,
        original_risk_score=0.75,
        projected_risk_score=0.35,
        risk_reduction=0.40,
        affected_entities=["supplier-1", "component-a", "product-1"],
        simulation_details={
            "scenarios_evaluated": 100,
            "confidence": 0.85,
            "time_to_effect": "30 days",
        },
    )
    
    _simulation_results[mitigation_id] = simulation

    return APIResponse(
        success=True,
        data=simulation,
    )


@mitigation_router.post(
    "/{mitigation_id}/track-outcome",
    response_model=APIResponse[dict],
)
async def track_mitigation_outcome(
    mitigation_id: str,
    request: OutcomeTrackingRequest,
    api_key: RequireWriter,
):
    """Track the actual outcome of a mitigation action."""
    return APIResponse(
        success=True,
        data={
            "mitigation_id": mitigation_id,
            "actual_risk_reduction": request.actual_risk_reduction,
            "notes": request.notes,
            "completed_at": request.completed_at or datetime.now(timezone.utc),
            "tracked": True,
        },
        message="Outcome tracked successfully",
    )


# =============================================================================
# Alert Rule Endpoints (8.4)
# =============================================================================


@alert_rules_router.get(
    "",
    response_model=APIResponse[list[AlertRuleResponse]],
)
async def list_alert_rules(
    api_key: RequireReader,
    status: AlertRuleStatus | None = None,
):
    """List all alert rules."""
    rules = list(_alert_rules.values())
    
    if status:
        rules = [r for r in rules if r.status == status.value]

    return APIResponse(
        success=True,
        data=rules,
    )


@alert_rules_router.post(
    "",
    response_model=APIResponse[AlertRuleResponse],
)
async def create_alert_rule(
    request: AlertRuleCreateRequest,
    api_key: RequireWriter,
):
    """Create a new alert rule."""
    rule_id = f"rule-{uuid.uuid4().hex[:8]}"
    
    rule = AlertRuleResponse(
        id=rule_id,
        name=request.name,
        status="Active",
        channels=[c.value for c in request.channels],
        event_types=[e.value for e in (request.event_types or [])],
        locations=request.locations or [],
        entity_ids=request.entity_ids or [],
        created_at=datetime.now(timezone.utc),
    )
    
    _alert_rules[rule_id] = rule

    return APIResponse(
        success=True,
        data=rule,
        message=f"Alert rule '{request.name}' created",
    )


@alert_rules_router.patch(
    "/{rule_id}",
    response_model=APIResponse[AlertRuleResponse],
)
async def update_alert_rule(
    rule_id: str,
    request: AlertRuleUpdateRequest,
    api_key: RequireWriter,
):
    """Update an existing alert rule."""
    if rule_id not in _alert_rules:
        raise HTTPException(status_code=404, detail=f"Rule {rule_id} not found")

    rule = _alert_rules[rule_id]
    
    if request.name:
        rule.name = request.name
    if request.channels:
        rule.channels = [c.value for c in request.channels]
    if request.event_types:
        rule.event_types = [e.value for e in request.event_types]
    if request.locations is not None:
        rule.locations = request.locations
    if request.entity_ids is not None:
        rule.entity_ids = request.entity_ids
    if request.status:
        rule.status = request.status.value
    
    rule.updated_at = datetime.now(timezone.utc)

    return APIResponse(
        success=True,
        data=rule,
        message="Alert rule updated",
    )


@alert_rules_router.delete(
    "/{rule_id}",
    response_model=APIResponse[dict],
)
async def delete_alert_rule(
    rule_id: str,
    api_key: RequireAdmin,
):
    """Delete an alert rule."""
    if rule_id not in _alert_rules:
        raise HTTPException(status_code=404, detail=f"Rule {rule_id} not found")

    del _alert_rules[rule_id]

    return APIResponse(
        success=True,
        data={"rule_id": rule_id, "deleted": True},
        message="Alert rule deleted",
    )


# =============================================================================
# Analytics Endpoints (8.5)
# =============================================================================


@analytics_router.get(
    "/patterns",
    response_model=APIResponse[list[PatternResponse]],
)
async def get_patterns(
    api_key: RequireReader,
    severity: str | None = None,
):
    """Get detected risk patterns."""
    patterns = _patterns.copy()
    
    if severity:
        patterns = [p for p in patterns if p.severity == severity]

    return APIResponse(
        success=True,
        data=patterns,
    )


@analytics_router.get(
    "/forecasts",
    response_model=APIResponse[list[ForecastResponse]],
)
async def get_forecasts(
    api_key: RequireReader,
    entity_id: str | None = None,
    time_horizon: str | None = None,
):
    """Get risk forecasts."""
    forecasts = _forecasts.copy()
    
    if entity_id:
        forecasts = [f for f in forecasts if f.entity_id == entity_id]
    if time_horizon:
        forecasts = [f for f in forecasts if f.time_horizon == time_horizon]

    return APIResponse(
        success=True,
        data=forecasts,
    )


@analytics_router.get(
    "/early-warnings",
    response_model=APIResponse[list[EarlyWarningResponse]],
)
async def get_early_warnings(
    api_key: RequireReader,
    severity: str | None = None,
):
    """Get early warning signals."""
    warnings = _early_warnings.copy()
    
    if severity:
        warnings = [w for w in warnings if w.severity == severity]

    return APIResponse(
        success=True,
        data=warnings,
    )


# =============================================================================
# Include Sub-routers
# =============================================================================

router.include_router(resilience_router)
router.include_router(search_router)
router.include_router(mitigation_router)
router.include_router(alert_rules_router)
router.include_router(analytics_router)
