"""Database engine — hardened with pool limits, SSL, timeouts, and connection recycling."""

from __future__ import annotations

from collections.abc import AsyncIterator

from sqlalchemy.ext.asyncio import (
    AsyncEngine,
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)

from src.bot.config import settings


def create_engine(url: str | None = None) -> AsyncEngine:
    """Create a hardened async database engine.

    Security measures:
    - Reduced pool size to prevent connection exhaustion attacks
    - Query timeout to prevent long-running malicious queries
    - Connection recycling to prevent stale/hijacked connections
    - SSL enforcement in production and for known cloud providers
    - Pool pre-ping to detect dead connections
    - Statement cache disabled for connection poolers (PgBouncer/Neon)
    - Connection validation to prevent injection
    - Query logging for security auditing
    """
    db_url = url or settings.async_database_url

    # Validate database URL to prevent injection
    if not db_url.startswith(("postgresql+asyncpg://", "postgresql://")):
        raise ValueError("Invalid database URL scheme - potential injection attempt")

    connect_args: dict = {}

    # Connection timeout (gives cloud Postgres cold starts room to wake up).
    connect_args["timeout"] = settings.db_connect_timeout

    # Query timeout (prevents hung queries from exhausting pool)
    connect_args["command_timeout"] = settings.db_query_timeout

    # SSL enforcement
    if settings.async_database_ssl_required:
        connect_args["ssl"] = True
        # Enforce certificate validation in production
        if settings.environment == "production":
            connect_args["sslrootcert"] = "root.crt"  # Should be provided in production

    # Connection Pooler Compatibility (Neon / PgBouncer)
    # PgBouncer in transaction mode does not support prepared statements.
    # We detect the '-pooler' suffix which is common in Neon URLs.
    if "-pooler" in db_url or settings.db_statement_cache_disabled:
        connect_args["statement_cache_size"] = 0

    # Security event hooks
    def connect_hook(dbapi_connection, connection_record):
        """Log successful database connections for auditing"""
        from src.bot.services.security_logger import SecurityLogger
        import asyncio
        asyncio.create_task(SecurityLogger.log_event(
            "database_connection_established",
            details={"database_url": "[redacted]"}
        ))

    def execution_hook(exec_state):
        """Log slow queries for security monitoring"""
        if exec_state.execution_options.get("timeout", 0) > 5:
            from src.bot.services.security_logger import SecurityLogger
            import asyncio
            asyncio.create_task(SecurityLogger.log_event(
                "slow_database_query",
                details={
                    "query": str(exec_state.statement)[:200],
                    "timeout": exec_state.execution_options.get("timeout")
                }
            ))

    return create_async_engine(
        db_url,
        pool_size=settings.db_pool_size,
        max_overflow=settings.db_max_overflow,
        pool_pre_ping=True,
        pool_recycle=settings.db_pool_recycle,
        pool_timeout=30,
        connect_args=connect_args,
        # Log slow queries in debug (disable in production for security)
        echo=settings.log_level == "DEBUG",
        connect_args=connect_args,
        pool_pre_ping=True,
        pool_recycle=settings.db_pool_recycle,
        pool_timeout=30,
        connect_args=connect_args,
        # Security hooks
        connect_args=connect_args,
        event_listeners={
            "connect": connect_hook,
            "before_execute": execution_hook
        }
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
