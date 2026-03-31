"""
TABLZ — Standard error codes and response builder.
All errors follow an identical structure across all endpoints.
"""

from datetime import datetime, timezone
from uuid import uuid4
from fastapi import HTTPException
from fastapi.responses import JSONResponse


# ─── Error Codes ───

class ErrorCode:
    AUTH_TOKEN_EXPIRED = "AUTH_TOKEN_EXPIRED"
    AUTH_INVALID_CREDENTIALS = "AUTH_INVALID_CREDENTIALS"
    AUTH_EMAIL_NOT_VERIFIED = "AUTH_EMAIL_NOT_VERIFIED"
    AUTH_INSUFFICIENT_ROLE = "AUTH_INSUFFICIENT_ROLE"
    AUTH_DUPLICATE_EMAIL = "AUTH_DUPLICATE_EMAIL"
    AUTH_ALREADY_VERIFIED = "AUTH_ALREADY_VERIFIED"
    AUTH_INVALID_TOKEN = "AUTH_INVALID_TOKEN"
    RESOURCE_NOT_FOUND = "RESOURCE_NOT_FOUND"
    ORDER_DUPLICATE = "ORDER_DUPLICATE"
    ORDER_INVALID_TRANSITION = "ORDER_INVALID_TRANSITION"
    SUBSCRIPTION_LIMIT_EXCEEDED = "SUBSCRIPTION_LIMIT_EXCEEDED"
    RATE_LIMIT_EXCEEDED = "RATE_LIMIT_EXCEEDED"
    VALIDATION_ERROR = "VALIDATION_ERROR"
    INTERNAL_ERROR = "INTERNAL_ERROR"
    SERVICE_UNAVAILABLE = "SERVICE_UNAVAILABLE"


def build_error_response(
    code: str,
    message: str,
    http_status: int,
    suggestion: str = "",
) -> JSONResponse:
    """Build a standardized error response."""
    return JSONResponse(
        status_code=http_status,
        content={
            "success": False,
            "error": {
                "code": code,
                "message": message,
                "suggestion": suggestion,
                "http_status": http_status,
                "request_id": str(uuid4()),
                "timestamp": datetime.now(timezone.utc).isoformat(),
            },
        },
    )


class AppException(HTTPException):
    """Custom exception with structured error response."""

    def __init__(
        self,
        code: str,
        message: str,
        http_status: int = 400,
        suggestion: str = "",
        headers: dict | None = None,
    ):
        self.code = code
        self.error_message = message
        self.suggestion = suggestion
        super().__init__(status_code=http_status, detail=message, headers=headers)


def not_found(message: str = "Resource not found") -> AppException:
    return AppException(
        code=ErrorCode.RESOURCE_NOT_FOUND,
        message=message,
        http_status=404,
    )


def unauthorized(message: str = "Invalid credentials") -> AppException:
    return AppException(
        code=ErrorCode.AUTH_INVALID_CREDENTIALS,
        message=message,
        http_status=401,
    )


def forbidden(message: str = "Insufficient permissions") -> AppException:
    return AppException(
        code=ErrorCode.AUTH_INSUFFICIENT_ROLE,
        message=message,
        http_status=403,
    )


def rate_limited(retry_after: int = 900) -> AppException:
    return AppException(
        code=ErrorCode.RATE_LIMIT_EXCEEDED,
        message="Too many requests",
        http_status=429,
        suggestion=f"Retry after {retry_after} seconds",
        headers={"Retry-After": str(retry_after)},
    )
