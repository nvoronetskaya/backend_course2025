import pytest
from unittest.mock import MagicMock, patch
from contextlib import asynccontextmanager

import fakeredis.aioredis
from repository.moderation_result.moderation_redis_repository import ModerationRedisRepository

@pytest.fixture
def fake_redis():
    return fakeredis.aioredis.FakeRedis(encoding="utf-8", decode_responses=True)

@pytest.fixture
def repo(fake_redis):
    @asynccontextmanager
    async def _fake_connection():
        yield fake_redis

    with patch(
        "repository.moderation_result.moderation_redis_repository.get_redis_connection",
        _fake_connection,
    ):
        yield ModerationRedisRepository()

def make_orm_object(id=1, item_id=10, status="completed", is_violation=True, probability=0.85):
    obj = MagicMock()
    obj.id = id
    obj.item_id = item_id
    obj.status = status
    obj.is_violation = is_violation
    obj.probability = probability
    obj.to_dict.return_value = {
        "id": id, "item_id": item_id, "status": status,
        "is_violation": is_violation, "probability": probability,
    }
    return obj

@pytest.mark.integration
class TestDeleteForItem:
    @pytest.mark.asyncio
    async def test_deletes_item_and_task_keys(self, repo, fake_redis):
        await repo.set_moderation(1, make_orm_object(id=1, item_id=10))
        await repo.set_moderation(2, make_orm_object(id=2, item_id=10))
        await repo.set_moderation(3, make_orm_object(id=3, item_id=10))

        assert await repo.get_moderation(1) is not None
        assert await repo.get_moderation(2) is not None
        assert await repo.get_moderation(3) is not None
        assert await repo.get_moderation_for_item(10) is not None

        await repo.delete_for_item(10, [1, 2, 3])

        assert await repo.get_moderation(1) is None
        assert await repo.get_moderation(2) is None
        assert await repo.get_moderation(3) is None
        assert await repo.get_moderation_for_item(10) is None

    @pytest.mark.asyncio
    async def test_deletes_item_key_with_empty_task_ids(self, repo, fake_redis):
        await repo.set_prediction_for_item(10, {"is_violation": False, "probability": 0.1})

        assert await repo.get_moderation_for_item(10) is not None

        await repo.delete_for_item(10, [])

        assert await repo.get_moderation_for_item(10) is None

    @pytest.mark.asyncio
    async def test_does_not_affect_other_items(self, repo, fake_redis):
        await repo.set_moderation(1, make_orm_object(id=1, item_id=10))
        await repo.set_moderation(2, make_orm_object(id=2, item_id=20))

        await repo.delete_for_item(10, [1])

        assert await repo.get_moderation(1) is None
        assert await repo.get_moderation_for_item(10) is None
        assert await repo.get_moderation(2) is not None
        assert await repo.get_moderation_for_item(20) is not None
