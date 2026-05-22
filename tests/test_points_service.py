from __future__ import annotations

from dataclasses import dataclass, field
from types import SimpleNamespace
from typing import Any

import pytest

import src.bot.services.point_service as point_service_module
from src.bot.models.points import PointTransaction, UserPoints
from src.bot.services.point_service import PointService


@dataclass
class FakeStorage:
    user_points: dict[tuple[int, int], UserPoints] = field(default_factory=dict)
    transactions: list[PointTransaction] = field(default_factory=list)
    next_transaction_id: int = 1


class FakeScalarResult:
    def __init__(self, rows: list[Any]) -> None:
        self._rows = rows

    def all(self) -> list[Any]:
        return list(self._rows)


class FakeResult:
    def __init__(self, rows: list[Any]) -> None:
        self._rows = rows

    def scalar_one_or_none(self) -> Any | None:
        return self._rows[0] if self._rows else None

    def scalars(self) -> FakeScalarResult:
        return FakeScalarResult(self._rows)

    def all(self) -> list[Any]:
        return list(self._rows)


class FakeTransaction:
    async def __aenter__(self) -> "FakeSession":
        return self.session

    async def __aexit__(self, exc_type, exc, tb) -> bool:
        return False

    def __init__(self, session: "FakeSession") -> None:
        self.session = session


class FakeSession:
    def __init__(self, storage: FakeStorage) -> None:
        self.storage = storage

    def begin(self) -> FakeTransaction:
        return FakeTransaction(self)

    async def __aenter__(self) -> "FakeSession":
        return self

    async def __aexit__(self, exc_type, exc, tb) -> bool:
        return False

    async def execute(self, query):
        compiled = str(query.compile(compile_kwargs={"literal_binds": True}))

        if "FROM point_transactions" in compiled:
            if "transaction_uid =" in compiled:
                transaction_uid = _extract_quoted_value(compiled, "transaction_uid")
                rows = [
                    transaction
                    for transaction in self.storage.transactions
                    if transaction.transaction_uid == transaction_uid
                ]
                return FakeResult(rows)

            group_id = _extract_int_value(compiled, "group_id")
            user_id = _extract_int_value(compiled, "user_id")
            rows = [
                transaction
                for transaction in self.storage.transactions
                if transaction.group_id == group_id
                and (user_id is None or transaction.user_id == user_id)
            ]
            rows.sort(
                key=lambda transaction: (
                    transaction.user_id,
                    transaction.transaction_time,
                    transaction.transaction_id or 0,
                )
            )
            return FakeResult(rows)

        if "FROM user_points" in compiled:
            group_id = _extract_int_value(compiled, "group_id")
            user_id = _extract_int_value(compiled, "user_id")
            rows = [
                user_points
                for (stored_user_id, stored_group_id), user_points in self.storage.user_points.items()
                if stored_group_id == group_id
                and (user_id is None or stored_user_id == user_id)
            ]
            return FakeResult(rows)

        return FakeResult([])

    def add(self, obj) -> None:
        if isinstance(obj, UserPoints):
            self.storage.user_points[(obj.user_id, obj.group_id)] = obj
            return

        if isinstance(obj, PointTransaction):
            if obj.transaction_id is None:
                obj.transaction_id = self.storage.next_transaction_id
                self.storage.next_transaction_id += 1
            self.storage.transactions.append(obj)
            return

    async def flush(self) -> None:
        return None


class FakeSessionFactory:
    def __init__(self, storage: FakeStorage) -> None:
        self.storage = storage

    def __call__(self) -> FakeSessionContext:
        return FakeSessionContext(self.storage)


class FakeSessionContext:
    def __init__(self, storage: FakeStorage) -> None:
        self.session = FakeSession(storage)

    async def __aenter__(self) -> FakeSession:
        return self.session

    async def __aexit__(self, exc_type, exc, tb) -> bool:
        return False


def _extract_int_value(sql: str, column_name: str) -> int | None:
    marker = f"{column_name} = "
    if marker not in sql:
        return None

    value_fragment = sql.split(marker, 1)[1].split()[0]
    value_fragment = value_fragment.rstrip(",")
    if value_fragment.endswith("FOR"):
        value_fragment = value_fragment[:-3]
    return int(value_fragment)


