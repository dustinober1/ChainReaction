"""
Unit tests for the REST API and webhook system.
"""

import pytest
from datetime import datetime, timezone
from fastapi.testclient import TestClient

from src.api.main import app
from src.api.schemas import (
    APIResponse,
    SupplierResponse,
    ProductResponse,
    RiskQueryRequest,
)
from src.api.auth import (
    APIKey,
    APIKeyStore,
    RateLimiter,
    get_key_store,
)
from src.api.webhooks import WebhookManager
from src.config import get_settings


# Create test client
client = TestClient(app)


def get_auth_header() -> dict[str, str]:
    """Get authentication header with development API key."""
    settings = get_settings()
    return {"X-API-Key": settings.api_key.get_secret_value()}


class TestHealthEndpoint:
    """Tests for health check endpoint."""

    def test_health_check(self):
        """Test health check returns 200."""
        response = client.get("/health")

        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "healthy"
        assert "version" in data
        assert "timestamp" in data

    def test_root_endpoint(self):
        """Test root endpoint."""
        response = client.get("/")

        assert response.status_code == 200
        data = response.json()
        assert data["success"] is True
        assert "ChainReaction" in data["data"]["name"]


class TestAuthentication:
    """Tests for authentication middleware."""

    def test_missing_api_key(self):
        """Test that missing API key returns 401."""
        response = client.get("/api/v1/supply-chain/stats")

        assert response.status_code == 401
        data = response.json()
        assert "Missing API key" in data["detail"]

    def test_invalid_api_key(self):
        """Test that invalid API key returns 401."""
        response = client.get(
            "/api/v1/supply-chain/stats",
            headers={"X-API-Key": "invalid-key"},
        )

        assert response.status_code == 401
        assert "Invalid API key" in response.json()["detail"]

    def test_valid_api_key(self):
        """Test that valid API key succeeds."""
        response = client.get(
            "/api/v1/supply-chain/stats",
            headers=get_auth_header(),
        )

        assert response.status_code == 200


class TestSupplyChainEndpoints:
    """Tests for supply chain endpoints."""

    def test_list_suppliers(self):
        """Test listing suppliers."""
        response = client.get(
            "/api/v1/supply-chain/suppliers",
            headers=get_auth_header(),
        )

        assert response.status_code == 200
        data = response.json()
        assert data["success"] is True
        assert isinstance(data["data"], list)

    def test_list_suppliers_with_filter(self):
        """Test filtering suppliers by location."""
        response = client.get(
            "/api/v1/supply-chain/suppliers?location=Taiwan",
            headers=get_auth_header(),
        )

        assert response.status_code == 200
        data = response.json()
        for supplier in data["data"]:
            assert "Taiwan" in supplier["location"]

    def test_get_supplier_not_found(self):
        """Test getting non-existent supplier."""
        response = client.get(
            "/api/v1/supply-chain/suppliers/SUP-99999",
            headers=get_auth_header(),
        )

        assert response.status_code == 404

    def test_list_components(self):
        """Test listing components."""
        response = client.get(
            "/api/v1/supply-chain/components",
            headers=get_auth_header(),
        )

        assert response.status_code == 200
        data = response.json()
        assert data["success"] is True
        assert isinstance(data["data"], list)

    def test_list_products(self):
        """Test listing products."""
        response = client.get(
            "/api/v1/supply-chain/products",
            headers=get_auth_header(),
        )

        assert response.status_code == 200
        data = response.json()
        assert data["success"] is True

    def test_get_stats(self):
        """Test getting statistics."""
        response = client.get(
            "/api/v1/supply-chain/stats",
            headers=get_auth_header(),
        )

        assert response.status_code == 200
        data = response.json()
        assert "total_suppliers" in data["data"]
        assert "total_products" in data["data"]


class TestRiskEndpoints:
    """Tests for risk management endpoints."""

    def test_list_risks(self):
        """Test listing risks."""
        response = client.get(
            "/api/v1/risks",
            headers=get_auth_header(),
        )

        assert response.status_code == 200
        data = response.json()
        assert data["success"] is True

    def test_create_risk(self):
        """Test creating a risk event."""
        risk_data = {
            "event_type": "Weather",
            "location": "Taiwan",
            "affected_entities": ["TSMC"],
            "severity": "High",
            "confidence": 0.9,
            "source_url": "https://test.com",
            "description": "Test typhoon event",
        }

        response = client.post(
            "/api/v1/risks",
            json=risk_data,
            headers=get_auth_header(),
        )

        assert response.status_code == 201
        data = response.json()
        assert data["success"] is True
        assert data["data"]["id"].startswith("RISK-")

    def test_query_product_risks(self):
        """Test querying product risks."""
        response = client.get(
            "/api/v1/risks/query/product/PROD-0001",
            headers=get_auth_header(),
        )

        assert response.status_code == 200
        data = response.json()
        assert data["data"]["product_id"] == "PROD-0001"


