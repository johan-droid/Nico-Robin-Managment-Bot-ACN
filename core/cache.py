from __future__ import annotations

import threading
import time
from dataclasses import dataclass
from typing import Any


@dataclass
class _CacheEntry:
    value: Any
    expires_at: float | None = None


class Cache:
    """Thread-safe in-memory cache with optional TTL support."""

    _instance: Cache | None = None
    _instance_lock = threading.Lock()

    def __new__(cls) -> Cache:
        with cls._instance_lock:
            if cls._instance is None:
                cls._instance = super().__new__(cls)
                cls._instance._store = {}
                cls._instance._lock = threading.RLock()
        return cls._instance

    def _is_expired(self, entry: _CacheEntry) -> bool:
        return entry.expires_at is not None and entry.expires_at <= time.monotonic()

    def get(self, key: str, default: Any = None) -> Any:
        with self._lock:
            entry = self._store.get(key)
            if entry is None:
                return default
            if self._is_expired(entry):
                self._store.pop(key, None)
                return default
            return entry.value

    def set(self, key: str, value: Any, ttl: int | float | None = None) -> None:
        with self._lock:
            expires_at = None if ttl is None else time.monotonic() + float(ttl)
            self._store[key] = _CacheEntry(value=value, expires_at=expires_at)

    def delete(self, key: str) -> None:
        with self._lock:
            self._store.pop(key, None)

    def clear(self) -> None:
        with self._lock:
            self._store.clear()

    def cleanup(self) -> int:
        """Remove expired entries and return how many were removed."""
        removed = 0
        with self._lock:
            for key in list(self._store.keys()):
                if self._is_expired(self._store[key]):
                    self._store.pop(key, None)
                    removed += 1
        return removed
