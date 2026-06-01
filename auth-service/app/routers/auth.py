"""Auth endpoints (HLD section 5.1)."""

from __future__ import annotations

import re
import uuid
from datetime import datetime, timezone

from fastapi import APIRouter, Depends, Request, status
from loguru import logger as log
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from app.db import get_db
from app.deps import get_current_user
from app.models import Organization, Role, User
from app.redis_client import (
    blacklist_jti,
    delete_refresh_token,
    get_refresh_user,
    store_refresh_token,
)
from app.schemas import (
    ChangePasswordRequest,
    LoginRequest,
    LogoutRequest,
    MessageResponse,
    RefreshRequest,
    RefreshResponse,
    RegisterRequest,
    RegisterResponse,
    TokenResponse,
    UpdateMeRequest,
    UserResponse,
)
from app.security import (
    create_access_token,
    hash_password,
    new_refresh_token,
    verify_password,
)
from config import get_settings
from echoscope_common import ConflictError, UnauthorizedError

router = APIRouter(prefix="/api/v1/auth", tags=["auth"])


def _slugify(name: str) -> str:
    base = re.sub(r"[^a-z0-9]+", "-", name.lower()).strip("-")
    return base or "org"


def _to_user_response(user: User) -> UserResponse:
    return UserResponse(
        id=str(user.id),
        email=user.email,
        full_name=user.full_name,
        role=user.role.value,
        org_id=str(user.org_id),
        is_active=user.is_active,
        is_verified=user.is_verified,
        avatar_url=user.avatar_url,
        created_at=user.created_at,
    )


@router.post("/register", response_model=RegisterResponse, status_code=status.HTTP_201_CREATED)
async def register(payload: RegisterRequest, db: AsyncSession = Depends(get_db)) -> RegisterResponse:
    existing = await db.scalar(select(User).where(User.email == payload.email))
    if existing is not None:
        raise ConflictError("An account with this email already exists")

    # ensure a unique org slug
    slug = _slugify(payload.org_name)
    if await db.scalar(select(Organization).where(Organization.slug == slug)) is not None:
        slug = f"{slug}-{uuid.uuid4().hex[:6]}"

    org = Organization(name=payload.org_name, slug=slug)
    # first user of an org is its admin
    user = User(
        email=payload.email,
        password_hash=hash_password(payload.password),
        full_name=payload.full_name,
        role=Role.admin,
        org=org,
    )
    db.add(org)
    db.add(user)
    try:
        await db.commit()
    except IntegrityError as exc:
        await db.rollback()
        raise ConflictError("Organization name or email already in use") from exc
    await db.refresh(user)

    # TODO(Phase 10): send verification email via SendGrid. Stubbed for now.
    log.info("verification email queued (stub)", email=payload.email, user_id=str(user.id))
    return RegisterResponse(user_id=str(user.id), message="Registration successful")


@router.post("/login", response_model=TokenResponse)
async def login(payload: LoginRequest, db: AsyncSession = Depends(get_db)) -> TokenResponse:
    user = await db.scalar(select(User).where(User.email == payload.email))
    if user is None or not verify_password(payload.password, user.password_hash):
        raise UnauthorizedError("Invalid email or password")
    if not user.is_active:
        raise UnauthorizedError("Account is disabled")

    settings = get_settings()
    access, expires_in, _ = create_access_token(str(user.id), user.role.value, str(user.org_id))
    refresh = new_refresh_token()
    await store_refresh_token(refresh, str(user.id), settings.refresh_expire_days)

    user.last_login_at = datetime.now(timezone.utc)
    await db.commit()

    return TokenResponse(access_token=access, refresh_token=refresh, expires_in=expires_in)


@router.post("/refresh", response_model=RefreshResponse)
async def refresh(payload: RefreshRequest, db: AsyncSession = Depends(get_db)) -> RefreshResponse:
    user_id = await get_refresh_user(payload.refresh_token)
    if user_id is None:
        raise UnauthorizedError("Invalid or expired refresh token")

    user = await db.get(User, user_id)
    if user is None or not user.is_active:
        raise UnauthorizedError("User not found or inactive")

    settings = get_settings()
    # rotate: invalidate the presented token and issue a fresh pair
    await delete_refresh_token(payload.refresh_token)
    new_refresh = new_refresh_token()
    await store_refresh_token(new_refresh, str(user.id), settings.refresh_expire_days)
    access, expires_in, _ = create_access_token(str(user.id), user.role.value, str(user.org_id))

    return RefreshResponse(access_token=access, refresh_token=new_refresh, expires_in=expires_in)


@router.post("/logout", response_model=MessageResponse)
async def logout(
    payload: LogoutRequest,
    request: Request,
    user: User = Depends(get_current_user),
) -> MessageResponse:
    await delete_refresh_token(payload.refresh_token)

    jti = getattr(request.state, "token_jti", None)
    exp = getattr(request.state, "token_exp", None)
    if jti and exp:
        remaining = int(exp - datetime.now(timezone.utc).timestamp())
        await blacklist_jti(jti, remaining)

    return MessageResponse(message="Logged out successfully")


@router.get("/me", response_model=UserResponse)
async def get_me(user: User = Depends(get_current_user)) -> UserResponse:
    return _to_user_response(user)


@router.put("/me", response_model=UserResponse)
async def update_me(
    payload: UpdateMeRequest,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
) -> UserResponse:
    if payload.full_name is not None:
        user.full_name = payload.full_name
    if payload.avatar is not None:
        user.avatar_url = payload.avatar
    await db.commit()
    await db.refresh(user)
    return _to_user_response(user)


@router.post("/change-password", response_model=MessageResponse)
async def change_password(
    payload: ChangePasswordRequest,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
) -> MessageResponse:
    if not verify_password(payload.old_password, user.password_hash):
        raise UnauthorizedError("Current password is incorrect")
    user.password_hash = hash_password(payload.new_password)
    await db.commit()
    return MessageResponse(message="Password changed successfully")
