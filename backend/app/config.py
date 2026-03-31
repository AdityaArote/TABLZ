"""
TABLZ — Settings via pydantic-settings.
All config from environment variables, never hardcoded.
"""

from pydantic_settings import BaseSettings
from pydantic import Field


class Settings(BaseSettings):
    # ─── Database ───
    DATABASE_URL: str = "postgresql+asyncpg://tablz_app:dev-password-changeme@localhost:5432/tablz"
    DATABASE_URL_SYNC: str = "postgresql://tablz_app:dev-password-changeme@localhost:5432/tablz"

    # ─── Security ───
    JWT_SECRET_KEY: str = "change-me-to-a-256-bit-random-string"
    JWT_ALGORITHM: str = "HS256"
    JWT_ACCESS_TOKEN_EXPIRE_MINUTES: int = 15
    JWT_REFRESH_TOKEN_EXPIRE_DAYS: int = 30

    # ─── Redis ───
    REDIS_URL: str = "redis://localhost:6379/0"

    # ─── AWS ───
    AWS_ACCESS_KEY_ID: str = ""
    AWS_SECRET_ACCESS_KEY: str = ""
    AWS_REGION: str = "ap-south-1"
    S3_BUCKET_NAME: str = "tablz-uploads-dev"

    # ─── Email ───
    SENDGRID_API_KEY: str = ""
    FROM_EMAIL: str = "noreply@tablz.app"

    # ─── App ───
    BASE_URL: str = "http://localhost:3000"
    ENVIRONMENT: str = "development"  # development | staging | production

    model_config = {"env_file": ".env", "env_file_encoding": "utf-8"}


settings = Settings()
