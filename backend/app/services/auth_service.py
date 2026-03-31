"""
TABLZ — AuthService: handles registration, login, token lifecycle, and audit logging.
"""

import uuid
from datetime import datetime, timedelta, timezone

from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.restaurant import Restaurant
from app.models.audit_log import AuditLog
from app.core.security import (
    hash_password,
    verify_password,
    create_access_token,
    create_refresh_token,
    create_email_verification_token,
    generate_admin_id,
)
from app.core.errors import AppException, ErrorCode
from app.core.rate_limit import increment_login_failure, reset_login_failures
from app.config import settings


class AuthService:

    @staticmethod
    async def register(
        db: AsyncSession,
        name: str,
        email: str,
        password: str,
        ip_address: str | None = None,
    ) -> dict:
        """Register a new restaurant account."""
        # Check if email already taken
        existing = await db.execute(
            select(Restaurant).where(Restaurant.email == email)
        )
        if existing.scalar_one_or_none():
            raise AppException(
                code=ErrorCode.AUTH_DUPLICATE_EMAIL,
                message="Email already registered",
                http_status=409,
                suggestion="Use a different email or try logging in",
            )

        # Generate admin_id (TBZ-YYXXXX)
        count_result = await db.execute(select(func.count(Restaurant.id)))
        count = count_result.scalar() or 0
        admin_id = generate_admin_id(count + 1)

        # Generate email verification token
        verification_token = create_email_verification_token()

        # Create restaurant record
        restaurant = Restaurant(
            id=uuid.uuid4(),
            admin_id=admin_id,
            name=name,
            email=email,
            password_hash=hash_password(password),
            email_verification_token=verification_token,
            email_verification_expires=datetime.now(timezone.utc) + timedelta(hours=24),
        )
        db.add(restaurant)

        # Audit log
        audit = AuditLog(
            restaurant_id=restaurant.id,
            actor_type="admin",
            actor_id=admin_id,
            action="auth.register",
            resource_type="restaurant",
            resource_id=restaurant.id,
            ip_address=ip_address,
        )
        db.add(audit)

        await db.commit()
        await db.refresh(restaurant)

        # TODO: Send verification email via SendGrid
        # In dev mode, return token for manual verification
        return {
            "admin_id": admin_id,
            "email": email,
            "message": "Verification email sent",
            "_dev_verification_token": verification_token if settings.ENVIRONMENT == "development" else None,
        }

    @staticmethod
    async def verify_email(db: AsyncSession, token: str) -> dict:
        """Verify a restaurant owner's email."""
        result = await db.execute(
            select(Restaurant).where(Restaurant.email_verification_token == token)
        )
        restaurant = result.scalar_one_or_none()

        if not restaurant:
            raise AppException(
                code=ErrorCode.AUTH_INVALID_TOKEN,
                message="Invalid verification token",
                http_status=400,
            )

        if restaurant.email_verified:
            raise AppException(
                code=ErrorCode.AUTH_ALREADY_VERIFIED,
                message="Email already verified",
                http_status=400,
            )

        if restaurant.email_verification_expires < datetime.now(timezone.utc):
            raise AppException(
                code=ErrorCode.AUTH_INVALID_TOKEN,
                message="Verification token expired",
                http_status=400,
                suggestion="Request a new verification email",
            )

        restaurant.email_verified = True
        restaurant.email_verification_token = None
        restaurant.email_verification_expires = None
        await db.commit()

        return {"message": "Email verified successfully"}

    @staticmethod
    async def login(
        db: AsyncSession,
        admin_id: str,
        password: str,
        ip_address: str | None = None,
    ) -> dict:
        """Authenticate admin and issue tokens."""
        # Rate limit check
        is_allowed, retry_after = await increment_login_failure(admin_id)
        if not is_allowed:
            raise AppException(
                code=ErrorCode.RATE_LIMIT_EXCEEDED,
                message="Too many login attempts",
                http_status=429,
                suggestion=f"Retry after {retry_after} seconds",
                headers={"Retry-After": str(retry_after)},
            )

        # Find restaurant
        result = await db.execute(
            select(Restaurant).where(Restaurant.admin_id == admin_id)
        )
        restaurant = result.scalar_one_or_none()

        if not restaurant or not verify_password(password, restaurant.password_hash):
            # Audit failed login
            audit = AuditLog(
                restaurant_id=restaurant.id if restaurant else None,
                actor_type="admin",
                actor_id=admin_id,
                action="auth.login_failed",
                ip_address=ip_address,
            )
            db.add(audit)
            await db.commit()

            raise AppException(
                code=ErrorCode.AUTH_INVALID_CREDENTIALS,
                message="Invalid admin ID or password",
                http_status=401,
            )

        # Check email verification
        if not restaurant.email_verified:
            raise AppException(
                code=ErrorCode.AUTH_EMAIL_NOT_VERIFIED,
                message="Email not verified",
                http_status=403,
                suggestion="Check your email for the verification link",
            )

        # Check active status
        if not restaurant.is_active:
            raise AppException(
                code=ErrorCode.AUTH_INVALID_CREDENTIALS,
                message="Account is disabled",
                http_status=401,
            )

        # Reset login failure counter
        await reset_login_failures(admin_id)

        # Create tokens
        access_token = create_access_token({
            "sub": str(restaurant.id),
            "admin_id": restaurant.admin_id,
            "restaurant_id": str(restaurant.id),
            "tier": restaurant.subscription_tier,
        })
        refresh_token = create_refresh_token()

        # Store refresh token hash
        restaurant.refresh_token_hash = hash_password(refresh_token)
        restaurant.refresh_token_expires = datetime.now(timezone.utc) + timedelta(
            days=settings.JWT_REFRESH_TOKEN_EXPIRE_DAYS
        )

        # Audit successful login
        audit = AuditLog(
            restaurant_id=restaurant.id,
            actor_type="admin",
            actor_id=admin_id,
            action="auth.login_success",
            ip_address=ip_address,
        )
        db.add(audit)
        await db.commit()

        return {
            "access_token": access_token,
            "refresh_token": refresh_token,
            "token_type": "bearer",
            "expires_in": settings.JWT_ACCESS_TOKEN_EXPIRE_MINUTES * 60,
        }

    @staticmethod
    async def refresh_token(db: AsyncSession, refresh_token: str) -> dict:
        """Rotate refresh token and issue a new access token."""
        # Find restaurant with valid refresh token
        result = await db.execute(
            select(Restaurant).where(
                Restaurant.refresh_token_expires > datetime.now(timezone.utc)
            )
        )
        restaurants = result.scalars().all()

        target_restaurant = None
        for restaurant in restaurants:
            if restaurant.refresh_token_hash and verify_password(
                refresh_token, restaurant.refresh_token_hash
            ):
                target_restaurant = restaurant
                break

        if not target_restaurant:
            raise AppException(
                code=ErrorCode.AUTH_TOKEN_EXPIRED,
                message="Invalid or expired refresh token",
                http_status=401,
            )

        # Create new tokens
        new_access_token = create_access_token({
            "sub": str(target_restaurant.id),
            "admin_id": target_restaurant.admin_id,
            "restaurant_id": str(target_restaurant.id),
            "tier": target_restaurant.subscription_tier,
        })
        new_refresh_token = create_refresh_token()

        # Rotate refresh token
        target_restaurant.refresh_token_hash = hash_password(new_refresh_token)
        target_restaurant.refresh_token_expires = datetime.now(timezone.utc) + timedelta(
            days=settings.JWT_REFRESH_TOKEN_EXPIRE_DAYS
        )
        await db.commit()

        return {
            "access_token": new_access_token,
            "refresh_token": new_refresh_token,
            "token_type": "bearer",
            "expires_in": settings.JWT_ACCESS_TOKEN_EXPIRE_MINUTES * 60,
        }

    @staticmethod
    async def logout(db: AsyncSession, restaurant_id: uuid.UUID) -> dict:
        """Invalidate refresh token."""
        result = await db.execute(
            select(Restaurant).where(Restaurant.id == restaurant_id)
        )
        restaurant = result.scalar_one_or_none()

        if restaurant:
            restaurant.refresh_token_hash = None
            restaurant.refresh_token_expires = None
            await db.commit()

        return {"message": "Logged out successfully"}
