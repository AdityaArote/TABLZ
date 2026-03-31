"""
TABLZ — Pydantic schemas for auth endpoints.
"""

from pydantic import BaseModel, EmailStr, Field


class RegisterRequest(BaseModel):
    name: str = Field(..., min_length=1, max_length=255, description="Restaurant name")
    email: EmailStr = Field(..., description="Owner email")
    password: str = Field(..., min_length=8, max_length=128, description="Password (min 8 chars)")


class LoginRequest(BaseModel):
    admin_id: str = Field(..., min_length=8, max_length=12, description="Admin ID (TBZ-YYXXXX)")
    password: str = Field(..., min_length=1, max_length=128)


class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    expires_in: int = 900  # seconds


class RegisterResponse(BaseModel):
    admin_id: str
    email: str
    message: str = "Verification email sent"


class ForgotPasswordRequest(BaseModel):
    email: EmailStr


class ResetPasswordRequest(BaseModel):
    token: str
    new_password: str = Field(..., min_length=8, max_length=128)
