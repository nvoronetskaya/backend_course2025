import hashlib

import pytest
from sqlalchemy.ext.asyncio import create_async_engine, async_sessionmaker, AsyncSession
from db.database import Base
import db.tables.account
from repository.account.account_repository import AccountRepository


@pytest.fixture
async def db_session():
    engine = create_async_engine("sqlite+aiosqlite://", echo=False)
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    session_factory = async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)
    async with session_factory() as session:
        yield session
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)
    await engine.dispose()


@pytest.fixture
def account_repo(db_session):
    return AccountRepository(db_session)


@pytest.mark.integration
class TestAccountRepository:
    async def test_create_and_get_by_id(self, account_repo):
        account = await account_repo.create_account("user1", "pass1")
        assert account is not None
        assert account.login == "user1"
        assert account.password == hashlib.md5(b"pass1").hexdigest()
        assert account.is_blocked is False

        fetched = await account_repo.get_by_id(account.id)
        assert fetched is not None
        assert fetched.id == account.id
        assert fetched.login == "user1"

    async def test_get_by_id_not_found(self, account_repo):
        result = await account_repo.get_by_id(999999)
        assert result is None

    async def test_delete_account(self, account_repo):
        account = await account_repo.create_account("user", "pass")
        deleted = await account_repo.delete_account(account.id)
        assert deleted is True
        assert await account_repo.get_by_id(account.id) is None

    async def test_delete_account_not_found(self, account_repo):
        deleted = await account_repo.delete_account(999999)
        assert deleted is False

    async def test_block_account(self, account_repo):
        account = await account_repo.create_account("user", "pass")
        assert account.is_blocked is False

        blocked = await account_repo.block_account(account.id)
        assert blocked is not None
        assert blocked.is_blocked is True
        assert blocked.id == account.id

    async def test_block_account_not_found(self, account_repo):
        result = await account_repo.block_account(999999)
        assert result is None

    async def test_get_by_login_and_password(self, account_repo):
        await account_repo.create_account("user", "secret")
        found = await account_repo.get_by_login_and_password("user", "secret")
        assert found is not None
        assert found.login == "user"
        assert found.password == hashlib.md5(b"secret").hexdigest()

    async def test_get_by_login_and_password_not_found(self, account_repo):
        result = await account_repo.get_by_login_and_password("no_user", "no_pass")
        assert result is None

    async def test_get_by_login_and_password_wrong_password(self, account_repo):
        await account_repo.create_account("user", "correct")
        result = await account_repo.get_by_login_and_password("user", "wrong")
        assert result is None
