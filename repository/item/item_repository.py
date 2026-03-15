import time
from types import SimpleNamespace

from sqlalchemy import text
from app.metrics import DB_QUERY_DURATION

class ItemRepository:
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
        d["is_closed"] = self.to_bool(d.get("is_closed", False))
        return SimpleNamespace(**d)

    async def get_item(self, id):
        start = time.perf_counter()
        result = await self.db.execute(
            text("SELECT * FROM items WHERE id = :id LIMIT 1"),
            {"id": id},
        )
        DB_QUERY_DURATION.labels(query_type="select_item").observe(time.perf_counter() - start)
        return self.to_obj(result.mappings().first())

    async def create_item(self, item):
        start = time.perf_counter()
        result = await self.db.execute(
            text(
                "INSERT INTO items (name, description, category, images_qty) "
                "VALUES (:name, :description, :category, :images_qty) "
                "RETURNING *"
            ),
            {
                "name": item.name,
                "description": item.description,
                "category": item.category,
                "images_qty": item.images_qty,
            },
        )
        await self.db.commit()
        DB_QUERY_DURATION.labels(query_type="insert_item").observe(time.perf_counter() - start)
        return self.to_obj(result.mappings().first())

    async def close_item(self, item_id):
        existing = await self.get_item(item_id)
        if existing is None:
            return None
        start = time.perf_counter()
        result = await self.db.execute(
            text(
                "UPDATE items SET is_closed = true "
                "WHERE id = :id RETURNING *"
            ),
            {"id": item_id},
        )
        await self.db.commit()
        DB_QUERY_DURATION.labels(query_type="update_item").observe(time.perf_counter() - start)
        return self.to_obj(result.mappings().first())
