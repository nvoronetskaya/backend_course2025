from http import HTTPStatus
import pytest

@pytest.mark.parametrize('images_qty', [0, 1, 2, 5, 7, 10, 15, 50, 100])
def test_ad_is_correct_on_verified_seller(app_client, predict_request, images_qty):
    predict_request.is_verified_seller = True
    predict_request.images_qty = images_qty
    prediction = app_client.post("/predict", json=predict_request.model_dump())
    prediction_json = prediction.json()
    assert prediction.status_code == HTTPStatus.OK
    assert (not prediction_json['has_errors'])

@pytest.mark.parametrize('images_qty', [1, 2, 5, 7, 10, 15, 50, 100])
def test_ad_is_correct_on_unverified_seller(app_client, predict_request, images_qty):
    predict_request.is_verified_seller = False
    predict_request.images_qty = images_qty
    prediction = app_client.post("/predict", json=predict_request.model_dump())
    prediction_json = prediction.json()
    assert prediction.status_code == HTTPStatus.OK
    assert (not prediction_json['has_errors'])

def test_ad_is_incorrect_on_unverified_seller_without_images(app_client, predict_request):
    predict_request.is_verified_seller = False
    predict_request.images_qty = 0
    prediction = app_client.post("/predict", json=predict_request.model_dump())
    prediction_json = prediction.json()
    assert prediction.status_code == HTTPStatus.OK
    assert prediction_json['has_errors']

@pytest.mark.parametrize('seller_id', [-1, -2, -5, -7, -10, -15, -50, -100])
def test_seller_id_should_not_be_negative(app_client, predict_request, seller_id):
    predict_request.seller_id = seller_id
    prediction = app_client.post("/predict", json=predict_request.model_dump())
    prediction_json = prediction.json()
    assert prediction.status_code == HTTPStatus.UNPROCESSABLE_ENTITY
    assert any(err['loc'][-1] == 'seller_id' for err in prediction_json['detail'])

@pytest.mark.parametrize('item_id', [-1, -2, -5, -7, -10, -15, -50, -100])
def test_item_id_should_not_be_negative(app_client, predict_request, item_id):
    predict_request.item_id = item_id
    prediction = app_client.post("/predict", json=predict_request.model_dump())
    prediction_json = prediction.json()
    assert prediction.status_code == HTTPStatus.UNPROCESSABLE_ENTITY
    assert any(err['loc'][-1] == 'item_id' for err in prediction_json['detail'])

@pytest.mark.parametrize('category', [-1, -2, -5, -7, -10, -15, -50, -100])
def test_category_should_not_be_negative(app_client, predict_request, category):
    predict_request.category = category
    prediction = app_client.post("/predict", json=predict_request.model_dump())
    prediction_json = prediction.json()
    assert prediction.status_code == HTTPStatus.UNPROCESSABLE_ENTITY
    assert any(err['loc'][-1] == 'category' for err in prediction_json['detail'])

@pytest.mark.parametrize('images_qty', [-1, -2, -5, -7, -10, -15, -50, -100])
def test_images_qty_should_not_be_negative(app_client, predict_request, images_qty):
    predict_request.images_qty = images_qty
    prediction = app_client.post("/predict", json=predict_request.model_dump())
    prediction_json = prediction.json()
    assert prediction.status_code == HTTPStatus.UNPROCESSABLE_ENTITY
    assert any(err['loc'][-1] == 'images_qty' for err in prediction_json['detail'])

def test_name_should_not_be_empty(app_client, predict_request):
    predict_request.name = ''
    prediction = app_client.post("/predict", json=predict_request.model_dump())
    prediction_json = prediction.json()
    assert prediction.status_code == HTTPStatus.UNPROCESSABLE_ENTITY
    assert any(err['loc'][-1] == 'name' for err in prediction_json['detail'])

def test_description_should_not_be_empty(app_client, predict_request):
    predict_request.description = ''
    prediction = app_client.post("/predict", json=predict_request.model_dump())
    prediction_json = prediction.json()
    assert prediction.status_code == HTTPStatus.UNPROCESSABLE_ENTITY
    assert any(err['loc'][-1] == 'description' for err in prediction_json['detail'])
