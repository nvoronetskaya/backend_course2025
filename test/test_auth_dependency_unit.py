import pytest
from unittest.mock import AsyncMock, MagicMock
from fastapi import HTTPException
from service.auth_service import AuthService

SECRET = "test-secret-key"


def _make_account(account_id=1, login="user", is_blocked=False):
    account = MagicMock()
    account.id = account_id
    account.login = login
    account.password = "pass"
    account.is_blocked = is_blocked
    return account


def _make_request(cookie_value=None):
    request = MagicMock()
    if cookie_value is not None:
        request.cookies = {"access_token": cookie_value}
    else:
        request.cookies = {}
    return request


class TestGetCurrentAccount:
    async def test_valid_token_returns_account(self):
        from routes.api import get_current_account, JWT_SECRET

        auth = AuthService(account_repo=None, secret_key=JWT_SECRET)
        token = auth.create_token(account_id=42, login="user")

        account = _make_account(account_id=42, login="user")
        mock_db = AsyncMock()
        mock_repo_result = MagicMock()
        mock_repo_result.scalars.return_value.first.return_value = account

        mock_db.execute = AsyncMock(return_value=mock_repo_result)

        request = _make_request(cookie_value=token)
        result = await get_current_account(request=request, db=mock_db)
        assert result.id == 42
        assert result.login == "user"

    async def test_missing_cookie_raises_401(self):
        from routes.api import get_current_account

        request = _make_request(cookie_value=None)
        mock_db = AsyncMock()

        with pytest.raises(HTTPException) as exc_info:
            await get_current_account(request=request, db=mock_db)
        assert exc_info.value.status_code == 401

    async def test_invalid_token_raises_401(self):
        from routes.api import get_current_account

        request = _make_request(cookie_value="garbage.token.value")
        mock_db = AsyncMock()

        with pytest.raises(HTTPException) as exc_info:
            await get_current_account(request=request, db=mock_db)
        assert exc_info.value.status_code == 401

    async def test_account_not_found_raises_403(self):
        from routes.api import get_current_account, JWT_SECRET

        auth = AuthService(account_repo=None, secret_key=JWT_SECRET)
        token = auth.create_token(account_id=999, login="user")

        mock_db = AsyncMock()
        mock_repo_result = MagicMock()
        mock_repo_result.scalars.return_value.first.return_value = None
        mock_db.execute = AsyncMock(return_value=mock_repo_result)

        request = _make_request(cookie_value=token)
        with pytest.raises(HTTPException) as exc_info:
            await get_current_account(request=request, db=mock_db)
        assert exc_info.value.status_code == 403
        assert "not found" in exc_info.value.detail.lower()

    async def test_blocked_account_raises_403(self):
        from routes.api import get_current_account, JWT_SECRET

        auth = AuthService(account_repo=None, secret_key=JWT_SECRET)
        token = auth.create_token(account_id=10, login="blocked_user")

        account = _make_account(account_id=10, login="blocked_user", is_blocked=True)
        mock_db = AsyncMock()
        mock_repo_result = MagicMock()
        mock_repo_result.scalars.return_value.first.return_value = account
        mock_db.execute = AsyncMock(return_value=mock_repo_result)

        request = _make_request(cookie_value=token)
        with pytest.raises(HTTPException) as exc_info:
            await get_current_account(request=request, db=mock_db)
        assert exc_info.value.status_code == 403
        assert "blocked" in exc_info.value.detail.lower()
