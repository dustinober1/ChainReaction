"""
Core data models for ChainReaction.

This module defines Pydantic models for all supply chain entities,
risk events, and impact assessments used throughout the system.
"""

from datetime import datetime, timedelta, timezone
from enum import Enum
from typing import Any

from pydantic import BaseModel, ConfigDict, Field, field_validator


def utc_now() -> datetime:
    """Get current UTC time as timezone-aware datetime."""
    return datetime.now(timezone.utc)


# =============================================================================
# Enums
# =============================================================================


class EventType(str, Enum):
    """Types of supply chain disruption events."""

    STRIKE = "Strike"
    WEATHER = "Weather"
    BANKRUPTCY = "Bankruptcy"
    GEOPOLITICAL = "Geopolitical"
    FIRE = "Fire"
    PANDEMIC = "Pandemic"
    CYBER_ATTACK = "CyberAttack"
    TRANSPORT = "Transport"
    OTHER = "Other"


class SeverityLevel(str, Enum):
    """Impact severity levels for risk events."""

    LOW = "Low"
    MEDIUM = "Medium"
    HIGH = "High"
    CRITICAL = "Critical"


class EntityTier(str, Enum):
    """Supply chain entity tiers."""

    RAW_MATERIAL = "Raw Material"
    COMPONENT = "Component"
    SUB_ASSEMBLY = "Sub-Assembly"
    FINAL_PRODUCT = "Final Product"


class RelationshipType(str, Enum):
    """Types of relationships between supply chain entities."""

    SUPPLIES = "SUPPLIES"
    LOCATED_IN = "LOCATED_IN"
    BACKUP_FOR = "BACKUP_FOR"
    PART_OF = "PART_OF"
    REQUIRES = "REQUIRES"
    ALTERNATIVE_TO = "ALTERNATIVE_TO"
    MANUFACTURES = "MANUFACTURES"


# =============================================================================
# Base Models
# =============================================================================


class BaseNode(BaseModel):
    """Base class for all graph nodes."""

    model_config = ConfigDict(from_attributes=True)

    id: str = Field(..., description="Unique identifier for the node")
    created_at: datetime = Field(default_factory=utc_now)
    updated_at: datetime = Field(default_factory=utc_now)


class BaseRelationship(BaseModel):
    """Base class for all graph relationships."""

    source_id: str = Field(..., description="ID of the source node")
    target_id: str = Field(..., description="ID of the target node")
    relationship_type: RelationshipType = Field(..., description="Type of relationship")
    properties: dict[str, Any] = Field(default_factory=dict)


# =============================================================================
# Supply Chain Entity Models
# =============================================================================


class Supplier(BaseNode):
    """A supplier entity in the supply chain graph."""

    name: str = Field(..., description="Supplier company name")
    location: str = Field(..., description="Primary operating location")
    risk_score: float = Field(
        default=0.0, ge=0.0, le=100.0, description="Baseline risk score (0-100)"
    )
    contact_info: dict[str, str] | None = Field(
        default=None, description="Contact information"
    )
    country: str | None = Field(default=None, description="Country of operation")
    tier: int = Field(default=1, ge=1, le=4, description="Supplier tier level")

    @field_validator("risk_score", mode="before")
    @classmethod
    def validate_risk_score(cls, v: float) -> float:
        """Clamp risk score to valid range before validation."""
        if isinstance(v, (int, float)):
            return round(min(max(float(v), 0.0), 100.0), 2)
        return v


class Component(BaseNode):
    """A component or part in the supply chain."""

    name: str = Field(..., description="Component name")
    category: str = Field(..., description="Component category")
    tier: EntityTier = Field(default=EntityTier.COMPONENT, description="Supply chain tier")
    specifications: dict[str, Any] = Field(
        default_factory=dict, description="Technical specifications"
    )
    lead_time_days: int | None = Field(
        default=None, ge=0, description="Standard lead time in days"
    )
    critical: bool = Field(default=False, description="Whether this is a critical component")


