from http import HTTPStatus
import pytest
from unittest.mock import AsyncMock, MagicMock
from fastapi.testclient import TestClient
from app.exceptions import InvalidCredentialsError, AccountBlockedError


@pytest.fixture
def login_client():
    from routes import api

    mock_auth_service = AsyncMock()
    mock_auth_service.authenticate = AsyncMock(return_value="fake.jwt.token")

    api.app.dependency_overrides[api.get_auth_service] = lambda: mock_auth_service
    with TestClient(api.app, raise_server_exceptions=False) as client:
        client.auth_service = mock_auth_service
        yield client
    api.app.dependency_overrides.pop(api.get_auth_service, None)


class TestLoginEndpoint:
    def test_login_success(self, login_client):
        response = login_client.post("/login", json={"login": "user", "password": "pass"})
        assert response.status_code == HTTPStatus.OK
        assert response.json()["message"] == "Login successful"
        cookies = response.cookies
        assert "access_token" in cookies
        assert cookies["access_token"] == "fake.jwt.token"

    def test_login_invalid_credentials(self, login_client):
        login_client.auth_service.authenticate = AsyncMock(
            side_effect=InvalidCredentialsError("Invalid login or password")
        )
        response = login_client.post("/login", json={"login": "user", "password": "wrong"})
        assert response.status_code == HTTPStatus.UNAUTHORIZED
        assert "Invalid login or password" in response.json()["detail"]

    def test_login_blocked_account(self, login_client):
        login_client.auth_service.authenticate = AsyncMock(
            side_effect=AccountBlockedError("Account is blocked")
        )
        response = login_client.post("/login", json={"login": "user", "password": "pass"})
        assert response.status_code == HTTPStatus.FORBIDDEN
        assert "blocked" in response.json()["detail"].lower()

    def test_login_missing_fields(self, login_client):
        response = login_client.post("/login", json={})
        assert response.status_code == HTTPStatus.UNPROCESSABLE_ENTITY
