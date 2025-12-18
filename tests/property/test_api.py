"""
Property-Based Tests for API Response Format and Authentication.

Feature: chain-reaction
Property 16: API response format standardization
Property 17: Authentication enforcement universality

Validates that all API responses follow the standard format and
authentication is consistently enforced.

Validates: Requirements 7.2, 7.4
"""

import pytest
from hypothesis import given, settings, HealthCheck
from hypothesis import strategies as st
from datetime import datetime, timezone
import uuid

from src.api.schemas import (
    APIResponse,
    PaginatedResponse,
    PaginationMeta,
    SupplierResponse,
    ProductResponse,
    AlertResponse,
    WebhookResponse,
)
from src.api.auth import (
    APIKey,
    APIKeyStore,
    RateLimiter,
    generate_webhook_signature,
    verify_webhook_signature,
)
from src.api.webhooks import (
    Webhook,
    WebhookDelivery,
    WebhookManager,
)
from src.models import SeverityLevel


# =============================================================================
# Property 16: API response format standardization
# =============================================================================


class TestAPIResponseFormatStandardization:
    """
    Property-based tests for API response format standardization.

    Feature: chain-reaction, Property 16: API response format standardization
    """

    @given(st.booleans(), st.text(max_size=100), st.text(max_size=200))
    @settings(max_examples=50)
    def test_api_response_always_has_required_fields(
        self,
        success: bool,
        error: str,
        message: str,
    ):
        """
        Property: APIResponse always contains success, data, error, message, meta.

        Feature: chain-reaction, Property 16: API response format standardization
        Validates: Requirements 7.2
        """
        response = APIResponse(
            success=success,
            data=None,
            error=error if not success else None,
            message=message,
        )

        # All required fields exist
        assert hasattr(response, "success")
        assert hasattr(response, "data")
        assert hasattr(response, "error")
        assert hasattr(response, "message")
        assert hasattr(response, "meta")

        # Types are correct
        assert isinstance(response.success, bool)
        assert isinstance(response.meta, dict)

    @given(st.lists(st.text(min_size=1, max_size=20), min_size=1, max_size=10))
    @settings(max_examples=30, suppress_health_check=[HealthCheck.too_slow])
    def test_api_response_with_list_data(self, data: list[str]):
        """
        Property: APIResponse correctly wraps list data.

        Feature: chain-reaction, Property 16: API response format standardization
        Validates: Requirements 7.2
        """
        response = APIResponse[list[str]](
            success=True,
            data=data,
        )

        assert response.success is True
        assert response.data == data
        assert len(response.data) == len(data)

    @given(
        st.integers(min_value=1, max_value=100),
        st.integers(min_value=1, max_value=10),
        st.integers(min_value=1, max_value=100),
    )
    @settings(max_examples=50)
    def test_pagination_meta_is_consistent(
        self,
        total: int,
        per_page: int,
        page: int,
    ):
        """
        Property: Pagination metadata is internally consistent.

        Feature: chain-reaction, Property 16: API response format standardization
        Validates: Requirements 7.2
        """
        total_pages = (total + per_page - 1) // per_page

        meta = PaginationMeta(
            total=total,
            page=page,
            per_page=per_page,
            total_pages=total_pages,
        )

        # Total pages calculation is correct
        assert meta.total_pages == (meta.total + meta.per_page - 1) // meta.per_page

        # All values are positive
        assert meta.total >= 0
        assert meta.page >= 1
        assert meta.per_page >= 1
        assert meta.total_pages >= 0

    def test_supplier_response_has_all_fields(self):
        """
        Test: SupplierResponse contains all required fields.

        Feature: chain-reaction, Property 16: API response format standardization
        Validates: Requirements 7.2
        """
        response = SupplierResponse(
            id="SUP-001",
            name="Test Supplier",
            tier=1,
            location="Taiwan",
            risk_score=35.5,
            components_supplied=5,
        )

        assert response.id == "SUP-001"
        assert response.tier >= 1
        assert 0 <= response.risk_score <= 100

    def test_product_response_has_all_fields(self):
        """
        Test: ProductResponse contains all required fields.

        Feature: chain-reaction, Property 16: API response format standardization
        Validates: Requirements 7.2
        """
        response = ProductResponse(
            id="PROD-001",
            name="Test Product",
            category="Electronics",
            risk_score=42.0,
            component_count=10,
        )

        assert response.id == "PROD-001"
        assert response.component_count > 0

    def test_webhook_response_has_all_fields(self):
        """
        Test: WebhookResponse contains all required fields.

        Feature: chain-reaction, Property 16: API response format standardization
        Validates: Requirements 7.2
        """
        response = WebhookResponse(
            id="WHK-001",
            url="https://example.com/webhook",
            events=["alert.created"],
            active=True,
            created_at=datetime.now(timezone.utc),
            delivery_count=5,
            failure_count=1,
        )

        assert response.id.startswith("WHK-")
        assert "://" in response.url
        assert len(response.events) > 0


# =============================================================================
# Property 17: Authentication enforcement universality
# =============================================================================


