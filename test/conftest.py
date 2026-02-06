from typing import Generator
import pytest
from fastapi.testclient import TestClient
from fastapi import FastAPI
from dto.request import PredictRequest
from repository.model.local_model_repository import LocalModelRepository
from service.model_service import ModelService
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
def app_client(mock_service) -> Generator[TestClient, None, None]:
    from routes import api
    api.app.dependency_overrides[api.get_service] = lambda: mock_service
    with TestClient(api.app, raise_server_exceptions=False) as client:
        client.service = mock_service
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
