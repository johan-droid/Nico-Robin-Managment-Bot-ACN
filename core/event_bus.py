from __future__ import annotations

import asyncio
import logging
import inspect
from collections import defaultdict
from collections.abc import Awaitable, Callable
from dataclasses import dataclass
from typing import Any

logger = logging.getLogger(__name__)
EventCallback = Callable[[dict[str, Any]], Awaitable[None]]


@dataclass(slots=True)
class EventMessage:
    event_type: str
    data: dict[str, Any]


class EventBus:
    """Async publish/subscribe bus with serialized dispatch."""

    _instance: "EventBus | None" = None

    def __new__(cls) -> "EventBus":
        if cls._instance is None:
            cls._instance = super().__new__(cls)
            cls._instance._subscribers = defaultdict(list)
            cls._instance._queue = asyncio.Queue()
            cls._instance._running = False
            cls._instance._worker_task = None
        return cls._instance

    def subscribe(self, event_type: str, callback: EventCallback) -> None:
        self._subscribers[event_type].append(callback)

    async def publish(self, event_type: str, data: dict[str, Any]) -> None:
        await self._queue.put(EventMessage(event_type=event_type, data=data))

    async def start(self) -> None:
        if self._running:
            return
        self._running = True
        self._worker_task = asyncio.create_task(self._worker(), name="event-bus")

    async def stop(self) -> None:
        self._running = False
        if self._worker_task is not None:
            await self._queue.put(EventMessage(event_type="__stop__", data={}))
            await self._worker_task
            self._worker_task = None

    async def _worker(self) -> None:
        while self._running:
            message = await self._queue.get()
            if message.event_type == "__stop__":
                break
            callbacks = list(self._subscribers.get(message.event_type, ()))
            if not callbacks:
                continue
            for callback in callbacks:
                asyncio.create_task(self._safe_dispatch(callback, message.data, message.event_type))

    async def _safe_dispatch(self, callback: EventCallback, data: dict[str, Any], event_type: str) -> None:
        try:
            result = callback(data)
            if inspect.isawaitable(result):
                await result
        except Exception:
            logger.exception("event_bus_callback_failed", extra={"event_type": event_type, "callback": getattr(callback, "__name__", repr(callback))})


event_bus = EventBus()
