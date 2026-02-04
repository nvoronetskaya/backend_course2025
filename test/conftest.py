from typing import Generator
import pytest
from fastapi.testclient import TestClient
from fastapi import FastAPI
from dto.request import PredictRequest
from repository.model.local_model_repository import LocalModelRepository
from service.model_service import ModelService
from contextlib import asynccontextmanager
import routes.api as api
from routes.api import app
from unittest.mock import patch

@asynccontextmanager
async def test_lifespan(app: FastAPI):
    mock_repo = LocalModelRepository()
    mock_service = ModelService(mock_repo)
    mock_service.load_or_train_model()
    app.state.service = mock_service
    yield

@pytest.fixture(scope="session")
def test_app() -> FastAPI:
    app = FastAPI(lifespan=test_lifespan)
    from routes.api import get_prediction

    @app.post("/predict")
    async def predict(request: PredictRequest):
        return await get_prediction(request)
    
    return app

@pytest.fixture
def app_client(test_app) -> Generator[TestClient, None, None]:
    mock_repo = LocalModelRepository()
    mock_service = ModelService(mock_repo)
    mock_service.load_or_train_model()
    app.state.service = mock_service
    api.service = mock_service
    api.repository = mock_repo
    with patch.object(api, 'mlflow'):
        with TestClient(app) as client:
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