class Product(BaseNode):
    """A final product in the supply chain."""

    name: str = Field(..., description="Product name")
    product_line: str = Field(..., description="Product line or family")
    revenue_impact: float = Field(
        default=0.0, ge=0.0, description="Revenue impact score"
    )
    sku: str | None = Field(default=None, description="Stock keeping unit")
    launch_date: datetime | None = Field(default=None, description="Product launch date")


class Location(BaseNode):
    """A geographic location in the supply chain."""

    name: str = Field(..., description="Location name")
    country: str = Field(..., description="Country")
    region: str = Field(..., description="Geographic region")
    risk_factors: list[str] = Field(
        default_factory=list, description="Known risk factors for this location"
    )
    latitude: float | None = Field(default=None, ge=-90.0, le=90.0)
    longitude: float | None = Field(default=None, ge=-180.0, le=180.0)


# =============================================================================
# Risk Event Models
# =============================================================================


class RawEvent(BaseModel):
    """Raw event data from external sources before processing."""

    source: str = Field(..., description="Source of the event (e.g., 'tavily', 'newsapi')")
    url: str = Field(..., description="Source URL")
    title: str = Field(..., description="Event title or headline")
    content: str = Field(..., description="Full content of the article/event")
    published_at: datetime | None = Field(default=None, description="Publication timestamp")
    fetched_at: datetime = Field(default_factory=utc_now)


class RiskEvent(BaseModel):
    """
    Structured risk event extracted from raw news content.

    This is the output of the DSPy Analyst Module.
    """

    id: str = Field(..., description="Unique event identifier")
    event_type: EventType = Field(..., description="Type of disruption event")
    location: str = Field(..., description="Geographic location of the event")
    affected_entities: list[str] = Field(
        default_factory=list, description="Entities affected by this event"
    )
    severity: SeverityLevel = Field(..., description="Impact severity level")
    confidence: float = Field(
        ..., ge=0.0, le=1.0, description="Extraction confidence score"
    )
    source_url: str = Field(..., description="Original source URL")
    detected_at: datetime = Field(default_factory=utc_now)
    estimated_duration: timedelta | None = Field(
        default=None, description="Estimated duration of the disruption"
    )
    description: str = Field(default="", description="Brief description of the event")

    @field_validator("confidence")
    @classmethod
    def validate_confidence(cls, v: float) -> float:
        """Round confidence to 3 decimal places."""
        return round(v, 3)


class ImpactPath(BaseModel):
    """A path through the supply chain showing impact propagation."""

    nodes: list[str] = Field(..., description="Ordered list of node IDs in the path")
    relationship_types: list[RelationshipType] = Field(
        ..., description="Relationships traversed"
    )
    total_hops: int = Field(..., ge=0, description="Total number of hops in the path")
    criticality_score: float = Field(
        default=0.0, ge=0.0, le=1.0, description="Path criticality score"
    )


class ImpactAssessment(BaseModel):
    """Complete impact assessment for a risk event."""

    risk_event_id: str = Field(..., description="ID of the associated risk event")
    affected_products: list[str] = Field(
        ..., description="List of affected product IDs"
    )
    impact_paths: list[ImpactPath] = Field(
        default_factory=list, description="Paths showing impact propagation"
    )
    severity_score: float = Field(
        ..., ge=0.0, le=10.0, description="Overall severity score (0-10)"
    )
    estimated_timeline: dict[str, datetime] = Field(
        default_factory=dict,
        description="Timeline estimates (e.g., 'impact_start', 'recovery_expected')",
    )
    mitigation_options: list[str] = Field(
        default_factory=list, description="Available mitigation strategies"
    )
    alternative_suppliers: list[str] = Field(
        default_factory=list, description="Available alternative suppliers"
    )
    redundancy_level: float = Field(
        default=0.0, ge=0.0, le=1.0, description="Supply chain redundancy level"
    )
    assessed_at: datetime = Field(default_factory=utc_now)


# =============================================================================
# Alert Models
# =============================================================================


