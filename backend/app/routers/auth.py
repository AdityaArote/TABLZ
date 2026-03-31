"""
TABLZ — Auth router: register, verify-email, login, refresh, logout.
"""

from fastapi import APIRouter, Depends, Request, Response

from sqlalchemy.ext.asyncio import AsyncSession

from app.deps import get_db, get_current_restaurant
from app.schemas.auth import RegisterRequest, LoginRequest, TokenResponse, RegisterResponse
from app.schemas.common import SuccessResponse
from app.services.auth_service import AuthService
from app.models.restaurant import Restaurant
from app.config import settings

router = APIRouter(prefix="/api/v1/auth", tags=["Authentication"])


@router.post("/register", status_code=201)
async def register(
    request: Request,
    body: RegisterRequest,
    db: AsyncSession = Depends(get_db),
):
    """Register a new restaurant account."""
    ip = request.client.host if request.client else None
    result = await AuthService.register(
        db=db,
        name=body.name,
        email=body.email,
        password=body.password,
        ip_address=ip,
    )
    return SuccessResponse(success=True, data=result)


@router.post("/verify-email/{token}")
async def verify_email(
    token: str,
    db: AsyncSession = Depends(get_db),
):
    """Verify email address with token."""
    result = await AuthService.verify_email(db=db, token=token)
    return SuccessResponse(success=True, data=result)


@router.post("/login")
async def login(
    request: Request,
    response: Response,
    body: LoginRequest,
    db: AsyncSession = Depends(get_db),
):
    """Authenticate and receive tokens."""
    ip = request.client.host if request.client else None
    result = await AuthService.login(
        db=db,
        admin_id=body.admin_id,
        password=body.password,
        ip_address=ip,
    )

    # Set refresh token as HttpOnly cookie
    response.set_cookie(
        key="refresh_token",
        value=result["refresh_token"],
        httponly=True,
        secure=settings.ENVIRONMENT != "development",
        samesite="strict",
        max_age=settings.JWT_REFRESH_TOKEN_EXPIRE_DAYS * 86400,
        path="/api/v1/auth",
    )

    return SuccessResponse(
        success=True,
        data={
            "access_token": result["access_token"],
            "token_type": result["token_type"],
            "expires_in": result["expires_in"],
        },
    )


@router.get("/me")
async def get_me(
    restaurant: Restaurant = Depends(get_current_restaurant),
):
    """Get current authenticated restaurant profile."""
    return SuccessResponse(
        success=True,
        data={
            "id": str(restaurant.id),
            "restaurant_id": str(restaurant.id),
            "admin_id": restaurant.admin_id,
            "name": restaurant.name,
            "email": restaurant.email,
        },
    )


@router.post("/refresh")
async def refresh_token(
    request: Request,
    response: Response,
    db: AsyncSession = Depends(get_db),
):
    """Refresh access token using HttpOnly cookie."""
    refresh_tok = request.cookies.get("refresh_token")
    if not refresh_tok:
        from app.core.errors import AppException, ErrorCode
        raise AppException(
            code=ErrorCode.AUTH_TOKEN_EXPIRED,
            message="No refresh token",
            http_status=401,
        )

    result = await AuthService.refresh_token(db=db, refresh_token=refresh_tok)

    # Set new refresh token cookie
    response.set_cookie(
        key="refresh_token",
        value=result["refresh_token"],
        httponly=True,
        secure=settings.ENVIRONMENT != "development",
        samesite="strict",
        max_age=settings.JWT_REFRESH_TOKEN_EXPIRE_DAYS * 86400,
        path="/api/v1/auth",
    )

    return SuccessResponse(
        success=True,
        data={
            "access_token": result["access_token"],
            "token_type": result["token_type"],
            "expires_in": result["expires_in"],
        },
    )


@router.post("/logout")
async def logout(
    response: Response,
    restaurant: Restaurant = Depends(get_current_restaurant),
    db: AsyncSession = Depends(get_db),
):
    """Logout and invalidate refresh token."""
    result = await AuthService.logout(db=db, restaurant_id=restaurant.id)

    # Clear the refresh token cookie
    response.delete_cookie(
        key="refresh_token",
        path="/api/v1/auth",
    )

    return SuccessResponse(success=True, data=result)
