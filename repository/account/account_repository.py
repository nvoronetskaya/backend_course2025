import hashlib
from types import SimpleNamespace

from sqlalchemy import text


class AccountRepository:
    def __init__(self, db):
        self.db = db

    def hash_password(self, password: str) -> str:
        return hashlib.md5(password.encode()).hexdigest()

    def to_bool(self, val):
        if isinstance(val, str):
            return val.lower() != "false"
        return bool(val)

    def to_obj(self, row):
        if row is None:
            return None
        d = dict(row)
        d["is_blocked"] = self.to_bool(d["is_blocked"])
        return SimpleNamespace(**d)

    async def create_account(self, login: str, password: str):
        result = await self.db.execute(
            text(
                "INSERT INTO account (login, password, is_blocked) "
                "VALUES (:login, :password, false) "
                "RETURNING *"
            ),
            {"login": login, "password": self.hash_password(password)},
        )
        await self.db.commit()
        return self.to_obj(result.mappings().first())

    async def get_by_id(self, account_id: int):
        result = await self.db.execute(
            text("SELECT * FROM account WHERE id = :id LIMIT 1"),
            {"id": account_id},
        )
        return self.to_obj(result.mappings().first())

    async def delete_account(self, account_id: int) -> bool:
        account = await self.get_by_id(account_id)
        if account is None:
            return False
        await self.db.execute(
            text("DELETE FROM account WHERE id = :id"),
            {"id": account_id},
        )
        await self.db.commit()
        return True

    async def block_account(self, account_id: int):
        result = await self.db.execute(
            text(
                "UPDATE account SET is_blocked = true "
                "WHERE id = :id RETURNING *"
            ),
            {"id": account_id},
        )
        await self.db.commit()
        return self.to_obj(result.mappings().first())

    async def get_by_login_and_password(self, login: str, password: str):
        result = await self.db.execute(
            text(
                "SELECT * FROM account "
                "WHERE login = :login AND password = :password "
                "LIMIT 1"
            ),
            {"login": login, "password": self.hash_password(password)},
        )
        return self.to_obj(result.mappings().first())