class Alert(BaseModel):
    """Risk alert generated by the system."""

    id: str = Field(..., description="Unique alert identifier")
    risk_event_id: str = Field(..., description="Associated risk event ID")
    product_ids: list[str] = Field(..., description="Affected product IDs")
    severity: SeverityLevel = Field(..., description="Alert severity")
    title: str = Field(..., description="Alert title")
    message: str = Field(..., description="Alert message")
    created_at: datetime = Field(default_factory=utc_now)
    acknowledged: bool = Field(default=False)
    acknowledged_at: datetime | None = Field(default=None)
    acknowledged_by: str | None = Field(default=None)


class ProcessingError(BaseModel):
    """Error that occurred during event processing."""

    error_type: str = Field(..., description="Type of error")
    message: str = Field(..., description="Error message")
    source: str | None = Field(default=None, description="Source that caused the error")
    occurred_at: datetime = Field(default_factory=utc_now)
    recoverable: bool = Field(default=True, description="Whether the error is recoverable")
    details: dict[str, Any] = Field(default_factory=dict)


# =============================================================================
# Relationship Models for Import/Export
# =============================================================================


class SuppliesRelation(BaseModel):
    """Relationship between a supplier and a component."""

    supplier_id: str = Field(..., description="ID of the supplier")
    component_id: str = Field(..., description="ID of the component")
    is_primary: bool = Field(default=False, description="Whether this is the primary supplier")
    lead_time_days: int | None = Field(default=None, ge=0, description="Lead time in days")


class PartOfRelation(BaseModel):
    """Relationship between a component and a product."""

    component_id: str = Field(..., description="ID of the component")
    product_id: str = Field(..., description="ID of the product")
    quantity: int = Field(default=1, ge=1, description="Quantity needed per product")


# =============================================================================
# Alert Channel and Rule Enums
# =============================================================================


class AlertChannel(str, Enum):
    """Available channels for alert delivery."""

    EMAIL = "Email"
    SLACK = "Slack"
    WEBHOOK = "Webhook"
    SMS = "SMS"


class AlertRuleStatus(str, Enum):
    """Status of an alert rule."""

    ACTIVE = "Active"
    DISABLED = "Disabled"
    TESTING = "Testing"


# =============================================================================
# Resilience Metrics Models
# =============================================================================


class ResilienceScore(BaseModel):
    """Resilience score for an entity at a specific level."""

    entity_id: str = Field(..., description="ID of the entity")
    entity_type: str = Field(..., description="Type of entity (supplier, component, product)")
    score: float = Field(..., ge=0.0, le=100.0, description="Resilience score (0-100)")
    redundancy_factor: float = Field(
        default=0.0, ge=0.0, le=1.0, description="Redundancy factor (0-1)"
    )
    calculated_at: datetime = Field(default_factory=utc_now)

    @field_validator("score")
    @classmethod
    def validate_score(cls, v: float) -> float:
        """Round score to 2 decimal places."""
        return round(v, 2)


class ResilienceMetrics(BaseModel):
    """
    Comprehensive resilience metrics for an entity or portfolio.

    Provides multi-level resilience calculations with trend analysis.
    """

    entity_id: str | None = Field(
        default=None, description="Entity ID (None for portfolio-level)"
    )
    level: str = Field(
        default="entity",
        description="Metrics level: 'component', 'product', 'portfolio'",
    )
    overall_score: float = Field(
        ..., ge=0.0, le=100.0, description="Overall resilience score"
    )
    component_scores: list[ResilienceScore] = Field(
        default_factory=list, description="Individual component scores"
    )
    redundancy_coverage: float = Field(
        default=0.0, ge=0.0, le=1.0, description="Percentage of components with backup suppliers"
    )
    single_points_of_failure: int = Field(
        default=0, ge=0, description="Number of single points of failure"
    )
    trend_direction: str | None = Field(
        default=None, description="Trend direction: 'improving', 'stable', 'declining'"
    )
    trend_rate: float | None = Field(
        default=None, description="Rate of change per week"
    )
    calculated_at: datetime = Field(default_factory=utc_now)

    @field_validator("overall_score")
    @classmethod
    def validate_overall_score(cls, v: float) -> float:
        """Round overall score to 2 decimal places."""
        return round(v, 2)

    @field_validator("level")
    @classmethod
    def validate_level(cls, v: str) -> str:
        """Validate level is one of allowed values."""
        allowed = {"component", "product", "portfolio", "entity"}
        if v.lower() not in allowed:
            raise ValueError(f"Level must be one of {allowed}")
        return v.lower()


