"""
FastAPI Routes for Supply Chain Risk Monitoring.

Implements REST endpoints for risk queries, supply chain data access,
and alert management.
"""

from datetime import datetime, timezone
from typing import Any
import uuid

from fastapi import APIRouter, Depends, HTTPException, Query, status
import structlog

from src.api.schemas import (
    APIResponse,
    PaginatedResponse,
    PaginationMeta,
    RiskQueryRequest,
    RiskQueryResponse,
    SupplierSearchRequest,
    SupplierResponse,
    ComponentResponse,
    ProductResponse,
    AlertResponse,
    RiskEventCreateRequest,
    StatsResponse,
)
from src.api.auth import (
    get_api_key,
    check_rate_limit,
    APIKey,
    RequireReader,
    RequireWriter,
    RequireAdmin,
)
from src.models import RiskEvent, ImpactAssessment, EventType, SeverityLevel

logger = structlog.get_logger(__name__)

# Create routers
router = APIRouter()
risk_router = APIRouter(prefix="/risks", tags=["risks"])
supply_chain_router = APIRouter(prefix="/supply-chain", tags=["supply-chain"])
alert_router = APIRouter(prefix="/alerts", tags=["alerts"])


# =============================================================================
# In-Memory Data Stores (for demonstration)
# =============================================================================

_risk_events: dict[str, RiskEvent] = {}
_alerts: dict[str, dict[str, Any]] = {}
_suppliers: list[dict[str, Any]] = []
_components: list[dict[str, Any]] = []
_products: list[dict[str, Any]] = []


def _init_demo_data():
    """Initialize demo data for the API."""
    global _suppliers, _components, _products

    if _suppliers:
        return  # Already initialized

    # Demo suppliers
    _suppliers = [
        {
            "id": f"SUP-{i:04d}",
            "name": f"Supplier {i}",
            "tier": (i % 3) + 1,
            "location": ["Taiwan", "Vietnam", "China", "Germany", "USA"][i % 5],
            "risk_score": 25.0 + (i * 5) % 50,
            "components_supplied": 3 + (i % 5),
        }
        for i in range(20)
    ]

    # Demo components
    _components = [
        {
            "id": f"COMP-{i:04d}",
            "name": f"Component {i}",
            "category": ["Semiconductor", "PCB", "Display", "Battery", "Sensor"][i % 5],
            "suppliers": [f"SUP-{(i*2) % 20:04d}", f"SUP-{(i*2+1) % 20:04d}"],
            "products": [f"PROD-{(i // 3) % 10:04d}"],
        }
        for i in range(30)
    ]

    # Demo products
    _products = [
        {
            "id": f"PROD-{i:04d}",
            "name": f"Product {i}",
            "category": ["Electronics", "Automotive", "Medical", "Industrial"][i % 4],
            "risk_score": 15.0 + (i * 7) % 60,
            "component_count": 5 + (i % 10),
        }
        for i in range(10)
    ]


_init_demo_data()


# =============================================================================
# Risk Endpoints
# =============================================================================


@risk_router.get("", response_model=APIResponse[list[RiskEvent]])
async def list_risks(
    api_key: RequireReader,
    page: int = Query(default=1, ge=1),
    per_page: int = Query(default=20, ge=1, le=100),
    severity: SeverityLevel | None = None,
    event_type: EventType | None = None,
):
    """List all risk events with optional filtering."""
    logger.info("Listing risks", user=api_key.name)

    risks = list(_risk_events.values())

    # Apply filters
    if severity:
        risks = [r for r in risks if r.severity == severity]
    if event_type:
        risks = [r for r in risks if r.event_type == event_type]

    # Paginate
    total = len(risks)
    start = (page - 1) * per_page
    end = start + per_page
    paginated = risks[start:end]

    return APIResponse(
        success=True,
        data=paginated,
        meta={
            "total": total,
            "page": page,
            "per_page": per_page,
            "total_pages": (total + per_page - 1) // per_page,
        },
    )


@risk_router.get("/{risk_id}", response_model=APIResponse[RiskEvent])
async def get_risk(risk_id: str, api_key: RequireReader):
    """Get a specific risk event."""
    if risk_id not in _risk_events:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Risk event {risk_id} not found",
        )

    return APIResponse(success=True, data=_risk_events[risk_id])


