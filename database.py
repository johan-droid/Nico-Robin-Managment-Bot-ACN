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
    - SSL enforcement in production and for known cloud providers
    - Pool pre-ping to detect dead connections
    - Statement cache disabled for connection poolers (PgBouncer/Neon)
    """
    db_url = url or settings.async_database_url
    connect_args: dict = {}

    # Query timeout (prevents hung queries from exhausting pool)
    connect_args["command_timeout"] = settings.db_query_timeout

    # SSL enforcement
    if settings.async_database_ssl_required:
        connect_args["ssl"] = True

    # Connection Pooler Compatibility (Neon / PgBouncer)
    # PgBouncer in transaction mode does not support prepared statements.
    # We detect the '-pooler' suffix which is common in Neon URLs.
    if "-pooler" in db_url:
        connect_args["statement_cache_size"] = 0

    return create_async_engine(
        db_url,
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