class HistoricalResilienceScore(BaseModel):
    """Historical resilience score record for trend analysis."""

    entity_id: str = Field(..., description="ID of the entity")
    score: float = Field(..., ge=0.0, le=100.0, description="Score at this point in time")
    recorded_at: datetime = Field(default_factory=utc_now)
    factors: dict[str, float] = Field(
        default_factory=dict, description="Contributing factors and their values"
    )


# =============================================================================
# Enhanced Alert Models
# =============================================================================


class AlertRule(BaseModel):
    """
    Rule for triggering alerts based on event conditions.

    Supports filtering by event type, location, entities, and severity.
    """

    id: str = Field(..., description="Unique rule identifier")
    name: str = Field(..., description="Human-readable rule name")
    description: str = Field(default="", description="Rule description")
    status: AlertRuleStatus = Field(
        default=AlertRuleStatus.ACTIVE, description="Rule status"
    )

    # Filter conditions
    event_types: list[EventType] = Field(
        default_factory=list, description="Event types to match (empty = all)"
    )
    severity_thresholds: list[SeverityLevel] = Field(
        default_factory=list, description="Minimum severity levels to trigger"
    )
    locations: list[str] = Field(
        default_factory=list, description="Locations to monitor (empty = all)"
    )
    entity_ids: list[str] = Field(
        default_factory=list, description="Specific entity IDs to monitor"
    )

    # Notification settings
    channels: list[AlertChannel] = Field(
        default_factory=lambda: [AlertChannel.WEBHOOK],
        description="Delivery channels",
    )
    recipients: list[str] = Field(
        default_factory=list, description="Email addresses or webhook URLs"
    )

    # Metadata
    created_at: datetime = Field(default_factory=utc_now)
    updated_at: datetime = Field(default_factory=utc_now)
    created_by: str | None = Field(default=None, description="Creator user ID")

    def matches_event(self, event: "RiskEvent") -> bool:
        """Check if an event matches this rule's conditions."""
        # Check event type filter
        if self.event_types and event.event_type not in self.event_types:
            return False

        # Check severity filter
        if self.severity_thresholds:
            severity_order = [
                SeverityLevel.LOW,
                SeverityLevel.MEDIUM,
                SeverityLevel.HIGH,
                SeverityLevel.CRITICAL,
            ]
            min_severity = min(severity_order.index(s) for s in self.severity_thresholds)
            if severity_order.index(event.severity) < min_severity:
                return False

        # Check location filter
        if self.locations and event.location not in self.locations:
            return False

        # Check entity filter
        if self.entity_ids:
            if not any(eid in event.affected_entities for eid in self.entity_ids):
                return False

        return True


class AlertAcknowledgment(BaseModel):
    """Record of alert acknowledgment."""

    alert_id: str = Field(..., description="ID of the acknowledged alert")
    acknowledged_by: str = Field(..., description="User who acknowledged")
    acknowledged_at: datetime = Field(default_factory=utc_now)
    notes: str = Field(default="", description="Acknowledgment notes")
    resolution_action: str | None = Field(
        default=None, description="Action taken to resolve"
    )


class AlertDeliveryRecord(BaseModel):
    """Record of alert delivery attempt."""

    alert_id: str = Field(..., description="ID of the alert")
    channel: AlertChannel = Field(..., description="Delivery channel used")
    recipient: str = Field(..., description="Target recipient")
    sent_at: datetime = Field(default_factory=utc_now)
    delivered: bool = Field(default=False, description="Whether delivery succeeded")
    delivery_latency_ms: int | None = Field(
        default=None, ge=0, description="Delivery latency in milliseconds"
    )
    error_message: str | None = Field(
        default=None, description="Error message if delivery failed"
    )


