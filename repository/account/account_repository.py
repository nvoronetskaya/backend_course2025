import hashlib

from sqlalchemy import select, delete
from db.tables.account import Account


class AccountRepository:
    def __init__(self, db):
        self.db = db

    @staticmethod
    def _hash_password(password: str) -> str:
        return hashlib.md5(password.encode()).hexdigest()

    async def create_account(self, login: str, password: str) -> Account:
        account = Account(login=login, password=self._hash_password(password))
        self.db.add(account)
        await self.db.commit()
        await self.db.refresh(account)
        return account

    async def get_by_id(self, account_id: int):
        result = await self.db.execute(
            select(Account).where(Account.id == account_id).limit(1)
        )
        return result.scalars().first()

    async def delete_account(self, account_id: int) -> bool:
        account = await self.get_by_id(account_id)
        if account is None:
            return False
        await self.db.execute(
            delete(Account).where(Account.id == account_id)
        )
        await self.db.commit()
        return True

    async def block_account(self, account_id: int):
        account = await self.get_by_id(account_id)
        if account is None:
            return None
        account.is_blocked = True
        await self.db.commit()
        await self.db.refresh(account)
        return account

    async def get_by_login_and_password(self, login: str, password: str):
        result = await self.db.execute(
            select(Account)
            .where(Account.login == login, Account.password == self._hash_password(password))
            .limit(1)
        )
        return result.scalars().first()
