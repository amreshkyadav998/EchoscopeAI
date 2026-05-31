"""JWT authentication dependency (HLD section 4.1, Phase 2.2).

Validates the ``Authorization: Bearer <token>`` header on protected routes,
extracts the user context (user_id, role, org_id) from the claims, and attaches it
to ``request.state.user``. Provides ``require_role`` for RBAC.

The Auth service (Phase 3) issues these HS256 tokens; here we only verify them
using the shared ``JWT_SECRET``.
"""

from __future__ import annotations

from dataclasses import dataclass

import jwt
from fastapi import Depends, Request

from config import get_settings
from echoscope_common import ForbiddenError, UnauthorizedError

ALGORITHM = "HS256"


@dataclass
class CurrentUser:
    """Authenticated user context derived from the JWT claims."""

    user_id: str
    role: str
    org_id: str


def _decode(token: str) -> dict:
    settings = get_settings()
    try:
        return jwt.decode(token, settings.jwt_secret, algorithms=[ALGORITHM])
    except jwt.ExpiredSignatureError as exc:
        raise UnauthorizedError("Token has expired") from exc
    except jwt.InvalidTokenError as exc:
        raise UnauthorizedError("Invalid authentication token") from exc


async def get_current_user(request: Request) -> CurrentUser:
    """Validate the bearer token and return the current user context."""
    header = request.headers.get("Authorization", "")
    if not header.startswith("Bearer "):
        raise UnauthorizedError("Missing or malformed Authorization header")

    claims = _decode(header[len("Bearer ") :].strip())
    try:
        user = CurrentUser(
            user_id=str(claims["sub"]),
            role=str(claims["role"]),
            org_id=str(claims["org_id"]),
        )
    except KeyError as exc:
        raise UnauthorizedError(
            f"Token missing required claim: {exc.args[0]}"
        ) from exc

    request.state.user = user
    return user


def require_role(*roles: str):
    """Dependency factory enforcing that the user holds one of ``roles``."""

    async def _dependency(
        user: CurrentUser = Depends(get_current_user),
    ) -> CurrentUser:
        if roles and user.role not in roles:
            raise ForbiddenError(
                f"This action requires one of roles: {', '.join(roles)}"
            )
        return user

    return _dependency
