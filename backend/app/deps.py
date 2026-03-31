"""
TABLZ — Dependency injection: get_db, get_current_restaurant, get_current_session.
"""

import uuid
from typing import AsyncGenerator

from fastapi import Depends, Request, HTTPException
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import async_session_factory
from app.core.security import decode_access_token
from app.core.errors import AppException, ErrorCode
from app.models.restaurant import Restaurant
from app.models.customer_session import CustomerSession


security_scheme = HTTPBearer(auto_error=False)


async def get_db() -> AsyncGenerator[AsyncSession, None]:
    """Yield an async database session."""
    async with async_session_factory() as session:
        try:
            yield session
        finally:
            await session.close()


async def get_current_restaurant(
    request: Request,
    credentials: HTTPAuthorizationCredentials | None = Depends(security_scheme),
    db: AsyncSession = Depends(get_db),
) -> Restaurant:
    """
    Extract and validate JWT. Returns the authenticated Restaurant.
    Never trust client-provided restaurant_id — always extract from JWT.
    """
    if not credentials:
        raise AppException(
            code=ErrorCode.AUTH_TOKEN_EXPIRED,
            message="Missing authentication token",
            http_status=401,
        )

    payload = decode_access_token(credentials.credentials)
    if not payload:
        raise AppException(
            code=ErrorCode.AUTH_TOKEN_EXPIRED,
            message="Invalid or expired token",
            http_status=401,
        )

    restaurant_id = payload.get("restaurant_id")
    if not restaurant_id:
        raise AppException(
            code=ErrorCode.AUTH_TOKEN_EXPIRED,
            message="Invalid token payload",
            http_status=401,
        )

    result = await db.execute(
        select(Restaurant).where(Restaurant.id == uuid.UUID(restaurant_id))
    )
    restaurant = result.scalar_one_or_none()

    if not restaurant or not restaurant.is_active:
        raise AppException(
            code=ErrorCode.RESOURCE_NOT_FOUND,
            message="Restaurant not found",
            http_status=404,
        )

    return restaurant


async def get_current_session(
    request: Request,
    db: AsyncSession = Depends(get_db),
) -> CustomerSession:
    """Extract customer session from HttpOnly cookie."""
    session_token = request.cookies.get("session_token")
    if not session_token:
        raise AppException(
            code=ErrorCode.AUTH_TOKEN_EXPIRED,
            message="No session token",
            http_status=401,
        )

    from datetime import datetime, timezone as tz
    result = await db.execute(
        select(CustomerSession).where(
            CustomerSession.session_token == session_token,
            CustomerSession.invalidated_at.is_(None),
            CustomerSession.expires_at > datetime.now(tz.utc),
        )
    )
    session = result.scalar_one_or_none()

    if not session:
        raise AppException(
            code=ErrorCode.AUTH_TOKEN_EXPIRED,
            message="Invalid or expired session",
            http_status=401,
        )

    return session