def _extract_quoted_value(sql: str, column_name: str) -> str | None:
    marker = f"{column_name} = "
    if marker not in sql:
        return None

    value_fragment = sql.split(marker, 1)[1].split(" AND ", 1)[0].strip()
    if value_fragment.startswith("'") and value_fragment.endswith("'"):
        return value_fragment[1:-1]
    return value_fragment


@pytest.fixture()
def point_service(monkeypatch: pytest.MonkeyPatch) -> tuple[PointService, FakeStorage]:
    storage = FakeStorage()
    monkeypatch.setattr(
        point_service_module,
        "async_session_factory",
        FakeSessionFactory(storage),
    )
    return PointService(), storage


@pytest.mark.asyncio
async def test_add_points_awards_and_records_transaction(point_service) -> None:
    service, storage = point_service

    success, message = await service.add_points(
        7,
        25,
        "helpful reply",
        group_id=-100,
        source="message",
        cooldown_seconds=0,
        transaction_uid="txn-1",
    )

    assert success is True
    assert message == "Awarded 25 points."
    user_points = storage.user_points[(7, -100)]
    assert user_points.current_points == 25
    assert user_points.total_earned == 25
    assert user_points.last_earned > 0
    assert storage.transactions[0].transaction_uid == "txn-1"


@pytest.mark.asyncio
async def test_add_points_rejects_duplicate_transaction(point_service) -> None:
    service, storage = point_service

    first_success, _ = await service.add_points(
        7,
        10,
        "initial award",
        group_id=-100,
        source="award",
        cooldown_seconds=0,
        transaction_uid="txn-dup",
    )
    second_success, second_message = await service.add_points(
        7,
        10,
        "initial award",
        group_id=-100,
        source="award",
        cooldown_seconds=0,
        transaction_uid="txn-dup",
    )

    assert first_success is True
    assert second_success is False
    assert second_message == "Duplicate transaction."
    assert storage.user_points[(7, -100)].current_points == 10
    assert len(storage.transactions) == 1


@pytest.mark.asyncio
async def test_add_points_honors_cooldown(point_service, monkeypatch: pytest.MonkeyPatch) -> None:
    service, storage = point_service
    current_time = [1_000]
    monkeypatch.setattr(point_service_module.time, "time", lambda: current_time[0])

    first_success, _ = await service.add_points(
        7,
        10,
        "message bonus",
        group_id=-100,
        source="message",
        cooldown_seconds=60,
        transaction_uid="txn-cooldown-1",
    )
    current_time[0] = 1_020
    second_success, second_message = await service.add_points(
        7,
        10,
        "message bonus",
        group_id=-100,
        source="message",
        cooldown_seconds=60,
        transaction_uid="txn-cooldown-2",
    )

    assert first_success is True
    assert second_success is False
    assert second_message == "Cooldown active. Try again in 40 seconds."
    assert storage.user_points[(7, -100)].current_points == 10


@pytest.mark.asyncio
async def test_recalculate_group_points_rebuilds_balances(point_service, monkeypatch: pytest.MonkeyPatch) -> None:
    service, storage = point_service
    monkeypatch.setattr(point_service_module.time, "time", lambda: 2_000)

    await service.add_points(
        7,
        15,
        "first award",
        group_id=-100,
        source="award",
        cooldown_seconds=0,
        transaction_uid="txn-recalc-1",
    )
    await service.add_points(
        7,
        5,
        "second award",
        group_id=-100,
        source="award",
        cooldown_seconds=0,
        transaction_uid="txn-recalc-2",
    )
    storage.user_points[(7, -100)].current_points = 999
    storage.user_points[(7, -100)].total_earned = 999
    storage.user_points[(7, -100)].total_spent = 1

    summary = await service.recalculate_group_points(-100)

    assert summary["updated_users"] == 1
    assert storage.user_points[(7, -100)].current_points == 20
    assert storage.user_points[(7, -100)].total_earned == 20
    assert storage.user_points[(7, -100)].total_spent == 0
    assert storage.user_points[(7, -100)].level == 1