@risk_router.post("", response_model=APIResponse[RiskEvent], status_code=201)
async def create_risk(request: RiskEventCreateRequest, api_key: RequireWriter):
    """Create a new risk event."""
    risk_id = f"RISK-{uuid.uuid4().hex[:8].upper()}"

    risk_event = RiskEvent(
        id=risk_id,
        event_type=request.event_type,
        location=request.location,
        affected_entities=request.affected_entities,
        severity=request.severity,
        confidence=request.confidence,
        source_url=request.source_url,
        description=request.description,
    )

    _risk_events[risk_id] = risk_event

    logger.info("Created risk event", risk_id=risk_id, user=api_key.name)

    return APIResponse(
        success=True,
        data=risk_event,
        message=f"Risk event {risk_id} created",
    )


@risk_router.delete("/{risk_id}", response_model=APIResponse[None])
async def delete_risk(risk_id: str, api_key: RequireAdmin):
    """Delete a risk event (admin only)."""
    if risk_id not in _risk_events:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Risk event {risk_id} not found",
        )

    del _risk_events[risk_id]

    logger.info("Deleted risk event", risk_id=risk_id, user=api_key.name)

    return APIResponse(success=True, message=f"Risk event {risk_id} deleted")


@risk_router.get("/query/product/{product_id}", response_model=APIResponse[RiskQueryResponse])
async def query_product_risks(
    product_id: str,
    api_key: RequireReader,
    include_paths: bool = False,
    max_depth: int = 5,
):
    """Query all risks affecting a specific product."""
    # Find product
    product = next((p for p in _products if p["id"] == product_id), None)
    if not product:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Product {product_id} not found",
        )

    # Get active risks (simplified - would use graph traversal in production)
    active_risks = list(_risk_events.values())[:5]

    # Create mock impact assessments
    assessments = [
        ImpactAssessment(
            risk_event_id=r.id,
            affected_products=[product_id],
            impact_paths=[],
            severity_score=5.0 + (hash(r.id) % 5),
            mitigation_options=["Monitor situation", "Contact suppliers"],
            redundancy_level=0.6,
        )
        for r in active_risks
    ]

    response = RiskQueryResponse(
        product_id=product_id,
        risk_score=product["risk_score"],
        active_risks=active_risks,
        impact_assessments=assessments,
        affected_entities_count=len(active_risks),
        last_updated=datetime.now(timezone.utc),
    )

    return APIResponse(success=True, data=response)


# =============================================================================
# Supply Chain Endpoints
# =============================================================================


@supply_chain_router.get("/suppliers", response_model=APIResponse[list[SupplierResponse]])
async def list_suppliers(
    api_key: RequireReader,
    page: int = Query(default=1, ge=1),
    per_page: int = Query(default=20, ge=1, le=100),
    location: str | None = None,
    tier: int | None = Query(default=None, ge=1, le=5),
):
    """List suppliers with optional filtering."""
    suppliers = _suppliers.copy()

    # Apply filters
    if location:
        suppliers = [s for s in suppliers if location.lower() in s["location"].lower()]
    if tier:
        suppliers = [s for s in suppliers if s["tier"] == tier]

    # Paginate
    total = len(suppliers)
    start = (page - 1) * per_page
    paginated = suppliers[start:start + per_page]

    return APIResponse(
        success=True,
        data=[SupplierResponse(**s) for s in paginated],
        meta={
            "total": total,
            "page": page,
            "per_page": per_page,
        },
    )


@supply_chain_router.get("/suppliers/{supplier_id}", response_model=APIResponse[SupplierResponse])
async def get_supplier(supplier_id: str, api_key: RequireReader):
    """Get a specific supplier."""
    supplier = next((s for s in _suppliers if s["id"] == supplier_id), None)
    if not supplier:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Supplier {supplier_id} not found",
        )

    return APIResponse(success=True, data=SupplierResponse(**supplier))


