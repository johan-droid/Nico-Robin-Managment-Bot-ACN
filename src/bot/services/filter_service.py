from __future__ import annotations

import re
from dataclasses import dataclass

from sqlalchemy import delete, select
from sqlalchemy.ext.asyncio import AsyncSession

from src.bot.models.filter import Filter


@dataclass(frozen=True)
class MatchedFilter:
    filter: Filter
    match_text: str


class FilterService:
    @staticmethod
    async def add_filter(
        session: AsyncSession,
        group_id: int,
        trigger: str,
        response: str | None,
        action: str,
        regex: bool,
        created_by: int | None,
        match_mode: str = "contains",
    ) -> Filter:
        normalized = trigger.lower()
        result = await session.execute(
            select(Filter).where(
                Filter.group_id == group_id,
                Filter.trigger == normalized,
            )
        )
        item = result.scalar_one_or_none()
        if item is None:
            item = Filter(
                group_id=group_id,
                trigger=normalized,
                response=response,
                action=action,
                regex=regex,
                match_mode=match_mode,
                created_by=created_by,
            )
            session.add(item)
        else:
            item.response = response
            item.action = action
            item.regex = regex
            item.created_by = created_by
        await session.flush()
        return item

    @staticmethod
    async def remove_filter(session: AsyncSession, group_id: int, trigger: str) -> int:
        result = await session.execute(
            delete(Filter).where(
                Filter.group_id == group_id,
                Filter.trigger == trigger.lower(),
            )
        )
        return int(result.rowcount or 0)

    @staticmethod
    async def list_filters(session: AsyncSession, group_id: int) -> list[Filter]:
        result = await session.execute(
            select(Filter).where(Filter.group_id == group_id).order_by(Filter.trigger)
        )
        return list(result.scalars().all())

    @staticmethod
    async def match_filters(
        session: AsyncSession,
        group_id: int,
        text: str,
    ) -> list[MatchedFilter]:
        items = await FilterService.list_filters(session, group_id)
        lowered = text.lower()
        matches: list[MatchedFilter] = []
        for item in items:
            mode = getattr(item, "match_mode", "contains")

            if item.regex or mode == "regex":
                try:
                    match = re.search(item.trigger, text, flags=re.IGNORECASE)
                    if match:
                        matches.append(MatchedFilter(item, match.group(0)))
                except re.error:
                    continue
            elif mode == "exact":
                if item.trigger == lowered:
                    matches.append(MatchedFilter(item, item.trigger))
            elif mode == "word":
                if re.search(rf"\b{re.escape(item.trigger)}\b", text, flags=re.IGNORECASE):
                    matches.append(MatchedFilter(item, item.trigger))
            else: # contains
                if item.trigger in lowered:
                    matches.append(MatchedFilter(item, item.trigger))
        return matches
