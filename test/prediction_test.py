import routes.api as api
from http import HTTPStatus
import pytest

@pytest.mark.parametrize('images_qty', [0, 1, 2, 5, 7, 10, 15, 50, 100])
def test_ad_is_correct_on_verified_seller(app_client, predict_request_builder, images_qty):
    predict_request = predict_request_builder(is_verified_seller=True, images_qty=images_qty)
    prediction = app_client.post("/predict", json=predict_request)
    prediction_json = prediction.json()
    assert prediction.status_code == HTTPStatus.OK
    assert not prediction_json['is_violation']

@pytest.mark.parametrize('images_qty', [2, 5, 7, 10, 15, 50, 100])
def test_ad_is_correct_on_unverified_seller(app_client, predict_request_builder, images_qty):
    predict_request = predict_request_builder(is_verified_seller=False, images_qty=images_qty)
    prediction = app_client.post("/predict", json=predict_request)
    prediction_json = prediction.json()
    assert prediction.status_code == HTTPStatus.OK
    assert not prediction_json['is_violation']

@pytest.mark.parametrize('images_qty', [0, 1])
def test_ad_is_incorrect_on_unverified_seller_without_images(app_client, predict_request_builder, images_qty):
    predict_request = predict_request_builder(is_verified_seller=False, images_qty=images_qty)
    prediction = app_client.post("/predict", json=predict_request)
    prediction_json = prediction.json()
    assert prediction.status_code == HTTPStatus.OK
    assert prediction_json['is_violation']

@pytest.mark.parametrize('seller_id', [-1, -2, -5, -7, -10, -15, -50, -100])
def test_seller_id_should_not_be_negative(app_client, predict_request_builder, seller_id):
    predict_request = predict_request_builder(seller_id=seller_id)
    prediction = app_client.post("/predict", json=predict_request)
    prediction_json = prediction.json()
    assert prediction.status_code == HTTPStatus.UNPROCESSABLE_ENTITY
    assert any(err['loc'][-1] == 'seller_id' for err in prediction_json['detail'])

@pytest.mark.parametrize('item_id', [-1, -2, -5, -7, -10, -15, -50, -100])
def test_item_id_should_not_be_negative(app_client, predict_request_builder, item_id):
    predict_request = predict_request_builder(item_id=item_id)
    prediction = app_client.post("/predict", json=predict_request)
    prediction_json = prediction.json()
    assert prediction.status_code == HTTPStatus.UNPROCESSABLE_ENTITY
    assert any(err['loc'][-1] == 'item_id' for err in prediction_json['detail'])

@pytest.mark.parametrize('category', [-1, -2, -5, -7, -10, -15, -50, -100])
def test_category_should_not_be_negative(app_client, predict_request_builder, category):
    predict_request = predict_request_builder(category=category)
    prediction = app_client.post("/predict", json=predict_request)
    prediction_json = prediction.json()
    assert prediction.status_code == HTTPStatus.UNPROCESSABLE_ENTITY
    assert any(err['loc'][-1] == 'category' for err in prediction_json['detail'])

@pytest.mark.parametrize('images_qty', [-1, -2, -5, -7, -10, -15, -50, -100])
def test_images_qty_should_not_be_negative(app_client, predict_request_builder, images_qty):
    predict_request = predict_request_builder(images_qty=images_qty)
    prediction = app_client.post("/predict", json=predict_request)
    prediction_json = prediction.json()
    assert prediction.status_code == HTTPStatus.UNPROCESSABLE_ENTITY
    assert any(err['loc'][-1] == 'images_qty' for err in prediction_json['detail'])

def test_name_should_not_be_empty(app_client, predict_request_builder):
    predict_request = predict_request_builder(name='')
    prediction = app_client.post("/predict", json=predict_request)
    prediction_json = prediction.json()
    assert prediction.status_code == HTTPStatus.UNPROCESSABLE_ENTITY
    assert any(err['loc'][-1] == 'name' for err in prediction_json['detail'])

def test_description_should_not_be_empty(app_client, predict_request_builder):
    predict_request = predict_request_builder(description='')
    prediction = app_client.post("/predict", json=predict_request)
    prediction_json = prediction.json()
    assert prediction.status_code == HTTPStatus.UNPROCESSABLE_ENTITY
    assert any(err['loc'][-1] == 'description' for err in prediction_json['detail'])