@supply_chain_router.get("/components", response_model=APIResponse[list[ComponentResponse]])
async def list_components(
    api_key: RequireReader,
    page: int = Query(default=1, ge=1),
    per_page: int = Query(default=20, ge=1, le=100),
    category: str | None = None,
):
    """List components with optional filtering."""
    components = _components.copy()

    if category:
        components = [c for c in components if category.lower() in c["category"].lower()]

    total = len(components)
    start = (page - 1) * per_page
    paginated = components[start:start + per_page]

    return APIResponse(
        success=True,
        data=[ComponentResponse(**c) for c in paginated],
        meta={"total": total, "page": page, "per_page": per_page},
    )


@supply_chain_router.get("/products", response_model=APIResponse[list[ProductResponse]])
async def list_products(
    api_key: RequireReader,
    page: int = Query(default=1, ge=1),
    per_page: int = Query(default=20, ge=1, le=100),
    category: str | None = None,
):
    """List products with optional filtering."""
    products = _products.copy()

    if category:
        products = [p for p in products if category.lower() in p["category"].lower()]

    total = len(products)
    start = (page - 1) * per_page
    paginated = products[start:start + per_page]

    return APIResponse(
        success=True,
        data=[ProductResponse(**p) for p in paginated],
        meta={"total": total, "page": page, "per_page": per_page},
    )


@supply_chain_router.get("/products/{product_id}", response_model=APIResponse[ProductResponse])
async def get_product(product_id: str, api_key: RequireReader):
    """Get a specific product."""
    product = next((p for p in _products if p["id"] == product_id), None)
    if not product:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Product {product_id} not found",
        )

    return APIResponse(success=True, data=ProductResponse(**product))


@supply_chain_router.get("/stats", response_model=APIResponse[StatsResponse])
async def get_stats(api_key: RequireReader):
    """Get supply chain statistics."""
    stats = StatsResponse(
        total_suppliers=len(_suppliers),
        total_components=len(_components),
        total_products=len(_products),
        active_risks=len(_risk_events),
        pending_alerts=len([a for a in _alerts.values() if not a.get("acknowledged")]),
        last_monitoring_run=datetime.now(timezone.utc),
        avg_risk_score=sum(p["risk_score"] for p in _products) / len(_products) if _products else 0,
    )

    return APIResponse(success=True, data=stats)


# =============================================================================
# Alert Endpoints
# =============================================================================


@alert_router.get("", response_model=APIResponse[list[AlertResponse]])
async def list_alerts(
    api_key: RequireReader,
    page: int = Query(default=1, ge=1),
    per_page: int = Query(default=20, ge=1, le=100),
    acknowledged: bool | None = None,
    severity: SeverityLevel | None = None,
):
    """List alerts with optional filtering."""
    alerts = list(_alerts.values())

    if acknowledged is not None:
        alerts = [a for a in alerts if a.get("acknowledged") == acknowledged]
    if severity:
        alerts = [a for a in alerts if a.get("severity") == severity]

    total = len(alerts)
    start = (page - 1) * per_page
    paginated = alerts[start:start + per_page]

    return APIResponse(
        success=True,
        data=[AlertResponse(**a) for a in paginated],
        meta={"total": total, "page": page, "per_page": per_page},
    )


@alert_router.get("/{alert_id}", response_model=APIResponse[AlertResponse])
async def get_alert(alert_id: str, api_key: RequireReader):
    """Get a specific alert."""
    if alert_id not in _alerts:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Alert {alert_id} not found",
        )

    return APIResponse(success=True, data=AlertResponse(**_alerts[alert_id]))


@alert_router.post("/{alert_id}/acknowledge", response_model=APIResponse[AlertResponse])
async def acknowledge_alert(alert_id: str, api_key: RequireWriter):
    """Acknowledge an alert."""
    if alert_id not in _alerts:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Alert {alert_id} not found",
        )

    _alerts[alert_id]["acknowledged"] = True
    _alerts[alert_id]["acknowledged_at"] = datetime.now(timezone.utc)

    logger.info("Alert acknowledged", alert_id=alert_id, user=api_key.name)

    return APIResponse(
        success=True,
        data=AlertResponse(**_alerts[alert_id]),
        message=f"Alert {alert_id} acknowledged",
    )


# Include routers in main router
router.include_router(risk_router)
router.include_router(supply_chain_router)
router.include_router(alert_router)
