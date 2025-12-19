"""
Pydantic schemas for API request and response models.

Provides standardized data structures for the FastAPI endpoints.
"""

from datetime import datetime
from typing import Any, Generic, TypeVar
from pydantic import BaseModel, Field, ConfigDict

from src.models import (
    EventType,
    SeverityLevel,
    RiskEvent,
    ImpactAssessment,
    Alert,
    Supplier,
    Component,
    Product,
)


# =============================================================================
# Generic Response Wrapper
# =============================================================================

DataT = TypeVar("DataT")


class APIResponse(BaseModel, Generic[DataT]):
    """
    Standardized API response wrapper.

    All API responses should use this format for consistency.
    """

    success: bool = True
    data: DataT | None = None
    error: str | None = None
    message: str | None = None
    meta: dict[str, Any] = Field(default_factory=dict)

    model_config = ConfigDict(extra="forbid")


class PaginationMeta(BaseModel):
    """Pagination metadata for list responses."""

    total: int
    page: int
    per_page: int
    total_pages: int


class PaginatedResponse(APIResponse[list[DataT]], Generic[DataT]):
    """Paginated API response."""

    pagination: PaginationMeta | None = None


# =============================================================================
# Request Schemas
# =============================================================================


class RiskQueryRequest(BaseModel):
    """Request for querying product risks."""

    product_id: str = Field(..., description="Product ID to query")
    include_paths: bool = Field(
        default=False, description="Include impact paths in response"
    )
    max_depth: int = Field(default=5, ge=1, le=20, description="Maximum traversal depth")


class SupplierSearchRequest(BaseModel):
    """Request for searching suppliers."""

    query: str = Field(default="", description="Search query")
    location: str | None = Field(default=None, description="Filter by location")
    tier: int | None = Field(default=None, ge=1, le=5, description="Filter by tier")
    page: int = Field(default=1, ge=1)
    per_page: int = Field(default=20, ge=1, le=100)


class RiskEventCreateRequest(BaseModel):
    """Request for creating a risk event."""

    event_type: EventType
    location: str
    affected_entities: list[str] = Field(default_factory=list)
    severity: SeverityLevel
    confidence: float = Field(ge=0.0, le=1.0)
    source_url: str
    description: str


class WebhookRegistration(BaseModel):
    """Request for registering a webhook."""

    url: str = Field(..., description="Webhook endpoint URL")
    events: list[str] = Field(
        default_factory=lambda: ["alert.created"],
        description="Events to subscribe to",
    )
    secret: str | None = Field(default=None, description="Shared secret for HMAC")
    active: bool = Field(default=True)


class WebhookUpdate(BaseModel):
    """Request for updating a webhook."""

    url: str | None = None
    events: list[str] | None = None
    secret: str | None = None
    active: bool | None = None


# =============================================================================
# Response Schemas
# =============================================================================


class HealthResponse(BaseModel):
    """Health check response."""

    status: str = "healthy"
    version: str
    timestamp: datetime
    services: dict[str, str] = Field(default_factory=dict)


class RiskQueryResponse(BaseModel):
    """Response for risk queries."""

    product_id: str
    risk_score: float
    active_risks: list[RiskEvent]
    impact_assessments: list[ImpactAssessment]
    affected_entities_count: int
    last_updated: datetime


class SupplierResponse(BaseModel):
    """Supplier data response."""

    id: str
    name: str
    tier: int
    location: str
    risk_score: float
    components_supplied: int


class ComponentResponse(BaseModel):
    """Component data response."""

    id: str
    name: str
    category: str
    suppliers: list[str]
    products: list[str]


class ProductResponse(BaseModel):
    """Product data response."""

    id: str
    name: str
    category: str
    risk_score: float
    component_count: int


class AlertResponse(BaseModel):
    """Alert data response."""

    id: str
    risk_event_id: str
    severity: SeverityLevel
    affected_products: list[str]
    recommended_actions: list[str]
    created_at: datetime
    acknowledged: bool = False
    acknowledged_at: datetime | None = None


class WebhookResponse(BaseModel):
    """Webhook registration response."""

    id: str
    url: str
    events: list[str]
    active: bool
    created_at: datetime
    last_triggered: datetime | None = None
    delivery_count: int = 0
    failure_count: int = 0


class StatsResponse(BaseModel):
    """System statistics response."""

    total_suppliers: int
    total_components: int
    total_products: int
    active_risks: int
    pending_alerts: int
    last_monitoring_run: datetime | None
class MitigationResponse(BaseModel):
    """Response containing AI-generated mitigation strategies."""

    risk_event_id: str
    top_priority_actions: list[str]
    strategic_mitigations: list[str]
    rationale: str
    estimated_risk_reduction: str
    generated_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
