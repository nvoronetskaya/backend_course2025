from http import HTTPStatus
import pytest
from unittest.mock import AsyncMock
from db.tables.item import Item as DbItem

@pytest.mark.asyncio
async def test_positive_prediction_for_verified_seller_with_images(app_client):
    mock_item = DbItem(
        id=1,
        name="Premium Headphones",
        description="High-quality wireless headphones with noise cancellation and long battery life",
        category=5,
        images_qty=7
    )
    app_client.service.item_repository.get_item = AsyncMock(return_value=mock_item)
    response = app_client.post("/simple_predict/1")
    assert response.status_code == HTTPStatus.OK
    prediction = response.json()
    assert 'is_violation' in prediction
    assert 'probability' in prediction
    assert not prediction['is_violation']

@pytest.mark.asyncio
async def test_negative_prediction_for_item_without_images(app_client):
    mock_item = DbItem(
        id=2,
        name="Suspicious Item",
        description="Item with no images - likely a violation",
        category=3,
        images_qty=0
    )
    app_client.service.item_repository.get_item = AsyncMock(return_value=mock_item)
    response = app_client.post("/simple_predict/2")
    assert response.status_code == HTTPStatus.OK
    prediction = response.json()
    assert 'is_violation' in prediction
    assert 'probability' in prediction
    assert prediction['is_violation']


@pytest.mark.asyncio
async def test_negative_prediction_for_item_with_few_images(app_client):
    mock_item = DbItem(
        id=3,
        name="Low Quality Ad",
        description="Short desc",
        category=2,
        images_qty=1
    )
    app_client.service.item_repository.get_item = AsyncMock(return_value=mock_item)
    response = app_client.post("/simple_predict/3")
    assert response.status_code == HTTPStatus.OK
    prediction = response.json()
    assert 'is_violation' in prediction
    assert prediction['is_violation']

@pytest.mark.asyncio
async def test_item_not_found(app_client):
    app_client.service.item_repository.get_item = AsyncMock(return_value=None)
    response = app_client.post("/simple_predict/99999")
    assert response.status_code in [
        HTTPStatus.INTERNAL_SERVER_ERROR,
        HTTPStatus.NOT_FOUND,
        HTTPStatus.SERVICE_UNAVAILABLE
    ]

@pytest.mark.asyncio
async def test_create_multiple_items_and_predict(app_client):
    items_data = [
        DbItem(id=10, name="Laptop Pro 2024", 
               description="Professional laptop with high-end specs for developers and creators",
               category=1, images_qty=10),
        DbItem(id=11, name="Gaming Mouse",
               description="RGB gaming mouse with adjustable DPI",
               category=2, images_qty=5),
        DbItem(id=12, name="Budget Phone",
               description="Cheap phone",
               category=3, images_qty=1)
    ]
    predictions = []
    for mock_item in items_data:
        app_client.service.item_repository.get_item = AsyncMock(return_value=mock_item)
        
        response = app_client.post(f"/simple_predict/{mock_item.id}")
        assert response.status_code == HTTPStatus.OK
        
        prediction = response.json()
        predictions.append({
            "name": mock_item.name,
            "images_qty": mock_item.images_qty,
            "is_violation": prediction['is_violation']
        })
    
    assert len(predictions) == 3
    assert not predictions[0]['is_violation']
    assert predictions[2]['is_violation']

@pytest.mark.asyncio
async def test_item_retrieval_and_prediction(app_client):
    mock_item = DbItem(
        id=20,
        name="Test Product XYZ",
        description="This is a detailed description for testing",
        category=7,
        images_qty=6
    )
    app_client.service.item_repository.get_item = AsyncMock(return_value=mock_item)
    
    response = app_client.post(f"/simple_predict/{mock_item.id}")
    assert response.status_code == HTTPStatus.OK
    prediction = response.json()
    assert 'is_violation' in prediction
    assert not prediction['is_violation']

@pytest.mark.asyncio
@pytest.mark.parametrize('images_qty,expected_violation', [
    (0, True),
    (1, True),
    (2, False),
    (5, False),
    (10, False),
])
async def test_images_qty_threshold(app_client, images_qty, expected_violation):
    mock_item = DbItem(
        id=30,
        name=f"Product with {images_qty} images",
        description="Product description for threshold testing",
        category=4,
        images_qty=images_qty
    )
    app_client.service.item_repository.get_item = AsyncMock(return_value=mock_item)
    
    response = app_client.post("/simple_predict/30")
    
    assert response.status_code == HTTPStatus.OK
    prediction = response.json()
    assert prediction['is_violation'] == expected_violation

@pytest.mark.asyncio
async def test_invalid_item_id_negative(app_client):
    app_client.service.item_repository.get_item = AsyncMock(return_value=None)
    response = app_client.post("/simple_predict/-1")
    assert response.status_code in [
        HTTPStatus.OK,
        HTTPStatus.UNPROCESSABLE_ENTITY,
        HTTPStatus.INTERNAL_SERVER_ERROR,
        HTTPStatus.NOT_FOUND,
        HTTPStatus.SERVICE_UNAVAILABLE
    ]

@pytest.mark.asyncio
async def test_prediction_uses_correct_item_data(app_client):
    mock_item = DbItem(
        id=40,
        name="Test Item",
        description="A" * 500,
        category=8,
        images_qty=3
    )
    app_client.service.item_repository.get_item = AsyncMock(return_value=mock_item)
    response = app_client.post("/simple_predict/40")
    assert response.status_code == HTTPStatus.OK
    prediction = response.json()
    assert 'is_violation' in prediction
    assert 'probability' in prediction
    app_client.service.item_repository.get_item.assert_called_once_with(40)

@pytest.mark.asyncio  
async def test_repository_exception_handling(app_client):
    app_client.service.item_repository.get_item = AsyncMock(
        side_effect=Exception("Database connection error")
    )
    response = app_client.post("/simple_predict/50")
    assert response.status_code == HTTPStatus.INTERNAL_SERVER_ERROR
