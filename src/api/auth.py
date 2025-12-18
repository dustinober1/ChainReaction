"""
Authentication and Authorization Middleware.

Provides API key authentication and role-based access control.
"""

import hashlib
import hmac
import secrets
from datetime import datetime, timezone
from functools import wraps
from typing import Annotated

from fastapi import Depends, HTTPException, Header, Request, status
from fastapi.security import APIKeyHeader
from pydantic import BaseModel, Field
import structlog

from src.config import get_settings

logger = structlog.get_logger(__name__)


# =============================================================================
# API Key Management
# =============================================================================


class APIKey(BaseModel):
    """API key with metadata."""

    key: str
    name: str
    role: str = "reader"  # reader, writer, admin
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    expires_at: datetime | None = None
    active: bool = True


class APIKeyStore:
    """
    In-memory API key store.

    In production, this would be backed by a database.
    """

    def __init__(self):
        """Initialize the key store with default development key."""
        self._keys: dict[str, APIKey] = {}

        # Create default development key
        settings = get_settings()
        dev_key = settings.api_key.get_secret_value()
        self._keys[dev_key] = APIKey(
            key=dev_key,
            name="Development Key",
            role="admin",
        )

    def get_key(self, key: str) -> APIKey | None:
        """Get an API key by its value."""
        return self._keys.get(key)

    def create_key(self, name: str, role: str = "reader") -> APIKey:
        """Create a new API key."""
        key = secrets.token_urlsafe(32)
        api_key = APIKey(key=key, name=name, role=role)
        self._keys[key] = api_key
        return api_key

    def revoke_key(self, key: str) -> bool:
        """Revoke an API key."""
        if key in self._keys:
            self._keys[key].active = False
            return True
        return False

    def list_keys(self) -> list[APIKey]:
        """List all API keys."""
        return list(self._keys.values())


# Global key store instance
_key_store: APIKeyStore | None = None


def get_key_store() -> APIKeyStore:
    """Get the global API key store."""
    global _key_store
    if _key_store is None:
        _key_store = APIKeyStore()
    return _key_store


# =============================================================================
# Authentication Dependencies
# =============================================================================

api_key_header = APIKeyHeader(name="X-API-Key", auto_error=False)


async def get_api_key(
    api_key: Annotated[str | None, Depends(api_key_header)],
) -> APIKey:
    """
    Validate API key and return key metadata.

    Raises:
        HTTPException: If API key is missing or invalid.
    """
    if not api_key:
        logger.warning("Missing API key")
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Missing API key",
            headers={"WWW-Authenticate": "X-API-Key"},
        )

    key_store = get_key_store()
    key_data = key_store.get_key(api_key)

    if not key_data:
        logger.warning("Invalid API key")
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid API key",
            headers={"WWW-Authenticate": "X-API-Key"},
        )

    if not key_data.active:
        logger.warning("Revoked API key used", key_name=key_data.name)
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="API key has been revoked",
        )

    if key_data.expires_at and key_data.expires_at < datetime.now(timezone.utc):
        logger.warning("Expired API key used", key_name=key_data.name)
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="API key has expired",
        )

    return key_data


def require_role(required_role: str):
    """
    Create a dependency that requires a specific role.

    Args:
        required_role: The minimum role required (reader < writer < admin).

    Returns:
        Dependency function.
    """
    role_hierarchy = {"reader": 0, "writer": 1, "admin": 2}

    async def check_role(api_key: APIKey = Depends(get_api_key)) -> APIKey:
        if role_hierarchy.get(api_key.role, 0) < role_hierarchy.get(required_role, 0):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"Insufficient permissions. Required role: {required_role}",
            )
        return api_key

    return check_role


# Create specific role dependencies
_require_writer = require_role("writer")
_require_admin = require_role("admin")


# Convenience dependencies
RequireReader = Annotated[APIKey, Depends(get_api_key)]
RequireWriter = Annotated[APIKey, Depends(_require_writer)]
RequireAdmin = Annotated[APIKey, Depends(_require_admin)]


# =============================================================================
# Webhook Signature Verification
# =============================================================================


def generate_webhook_signature(payload: bytes, secret: str) -> str:
    """
    Generate HMAC signature for webhook payload.

    Args:
        payload: The payload bytes.
        secret: The shared secret.

    Returns:
        Hex-encoded HMAC-SHA256 signature.
    """
    return hmac.new(
        secret.encode(),
        payload,
        hashlib.sha256,
    ).hexdigest()


def verify_webhook_signature(
    payload: bytes,
    signature: str,
    secret: str,
) -> bool:
    """
    Verify webhook payload signature.

    Args:
        payload: The payload bytes.
        signature: The provided signature.
        secret: The shared secret.

    Returns:
        True if signature is valid.
    """
    expected = generate_webhook_signature(payload, secret)
    return hmac.compare_digest(signature, expected)


# =============================================================================
# Rate Limiting (Simple In-Memory)
# =============================================================================


class RateLimiter:
    """
    Simple in-memory rate limiter.

    In production, use Redis-backed rate limiting.
    """

    def __init__(self, requests_per_minute: int = 60):
        """Initialize the rate limiter."""
        self.rpm = requests_per_minute
        self._requests: dict[str, list[datetime]] = {}

    def is_allowed(self, client_id: str) -> bool:
        """Check if a request is allowed."""
        now = datetime.now(timezone.utc)
        minute_ago = now.replace(second=0, microsecond=0)

        if client_id not in self._requests:
            self._requests[client_id] = []

        # Filter to requests in current minute
        self._requests[client_id] = [
            t for t in self._requests[client_id] if t >= minute_ago
        ]

        if len(self._requests[client_id]) >= self.rpm:
            return False

        self._requests[client_id].append(now)
        return True

    def get_remaining(self, client_id: str) -> int:
        """Get remaining requests for client."""
        now = datetime.now(timezone.utc)
        minute_ago = now.replace(second=0, microsecond=0)

        if client_id not in self._requests:
            return self.rpm

        current = len([t for t in self._requests[client_id] if t >= minute_ago])
        return max(0, self.rpm - current)


_rate_limiter: RateLimiter | None = None


def get_rate_limiter() -> RateLimiter:
    """Get the global rate limiter."""
    global _rate_limiter
    if _rate_limiter is None:
        _rate_limiter = RateLimiter()
    return _rate_limiter


async def check_rate_limit(
    request: Request,
    api_key: APIKey = Depends(get_api_key),
) -> None:
    """
    Check rate limit for the current request.

    Raises:
        HTTPException: If rate limit exceeded.
    """
    limiter = get_rate_limiter()
    client_id = api_key.key[:8]  # Use key prefix as client ID

    if not limiter.is_allowed(client_id):
        remaining = limiter.get_remaining(client_id)
        raise HTTPException(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail="Rate limit exceeded",
            headers={
                "X-RateLimit-Limit": str(limiter.rpm),
                "X-RateLimit-Remaining": str(remaining),
                "Retry-After": "60",
            },
        )
