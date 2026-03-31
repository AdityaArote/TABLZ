"""
TABLZ — JWT creation/validation, bcrypt password hashing.
Access JWT: 15-min TTL, HS256.
Refresh Token: 30-day TTL, cryptographic random string.
"""

import secrets
from datetime import datetime, timedelta, timezone
from typing import Any

from jose import JWTError, jwt
from passlib.context import CryptContext

from app.config import settings

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")


# ─── Password Hashing ───

def hash_password(password: str) -> str:
    """Hash a password with bcrypt."""
    return pwd_context.hash(password)


def verify_password(plain_password: str, hashed_password: str) -> bool:
    """Verify a plain password against a bcrypt hash."""
    return pwd_context.verify(plain_password, hashed_password)


# ─── JWT Tokens ───

def create_access_token(data: dict[str, Any], expires_delta: timedelta | None = None) -> str:
    """Create a short-lived access JWT (default 15 min)."""
    to_encode = data.copy()
    expire = datetime.now(timezone.utc) + (
        expires_delta or timedelta(minutes=settings.JWT_ACCESS_TOKEN_EXPIRE_MINUTES)
    )
    to_encode.update({"exp": expire, "iat": datetime.now(timezone.utc), "type": "access"})
    return jwt.encode(to_encode, settings.JWT_SECRET_KEY, algorithm=settings.JWT_ALGORITHM)


def create_refresh_token() -> str:
    """Create a cryptographically secure refresh token (128 chars)."""
    return secrets.token_urlsafe(96)


def create_email_verification_token() -> str:
    """Create a token for email verification (64 chars, 24h TTL enforced at check time)."""
    return secrets.token_urlsafe(48)


def decode_access_token(token: str) -> dict[str, Any] | None:
    """Decode and validate an access JWT. Returns claims or None on failure."""
    try:
        payload = jwt.decode(
            token,
            settings.JWT_SECRET_KEY,
            algorithms=[settings.JWT_ALGORITHM],
        )
        if payload.get("type") != "access":
            return None
        return payload
    except JWTError:
        return None


def generate_admin_id(sequence_number: int) -> str:
    """Generate admin_id in format TBZ-YYXXXX (e.g., TBZ-250001)."""
    year_suffix = datetime.now(timezone.utc).strftime("%y")
    return f"TBZ-{year_suffix}{sequence_number:04d}"


def generate_qr_token() -> str:
    """Generate a cryptographically secure QR code token (128 chars)."""
    return secrets.token_urlsafe(96)


def generate_session_token() -> str:
    """Generate a cryptographically secure session token (128 chars)."""
    return secrets.token_urlsafe(96)


def generate_barcode_token() -> str:
    """Generate a unique barcode token for bill finalization."""
    return secrets.token_urlsafe(96)
