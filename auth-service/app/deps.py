"""Auth dependencies: current-user resolution and RBAC.

Resolves the current user from EITHER:
  - the gateway-injected `X-User-Id` header (the gateway already validated the JWT and
    strips Authorization), or
  - a local `Authorization: Bearer` token (direct calls / tests / logout needing the jti).
"""

from __future__ import annotations

import jwt
from fastapi import Depends, Request
from sqlalchemy.ext.asyncio import AsyncSession

from app.db import get_db
from app.models import User
from app.redis_client import is_blacklisted
from app.security import decode_access_token
from echoscope_common import ForbiddenError, UnauthorizedError


async def get_current_user(
    request: Request, db: AsyncSession = Depends(get_db)
) -> User:
    # Trust the gateway-injected identity when present (Authorization was stripped upstream).
    gateway_uid = request.headers.get("X-User-Id")
    if gateway_uid:
        user = await db.get(User, gateway_uid)
        if user is None or not user.is_active:
            raise UnauthorizedError("User not found or inactive")
        return user

    header = request.headers.get("Authorization", "")
    if not header.startswith("Bearer "):
        raise UnauthorizedError("Missing or malformed Authorization header")

    token = header[len("Bearer ") :].strip()
    try:
        claims = decode_access_token(token)
    except jwt.ExpiredSignatureError as exc:
        raise UnauthorizedError("Token has expired") from exc
    except jwt.InvalidTokenError as exc:
        raise UnauthorizedError("Invalid authentication token") from exc

    jti = claims.get("jti")
    if jti and await is_blacklisted(jti):
        raise UnauthorizedError("Token has been revoked")

    user = await db.get(User, claims.get("sub"))
    if user is None or not user.is_active:
        raise UnauthorizedError("User not found or inactive")

    # stash the validated jti so logout can blacklist it
    request.state.token_jti = jti
    request.state.token_exp = claims.get("exp")
    return user


def require_role(*roles: str):
    async def _dependency(user: User = Depends(get_current_user)) -> User:
        if roles and user.role.value not in roles:
            raise ForbiddenError(f"This action requires one of roles: {', '.join(roles)}")
        return user

    return _dependency
