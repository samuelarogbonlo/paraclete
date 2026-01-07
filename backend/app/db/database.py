"""
Database configuration and session management.
"""
from typing import AsyncGenerator
from sqlalchemy.ext.asyncio import (
    AsyncSession,
    create_async_engine,
    async_sessionmaker,
    AsyncEngine,
)
from sqlalchemy.orm import declarative_base
from sqlalchemy.pool import NullPool
import logging

from app.config import settings

logger = logging.getLogger(__name__)

# Create async engine
# Note: Don't use pool_size/max_overflow with NullPool
engine_kwargs = {
    "url": settings.DATABASE_URL,
    "echo": settings.DEBUG,
    "pool_pre_ping": True,  # Verify connections before using
}

# Only add pooling params if not using NullPool
use_null_pool = settings.DATABASE_URL.startswith("postgresql+asyncpg://")
if use_null_pool:
    engine_kwargs["poolclass"] = NullPool
else:
    engine_kwargs["pool_size"] = settings.DATABASE_POOL_SIZE
    engine_kwargs["max_overflow"] = settings.DATABASE_MAX_OVERFLOW

engine: AsyncEngine = create_async_engine(**engine_kwargs)

# Create async session factory
AsyncSessionLocal = async_sessionmaker(
    engine,
    class_=AsyncSession,
    expire_on_commit=False,
    autocommit=False,
    autoflush=False,
)

# Create declarative base for models
Base = declarative_base()


async def get_session() -> AsyncGenerator[AsyncSession, None]:
    """
    Dependency to get database session.

    Yields:
        AsyncSession: Database session

    Usage:
        @app.get("/items")
        async def read_items(db: AsyncSession = Depends(get_session)):
            ...
    """
    async with AsyncSessionLocal() as session:
        try:
            yield session
            await session.commit()
        except Exception:
            await session.rollback()
            raise
        finally:
            await session.close()


async def init_db() -> None:
    """
    Initialize database tables.

    This should be called on application startup.
    In production, use Alembic migrations instead.
    """
    async with engine.begin() as conn:
        # Import all models to register them with Base
        from app.db.models import User, Session, Message, UserAPIKeys  # noqa

        # Create all tables
        await conn.run_sync(Base.metadata.create_all)
        logger.info("Database tables created successfully")


async def close_db() -> None:
    """
    Close database connections.

    This should be called on application shutdown.
    """
    await engine.dispose()
    logger.info("Database connections closed")