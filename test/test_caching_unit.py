import pytest
from unittest.mock import AsyncMock, MagicMock
from service.moderation_service import ModerationService
from dto.response import PredictResponse


@pytest.fixture
def redis_repo():
    repo = AsyncMock()
    repo.get_moderation = AsyncMock(return_value=None)
    repo.get_moderation_for_item = AsyncMock(return_value=None)
    repo.set_moderation = AsyncMock()
    repo.set_prediction_for_item = AsyncMock()
    return repo

@pytest.fixture
def moder_repo():
    repo = AsyncMock()
    repo.get_moderation = AsyncMock(return_value=None)
    repo.get_moderation_for_item = AsyncMock(return_value=None)
    repo.create_moderation = AsyncMock()
    return repo

@pytest.fixture
def item_repo():
    return AsyncMock()

@pytest.fixture
def service(moder_repo, redis_repo, item_repo):
    return ModerationService(
        moder_repo=moder_repo,
        redis_repo=redis_repo,
        item_repo=item_repo,
    )

COMPLETED_CACHE_DICT = {
    "id": 1,
    "item_id": 10,
    "status": "completed",
    "is_violation": True,
    "probability": 0.85,
}

PENDING_CACHE_DICT = {
    "id": 2,
    "item_id": 10,
    "status": "pending",
    "is_violation": None,
    "probability": None,
}

FAILED_CACHE_DICT = {
    "id": 3,
    "item_id": 10,
    "status": "failed",
    "is_violation": None,
    "probability": None,
}

def make_orm_result(id=1, item_id=10, status="completed", is_violation=True, probability=0.85):
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

class TestGetPredictionForItem:
    @pytest.mark.asyncio
    async def test_returns_from_cache_when_completed(self, service, redis_repo, moder_repo):
        redis_repo.get_moderation_for_item.return_value = COMPLETED_CACHE_DICT

        result = await service.get_prediction_for_item(10)

        assert result == COMPLETED_CACHE_DICT
        redis_repo.get_moderation_for_item.assert_awaited_once_with(10)
        moder_repo.get_moderation_for_item.assert_not_awaited()

    @pytest.mark.asyncio
    async def test_skips_cache_when_pending_and_goes_to_db(self, service, redis_repo, moder_repo):
        redis_repo.get_moderation_for_item.return_value = PENDING_CACHE_DICT
        db_result = make_orm_result(status="completed")
        moder_repo.get_moderation_for_item.return_value = db_result

        result = await service.get_prediction_for_item(10)

        assert result is db_result
        moder_repo.get_moderation_for_item.assert_awaited_once_with(10)

    @pytest.mark.asyncio
    async def test_returns_from_db_when_cache_empty(self, service, redis_repo, moder_repo):
        redis_repo.get_moderation_for_item.return_value = None
        db_result = make_orm_result(status="completed")
        moder_repo.get_moderation_for_item.return_value = db_result

        result = await service.get_prediction_for_item(10)

        assert result is db_result
        redis_repo.get_moderation_for_item.assert_awaited_once_with(10)
        moder_repo.get_moderation_for_item.assert_awaited_once_with(10)

    @pytest.mark.asyncio
    async def test_returns_none_when_both_empty(self, service, redis_repo, moder_repo):
        redis_repo.get_moderation_for_item.return_value = None
        moder_repo.get_moderation_for_item.return_value = None

        result = await service.get_prediction_for_item(10)

        assert result is None

    @pytest.mark.asyncio
    async def test_skips_failed_db_result(self, service, redis_repo, moder_repo):
        redis_repo.get_moderation_for_item.return_value = None
        moder_repo.get_moderation_for_item.return_value = make_orm_result(status="failed")

        result = await service.get_prediction_for_item(10)

        assert result is None