# =============================================================================
# Enhanced Impact Assessment Models
# =============================================================================


class EnhancedImpactPath(BaseModel):
    """
    Enhanced path through the supply chain showing impact propagation.

    Extends ImpactPath with additional metadata for visualization and analysis.
    """

    path_id: str = Field(..., description="Unique path identifier")
    nodes: list[str] = Field(..., description="Ordered list of node IDs in the path")
    node_types: list[str] = Field(
        default_factory=list, description="Types of each node in the path"
    )
    relationship_types: list[RelationshipType] = Field(
        ..., description="Relationships traversed"
    )
    total_hops: int = Field(..., ge=0, description="Total number of hops in the path")
    criticality_score: float = Field(
        default=0.0, ge=0.0, le=1.0, description="Path criticality score"
    )
    affected_revenue: float = Field(
        default=0.0, ge=0.0, description="Estimated revenue impact"
    )
    has_alternative: bool = Field(
        default=False, description="Whether alternative paths exist"
    )

    @field_validator("criticality_score")
    @classmethod
    def validate_criticality(cls, v: float) -> float:
        """Round criticality to 3 decimal places."""
        return round(v, 3)


# =============================================================================
# Data Validation Models
# =============================================================================


class ValidationError(BaseModel):
    """Error encountered during data validation."""

    field: str = Field(..., description="Field that failed validation")
    message: str = Field(..., description="Error message")
    value: Any = Field(default=None, description="Invalid value")
    code: str = Field(default="validation_error", description="Error code")


class EntityValidationResult(BaseModel):
    """Result of validating an entity against the graph."""

    entity_id: str = Field(..., description="ID of the entity being validated")
    exists_in_graph: bool = Field(..., description="Whether entity exists in Neo4j")
    entity_type: str | None = Field(
        default=None, description="Type of entity if found"
    )
    validation_errors: list[ValidationError] = Field(
        default_factory=list, description="List of validation errors"
    )
    is_valid: bool = Field(default=True, description="Overall validation status")
    validated_at: datetime = Field(default_factory=utc_now)


class ReferentialIntegrityResult(BaseModel):
    """Result of checking referential integrity for a risk event."""

    risk_event_id: str = Field(..., description="ID of the risk event")
    all_entities_valid: bool = Field(
        ..., description="Whether all referenced entities exist"
    )
    missing_entities: list[str] = Field(
        default_factory=list, description="List of missing entity IDs"
    )
    orphaned_relationships: list[str] = Field(
        default_factory=list, description="List of orphaned relationship IDs"
    )
    checked_at: datetime = Field(default_factory=utc_now)


# =============================================================================
# Low Confidence Handling
# =============================================================================


class LowConfidenceFlag(BaseModel):
    """Flag for low confidence extractions requiring review."""

    event_id: str = Field(..., description="ID of the flagged event")
    original_confidence: float = Field(
        ..., ge=0.0, le=1.0, description="Original confidence score"
    )
    threshold: float = Field(
        ..., ge=0.0, le=1.0, description="Threshold that was not met"
    )
    flagged_at: datetime = Field(default_factory=utc_now)
    review_status: str = Field(
        default="pending", description="Review status: 'pending', 'approved', 'rejected'"
    )
    reviewed_by: str | None = Field(default=None, description="Reviewer user ID")
    reviewed_at: datetime | None = Field(default=None)
    review_notes: str | None = Field(default=None)

    @field_validator("review_status")
    @classmethod
    def validate_review_status(cls, v: str) -> str:
        """Validate review status is one of allowed values."""
        allowed = {"pending", "approved", "rejected"}
        if v.lower() not in allowed:
            raise ValueError(f"Review status must be one of {allowed}")
        return v.lower()

