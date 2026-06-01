"""Request/response models for the Auth service (HLD section 5.1)."""

from __future__ import annotations

from datetime import datetime

from pydantic import EmailStr, Field

from echoscope_common import BaseSchema


class RegisterRequest(BaseSchema):
    email: EmailStr
    password: str = Field(min_length=8, max_length=128)
    full_name: str = Field(min_length=1, max_length=100)
    org_name: str = Field(min_length=1, max_length=200)


class RegisterResponse(BaseSchema):
    user_id: str
    message: str


class LoginRequest(BaseSchema):
    email: EmailStr
    password: str


class TokenResponse(BaseSchema):
    access_token: str
    refresh_token: str
    expires_in: int


class RefreshRequest(BaseSchema):
    refresh_token: str


class RefreshResponse(BaseSchema):
    access_token: str
    refresh_token: str
    expires_in: int


class LogoutRequest(BaseSchema):
    refresh_token: str


class MessageResponse(BaseSchema):
    message: str


class UserResponse(BaseSchema):
    id: str
    email: str
    full_name: str
    role: str
    org_id: str
    is_active: bool
    is_verified: bool
    avatar_url: str | None = None
    created_at: datetime


class UpdateMeRequest(BaseSchema):
    full_name: str | None = Field(default=None, max_length=100)
    avatar: str | None = None


class ChangePasswordRequest(BaseSchema):
    old_password: str
    new_password: str = Field(min_length=8, max_length=128)
