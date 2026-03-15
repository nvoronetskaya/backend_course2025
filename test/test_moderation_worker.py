import json
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from app.exceptions import ModelIsNotAvailable, AdvertisementNotFoundError
from app.workers.moderation_worker import (
    is_retryable_error,
    calculate_retry_delay,
    handle_moderation,
    process_with_retry,
    mark_moderation_failed,
    send_to_dlq,
    RetryableError,
    PermanentError,
    MAX_RETRIES,
    RETRY_DELAY,
)

def make_item(item_id=1):
    item = MagicMock()
    item.id = item_id
    item.name = "Test"
    item.description = "Description"
    item.category = 1
    item.images_qty = 3
    return item


def make_task(task_id=10):
    task = MagicMock()
    task.id = task_id
    task.item_id = 1
    task.status = "pending"
    return task


def make_session_maker(mock_db):
    cm = AsyncMock()
    cm.__aenter__ = AsyncMock(return_value=mock_db)
    cm.__aexit__ = AsyncMock(return_value=False)
    factory = MagicMock(return_value=cm)
    return factory

def test_is_retryable_error_with_retryable_types():
    for exc in (
        RetryableError(),
        ModelIsNotAvailable(),
        RuntimeError(),
        ConnectionError(),
        TimeoutError(),
    ):
        assert is_retryable_error(exc) is True

def test_is_retryable_error_with_permanent_types():
    for exc in (
        PermanentError(),
        ValueError(),
        KeyError(),
        AdvertisementNotFoundError(),
    ):
        assert is_retryable_error(exc) is False

def test_calculate_retry_delay():
    assert calculate_retry_delay(0) == RETRY_DELAY * 1
    assert calculate_retry_delay(1) == RETRY_DELAY * 2
    assert calculate_retry_delay(2) == RETRY_DELAY * 4
    assert calculate_retry_delay(3) == RETRY_DELAY * 8

@patch("app.workers.moderation_worker.ModelService")
@patch("app.workers.moderation_worker.ModerationResultRepository")
@patch("app.workers.moderation_worker.ItemRepository")
async def test_handle_moderation_success(MockItemRepo, MockModerRepo, MockModelService):
    mock_item_repo = AsyncMock()
    mock_item_repo.get_item = AsyncMock(return_value=make_item())
    MockItemRepo.return_value = mock_item_repo

    task = make_task()
    mock_moder_repo = AsyncMock()
    mock_moder_repo.get_latest_pending = AsyncMock(return_value=task)
    mock_moder_repo.update_task = AsyncMock()
    MockModerRepo.return_value = mock_moder_repo

    mock_result = MagicMock()
    mock_result.is_violation = True
    mock_result.probability = 0.95
    mock_service = MagicMock()
    mock_service.predict.return_value = mock_result
    MockModelService.return_value = mock_service

    await handle_moderation(db=AsyncMock(), item_id=1, model=MagicMock(), model_repo=MagicMock())

    mock_moder_repo.update_task.assert_awaited_once()
    call_kwargs = mock_moder_repo.update_task.call_args
    assert call_kwargs.kwargs["status"] == "completed"
    assert call_kwargs.kwargs["is_violation"] is True

@patch("app.workers.moderation_worker.ItemRepository")
async def test_handle_moderation_item_not_found(MockItemRepo):
    mock_item_repo = AsyncMock()
    mock_item_repo.get_item = AsyncMock(return_value=None)
    MockItemRepo.return_value = mock_item_repo

    with pytest.raises(AdvertisementNotFoundError):
        await handle_moderation(db=AsyncMock(), item_id=999, model=MagicMock(), model_repo=MagicMock())

@patch("app.workers.moderation_worker.ModerationResultRepository")
@patch("app.workers.moderation_worker.ItemRepository")
async def test_handle_moderation_no_pending_task(MockItemRepo, MockModerRepo):
    mock_item_repo = AsyncMock()
    mock_item_repo.get_item = AsyncMock(return_value=make_item())
    MockItemRepo.return_value = mock_item_repo

    mock_moder_repo = AsyncMock()
    mock_moder_repo.get_latest_pending = AsyncMock(return_value=None)
    mock_moder_repo.update_task = AsyncMock()
    MockModerRepo.return_value = mock_moder_repo

    await handle_moderation(db=AsyncMock(), item_id=1, model=MagicMock(), model_repo=MagicMock())

    mock_moder_repo.update_task.assert_not_awaited()

@patch("app.workers.moderation_worker.ModerationResultRepository")
@patch("app.workers.moderation_worker.ItemRepository")
async def test_handle_moderation_model_not_available(MockItemRepo, MockModerRepo):
    mock_item_repo = AsyncMock()
    mock_item_repo.get_item = AsyncMock(return_value=make_item())
    MockItemRepo.return_value = mock_item_repo

    mock_moder_repo = AsyncMock()
    mock_moder_repo.get_latest_pending = AsyncMock(return_value=make_task())
    MockModerRepo.return_value = mock_moder_repo

    with pytest.raises(ModelIsNotAvailable):
        await handle_moderation(db=AsyncMock(), item_id=1, model=None, model_repo=MagicMock())

