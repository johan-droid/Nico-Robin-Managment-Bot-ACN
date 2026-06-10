from __future__ import annotations

from functools import lru_cache
from typing import Any
from urllib.parse import urlparse

import structlog
from redis.asyncio import Redis

from src.bot.config import settings

logger = structlog.get_logger(__name__)


class _NoOpPipeline:
    def zadd(self, *args: Any, **kwargs: Any) -> _NoOpPipeline:
        return self

    def zremrangebyscore(self, *args: Any, **kwargs: Any) -> _NoOpPipeline:
        return self

    def zcard(self, *args: Any, **kwargs: Any) -> _NoOpPipeline:
        return self

    def expire(self, *args: Any, **kwargs: Any) -> _NoOpPipeline:
        return self

    async def execute(self) -> tuple[int, int, int, int]:
        return (0, 0, 0, 0)


class _NoOpRedis:
    def pipeline(self) -> _NoOpPipeline:
        return _NoOpPipeline()

    async def exists(self, *args: Any, **kwargs: Any) -> int:
        return 0

    async def ttl(self, *args: Any, **kwargs: Any) -> int:
        return -2

    async def incr(self, *args: Any, **kwargs: Any) -> int:
        return 1

    async def expire(self, *args: Any, **kwargs: Any) -> bool:
        return True

    async def set(self, *args: Any, **kwargs: Any) -> bool:
        return True

    async def get(self, *args: Any, **kwargs: Any) -> str | None:
        return None

    async def getdel(self, *args: Any, **kwargs: Any) -> int:
        return 0

    async def xadd(self, *args: Any, **kwargs: Any) -> str:
        return "0-0"

    async def xrevrange(self, *args: Any, **kwargs: Any) -> list:
        return []

    async def zadd(self, *args: Any, **kwargs: Any) -> int:
        return 0

    async def zcard(self, *args: Any, **kwargs: Any) -> int:
        return 0

    async def zremrangebyscore(self, *args: Any, **kwargs: Any) -> int:
        return 0

    async def smembers(self, *args: Any, **kwargs: Any) -> set[str]:
        return set()

    async def delete(self, *args: Any, **kwargs: Any) -> int:
        return 0

    async def aclose(self) -> None:
        return None


def _is_loopback_redis_url(redis_url: str) -> bool:
    parsed = urlparse(redis_url)
    return parsed.hostname in {"localhost", "127.0.0.1", "::1"}


@lru_cache(maxsize=1)
def get_redis() -> Redis | _NoOpRedis:
    if settings.redis_url:
        if settings.environment in {"local", "test"} and _is_loopback_redis_url(
            settings.redis_url
        ):
            logger.info("redis_disabled_for_local_loopback", redis_url="loopback")
            return _NoOpRedis()
        try:
            return Redis.from_url(settings.redis_url, decode_responses=True)
        except Exception as exc:
            logger.warning("redis_init_failed", error=str(exc))
    if settings.environment in {"local", "test"}:
        return _NoOpRedis()
    raise RuntimeError("Redis is required outside local/test environments")


async def close_redis() -> None:
    await get_redis().aclose()
