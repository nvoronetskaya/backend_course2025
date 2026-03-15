import pytest
from unittest.mock import AsyncMock, MagicMock
from service.moderation_service import ModerationService

@pytest.fixture
def moder_repo():
    repo = AsyncMock()
    repo.delete_for_item = AsyncMock(return_value=[])
    return repo

@pytest.fixture
def item_repo():
    repo = AsyncMock()
    repo.get_item = AsyncMock(return_value=None)
    repo.close_item = AsyncMock(return_value=None)
    return repo

@pytest.fixture
def service(moder_repo, item_repo):
    return ModerationService(
        moder_repo=moder_repo,
        item_repo=item_repo,
    )

def make_item(id=1, is_closed=False):
    item = MagicMock()
    item.id = id
    item.is_closed = is_closed
    return item

class TestCloseItem:
    @pytest.mark.asyncio
    async def test_close_item_full_flow(self, service, item_repo, moder_repo):
        item = make_item(id=1)
        closed_item = make_item(id=1, is_closed=True)
        item_repo.get_item.return_value = item
        item_repo.close_item.return_value = closed_item
        moder_repo.delete_for_item.return_value = [10, 11, 12]

        result = await service.close_item(1)

        assert result is closed_item
        item_repo.get_item.assert_awaited_once_with(1)
        moder_repo.delete_for_item.assert_awaited_once_with(1)
        item_repo.close_item.assert_awaited_once_with(1)

    @pytest.mark.asyncio
    async def test_close_item_returns_none_when_not_found(self, service, item_repo, moder_repo):
        item_repo.get_item.return_value = None

        result = await service.close_item(999)

        assert result is None
        item_repo.get_item.assert_awaited_once_with(999)
        moder_repo.delete_for_item.assert_not_awaited()
        item_repo.close_item.assert_not_awaited()

    @pytest.mark.asyncio
    async def test_close_item_with_no_moderation_results(self, service, item_repo, moder_repo):
        item = make_item(id=5)
        closed_item = make_item(id=5, is_closed=True)
        item_repo.get_item.return_value = item
        item_repo.close_item.return_value = closed_item
        moder_repo.delete_for_item.return_value = []

        result = await service.close_item(5)

        assert result is closed_item
        item_repo.close_item.assert_awaited_once_with(5)