@pytest.mark.parametrize('seller_id', [True, 1.0, 'a'])
def test_seller_should_be_int(app_client, predict_request_builder, seller_id):
    predict_request = predict_request_builder(seller_id=seller_id)
    prediction = app_client.post("/predict", json=predict_request)
    prediction_json = prediction.json()
    assert prediction.status_code == HTTPStatus.UNPROCESSABLE_ENTITY
    assert any(err['loc'][-1] == 'seller_id' for err in prediction_json['detail'])

@pytest.mark.parametrize('is_verified_seller', [10, 1.0, 'a'])
def test_verified_seller_should_be_bool(app_client, predict_request_builder, is_verified_seller):
    predict_request = predict_request_builder(is_verified_seller='a')
    prediction = app_client.post("/predict", json=predict_request)
    prediction_json = prediction.json()
    assert prediction.status_code == HTTPStatus.UNPROCESSABLE_ENTITY
    assert any(err['loc'][-1] == 'is_verified_seller' for err in prediction_json['detail'])

@pytest.mark.parametrize('item_id', [True, 1.0, 'a'])
def test_item_id_should_be_int(app_client, predict_request_builder, item_id):
    predict_request = predict_request_builder(item_id=item_id)
    prediction = app_client.post("/predict", json=predict_request)
    prediction_json = prediction.json()
    assert prediction.status_code == HTTPStatus.UNPROCESSABLE_ENTITY
    assert any(err['loc'][-1] == 'item_id' for err in prediction_json['detail'])

@pytest.mark.parametrize('name', [10, 1.0, True])
def test_name_should_be_string(app_client, predict_request_builder, name):
    predict_request = predict_request_builder(name=name)
    prediction = app_client.post("/predict", json=predict_request)
    prediction_json = prediction.json()
    assert prediction.status_code == HTTPStatus.UNPROCESSABLE_ENTITY
    assert any(err['loc'][-1] == 'name' for err in prediction_json['detail'])

@pytest.mark.parametrize('description', [10, 1.0, True])
def test_description_should_be_string(app_client, predict_request_builder, description):
    predict_request = predict_request_builder(description=description)
    prediction = app_client.post("/predict", json=predict_request)
    prediction_json = prediction.json()
    assert prediction.status_code == HTTPStatus.UNPROCESSABLE_ENTITY
    assert any(err['loc'][-1] == 'description' for err in prediction_json['detail'])

@pytest.mark.parametrize('category', ['a', 1.0, True])
def test_category_should_be_int(app_client, predict_request_builder, category):
    predict_request = predict_request_builder(category=category)
    prediction = app_client.post("/predict", json=predict_request)
    prediction_json = prediction.json()
    assert prediction.status_code == HTTPStatus.UNPROCESSABLE_ENTITY
    assert any(err['loc'][-1] == 'category' for err in prediction_json['detail'])

@pytest.mark.parametrize('images_qty', ['a', 1.0, True])
def test_images_qty_should_be_int(app_client, predict_request_builder, images_qty):
    predict_request = predict_request_builder(images_qty=images_qty)
    prediction = app_client.post("/predict", json=predict_request)
    prediction_json = prediction.json()
    assert prediction.status_code == HTTPStatus.UNPROCESSABLE_ENTITY
    assert any(err['loc'][-1] == 'images_qty' for err in prediction_json['detail'])

def test_server_error(app_client, predict_request_builder, monkeypatch):
    def predict_exception(request):
        raise Exception('Internal server error')
    monkeypatch.setattr(api.service, 'predict', predict_exception)
    prediction = app_client.post("/predict", json=predict_request_builder())
    assert prediction.status_code == HTTPStatus.INTERNAL_SERVER_ERROR
    assert "internal server error".lower() in prediction.text.lower()

def test_model_unavailable_returns_503(app_client, predict_request_builder, monkeypatch):
    monkeypatch.setattr(api.service, "model", None, raising=False)

    resp = app_client.post("/predict", json=predict_request_builder())

    assert resp.status_code == HTTPStatus.SERVICE_UNAVAILABLE
    body = resp.json()
    assert "одель не загружена." in body["detail"].lower()