class TestAlertEndpoints:
    """Tests for alert management endpoints."""

    def test_list_alerts(self):
        """Test listing alerts."""
        response = client.get(
            "/api/v1/alerts",
            headers=get_auth_header(),
        )

        assert response.status_code == 200
        data = response.json()
        assert data["success"] is True


class TestWebhookEndpoints:
    """Tests for webhook management endpoints."""

    def test_list_webhooks(self):
        """Test listing webhooks."""
        response = client.get(
            "/api/v1/webhooks",
            headers=get_auth_header(),
        )

        assert response.status_code == 200
        data = response.json()
        assert data["success"] is True

    def test_register_webhook(self):
        """Test registering a webhook."""
        webhook_data = {
            "url": "https://example.com/webhook",
            "events": ["alert.created"],
            "active": True,
        }

        response = client.post(
            "/api/v1/webhooks",
            json=webhook_data,
            headers=get_auth_header(),
        )

        assert response.status_code == 201
        data = response.json()
        assert data["success"] is True
        assert data["data"]["id"].startswith("WHK-")

    def test_get_webhook_stats(self):
        """Test getting webhook statistics."""
        response = client.get(
            "/api/v1/webhooks/stats/overview",
            headers=get_auth_header(),
        )

        assert response.status_code == 200
        data = response.json()
        assert "total_webhooks" in data["data"]


class TestAPIKeyStore:
    """Tests for APIKeyStore."""

    def test_create_key(self):
        """Test creating an API key."""
        store = APIKeyStore()
        key = store.create_key(name="Test Key", role="reader")

        assert key.name == "Test Key"
        assert key.role == "reader"
        assert key.active is True
        assert len(key.key) > 20

    def test_revoke_key(self):
        """Test revoking an API key."""
        store = APIKeyStore()
        key = store.create_key(name="Revokable Key")

        result = store.revoke_key(key.key)

        assert result is True
        assert store.get_key(key.key).active is False

    def test_list_keys(self):
        """Test listing API keys."""
        store = APIKeyStore()
        store.create_key(name="Key 1")
        store.create_key(name="Key 2")

        keys = store.list_keys()

        # Should include development key + 2 created keys
        assert len(keys) >= 2


class TestRateLimiter:
    """Tests for RateLimiter."""

    def test_allows_within_limit(self):
        """Test that requests within limit are allowed."""
        limiter = RateLimiter(requests_per_minute=5)

        for _ in range(5):
            assert limiter.is_allowed("client")

    def test_blocks_over_limit(self):
        """Test that requests over limit are blocked."""
        limiter = RateLimiter(requests_per_minute=2)

        limiter.is_allowed("client")
        limiter.is_allowed("client")

        assert not limiter.is_allowed("client")

    def test_separate_clients(self):
        """Test that clients are tracked separately."""
        limiter = RateLimiter(requests_per_minute=2)

        limiter.is_allowed("client1")
        limiter.is_allowed("client1")

        # Client 2 should still have quota
        assert limiter.is_allowed("client2")


class TestWebhookManager:
    """Tests for WebhookManager."""

    def test_register_and_retrieve(self):
        """Test webhook registration and retrieval."""
        manager = WebhookManager()

        webhook = manager.register(
            url="https://test.com/webhook",
            events=["alert.created"],
        )

        retrieved = manager.get(webhook.id)

        assert retrieved is not None
        assert retrieved.url == "https://test.com/webhook"

    def test_update_webhook(self):
        """Test updating a webhook."""
        manager = WebhookManager()

        webhook = manager.register(
            url="https://test.com/webhook",
            events=["alert.created"],
        )

        manager.update(webhook.id, active=False)

        updated = manager.get(webhook.id)
        assert updated.active is False

    def test_delete_webhook(self):
        """Test deleting a webhook."""
        manager = WebhookManager()

        webhook = manager.register(
            url="https://test.com/webhook",
            events=["alert.created"],
        )

        assert manager.delete(webhook.id) is True
        assert manager.get(webhook.id) is None

    def test_list_deliveries(self):
        """Test listing webhook deliveries."""
        manager = WebhookManager()

        deliveries = manager.list_deliveries()
        assert isinstance(deliveries, list)
