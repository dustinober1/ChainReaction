"""
ChainReaction API Module.

Contains FastAPI application, routes, and authentication.
"""

from src.api.main import app, create_app
from src.api.schemas import (
    APIResponse,
    PaginatedResponse,
    PaginationMeta,
    HealthResponse,
    RiskQueryResponse,
    SupplierResponse,
    ComponentResponse,
    ProductResponse,
    AlertResponse,
    WebhookResponse,
    StatsResponse,
)
from src.api.auth import (
    APIKey,
    APIKeyStore,
    get_api_key,
    get_key_store,
    check_rate_limit,
    RateLimiter,
)
from src.api.webhooks import (
    Webhook,
    WebhookDelivery,
    WebhookManager,
    get_webhook_manager,
    dispatch_alert_webhook,
    dispatch_risk_event_webhook,
)

__all__ = [
    # App
    "app",
    "create_app",
    # Schemas
    "APIResponse",
    "PaginatedResponse",
    "PaginationMeta",
    "HealthResponse",
    "RiskQueryResponse",
    "SupplierResponse",
    "ComponentResponse",
    "ProductResponse",
    "AlertResponse",
    "WebhookResponse",
    "StatsResponse",
    # Auth
    "APIKey",
    "APIKeyStore",
    "get_api_key",
    "get_key_store",
    "check_rate_limit",
    "RateLimiter",
    # Webhooks
    "Webhook",
    "WebhookDelivery",
    "WebhookManager",
    "get_webhook_manager",
    "dispatch_alert_webhook",
    "dispatch_risk_event_webhook",
]
