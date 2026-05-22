from __future__ import annotations

import re

from sqlalchemy import func, select, update
from sqlalchemy.ext.asyncio import AsyncSession

from src.bot.models.note import Note
from src.bot.services.crypto_service import get_crypto_service

NOTE_NAME_RE = re.compile(r"^[A-Za-z0-9_]{1,32}$")


class NoteService:
    @staticmethod
    def validate_note_name(name: str) -> str | None:
        normalized = name.lower().strip()
        if NOTE_NAME_RE.fullmatch(normalized):
            return normalized
        return None

    @staticmethod
    async def save_note(
        session: AsyncSession,
        group_id: int,
        name: str,
        content: str,
        created_by: int | None,
        media_id: str | None = None,
    ) -> Note:
        normalized = NoteService.validate_note_name(name)
        if normalized is None:
            raise ValueError("Invalid note name")
        crypto = get_crypto_service()
        result = await session.execute(
            select(Note).where(
                Note.group_id == group_id,
                Note.name == normalized,
                Note.deleted_at.is_(None),
            )
        )
        note = result.scalar_one_or_none()
        if note is None:
            note = Note(
                group_id=group_id,
                name=normalized,
                content=crypto.encrypt_text(content) or "",
                media_id=media_id,
                created_by=created_by,
            )
            session.add(note)
        else:
            note.content = crypto.encrypt_text(content) or ""
            note.media_id = media_id
            note.created_by = created_by
            note.deleted_at = None
        await session.flush()
        return note

    @staticmethod
    async def get_note(session: AsyncSession, group_id: int, name: str) -> Note | None:
        normalized = NoteService.validate_note_name(name)
        if normalized is None:
            return None
        result = await session.execute(
            select(Note).where(
                Note.group_id == group_id,
                Note.name == normalized,
                Note.deleted_at.is_(None),
            )
        )
        note = result.scalar_one_or_none()
        if note is not None:
            note.content = get_crypto_service().decrypt_text(note.content) or ""
        return note

    @staticmethod
    async def list_notes(session: AsyncSession, group_id: int) -> list[Note]:
        result = await session.execute(
            select(Note)
            .where(Note.group_id == group_id, Note.deleted_at.is_(None))
            .order_by(Note.name.asc())
        )
        return list(result.scalars().all())

    @staticmethod
    async def delete_note(session: AsyncSession, group_id: int, name: str) -> int:
        normalized = NoteService.validate_note_name(name)
        if normalized is None:
            return 0
        result = await session.execute(
            update(Note)
            .where(
                Note.group_id == group_id,
                Note.name == normalized,
                Note.deleted_at.is_(None),
            )
            .values(deleted_at=func.now())
        )
        return int(result.rowcount or 0)
