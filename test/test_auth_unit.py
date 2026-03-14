import pytest
from unittest.mock import AsyncMock, MagicMock
from service.auth_service import AuthService
from app.exceptions import InvalidCredentialsError, AccountBlockedError, InvalidTokenError

SECRET = "test-secret-key"


def _make_account(account_id=1, login="user", password="pass", is_blocked=False):
    account = MagicMock()
    account.id = account_id
    account.login = login
    account.password = password
    account.is_blocked = is_blocked
    return account


def make_service(account_repo=None):
    if account_repo is None:
        account_repo = AsyncMock()
    return AuthService(account_repo=account_repo, secret_key=SECRET, token_ttl_minutes=30)


class TestAuthenticate:
    async def test_authenticate_success(self):
        repo = AsyncMock()
        account = _make_account()
        repo.get_by_login_and_password = AsyncMock(return_value=account)

        service = make_service(repo)
        token = await service.authenticate("user", "pass")

        assert isinstance(token, str)
        assert len(token) > 0
        repo.get_by_login_and_password.assert_awaited_once_with("user", "pass")

    async def test_authenticate_invalid_credentials(self):
        repo = AsyncMock()
        repo.get_by_login_and_password = AsyncMock(return_value=None)

        service = make_service(repo)
        with pytest.raises(InvalidCredentialsError):
            await service.authenticate("wrong", "creds")

    async def test_authenticate_blocked_account(self):
        repo = AsyncMock()
        account = _make_account(is_blocked=True)
        repo.get_by_login_and_password = AsyncMock(return_value=account)

        service = make_service(repo)
        with pytest.raises(AccountBlockedError):
            await service.authenticate("user", "pass")


class TestToken:
    def test_create_and_verify_token(self):
        service = make_service()
        token = service.create_token(account_id=42, login="alice")
        payload = service.verify_token(token)

        assert payload["sub"] == 42
        assert payload["login"] == "alice"
        assert "exp" in payload

    def test_verify_token_expired(self):
        service = AuthService(
            account_repo=AsyncMock(),
            secret_key=SECRET,
            token_ttl_minutes=0,
        )
        token = service.create_token(account_id=1, login="user")

        with pytest.raises(InvalidTokenError, match="expired"):
            service.verify_token(token)

    def test_verify_token_invalid(self):
        service = make_service()
        with pytest.raises(InvalidTokenError, match="Invalid token"):
            service.verify_token("not.a.valid.token")

    def test_verify_token_wrong_secret(self):
        service_a = AuthService(account_repo=AsyncMock(), secret_key="secret-a")
        service_b = AuthService(account_repo=AsyncMock(), secret_key="secret-b")

        token = service_a.create_token(account_id=1, login="user")
        with pytest.raises(InvalidTokenError):
            service_b.verify_token(token)
