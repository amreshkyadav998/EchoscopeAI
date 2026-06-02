"""JWT validation for the WebSocket handshake (HS256, shared JWT_SECRET)."""

from __future__ import annotations

import jwt

from config import get_settings

ALGORITHM = "HS256"


def decode_token(token: str) -> dict:
    return jwt.decode(token, get_settings().jwt_secret, algorithms=[ALGORITHM])


def org_from_token(token: str | None) -> str | None:
    """Return org_id from a valid token, or None if missing/invalid."""
    if not token:
        return None
    try:
        return decode_token(token).get("org_id")
    except jwt.InvalidTokenError:
        return None
