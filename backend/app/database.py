"""
TABLZ — SQLAlchemy async engine + session factory.
Connection pool: pool_size=20, max_overflow=10, pool_timeout=30s.
"""

from sqlalchemy.ext.asyncio import create_async_engine, async_sessionmaker, AsyncSession
from sqlalchemy.orm import DeclarativeBase

from app.config import settings

engine = create_async_engine(
    settings.DATABASE_URL,
    pool_size=20,
    max_overflow=10,
    pool_timeout=30,
    echo=settings.ENVIRONMENT == "development",
)

async_session_factory = async_sessionmaker(
    engine,
    class_=AsyncSession,
    expire_on_commit=False,
)


class Base(DeclarativeBase):
    """Base class for all ORM models."""
    pass


async def get_async_session() -> AsyncSession:
    """Yields an async database session."""
    async with async_session_factory() as session:
        try:
            yield session
        finally:
            await session.close()
