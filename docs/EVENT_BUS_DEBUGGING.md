# Event Bus Debugging Guide

The event bus in this scaffold is used to serialize cross-module work that would otherwise be easy to race: points, flair rewards, report handling, and broadcast notifications.

## Why it prevents race conditions

Direct module-to-module calls let one command mutate shared state while another command is reading it. The event bus avoids that by:

1. Putting every event into a single asyncio queue.
2. Dispatching events in submission order.
3. Running subscriber callbacks through a controlled worker task.
4. Letting each module update SQLite inside its own transactional section.

That means a flair success can publish `points:add`, the points module can update totals once, and no other command needs to know how the point write happened.

## What to check first when something looks inconsistent

1. Confirm the publisher emitted the event with the expected payload.
2. Check that the subscriber is registered before the event is published.
3. Verify the callback uses the database singleton and not an ad hoc connection.
4. Look for duplicate event IDs or repeated `transaction_uid` values.
5. Review the cache key if a module is using a cached feature flag or admin list.

## Practical debugging flow

If a command appears to succeed but downstream behavior does not happen:

1. Search the log file for the event type.
2. Confirm the subscriber callback ran.
3. Inspect the SQLite row for the target table.
4. Check whether a cache value is shadowing the database row.
5. Re-run with a unique transaction ID to rule out deduplication.

## Stable pattern

Use this flow for event-driven changes:

- command handler validates input
- handler publishes an event
- subscriber performs the database write
- subscriber updates the cache
- the handler replies after publish if needed

This keeps the command path short and makes failures easier to isolate.
