import pytest
from unittest.mock import AsyncMock, MagicMock
from service.moderation_service import ModerationService
from repository.moderation_result.moderation_result_repository import ModerationResultRepository
from dto.response import PredictResponse

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

@pytest.fixture
def redis_repo():
    repo = AsyncMock()
    repo.get_moderation = AsyncMock(return_value=None)
    repo.get_moderation_for_item = AsyncMock(return_value=None)
    repo.set_moderation = AsyncMock()
    repo.set_prediction_for_item = AsyncMock()
    repo.delete_for_item = AsyncMock()
    return repo

@pytest.fixture
def db_session():
    return AsyncMock()

@pytest.fixture
def repo(db_session, redis_repo):
    r = ModerationResultRepository(db_session, redis_repo)
    r.get_moderation_for_item = AsyncMock(return_value=None)
    r.get_moderation = AsyncMock(return_value=None)
    r.create_moderation = AsyncMock()
    r.delete_moderations_for_item = AsyncMock(return_value=[])
    return r

@pytest.fixture
def moder_repo():
    repo = AsyncMock()
    repo.get_completed_for_item = AsyncMock(return_value=None)
    repo.get_result = AsyncMock(return_value=None)
    repo.create_and_cache = AsyncMock()
    repo.save_to_cache = AsyncMock()
    repo.delete_for_item = AsyncMock(return_value=[])
    return repo

@pytest.fixture
def item_repo():
    return AsyncMock()

@pytest.fixture
def service(moder_repo, item_repo):
    return ModerationService(
        moder_repo=moder_repo,
        item_repo=item_repo,
    )

class TestRepoGetCompletedForItem:
    @pytest.mark.asyncio
    async def test_returns_from_cache_when_completed(self, repo, redis_repo):
        redis_repo.get_moderation_for_item.return_value = COMPLETED_CACHE_DICT

        result = await repo.get_completed_for_item(10)

        assert result == COMPLETED_CACHE_DICT
        redis_repo.get_moderation_for_item.assert_awaited_once_with(10)
        repo.get_moderation_for_item.assert_not_awaited()

    @pytest.mark.asyncio
    async def test_skips_cache_when_pending_and_goes_to_db(self, repo, redis_repo):
        redis_repo.get_moderation_for_item.return_value = PENDING_CACHE_DICT
        db_result = make_orm_result(status="completed")
        repo.get_moderation_for_item.return_value = db_result

        result = await repo.get_completed_for_item(10)

        assert result is db_result
        repo.get_moderation_for_item.assert_awaited_once_with(10)

    @pytest.mark.asyncio
    async def test_returns_from_db_when_cache_empty(self, repo, redis_repo):
        redis_repo.get_moderation_for_item.return_value = None
        db_result = make_orm_result(status="completed")
        repo.get_moderation_for_item.return_value = db_result

        result = await repo.get_completed_for_item(10)

        assert result is db_result
        redis_repo.get_moderation_for_item.assert_awaited_once_with(10)
        repo.get_moderation_for_item.assert_awaited_once_with(10)

    @pytest.mark.asyncio
    async def test_returns_none_when_both_empty(self, repo, redis_repo):
        redis_repo.get_moderation_for_item.return_value = None
        repo.get_moderation_for_item.return_value = None

        result = await repo.get_completed_for_item(10)

        assert result is None

    @pytest.mark.asyncio
    async def test_skips_failed_db_result(self, repo, redis_repo):
        redis_repo.get_moderation_for_item.return_value = None
        repo.get_moderation_for_item.return_value = make_orm_result(status="failed")

        result = await repo.get_completed_for_item(10)

        assert result is None

