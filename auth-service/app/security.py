"""Password hashing (bcrypt) and JWT issuance/decoding (HS256).

Tokens carry the claims the API gateway expects: sub (user_id), role, org_id —
plus iat, exp, jti, and a type marker.
"""

from __future__ import annotations

import uuid
from datetime import datetime, timedelta, timezone

import bcrypt
import jwt

from config import get_settings

ALGORITHM = "HS256"
BCRYPT_ROUNDS = 12


def hash_password(password: str) -> str:
    return bcrypt.hashpw(password.encode(), bcrypt.gensalt(rounds=BCRYPT_ROUNDS)).decode()


def verify_password(password: str, password_hash: str) -> bool:
    # constant-time comparison inside bcrypt.checkpw
    return bcrypt.checkpw(password.encode(), password_hash.encode())


def create_access_token(user_id: str, role: str, org_id: str) -> tuple[str, int, str]:
    """Return (token, expires_in_seconds, jti)."""
    settings = get_settings()
    now = datetime.now(timezone.utc)
    expires_in = settings.jwt_expire_minutes * 60
    jti = str(uuid.uuid4())
    payload = {
        "sub": user_id,
        "role": role,
        "org_id": org_id,
        "type": "access",
        "jti": jti,
        "iat": int(now.timestamp()),
        "exp": int((now + timedelta(seconds=expires_in)).timestamp()),
    }
    token = jwt.encode(payload, settings.jwt_secret, algorithm=ALGORITHM)
    return token, expires_in, jti


def decode_access_token(token: str) -> dict:
    settings = get_settings()
    return jwt.decode(token, settings.jwt_secret, algorithms=[ALGORITHM])


def new_refresh_token() -> str:
    return str(uuid.uuid4())
