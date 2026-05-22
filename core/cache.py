from __future__ import annotations

import threading
import time
from dataclasses import dataclass
from typing import Any


@dataclass(slots=True)
class _CacheEntry:
    value: Any
    expires_at: float | None = None


class Cache:
    _instance: "Cache | None" = None

    def __new__(cls) -> "Cache":
        if cls._instance is None:
            cls._instance = super().__new__(cls)
            cls._instance._store = {}
            cls._instance._lock = threading.RLock()
        return cls._instance

    def get(self, key: str, default: Any = None) -> Any:
        with self._lock:
            entry = self._store.get(key)
            if entry is None:
                return default
            if entry.expires_at is not None and entry.expires_at <= time.time():
                self._store.pop(key, None)
                return default
            return entry.value

    def set(self, key: str, value: Any, ttl: int | None = None) -> None:
        with self._lock:
            expires_at = time.time() + ttl if ttl else None
            self._store[key] = _CacheEntry(value=value, expires_at=expires_at)

    def delete(self, key: str) -> None:
        with self._lock:
            self._store.pop(key, None)

    def clear_prefix(self, prefix: str) -> None:
        with self._lock:
            for key in list(self._store):
                if key.startswith(prefix):
                    self._store.pop(key, None)

    def keys(self) -> list[str]:
        with self._lock:
            return list(self._store.keys())


cache = Cache()
