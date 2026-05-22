# Event Bus Debugging Guide

## Why this design avoids race-heavy module coupling
- Modules do not call each other directly.
- Command handlers publish events and return quickly.
- Dedicated event workers consume events in FIFO order from an async queue.
- Failures in one subscriber do not stop other subscribers.

## Event flow in this bot
1. A module publishes with `await event_bus.publish("points:add", payload)`.
2. The event is pushed into `EventBus._queue`.
3. Worker tasks pull events and dispatch to all subscribers for that type.
4. Each subscriber runs as an async task via `gather`.
5. Exceptions are captured and logged, while the queue keeps processing.

## Practical debugging checklist
1. Confirm the subscriber is registered:
   - Check startup logs for `event_bus_subscribed`.
2. Confirm event type spelling matches exactly:
   - Example: `points:add` is not `point:add`.
3. Confirm publish path executes:
   - Add temporary logging right before `publish`.
4. Confirm worker is alive:
   - Check logs for `event_bus_worker_started`.
5. Confirm payload schema:
   - Required keys must exist for subscriber logic.
6. Confirm DB side effects:
   - Query `point_transactions` and `user_points` after a test event.

## Handling high load safely
- Keep subscribers fast and idempotent.
- Use cache for hot reads and SQLite for durable writes.
- Avoid long blocking loops inside callbacks.
- Publish one event per business action; do not publish recursively unless needed.

## Example test flow
1. Use `/flirt beautiful` in a group.
2. `flirt` publishes `points:add`.
3. `points` subscriber updates `user_points` and writes `point_transactions`.
4. Use `/points` to confirm updated balance.
