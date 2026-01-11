"""API authentication for MSM web backend."""
import hashlib
import hmac
import logging
import secrets
from datetime import datetime
from pathlib import Path
from typing import Optional

from fastapi import Depends, HTTPException, Security
from fastapi.security import APIKeyHeader, APIKeyQuery
from pydantic import BaseModel

from msm_core.db import get_session, Base
from msm_core.config import get_config
from sqlalchemy import String, DateTime, Boolean
from sqlalchemy.orm import Mapped, mapped_column

logger = logging.getLogger(__name__)

# Security schemes
api_key_header = APIKeyHeader(name="X-API-Key", auto_error=False)
api_key_query = APIKeyQuery(name="api_key", auto_error=False)


class APIKey(Base):
    """API Key model."""
    __tablename__ = "api_keys"

    id: Mapped[int] = mapped_column(primary_key=True)
    name: Mapped[str] = mapped_column(String(255))
    key_hash: Mapped[str] = mapped_column(String(64), unique=True, index=True)
    key_prefix: Mapped[str] = mapped_column(String(8))  # First 8 chars for identification
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    last_used: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    permissions: Mapped[Optional[str]] = mapped_column(String(500), nullable=True)  # JSON list


class AuthConfig(BaseModel):
    """Authentication configuration."""
    enabled: bool = False
    allow_localhost: bool = True


def hash_api_key(key: str) -> str:
    """Hash an API key for storage.

    Args:
        key: The raw API key.

    Returns:
        SHA-256 hash of the key.
    """
    return hashlib.sha256(key.encode()).hexdigest()


def generate_api_key() -> str:
    """Generate a new secure API key.

    Returns:
        A URL-safe random string (44 characters).
    """
    return secrets.token_urlsafe(32)


def create_api_key(name: str, permissions: Optional[list] = None) -> dict:
    """Create a new API key.

    Args:
        name: Name/description for the key.
        permissions: Optional list of permissions.

    Returns:
        Dictionary with key info (including the raw key - only time it's returned).
    """
    import json

    raw_key = generate_api_key()
    key_hash = hash_api_key(raw_key)
    key_prefix = raw_key[:8]

    with get_session() as session:
        api_key = APIKey(
            name=name,
            key_hash=key_hash,
            key_prefix=key_prefix,
            permissions=json.dumps(permissions) if permissions else None,
        )
        session.add(api_key)
        session.flush()

        return {
            "id": api_key.id,
            "name": api_key.name,
            "key": raw_key,  # Only returned once!
            "key_prefix": key_prefix,
            "created_at": api_key.created_at.isoformat(),
            "message": "Save this key securely - it won't be shown again!",
        }


def list_api_keys() -> list:
    """List all API keys (without the actual keys).

    Returns:
        List of API key info dictionaries.
    """
    with get_session() as session:
        keys = session.query(APIKey).order_by(APIKey.created_at.desc()).all()

        return [
            {
                "id": k.id,
                "name": k.name,
                "key_prefix": k.key_prefix,
                "created_at": k.created_at.isoformat(),
                "last_used": k.last_used.isoformat() if k.last_used else None,
                "is_active": k.is_active,
            }
            for k in keys
        ]


def revoke_api_key(key_id: int) -> bool:
    """Revoke (deactivate) an API key.

    Args:
        key_id: The API key database ID.

    Returns:
        True if revoked successfully.
    """
    with get_session() as session:
        api_key = session.query(APIKey).filter(APIKey.id == key_id).first()
        if not api_key:
            return False

        api_key.is_active = False
        logger.info(f"Revoked API key: {api_key.name} ({api_key.key_prefix}...)")
        return True


def delete_api_key(key_id: int) -> bool:
    """Delete an API key permanently.

    Args:
        key_id: The API key database ID.

    Returns:
        True if deleted successfully.
    """
    with get_session() as session:
        api_key = session.query(APIKey).filter(APIKey.id == key_id).first()
        if not api_key:
            return False

        session.delete(api_key)
        logger.info(f"Deleted API key: {api_key.name}")
        return True


def validate_api_key(key: str) -> Optional[dict]:
    """Validate an API key and return key info if valid.

    Args:
        key: The raw API key.

    Returns:
        Dictionary with key info if valid, None otherwise.
    """
    key_hash = hash_api_key(key)

    with get_session() as session:
        api_key = (
            session.query(APIKey)
            .filter(APIKey.key_hash == key_hash)
            .filter(APIKey.is_active == True)
            .first()
        )

        if not api_key:
            return None

        # Update last used timestamp
        api_key.last_used = datetime.utcnow()

        return {
            "id": api_key.id,
            "name": api_key.name,
            "permissions": api_key.permissions,
        }


def get_auth_config() -> AuthConfig:
    """Get authentication configuration.

    Returns:
        AuthConfig instance.
    """
    config = get_config()
    return AuthConfig(
        enabled=getattr(config, "auth_enabled", False),
        allow_localhost=getattr(config, "auth_allow_localhost", True),
    )


def is_localhost(host: str) -> bool:
    """Check if the request is from localhost.

    Args:
        host: The client host.

    Returns:
        True if localhost.
    """
    localhost_addresses = {"127.0.0.1", "localhost", "::1"}
    return host in localhost_addresses


async def verify_api_key(
    api_key_header: Optional[str] = Security(api_key_header),
    api_key_query: Optional[str] = Security(api_key_query),
) -> Optional[dict]:
    """Verify API key from header or query parameter.

    This is a FastAPI dependency that can be used to protect endpoints.

    Args:
        api_key_header: API key from X-API-Key header.
        api_key_query: API key from api_key query parameter.

    Returns:
        Dictionary with key info if valid.

    Raises:
        HTTPException: If authentication fails and is required.
    """
    auth_config = get_auth_config()

    # If auth is disabled, allow all requests
    if not auth_config.enabled:
        return None

    # Get API key from header or query
    api_key = api_key_header or api_key_query

    if not api_key:
        raise HTTPException(
            status_code=401,
            detail="API key required. Provide via X-API-Key header or api_key query parameter.",
            headers={"WWW-Authenticate": "ApiKey"},
        )

    # Validate the key
    key_info = validate_api_key(api_key)

    if not key_info:
        raise HTTPException(
            status_code=403,
            detail="Invalid or revoked API key.",
        )

    return key_info


async def optional_api_key(
    api_key_header: Optional[str] = Security(api_key_header),
    api_key_query: Optional[str] = Security(api_key_query),
) -> Optional[dict]:
    """Optionally verify API key - doesn't fail if not provided.

    Use this for endpoints that should work both authenticated and unauthenticated.

    Args:
        api_key_header: API key from X-API-Key header.
        api_key_query: API key from api_key query parameter.

    Returns:
        Dictionary with key info if valid key provided, None otherwise.
    """
    api_key = api_key_header or api_key_query

    if not api_key:
        return None

    return validate_api_key(api_key)


def has_permission(key_info: Optional[dict], permission: str) -> bool:
    """Check if an API key has a specific permission.

    Args:
        key_info: Key info from verify_api_key.
        permission: Permission to check.

    Returns:
        True if has permission (or no permissions defined = all access).
    """
    import json

    if key_info is None:
        return True  # Auth disabled or localhost bypass

    permissions_str = key_info.get("permissions")
    if not permissions_str:
        return True  # No specific permissions = all access

    try:
        permissions = json.loads(permissions_str)
        return permission in permissions or "*" in permissions
    except json.JSONDecodeError:
        return False
