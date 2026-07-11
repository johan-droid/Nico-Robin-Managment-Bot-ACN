The task was to implement the following phases:
1. Detect framework (python-telegram-bot), inventory handlers, permission checks, db access, and dangerous execution paths into docs/audit-baseline.md.
2. Centralize permissions: Added `moderator_only` and updated admin.py to use it for `warn`/`mute`.
3. Disable dangerous execution: Handled `subprocess.run` inside `src/merge/resolver.py` based on `ENABLE_DEV_COMMANDS`.
4. Telegram API Resilience: Updated `error_handler` to properly handle `RetryAfter`, `Forbidden`, `BadRequest`, `NetworkError` and `TimedOut`.
5. Database Concurrency Hardening: Using postgres, added `with_for_update()` to `ensure_user` and `ensure_minimal_user` to avoid concurrency problems when creating users.

I have executed tests successfully and want to request a code review.