class TestGetModerationResult:
    @pytest.mark.asyncio
    async def test_returns_from_cache_when_completed(self, service, redis_repo, moder_repo):
        redis_repo.get_moderation.return_value = COMPLETED_CACHE_DICT

        result = await service.get_moderation_result(1)

        assert result == COMPLETED_CACHE_DICT
        redis_repo.get_moderation.assert_awaited_once_with(1)
        moder_repo.get_moderation.assert_not_awaited()

    @pytest.mark.asyncio
    async def test_returns_from_cache_when_failed(self, service, redis_repo, moder_repo):
        redis_repo.get_moderation.return_value = FAILED_CACHE_DICT

        result = await service.get_moderation_result(3)

        assert result == FAILED_CACHE_DICT
        moder_repo.get_moderation.assert_not_awaited()

    @pytest.mark.asyncio
    async def test_skips_pending_cache_goes_to_db(self, service, redis_repo, moder_repo):
        redis_repo.get_moderation.return_value = PENDING_CACHE_DICT
        db_result = make_orm_result(id=2, status="completed")
        moder_repo.get_moderation.return_value = db_result

        result = await service.get_moderation_result(2)

        assert result is db_result
        moder_repo.get_moderation.assert_awaited_once_with(2)
        redis_repo.set_moderation.assert_awaited_once_with(2, db_result)

    @pytest.mark.asyncio
    async def test_goes_to_db_when_cache_empty_and_updates_cache(self, service, redis_repo, moder_repo):
        redis_repo.get_moderation.return_value = None
        db_result = make_orm_result(id=5, status="completed")
        moder_repo.get_moderation.return_value = db_result

        result = await service.get_moderation_result(5)

        assert result is db_result
        redis_repo.set_moderation.assert_awaited_once_with(5, db_result)

    @pytest.mark.asyncio
    async def test_returns_none_when_both_empty(self, service, redis_repo, moder_repo):
        redis_repo.get_moderation.return_value = None
        moder_repo.get_moderation.return_value = None

        result = await service.get_moderation_result(999)

        assert result is None
        redis_repo.set_moderation.assert_not_awaited()

class TestGetModerationTaskIdForItem:
    @pytest.mark.asyncio
    async def test_creates_task_caches_and_returns_id(self, service, redis_repo, moder_repo, item_repo):
        item_repo.get_item.return_value = MagicMock(id=10)
        task = make_orm_result(id=42, item_id=10, status="pending")
        moder_repo.create_moderation.return_value = task

        result = await service.get_moderation_task_id_for_item(10)

        assert result == 42
        item_repo.get_item.assert_awaited_once_with(10)
        moder_repo.create_moderation.assert_awaited_once_with(10)
        redis_repo.set_moderation.assert_awaited_once_with(42, task)

    @pytest.mark.asyncio
    async def test_returns_none_when_item_not_found(self, service, redis_repo, moder_repo, item_repo):
        item_repo.get_item.return_value = None

        result = await service.get_moderation_task_id_for_item(999)

        assert result is None
        moder_repo.create_moderation.assert_not_awaited()
        redis_repo.set_moderation.assert_not_awaited()

class TestSavePredictionToCache:
    @pytest.mark.asyncio
    async def test_orm_object_uses_set_moderation(self, service, redis_repo):
        orm_obj = make_orm_result(id=7, item_id=10)

        await service.save_prediction_to_cache(10, orm_obj)

        redis_repo.set_moderation.assert_awaited_once_with(7, orm_obj)
        redis_repo.set_prediction_for_item.assert_not_awaited()

    @pytest.mark.asyncio
    async def test_predict_response_uses_set_prediction_for_item(self, service, redis_repo):
        predict_resp = PredictResponse(is_violation=False, probability=0.12)

        await service.save_prediction_to_cache(10, predict_resp)

        redis_repo.set_prediction_for_item.assert_awaited_once_with(10, predict_resp)
        redis_repo.set_moderation.assert_not_awaited()

    @pytest.mark.asyncio
    async def test_none_result_does_nothing(self, service, redis_repo):
        await service.save_prediction_to_cache(10, None)

        redis_repo.set_moderation.assert_not_awaited()
        redis_repo.set_prediction_for_item.assert_not_awaited()
