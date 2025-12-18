"""
Webhook Notification System.

Provides webhook registration, management, and delivery for real-time
alert notifications.
"""

import asyncio
import hashlib
import hmac
import json
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any
import uuid

import httpx
import structlog

from src.api.auth import generate_webhook_signature

logger = structlog.get_logger(__name__)


@dataclass
class WebhookDelivery:
    """Record of a webhook delivery attempt."""

    id: str
    webhook_id: str
    event_type: str
    payload: dict[str, Any]
    status: str  # pending, success, failed
    response_code: int | None = None
    response_body: str | None = None
    attempts: int = 0
    created_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    delivered_at: datetime | None = None


@dataclass
class Webhook:
    """Webhook registration."""

    id: str
    url: str
    events: list[str]
    secret: str | None = None
    active: bool = True
    created_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    last_triggered: datetime | None = None
    delivery_count: int = 0
    failure_count: int = 0


class WebhookManager:
    """
    Manages webhook registrations and deliveries.

    Provides:
    - Webhook registration and management
    - Event dispatching
    - Retry logic for failed deliveries
    - Delivery history tracking
    """

    MAX_RETRIES = 3
    RETRY_DELAYS = [5, 30, 120]  # Seconds between retries

    def __init__(self):
        """Initialize the webhook manager."""
        self._webhooks: dict[str, Webhook] = {}
        self._deliveries: dict[str, WebhookDelivery] = {}
        self._pending_retries: list[tuple[str, int]] = []

    def register(
        self,
        url: str,
        events: list[str],
        secret: str | None = None,
    ) -> Webhook:
        """
        Register a new webhook.

        Args:
            url: The webhook endpoint URL.
            events: List of event types to subscribe to.
            secret: Optional shared secret for HMAC signature.

        Returns:
            The created Webhook object.
        """
        webhook_id = f"WHK-{uuid.uuid4().hex[:8].upper()}"

        webhook = Webhook(
            id=webhook_id,
            url=url,
            events=events,
            secret=secret,
        )

        self._webhooks[webhook_id] = webhook

        logger.info("Webhook registered", webhook_id=webhook_id, url=url)

        return webhook

    def get(self, webhook_id: str) -> Webhook | None:
        """Get a webhook by ID."""
        return self._webhooks.get(webhook_id)

    def list_webhooks(self) -> list[Webhook]:
        """List all registered webhooks."""
        return list(self._webhooks.values())

    def update(
        self,
        webhook_id: str,
        url: str | None = None,
        events: list[str] | None = None,
        secret: str | None = None,
        active: bool | None = None,
    ) -> Webhook | None:
        """Update a webhook."""
        webhook = self._webhooks.get(webhook_id)
        if not webhook:
            return None

        if url is not None:
            webhook.url = url
        if events is not None:
            webhook.events = events
        if secret is not None:
            webhook.secret = secret
        if active is not None:
            webhook.active = active

        return webhook

    def delete(self, webhook_id: str) -> bool:
        """Delete a webhook."""
        if webhook_id in self._webhooks:
            del self._webhooks[webhook_id]
            logger.info("Webhook deleted", webhook_id=webhook_id)
            return True
        return False

    async def dispatch(
        self,
        event_type: str,
        payload: dict[str, Any],
    ) -> list[str]:
        """
        Dispatch an event to all subscribed webhooks.

        Args:
            event_type: The type of event (e.g., "alert.created").
            payload: The event payload.

        Returns:
            List of delivery IDs.
        """
        delivery_ids = []

        for webhook in self._webhooks.values():
            if not webhook.active:
                continue

            if event_type not in webhook.events and "*" not in webhook.events:
                continue

            delivery_id = await self._deliver(webhook, event_type, payload)
            delivery_ids.append(delivery_id)

        return delivery_ids

    async def _deliver(
        self,
        webhook: Webhook,
        event_type: str,
        payload: dict[str, Any],
    ) -> str:
        """
        Deliver a payload to a webhook.

        Args:
            webhook: The target webhook.
            event_type: The event type.
            payload: The event payload.

        Returns:
            The delivery ID.
        """
        delivery_id = f"DLV-{uuid.uuid4().hex[:8].upper()}"

        delivery = WebhookDelivery(
            id=delivery_id,
            webhook_id=webhook.id,
            event_type=event_type,
            payload=payload,
            status="pending",
        )

        self._deliveries[delivery_id] = delivery

        # Attempt delivery
        success = await self._attempt_delivery(delivery, webhook)

        if success:
            delivery.status = "success"
            delivery.delivered_at = datetime.now(timezone.utc)
            webhook.delivery_count += 1
            webhook.last_triggered = datetime.now(timezone.utc)
        else:
            delivery.status = "failed"
            webhook.failure_count += 1

            # Schedule retry if within limit
            if delivery.attempts < self.MAX_RETRIES:
                self._pending_retries.append((delivery_id, delivery.attempts))

        return delivery_id

    async def _attempt_delivery(
        self,
        delivery: WebhookDelivery,
        webhook: Webhook,
    ) -> bool:
        """
        Attempt to deliver a webhook payload.

        Args:
            delivery: The delivery record.
            webhook: The target webhook.

        Returns:
            True if delivery succeeded.
        """
        delivery.attempts += 1

        # Prepare payload
        body = {
            "event": delivery.event_type,
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "data": delivery.payload,
        }

        body_bytes = json.dumps(body).encode()

        # Prepare headers
        headers = {
            "Content-Type": "application/json",
            "X-Webhook-Event": delivery.event_type,
            "X-Webhook-Delivery": delivery.id,
        }

        # Add signature if secret is configured
        if webhook.secret:
            signature = generate_webhook_signature(body_bytes, webhook.secret)
            headers["X-Webhook-Signature"] = f"sha256={signature}"

        # Send request
        try:
            async with httpx.AsyncClient(timeout=30.0) as client:
                response = await client.post(
                    webhook.url,
                    content=body_bytes,
                    headers=headers,
                )

                delivery.response_code = response.status_code
                delivery.response_body = response.text[:500]

                if 200 <= response.status_code < 300:
                    logger.info(
                        "Webhook delivery succeeded",
                        delivery_id=delivery.id,
                        webhook_id=webhook.id,
                        status_code=response.status_code,
                    )
                    return True
                else:
                    logger.warning(
                        "Webhook delivery failed",
                        delivery_id=delivery.id,
                        webhook_id=webhook.id,
                        status_code=response.status_code,
                    )
                    return False

        except Exception as e:
            logger.error(
                "Webhook delivery error",
                delivery_id=delivery.id,
                webhook_id=webhook.id,
                error=str(e),
            )
            delivery.response_body = str(e)
            return False

    async def process_retries(self) -> int:
        """
        Process pending retries.

        Returns:
            Number of retries processed.
        """
        processed = 0
        remaining = []

        for delivery_id, attempt in self._pending_retries:
            delivery = self._deliveries.get(delivery_id)
            if not delivery:
                continue

            webhook = self._webhooks.get(delivery.webhook_id)
            if not webhook or not webhook.active:
                continue

            # Wait for retry delay
            if attempt < len(self.RETRY_DELAYS):
                await asyncio.sleep(self.RETRY_DELAYS[attempt])

            success = await self._attempt_delivery(delivery, webhook)

            if success:
                delivery.status = "success"
                delivery.delivered_at = datetime.now(timezone.utc)
                webhook.delivery_count += 1
            elif delivery.attempts < self.MAX_RETRIES:
                remaining.append((delivery_id, delivery.attempts))
            else:
                delivery.status = "failed"

            processed += 1

        self._pending_retries = remaining
        return processed

    def get_delivery(self, delivery_id: str) -> WebhookDelivery | None:
        """Get a delivery by ID."""
        return self._deliveries.get(delivery_id)

    def list_deliveries(
        self,
        webhook_id: str | None = None,
        status: str | None = None,
        limit: int = 50,
    ) -> list[WebhookDelivery]:
        """List deliveries with optional filtering."""
        deliveries = list(self._deliveries.values())

        if webhook_id:
            deliveries = [d for d in deliveries if d.webhook_id == webhook_id]
        if status:
            deliveries = [d for d in deliveries if d.status == status]

        # Sort by creation time (newest first) and limit
        deliveries.sort(key=lambda d: d.created_at, reverse=True)
        return deliveries[:limit]

    def get_stats(self) -> dict[str, Any]:
        """Get webhook system statistics."""
        return {
            "total_webhooks": len(self._webhooks),
            "active_webhooks": len([w for w in self._webhooks.values() if w.active]),
            "total_deliveries": len(self._deliveries),
            "successful_deliveries": len(
                [d for d in self._deliveries.values() if d.status == "success"]
            ),
            "failed_deliveries": len(
                [d for d in self._deliveries.values() if d.status == "failed"]
            ),
            "pending_retries": len(self._pending_retries),
        }


# Global webhook manager instance
_webhook_manager: WebhookManager | None = None


def get_webhook_manager() -> WebhookManager:
    """Get the global webhook manager."""
    global _webhook_manager
    if _webhook_manager is None:
        _webhook_manager = WebhookManager()
    return _webhook_manager


# =============================================================================
# Helper Functions
# =============================================================================


async def dispatch_alert_webhook(alert: dict[str, Any]) -> list[str]:
    """
    Dispatch an alert.created webhook event.

    Args:
        alert: The alert data.

    Returns:
        List of delivery IDs.
    """
    manager = get_webhook_manager()
    return await manager.dispatch("alert.created", alert)


async def dispatch_risk_event_webhook(risk_event: dict[str, Any]) -> list[str]:
    """
    Dispatch a risk.created webhook event.

    Args:
        risk_event: The risk event data.

    Returns:
        List of delivery IDs.
    """
    manager = get_webhook_manager()
    return await manager.dispatch("risk.created", risk_event)
