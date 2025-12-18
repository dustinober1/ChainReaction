"""
Webhook Management API Routes.

REST endpoints for managing webhook registrations.
"""

from datetime import datetime, timezone

from fastapi import APIRouter, HTTPException, status
import structlog

from src.api.schemas import (
    APIResponse,
    WebhookRegistration,
    WebhookUpdate,
    WebhookResponse,
)
from src.api.auth import RequireReader, RequireWriter, RequireAdmin
from src.api.webhooks import get_webhook_manager, Webhook

logger = structlog.get_logger(__name__)

router = APIRouter()


def _webhook_to_response(webhook: Webhook) -> WebhookResponse:
    """Convert Webhook to WebhookResponse."""
    return WebhookResponse(
        id=webhook.id,
        url=webhook.url,
        events=webhook.events,
        active=webhook.active,
        created_at=webhook.created_at,
        last_triggered=webhook.last_triggered,
        delivery_count=webhook.delivery_count,
        failure_count=webhook.failure_count,
    )


@router.get("", response_model=APIResponse[list[WebhookResponse]])
async def list_webhooks(api_key: RequireReader):
    """List all registered webhooks."""
    manager = get_webhook_manager()
    webhooks = manager.list_webhooks()

    return APIResponse(
        success=True,
        data=[_webhook_to_response(w) for w in webhooks],
        meta={"total": len(webhooks)},
    )


@router.post("", response_model=APIResponse[WebhookResponse], status_code=201)
async def register_webhook(request: WebhookRegistration, api_key: RequireWriter):
    """Register a new webhook."""
    manager = get_webhook_manager()

    webhook = manager.register(
        url=request.url,
        events=request.events,
        secret=request.secret,
    )

    logger.info("Webhook registered", webhook_id=webhook.id, user=api_key.name)

    return APIResponse(
        success=True,
        data=_webhook_to_response(webhook),
        message=f"Webhook {webhook.id} registered",
    )


@router.get("/{webhook_id}", response_model=APIResponse[WebhookResponse])
async def get_webhook(webhook_id: str, api_key: RequireReader):
    """Get a specific webhook."""
    manager = get_webhook_manager()
    webhook = manager.get(webhook_id)

    if not webhook:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Webhook {webhook_id} not found",
        )

    return APIResponse(success=True, data=_webhook_to_response(webhook))


@router.patch("/{webhook_id}", response_model=APIResponse[WebhookResponse])
async def update_webhook(
    webhook_id: str, request: WebhookUpdate, api_key: RequireWriter
):
    """Update a webhook."""
    manager = get_webhook_manager()

    webhook = manager.update(
        webhook_id=webhook_id,
        url=request.url,
        events=request.events,
        secret=request.secret,
        active=request.active,
    )

    if not webhook:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Webhook {webhook_id} not found",
        )

    logger.info("Webhook updated", webhook_id=webhook_id, user=api_key.name)

    return APIResponse(
        success=True,
        data=_webhook_to_response(webhook),
        message=f"Webhook {webhook_id} updated",
    )


@router.delete("/{webhook_id}", response_model=APIResponse[None])
async def delete_webhook(webhook_id: str, api_key: RequireAdmin):
    """Delete a webhook (admin only)."""
    manager = get_webhook_manager()

    if not manager.delete(webhook_id):
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Webhook {webhook_id} not found",
        )

    logger.info("Webhook deleted", webhook_id=webhook_id, user=api_key.name)

    return APIResponse(success=True, message=f"Webhook {webhook_id} deleted")


@router.get("/{webhook_id}/deliveries", response_model=APIResponse[list[dict]])
async def list_webhook_deliveries(
    webhook_id: str,
    api_key: RequireReader,
    status_filter: str | None = None,
    limit: int = 50,
):
    """List deliveries for a webhook."""
    manager = get_webhook_manager()

    # Verify webhook exists
    webhook = manager.get(webhook_id)
    if not webhook:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Webhook {webhook_id} not found",
        )

    deliveries = manager.list_deliveries(
        webhook_id=webhook_id,
        status=status_filter,
        limit=limit,
    )

    return APIResponse(
        success=True,
        data=[
            {
                "id": d.id,
                "event_type": d.event_type,
                "status": d.status,
                "attempts": d.attempts,
                "response_code": d.response_code,
                "created_at": d.created_at.isoformat(),
                "delivered_at": d.delivered_at.isoformat() if d.delivered_at else None,
            }
            for d in deliveries
        ],
        meta={"total": len(deliveries)},
    )


@router.post("/{webhook_id}/test", response_model=APIResponse[dict])
async def test_webhook(webhook_id: str, api_key: RequireWriter):
    """Send a test event to a webhook."""
    manager = get_webhook_manager()

    webhook = manager.get(webhook_id)
    if not webhook:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Webhook {webhook_id} not found",
        )

    # Send test event
    delivery_ids = await manager.dispatch(
        event_type="test",
        payload={
            "message": "This is a test webhook delivery",
            "timestamp": datetime.now(timezone.utc).isoformat(),
        },
    )

    return APIResponse(
        success=True,
        data={"delivery_ids": delivery_ids},
        message="Test webhook sent",
    )


@router.get("/stats/overview", response_model=APIResponse[dict])
async def get_webhook_stats(api_key: RequireReader):
    """Get webhook system statistics."""
    manager = get_webhook_manager()
    stats = manager.get_stats()

    return APIResponse(success=True, data=stats)