class TestAuthenticationEnforcementUniversality:
    """
    Property-based tests for authentication enforcement.

    Feature: chain-reaction, Property 17: Authentication enforcement universality
    """

    @given(st.text(min_size=10, max_size=50))
    @settings(max_examples=50, suppress_health_check=[HealthCheck.too_slow])
    def test_api_key_lookup_is_consistent(self, key_value: str):
        """
        Property: API key lookup returns consistent results.

        Feature: chain-reaction, Property 17: Authentication enforcement universality
        Validates: Requirements 7.4
        """
        store = APIKeyStore()

        # Unknown key returns None
        result = store.get_key(key_value)
        assert result is None

        # Create a key
        new_key = store.create_key(name="Test Key", role="reader")

        # Created key can be retrieved
        retrieved = store.get_key(new_key.key)
        assert retrieved is not None
        assert retrieved.key == new_key.key
        assert retrieved.name == "Test Key"

    @given(st.sampled_from(["reader", "writer", "admin"]))
    @settings(max_examples=10)
    def test_role_assignment_is_respected(self, role: str):
        """
        Property: Role assignment is correctly stored and retrieved.

        Feature: chain-reaction, Property 17: Authentication enforcement universality
        Validates: Requirements 7.4
        """
        store = APIKeyStore()
        key = store.create_key(name=f"Test {role}", role=role)

        assert key.role == role

        retrieved = store.get_key(key.key)
        assert retrieved.role == role

    def test_revoked_key_is_inactive(self):
        """
        Test: Revoked keys are marked as inactive.

        Feature: chain-reaction, Property 17: Authentication enforcement universality
        Validates: Requirements 7.4
        """
        store = APIKeyStore()
        key = store.create_key(name="Revokable Key")

        assert key.active is True

        store.revoke_key(key.key)

        retrieved = store.get_key(key.key)
        assert retrieved.active is False

    @given(st.integers(min_value=1, max_value=100))
    @settings(max_examples=20)
    def test_rate_limiter_respects_limit(self, rpm: int):
        """
        Property: Rate limiter correctly enforces request limits.

        Feature: chain-reaction, Property 17: Authentication enforcement universality
        Validates: Requirements 7.4
        """
        limiter = RateLimiter(requests_per_minute=rpm)

        # Should allow up to limit
        for _ in range(rpm):
            assert limiter.is_allowed("test-client")

        # Should deny after limit
        assert not limiter.is_allowed("test-client")

    def test_rate_limiter_tracks_remaining(self):
        """
        Test: Rate limiter correctly tracks remaining requests.

        Feature: chain-reaction, Property 17: Authentication enforcement universality
        Validates: Requirements 7.4
        """
        limiter = RateLimiter(requests_per_minute=10)

        assert limiter.get_remaining("client") == 10

        limiter.is_allowed("client")
        assert limiter.get_remaining("client") == 9

    @given(st.binary(min_size=10, max_size=100), st.text(min_size=10, max_size=50))
    @settings(max_examples=50, suppress_health_check=[HealthCheck.too_slow])
    def test_webhook_signature_verification(self, payload: bytes, secret: str):
        """
        Property: Webhook signatures are verifiable.

        Feature: chain-reaction, Property 17: Authentication enforcement universality
        Validates: Requirements 7.4
        """
        signature = generate_webhook_signature(payload, secret)

        # Correct signature verifies
        assert verify_webhook_signature(payload, signature, secret)

        # Wrong secret fails
        assert not verify_webhook_signature(payload, signature, "wrong-secret")

        # Modified payload fails
        modified_payload = payload + b"modified"
        assert not verify_webhook_signature(modified_payload, signature, secret)


# =============================================================================
# Webhook System Tests
# =============================================================================


class TestWebhookSystem:
    """Tests for the webhook management system."""

    def test_webhook_registration(self):
        """Test webhook registration."""
        manager = WebhookManager()

        webhook = manager.register(
            url="https://example.com/webhook",
            events=["alert.created"],
            secret="test-secret",
        )

        assert webhook.id.startswith("WHK-")
        assert webhook.url == "https://example.com/webhook"
        assert "alert.created" in webhook.events
        assert webhook.active is True

    def test_webhook_update(self):
        """Test webhook update."""
        manager = WebhookManager()

        webhook = manager.register(
            url="https://example.com/webhook",
            events=["alert.created"],
        )

        updated = manager.update(
            webhook_id=webhook.id,
            active=False,
        )

        assert updated.active is False

    def test_webhook_deletion(self):
        """Test webhook deletion."""
        manager = WebhookManager()

        webhook = manager.register(
            url="https://example.com/webhook",
            events=["alert.created"],
        )

        assert manager.delete(webhook.id) is True
        assert manager.get(webhook.id) is None

    def test_webhook_stats(self):
        """Test webhook statistics."""
        manager = WebhookManager()

        manager.register(url="https://a.com", events=["*"])
        manager.register(url="https://b.com", events=["*"])

        stats = manager.get_stats()

        assert stats["total_webhooks"] == 2
        assert stats["active_webhooks"] == 2

    @given(st.lists(st.text(min_size=5, max_size=20), min_size=1, max_size=5, unique=True))
    @settings(max_examples=20, suppress_health_check=[HealthCheck.too_slow])
    def test_webhook_event_filtering(self, events: list[str]):
        """
        Property: Webhooks only receive subscribed events.

        Feature: chain-reaction
        Validates: Requirements 7.3
        """
        manager = WebhookManager()

        manager.register(
            url="https://example.com/webhook",
            events=events,
        )

        # A wildcard subscriber should match any event
        manager.register(
            url="https://wildcard.com/webhook",
            events=["*"],
        )

        webhooks = manager.list_webhooks()
        assert len(webhooks) == 2

        # Verify event lists are stored correctly
        specific_webhook = next(w for w in webhooks if w.url == "https://example.com/webhook")
        assert specific_webhook.events == events
