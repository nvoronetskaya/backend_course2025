from types import SimpleNamespace

from sqlalchemy import text


class SellerRepository:
    def __init__(self, db):
        self.db = db

    def to_bool(self, val):
        if isinstance(val, str):
            return val.lower() != "false"
        return bool(val)

    def to_obj(self, row):
        if row is None:
            return None
        d = dict(row)
        d["is_verified_seller"] = self._to_bool(d["is_verified_seller"])
        return SimpleNamespace(**d)

    async def get_seller(self, id):
        result = await self.db.execute(
            text("SELECT * FROM sellers WHERE id = :id LIMIT 1"),
            {"id": id},
        )
        return self.to_obj(result.mappings().first())

    async def create_seller(self, seller):
        result = await self.db.execute(
            text(
                "INSERT INTO sellers (is_verified_seller) "
                "VALUES (:is_verified_seller) "
                "RETURNING *"
            ),
            {"is_verified_seller": seller.is_verified_seller},
        )
        await self.db.commit()
        row = self.to_obj(result.mappings().first())
        seller.id = row.id
        return seller
