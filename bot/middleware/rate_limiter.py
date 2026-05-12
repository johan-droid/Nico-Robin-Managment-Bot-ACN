from __future__ import annotations

from functools import lru_cache
from typing import Any

import structlog

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

    async def smembers(self, *args: Any, **kwargs: Any) -> set[str]:
        return set()

    async def delete(self, *args: Any, **kwargs: Any) -> int:
        return 0

    async def aclose(self) -> None:
        return None


@lru_cache(maxsize=1)
def get_redis() -> _NoOpRedis:
    return _NoOpRedis()


async def close_redis() -> None:
    await get_redis().aclose()
