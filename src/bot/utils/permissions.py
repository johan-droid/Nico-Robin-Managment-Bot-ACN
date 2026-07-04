from __future__ import annotations

from telegram import Chat, ChatMember, ChatMemberAdministrator, Message, User
from telegram.ext import ContextTypes

from src.bot.config import settings

ADMIN_STATUSES = {ChatMember.ADMINISTRATOR, ChatMember.OWNER}


def is_sudo(user_id: int | None) -> bool:
    return user_id is not None and user_id in settings.sudo_users


def is_group_chat(chat: Chat | None) -> bool:
    return chat is not None and chat.type in {"group", "supergroup"}


async def is_telegram_admin(
    context: ContextTypes.DEFAULT_TYPE,
    chat_id: int,
    user_id: int,
) -> bool:
    """Check if user is admin with rate limiting to prevent enumeration attacks."""
    if is_sudo(user_id):
        return True

    # Rate limit permission checks to prevent user enumeration
    from src.bot.bot.middleware.rate_limiter import get_redis
    try:
        redis = get_redis()
        key = f"perm_check:{user_id}:{chat_id}"
        count = await redis.incr(key)
        if count == 1:
            await redis.expire(key, 60)  # 1 minute window
        elif count > 20:  # Rate limit
            await redis.expire(key, 3600)  # Extend to 1 hour if rate limited
            from src.bot.services.security_logger import SecurityLogger
            await SecurityLogger.log_event(
                "permission_check_rate_limited",
                user_id=user_id,
                chat_id=chat_id,
                severity="MEDIUM"
            )
            return False
    except Exception:
        pass  # Continue with normal check if Redis fails

    try:
        member = await context.bot.get_chat_member(chat_id, user_id)
        return member.status in ADMIN_STATUSES
    except Exception as e:
        from src.bot.services.security_logger import SecurityLogger
        await SecurityLogger.log_event(
            "permission_check_failed",
            user_id=user_id,
            chat_id=chat_id,
            severity="LOW",
            details={"error": str(e)}
        )
        return False


async def is_telegram_owner(
    context: ContextTypes.DEFAULT_TYPE,
    chat_id: int,
    user_id: int,
) -> bool:
    if is_sudo(user_id):
        return True
    member = await context.bot.get_chat_member(chat_id, user_id)
    return member.status == ChatMember.OWNER


def user_display(user: User | None) -> str:
    if user is None:
        return "Unknown"
    if user.username:
        return f"@{user.username}"
    return user.full_name or str(user.id)


def is_anonymous_admin_message(message: Message | None) -> bool:
    return (
        message is not None
        and message.sender_chat is not None
        and message.from_user is None
    )


async def bot_has_admin_rights(
    context: ContextTypes.DEFAULT_TYPE,
    chat_id: int,
    *rights: str,
) -> bool:
    bot_user = await context.bot.get_me()
    member = await context.bot.get_chat_member(chat_id, bot_user.id)
    if member.status not in ADMIN_STATUSES:
        return False
    if member.status == ChatMember.OWNER:
        return True
    if not isinstance(member, ChatMemberAdministrator):
        return False
    return all(bool(getattr(member, right, False)) for right in rights)
