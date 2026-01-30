from typing import Generator
import pytest
from fastapi.testclient import TestClient
from api import app
from model.request import PredictRequest

@pytest.fixture
def app_client() -> Generator[TestClient, None, None]:
    return TestClient(app, raise_server_exceptions=False)

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