class TestRepoGetResult:
    @pytest.mark.asyncio
    async def test_returns_from_cache_when_completed(self, repo, redis_repo):
        redis_repo.get_moderation.return_value = COMPLETED_CACHE_DICT

        result = await repo.get_result(1)

        assert result == COMPLETED_CACHE_DICT
        redis_repo.get_moderation.assert_awaited_once_with(1)
        repo.get_moderation.assert_not_awaited()

    @pytest.mark.asyncio
    async def test_returns_from_cache_when_failed(self, repo, redis_repo):
        redis_repo.get_moderation.return_value = FAILED_CACHE_DICT

        result = await repo.get_result(3)

        assert result == FAILED_CACHE_DICT
        repo.get_moderation.assert_not_awaited()

    @pytest.mark.asyncio
    async def test_skips_pending_cache_goes_to_db(self, repo, redis_repo):
        redis_repo.get_moderation.return_value = PENDING_CACHE_DICT
        db_result = make_orm_result(id=2, status="completed")
        repo.get_moderation.return_value = db_result

        result = await repo.get_result(2)

        assert result is db_result
        repo.get_moderation.assert_awaited_once_with(2)
        redis_repo.set_moderation.assert_awaited_once_with(2, db_result)

    @pytest.mark.asyncio
    async def test_goes_to_db_when_cache_empty_and_updates_cache(self, repo, redis_repo):
        redis_repo.get_moderation.return_value = None
        db_result = make_orm_result(id=5, status="completed")
        repo.get_moderation.return_value = db_result

        result = await repo.get_result(5)

        assert result is db_result
        redis_repo.set_moderation.assert_awaited_once_with(5, db_result)

    @pytest.mark.asyncio
    async def test_returns_none_when_both_empty(self, repo, redis_repo):
        redis_repo.get_moderation.return_value = None
        repo.get_moderation.return_value = None

        result = await repo.get_result(999)

        assert result is None
        redis_repo.set_moderation.assert_not_awaited()

class TestRepoCreateAndCache:
    @pytest.mark.asyncio
    async def test_creates_and_caches(self, repo, redis_repo):
        task = make_orm_result(id=42, item_id=10, status="pending")
        repo.create_moderation.return_value = task

        result = await repo.create_and_cache(10)

        assert result is task
        repo.create_moderation.assert_awaited_once_with(10)
        redis_repo.set_moderation.assert_awaited_once_with(42, task)

class TestRepoSaveToCache:
    @pytest.mark.asyncio
    async def test_orm_object_uses_set_moderation(self, repo, redis_repo):
        orm_obj = make_orm_result(id=7, item_id=10)

        await repo.save_to_cache(10, orm_obj)

        redis_repo.set_moderation.assert_awaited_once_with(7, orm_obj)
        redis_repo.set_prediction_for_item.assert_not_awaited()

    @pytest.mark.asyncio
    async def test_predict_response_uses_set_prediction_for_item(self, repo, redis_repo):
        predict_resp = PredictResponse(is_violation=False, probability=0.1)

        await repo.save_to_cache(10, predict_resp)

        redis_repo.set_prediction_for_item.assert_awaited_once_with(10, predict_resp)
        redis_repo.set_moderation.assert_not_awaited()

    @pytest.mark.asyncio
    async def test_none_result_does_nothing(self, repo, redis_repo):
        await repo.save_to_cache(10, None)

        redis_repo.set_moderation.assert_not_awaited()
        redis_repo.set_prediction_for_item.assert_not_awaited()

class TestRepoDeleteForItem:
    @pytest.mark.asyncio
    async def test_deletes_from_db_and_cache(self, repo, redis_repo):
        repo.delete_moderations_for_item.return_value = [1, 2, 3]

        result = await repo.delete_for_item(10)

        assert result == [1, 2, 3]
        repo.delete_moderations_for_item.assert_awaited_once_with(10)
        redis_repo.delete_for_item.assert_awaited_once_with(10, [1, 2, 3])

class TestServiceGetPredictionForItem:
    @pytest.mark.asyncio
    async def test_delegates_to_repo(self, service, moder_repo):
        moder_repo.get_completed_for_item.return_value = COMPLETED_CACHE_DICT

        result = await service.get_prediction_for_item(10)

        assert result == COMPLETED_CACHE_DICT
        moder_repo.get_completed_for_item.assert_awaited_once_with(10)