async def test_send_to_dlq_success():
    producer = AsyncMock()
    producer.send_and_wait = AsyncMock()

    await send_to_dlq(
        dlq_producer=producer,
        item_id=1,
        error=RuntimeError(),
        event={"item_id": 1},
        retry_count=2,
        is_permanent=False,
    )

    producer.send_and_wait.assert_awaited_once()
    sent_data = producer.send_and_wait.call_args[0][1]
    payload = json.loads(sent_data.decode("utf-8"))
    assert payload["item_id"] == 1
    assert payload["retry_count"] == 2
    assert payload["is_permanent_error"] is False
    assert payload["error_type"] == "RuntimeError"

async def test_send_to_dlq_failure_does_not_raise():
    producer = AsyncMock()
    producer.send_and_wait = AsyncMock(side_effect=Exception())

    await send_to_dlq(
        dlq_producer=producer,
        item_id=1,
        error=RuntimeError(),
        event={"item_id": 1},
        retry_count=0,
        is_permanent=False,
    )

@patch("app.workers.moderation_worker.ModerationResultRepository")
async def test_mark_moderation_failed_success(MockModerRepo):
    task = make_task()
    mock_repo = AsyncMock()
    mock_repo.get_latest_pending = AsyncMock(return_value=task)
    mock_repo.update_task = AsyncMock()
    MockModerRepo.return_value = mock_repo

    await mark_moderation_failed(db=AsyncMock(), item_id=1, error_message="fail", retry_count=2)

    mock_repo.update_task.assert_awaited_once()
    call_kwargs = mock_repo.update_task.call_args
    assert call_kwargs.kwargs["status"] == "failed"
    assert call_kwargs.kwargs["error_message"] == "fail"
    assert call_kwargs.kwargs["retry_count"] == 2

@patch("app.workers.moderation_worker.ModerationResultRepository")
async def test_mark_moderation_failed_no_task(MockModerRepo):
    mock_repo = AsyncMock()
    mock_repo.get_latest_pending = AsyncMock(return_value=None)
    mock_repo.update_task = AsyncMock()
    MockModerRepo.return_value = mock_repo

    await mark_moderation_failed(db=AsyncMock(), item_id=1, error_message="fail")

    mock_repo.update_task.assert_not_awaited()

async def test_mark_moderation_failed_item_id_none():
    await mark_moderation_failed(db=AsyncMock(), item_id=None, error_message="fail")

@patch("app.workers.moderation_worker.handle_moderation", new_callable=AsyncMock)
@patch("app.workers.moderation_worker.session_maker")
async def test_process_with_retry_success_first_try(mock_sm, mock_handle):
    mock_db = AsyncMock()
    mock_sm.return_value = make_session_maker(mock_db).return_value

    mock_handle.return_value = None

    dlq = AsyncMock()
    dlq.send_and_wait = AsyncMock()

    await process_with_retry(
        item_id=1, model=MagicMock(), model_repo=MagicMock(),
        dlq_producer=dlq, original_event={"item_id": 1},
    )

    mock_handle.assert_awaited_once()
    dlq.send_and_wait.assert_not_awaited()

@patch("app.workers.moderation_worker.send_to_dlq", new_callable=AsyncMock)
@patch("app.workers.moderation_worker.mark_moderation_failed", new_callable=AsyncMock)
@patch("asyncio.sleep", new_callable=AsyncMock)
@patch("app.workers.moderation_worker.handle_moderation", new_callable=AsyncMock)
@patch("app.workers.moderation_worker.session_maker")
async def test_process_with_retry_retryable_then_success(mock_sm, mock_handle, mock_sleep, mock_mark, mock_dlq):
    mock_db = AsyncMock()
    mock_sm.return_value = make_session_maker(mock_db).return_value

    mock_handle.side_effect = [RetryableError(), None]

    await process_with_retry(
        item_id=1, model=MagicMock(), model_repo=MagicMock(),
        dlq_producer=AsyncMock(), original_event={"item_id": 1},
    )

    assert mock_handle.await_count == 2
    mock_sleep.assert_awaited_once()
    mock_dlq.assert_not_awaited()

@patch("app.workers.moderation_worker.handle_moderation", new_callable=AsyncMock)
@patch("app.workers.moderation_worker.session_maker")
async def test_process_with_retry_permanent_error(mock_sm, mock_handle):
    mock_db = AsyncMock()
    mock_sm.return_value = make_session_maker(mock_db).return_value

    mock_handle.side_effect = AdvertisementNotFoundError()

    with pytest.raises(PermanentError):
        await process_with_retry(
            item_id=999, model=MagicMock(), model_repo=MagicMock(),
            dlq_producer=AsyncMock(), original_event={"item_id": 999},
        )

@patch("app.workers.moderation_worker.send_to_dlq", new_callable=AsyncMock)
@patch("app.workers.moderation_worker.mark_moderation_failed", new_callable=AsyncMock)
@patch("asyncio.sleep", new_callable=AsyncMock)
@patch("app.workers.moderation_worker.handle_moderation", new_callable=AsyncMock)
@patch("app.workers.moderation_worker.session_maker")
async def test_process_with_retry_max_retries_exceeded(mock_sm, mock_handle, mock_sleep, mock_mark, mock_dlq):
    mock_db = AsyncMock()
    mock_sm.return_value = make_session_maker(mock_db).return_value

    mock_handle.side_effect = RetryableError()

    await process_with_retry(
        item_id=1, model=MagicMock(), model_repo=MagicMock(),
        dlq_producer=AsyncMock(), original_event={"item_id": 1},
    )

    assert mock_handle.await_count == MAX_RETRIES + 1
    mock_dlq.assert_awaited_once()
    mock_mark.assert_awaited_once()
