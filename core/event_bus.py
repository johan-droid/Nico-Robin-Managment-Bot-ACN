from __future__ import annotations

import asyncio
import logging
import time
from collections.abc import Awaitable, Callable
from dataclasses import dataclass, field
from typing import Any

EventCallback = Callable[[dict[str, Any]], Awaitable[None]]


@dataclass(slots=True)
class _Subscription:
    event_type: str
    callback: EventCallback
    name: str = field(default="")


class EventBus:
    """Async event bus for decoupled inter-module communication."""

    def __init__(self) -> None:
        self._queue: asyncio.Queue[dict[str, Any]] = asyncio.Queue()
        self._subscribers: dict[str, list[_Subscription]] = {}
        self._workers: list[asyncio.Task[None]] = []
        self._running = False
        self._logger = logging.getLogger(__name__)

    def subscribe(
        self, event_type: str, callback: EventCallback, *, name: str = ""
    ) -> None:
        subscription = _Subscription(
            event_type=event_type, callback=callback, name=name
        )
        self._subscribers.setdefault(event_type, []).append(subscription)
        self._logger.info(
            "event_bus_subscribed",
            extra={"event_type": event_type, "name": name or callback.__name__},
        )

    def unsubscribe(self, event_type: str, callback: EventCallback) -> None:
        current = self._subscribers.get(event_type, [])
        self._subscribers[event_type] = [
            sub for sub in current if sub.callback != callback
        ]

    async def publish(self, event_type: str, data: dict[str, Any]) -> None:
        event = {
            "event_type": event_type,
            "data": data,
            "published_at": time.time(),
        }
        await self._queue.put(event)

    async def start(self, worker_count: int = 2) -> None:
        if self._running:
            return
        self._running = True
        self._workers = [
            asyncio.create_task(
                self._worker_loop(worker_id), name=f"event-bus-{worker_id}"
            )
            for worker_id in range(worker_count)
        ]

    async def stop(self) -> None:
        if not self._running:
            return
        self._running = False
        for task in self._workers:
            task.cancel()
        if self._workers:
            await asyncio.gather(*self._workers, return_exceptions=True)
        self._workers.clear()

    async def _worker_loop(self, worker_id: int) -> None:
        self._logger.info("event_bus_worker_started", extra={"worker_id": worker_id})
        while self._running:
            got_event = False
            try:
                event = await self._queue.get()
                got_event = True
                await self._dispatch(event)
            except asyncio.CancelledError:
                raise
            except Exception:
                self._logger.exception(
                    "event_bus_worker_failure", extra={"worker_id": worker_id}
                )
            finally:
                if got_event:
                    self._queue.task_done()

    async def _dispatch(self, event: dict[str, Any]) -> None:
        event_type = str(event.get("event_type", ""))
        callbacks = self._subscribers.get(event_type, [])
        if not callbacks:
            return

        tasks = [sub.callback(event) for sub in callbacks]
        results = await asyncio.gather(*tasks, return_exceptions=True)
        for idx, result in enumerate(results):
            if isinstance(result, Exception):
                self._logger.exception(
                    "event_bus_callback_error",
                    extra={
                        "event_type": event_type,
                        "callback": callbacks[idx].name
                        or callbacks[idx].callback.__name__,
                    },
                    exc_info=result,
                )
