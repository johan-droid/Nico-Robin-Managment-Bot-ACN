from collections.abc import Callable
from functools import wraps
from typing import Any

import structlog

from database import async_session_factory

logger = structlog.get_logger(__name__)


def with_db_session(func: Callable) -> Callable:
    """Decorator to inject a database session into a PTB handler."""

    @wraps(func)
    async def wrapper(update, context, *args, **kwargs) -> Any:
        async with async_session_factory() as session:
            try:
                # Inject session into kwargs
                kwargs["session"] = session
                result = await func(update, context, *args, **kwargs)
                await session.commit()
                return result
            except Exception as e:
                await session.rollback()
                logger.error("db_session_rollback", error=str(e), handler=func.__name__)
                raise

    return wrapper
