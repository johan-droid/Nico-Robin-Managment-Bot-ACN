"""Database engine — hardened with pool limits, SSL, timeouts, and connection recycling."""

from __future__ import annotations

from collections.abc import AsyncIterator

from sqlalchemy.ext.asyncio import (
    AsyncEngine,
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)

from config import settings


def create_engine(url: str | None = None) -> AsyncEngine:
    """Create a hardened async database engine.

    Security measures:
    - Reduced pool size to prevent connection exhaustion attacks
    - Query timeout to prevent long-running malicious queries
    - Connection recycling to prevent stale/hijacked connections
    - SSL enforcement in production
    - Pool pre-ping to detect dead connections
    """
    connect_args: dict = {}

    # Query timeout (prevents hung queries from exhausting pool)
    connect_args["command_timeout"] = settings.db_query_timeout

    # SSL enforcement in production
    if settings.db_ssl_required or settings.environment == "production":
        connect_args["ssl"] = True

    return create_async_engine(
        url or settings.database_url,
        pool_size=settings.db_pool_size,
        max_overflow=settings.db_max_overflow,
        pool_pre_ping=True,
        pool_recycle=settings.db_pool_recycle,
        pool_timeout=30,
        connect_args=connect_args,
        # Log slow queries in debug (disable in production for security)
        echo=False,
    )


engine = create_engine()
async_session_factory = async_sessionmaker(
    bind=engine,
    expire_on_commit=False,
    autoflush=False,
)


async def get_session() -> AsyncIterator[AsyncSession]:
    async with async_session_factory() as session:
        yield session


async def dispose_engine() -> None:
    await engine.dispose()
