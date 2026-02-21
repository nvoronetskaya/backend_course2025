import pytest
from unittest.mock import MagicMock, patch
from contextlib import asynccontextmanager

import fakeredis.aioredis
from dto.response import PredictResponse
from repository.moderation_result.moderation_redis_repository import ModerationRedisRepository


@pytest.fixture
def fake_redis():
    return fakeredis.aioredis.FakeRedis(encoding="utf-8", decode_responses=True)


@pytest.fixture
def repo(fake_redis):
    @asynccontextmanager
    async def fake_connection():
        yield fake_redis

    with patch(
        "repository.moderation_result.moderation_redis_repository.get_redis_connection",
        fake_connection,
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
        "id": id,
        "item_id": item_id,
        "status": status,
        "is_violation": is_violation,
        "probability": probability,
    }
    return obj

@pytest.mark.integration
class TestSetAndGetModeration:
    @pytest.mark.asyncio
    async def test_roundtrip_by_task_id(self, repo):
        orm_obj = make_orm_object(id=1, item_id=10)

        await repo.set_moderation(1, orm_obj)
        result = await repo.get_moderation(1)

        assert result is not None
        assert result["id"] == 1
        assert result["item_id"] == 10
        assert result["status"] == "completed"
        assert result["is_violation"] is True
        assert result["probability"] == 0.85

    @pytest.mark.asyncio
    async def test_roundtrip_by_item_id(self, repo):
        orm_obj = make_orm_object(id=5, item_id=20)

        await repo.set_moderation(5, orm_obj)
        result = await repo.get_moderation_for_item(20)

        assert result is not None
        assert result["id"] == 5
        assert result["item_id"] == 20

    @pytest.mark.asyncio
    async def test_dict_data_with_item_id(self, repo):
        data = {
            "id": 3,
            "item_id": 30,
            "status": "completed",
            "is_violation": False,
            "probability": 0.1,
        }

        await repo.set_moderation(3, data)

        by_task = await repo.get_moderation(3)
        assert by_task["id"] == 3

        by_item = await repo.get_moderation_for_item(30)
        assert by_item["id"] == 3

@pytest.mark.integration
class TestSetModerationWithoutItemId:
    @pytest.mark.asyncio
    async def test_data_without_item_id_only_sets_task_key(self, repo, fake_redis):
        data = {"id": 99, "status": "completed", "is_violation": True, "probability": 0.9}

        await repo.set_moderation(99, data)

        by_task = await repo.get_moderation(99)
        assert by_task is not None
        assert by_task["id"] == 99

        keys = await fake_redis.keys("item-*")
        assert len(keys) == 0

@pytest.mark.integration
class TestSetPredictionForItem:
    @pytest.mark.asyncio
    async def test_predict_response_roundtrip(self, repo):
        predict_resp = PredictResponse(is_violation=False, probability=0.12)

        await repo.set_prediction_for_item(10, predict_resp)
        result = await repo.get_moderation_for_item(10)

        assert result is not None
        assert result["is_violation"] is False
        assert result["probability"] == 0.12

    @pytest.mark.asyncio
    async def test_overwrite_existing_item_cache(self, repo):
        await repo.set_prediction_for_item(10, PredictResponse(is_violation=True, probability=0.9))
        await repo.set_prediction_for_item(10, PredictResponse(is_violation=False, probability=0.1))

        result = await repo.get_moderation_for_item(10)
        assert result["is_violation"] is False
        assert result["probability"] == 0.1

@pytest.mark.integration
class TestTTL:
    @pytest.mark.asyncio
    async def test_set_moderation_sets_ttl_on_task_key(self, repo, fake_redis):
        orm_obj = make_orm_object(id=1, item_id=10)

        await repo.set_moderation(1, orm_obj)

        ttl = await fake_redis.ttl("task-1")
        assert ttl > 0
        assert ttl <= 1800

    @pytest.mark.asyncio
    async def test_set_moderation_sets_ttl_on_item_key(self, repo, fake_redis):
        orm_obj = make_orm_object(id=1, item_id=10)

        await repo.set_moderation(1, orm_obj)

        ttl = await fake_redis.ttl("item-10")
        assert ttl > 0
        assert ttl <= 1800

    @pytest.mark.asyncio
    async def test_set_prediction_for_item_sets_ttl(self, repo, fake_redis):
        await repo.set_prediction_for_item(10, PredictResponse(is_violation=False, probability=0.5))

        ttl = await fake_redis.ttl("item-10")
        assert ttl > 0
        assert ttl <= 1800

@pytest.mark.integration
class TestNonexistentKeys:
    @pytest.mark.asyncio
    async def test_get_moderation_returns_none(self, repo):
        result = await repo.get_moderation(999)
        assert result is None

    @pytest.mark.asyncio
    async def test_get_moderation_for_item_returns_none(self, repo):
        result = await repo.get_moderation_for_item(999)
        assert result is None

@pytest.mark.integration
class TestDelete:
    @pytest.mark.asyncio
    async def test_delete_removes_key(self, repo, fake_redis):
        orm_obj = make_orm_object(id=1, item_id=10)
        await repo.set_moderation(1, orm_obj)

        assert await repo.get_moderation(1) is not None

        await repo.delete("task-1")

        assert await repo.get_moderation(1) is None
