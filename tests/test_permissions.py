from unittest.mock import AsyncMock, patch

import pytest


@pytest.mark.asyncio
async def test_permission_role_recognition():
    with (
        patch("src.bot.services.acn_service.get_redis") as mock_redis,
        patch("src.bot.services.acn_service.async_session_factory") as mock_db,
    ):

        # Setting up mocks to avoid database connection
        mock_redis.return_value.get = AsyncMock(return_value=None)

        class MockResult:
            def scalar_one_or_none(self):
                return None

        class MockSessionContext:
            async def __aenter__(self):
                return self

            async def __aexit__(self, exc_type, exc, tb):
                pass

            async def execute(self, *args, **kwargs):
                return MockResult()

        mock_db.return_value = MockSessionContext()

        from src.bot.services.acn_service import ACNService

        ACNService.CAPTAIN_ID = 1001
        ACNService.COMMANDER_IDS = (1002, 1003)

        assert await ACNService.is_captain(1001)
        assert await ACNService.is_commander(1002)
        assert await ACNService.is_commander(1003)
        assert not await ACNService.is_captain(9999)