class TestServiceGetModerationResult:
    @pytest.mark.asyncio
    async def test_delegates_to_repo(self, service, moder_repo):
        moder_repo.get_result.return_value = COMPLETED_CACHE_DICT

        result = await service.get_moderation_result(1)

        assert result == COMPLETED_CACHE_DICT
        moder_repo.get_result.assert_awaited_once_with(1)

class TestServiceGetModerationTaskIdForItem:
    @pytest.mark.asyncio
    async def test_creates_task_and_returns_id(self, service, moder_repo, item_repo):
        item_repo.get_item.return_value = MagicMock(id=10)
        task = make_orm_result(id=5, item_id=10, status="pending")
        moder_repo.create_and_cache.return_value = task

        result = await service.get_moderation_task_id_for_item(10)

        assert result == 5
        item_repo.get_item.assert_awaited_once_with(10)
        moder_repo.create_and_cache.assert_awaited_once_with(10)

    @pytest.mark.asyncio
    async def test_returns_none_when_item_not_found(self, service, moder_repo, item_repo):
        item_repo.get_item.return_value = None

        result = await service.get_moderation_task_id_for_item(1000)

        assert result is None
        moder_repo.create_and_cache.assert_not_awaited()


class TestServiceSavePredictionToCache:
    @pytest.mark.asyncio
    async def test_delegates_to_repo(self, service, moder_repo):
        predict_resp = PredictResponse(is_violation=False, probability=0.1)

        await service.save_prediction_to_cache(10, predict_resp)

        moder_repo.save_to_cache.assert_awaited_once_with(10, predict_resp)


class TestServiceGetOrPredictForItem:
    @pytest.mark.asyncio
    async def test_returns_cached_result_without_calling_model(self, service, moder_repo):
        moder_repo.get_completed_for_item.return_value = COMPLETED_CACHE_DICT
        model_service = AsyncMock()

        result = await service.get_or_predict_for_item(10, model_service)

        assert result == COMPLETED_CACHE_DICT
        model_service.get_prediction_for_item.assert_not_awaited()

    @pytest.mark.asyncio
    async def test_calls_model_on_cache_miss_and_saves(self, service, moder_repo):
        moder_repo.get_completed_for_item.return_value = None
        model_service = AsyncMock()
        predict_resp = PredictResponse(is_violation=False, probability=0.4)
        model_service.get_prediction_for_item.return_value = predict_resp

        result = await service.get_or_predict_for_item(10, model_service)

        assert result is predict_resp
        model_service.get_prediction_for_item.assert_awaited_once_with(10)
        moder_repo.save_to_cache.assert_awaited_once_with(10, predict_resp)

    @pytest.mark.asyncio
    async def test_returns_none_when_both_miss(self, service, moder_repo):
        moder_repo.get_completed_for_item.return_value = None
        model_service = AsyncMock()
        model_service.get_prediction_for_item.return_value = None

        result = await service.get_or_predict_for_item(10, model_service)

        assert result is None
        moder_repo.save_to_cache.assert_not_awaited()

class TestServiceCloseItem:
    @pytest.mark.asyncio
    async def test_closes_item(self, service, moder_repo, item_repo):
        item_repo.get_item.return_value = MagicMock(id=10)
        item_repo.close_item.return_value = MagicMock()
        moder_repo.delete_for_item.return_value = [1, 2]

        result = await service.close_item(10)

        assert result is not None
        moder_repo.delete_for_item.assert_awaited_once_with(10)
        item_repo.close_item.assert_awaited_once_with(10)

    @pytest.mark.asyncio
    async def test_returns_none_when_item_not_found(self, service, moder_repo, item_repo):
        item_repo.get_item.return_value = None

        result = await service.close_item(1000)

        assert result is None
        moder_repo.delete_for_item.assert_not_awaited()
