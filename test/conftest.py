from typing import Generator
import pytest
from fastapi.testclient import TestClient
from fastapi import FastAPI
from dto.request import PredictRequest
from repository.model.local_model_repository import LocalModelRepository
from service.model_service import ModelService
from service.moderation_service import ModerationService
from unittest.mock import patch, MagicMock, AsyncMock
from db.tables.item import Item
import os
import sys
import pytest_asyncio

os.environ["TESTING"] = "1"

mock_mlflow = MagicMock()
mock_mlflow.tracking = MagicMock()
mock_mlflow.tracking.MlflowClient = MagicMock
mock_mlflow.sklearn = MagicMock()
sys.modules['mlflow'] = mock_mlflow
sys.modules['mlflow.tracking'] = mock_mlflow.tracking
sys.modules['mlflow.sklearn'] = mock_mlflow.sklearn

@pytest.fixture(scope="session")
def mock_service():
    mock_repo = LocalModelRepository()
    item_repo = MagicMock()
    item = Item(
        id = 1,
        name="Wireless Earbuds X2",
        description="Compact TWS earbuds with active noise reduction and 20h total playback.",
        category=2,
        images_qty=5,
    )
    item_repo.get_item.return_value = AsyncMock(item)
    mock_service = ModelService(model_repository=mock_repo, item_repository=item_repo)
    mock_service.load_or_train_model()
    return mock_service

@pytest.fixture
def mock_moderation_service():
    redis_repo = AsyncMock()
    redis_repo.get_moderation_for_item = AsyncMock(return_value=None)
    redis_repo.get_moderation = AsyncMock(return_value=None)
    redis_repo.set_moderation = AsyncMock()
    redis_repo.set_prediction_for_item = AsyncMock()
    redis_repo.delete_for_item = AsyncMock()

    moder_repo = AsyncMock()
    moder_repo.get_moderation_for_item = AsyncMock(return_value=None)
    moder_repo.get_moderation = AsyncMock(return_value=None)
    moder_repo.delete_moderations_for_item = AsyncMock(return_value=[])

    item_repo = AsyncMock()
    item_repo.get_item = AsyncMock(return_value=None)
    item_repo.close_item = AsyncMock(return_value=None)

    return ModerationService(
        moder_repo=moder_repo,
        redis_repo=redis_repo,
        item_repo=item_repo,
    )

@pytest.fixture
def mock_account():
    account = MagicMock()
    account.id = 1
    account.login = "test"
    account.password = "test"
    account.is_blocked = False
    return account

@pytest.fixture
def app_client(mock_service, mock_moderation_service, mock_account) -> Generator[TestClient, None, None]:
    from routes import api
    api.app.dependency_overrides[api.get_model_service] = lambda: mock_service
    api.app.dependency_overrides[api.get_moderation_service] = lambda: mock_moderation_service
    api.app.dependency_overrides[api.get_current_account] = lambda: mock_account
    with TestClient(api.app, raise_server_exceptions=False) as client:
        client.service = mock_service
        client.moder_service = mock_moderation_service
        yield client

@pytest.fixture
def predict_request_builder():
    def build(**new_params) -> PredictRequest:
        predict = {
            "seller_id": 0,
            "is_verified_seller": True,
            "item_id": 0,
            "name": "Item",
            "description": "Description",
            "category": 0,
            "images_qty": 0,
        }
        predict.update(new_params)
        return predict
    return build
