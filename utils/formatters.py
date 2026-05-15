from __future__ import annotations

from datetime import UTC, datetime

from telegram import User

from utils.i18n import gettext
from utils.robin_quotes import action_quote


class _SafeFormatDict(dict[str, object]):
    def __missing__(self, key: str) -> str:
        return f"{{{key}}}"


def display_user(
    user_id: int, username: str | None = None, name: str | None = None
) -> str:
    if username:
        return f"@{username.removeprefix('@')}"
    if name:
        return f"{name} ({user_id})"
    return str(user_id)


def telegram_user_label(user: User | None) -> str:
    if user is None:
        return "Unknown"
    if user.username:
        return f"@{user.username} (ID: {user.id})"
    full_name = user.full_name or str(user.id)
    return f"{full_name} (ID: {user.id})"


def ban_message(target: str, reason: str, locale: str = "en") -> str:
    return gettext("ban.success", locale, target=target, reason=reason)


def mute_message(target: str, duration: str, reason: str, locale: str = "en") -> str:
    return gettext(
        "mute.success", locale, target=target, duration=duration, reason=reason
    )


def warn_message(
    target: str,
    count: int,
    maximum: int,
    reason: str,
    locale: str = "en",
) -> str:
    return gettext(
        "warn.issued",
        locale,
        target=target,
        count=count,
        max=maximum,
        reason=reason,
    )


def format_welcome(
    template: str | None,
    first: str,
    username: str,
    chat: str,
    count: int | None,
    locale: str = "en",
) -> str:
    raw = template or gettext("welcome.default", locale)
    return raw.format_map(
        _SafeFormatDict(
            first=first,
            username=username,
            chat=chat,
            count=count if count is not None else "?",
        )
    )


def safe_format(template: str, **values: object) -> str:
    return template.format_map(_SafeFormatDict(values))


def format_action_log(
    action: str,
    actor: str,
    target: str,
    group: str,
    reason: str,
) -> str:
    now = datetime.now(UTC).strftime("%Y-%m-%d %H:%M:%S UTC")
    return (
        f"🌸 [{action.upper()}]\n"
        f"Admin:  {actor}\n"
        f"Target: {target}\n"
        f"Group:  {group}\n"
        f"Reason: {reason}\n"
        f"Time:   {now}\n\n"
        "— Nico Robin has added another Poneglyph to the record."
    )


def action_success(action: str, target: str) -> str:
    return f"🌸 {target}: {action_quote(action)}"
