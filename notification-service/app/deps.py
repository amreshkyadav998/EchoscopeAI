"""Auth dependency: trust gateway-injected X-User-* headers."""

from __future__ import annotations

from dataclasses import dataclass

from fastapi import Depends, Request

from echoscope_common import ForbiddenError, UnauthorizedError


@dataclass
class CurrentUser:
    user_id: str
    role: str
    org_id: str


async def get_current_user(request: Request) -> CurrentUser:
    user_id = request.headers.get("X-User-Id")
    role = request.headers.get("X-Role")
    org_id = request.headers.get("X-Org-Id")
    if not (user_id and role and org_id):
        raise UnauthorizedError("Missing user context (gateway X-User-* headers required)")
    return CurrentUser(user_id=user_id, role=role, org_id=org_id)


def require_role(*roles: str):
    async def _dependency(user: CurrentUser = Depends(get_current_user)) -> CurrentUser:
        if roles and user.role not in roles:
            raise ForbiddenError(f"This action requires one of roles: {', '.join(roles)}")
        return user

    return _dependency
