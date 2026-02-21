from http import HTTPStatus
import pytest
from unittest.mock import AsyncMock, MagicMock
from db.tables.item import Item as DbItem

@pytest.mark.asyncio
async def test_close_item_success(app_client):
    item = MagicMock()
    item.id = 1
    item.is_closed = True
    app_client.moder_service.item_repo.get_item = AsyncMock(return_value=item)
    app_client.moder_service.item_repo.close_item = AsyncMock(return_value=item)
    app_client.moder_service.moder_repo.delete_moderations_for_item = AsyncMock(return_value=[10, 11])
    app_client.moder_service.redis_repo.delete_for_item = AsyncMock()
    response = app_client.post("/close/1")
    assert response.status_code == HTTPStatus.OK
    body = response.json()
    assert body["message"] == "Item closed"
    assert body["item_id"] == 1

@pytest.mark.asyncio
async def test_close_item_not_found(app_client):
    app_client.moder_service.item_repo.get_item = AsyncMock(return_value=None)
    response = app_client.post("/close/999999")
    assert response.status_code == HTTPStatus.NOT_FOUND
    assert "not found" in response.json()["detail"].lower()

@pytest.mark.asyncio
async def test_close_item_internal_error(app_client):
    app_client.moder_service.item_repo.get_item = AsyncMock(
        side_effect=Exception("DB connection lost")
    )
    response = app_client.post("/close/1")
    assert response.status_code == HTTPStatus.INTERNAL_SERVER_ERROR
