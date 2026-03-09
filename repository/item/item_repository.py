import time
from sqlalchemy import select
from db.tables.item import Item as DbItem
from app.metrics import DB_QUERY_DURATION

class ItemRepository:
    def __init__(self, db):
        self.db = db

    async def get_item(self, id):
        start = time.perf_counter()
        result = await self.db.execute(select(DbItem).where(DbItem.id == id).limit(1))
        DB_QUERY_DURATION.labels(query_type="select_item").observe(time.perf_counter() - start)
        return result.scalars().first()

    async def create_item(self, item):
        db_item = DbItem(
            name = item.name,
            description = item.description,
            category = item.category,
            images_qty = item.images_qty
        )
        self.db.add(db_item)
        start = time.perf_counter()
        await self.db.commit()
        DB_QUERY_DURATION.labels(query_type="insert_item").observe(time.perf_counter() - start)
        await self.db.refresh(db_item)
        return item

    async def close_item(self, item_id):
        item = await self.get_item(item_id)
        if item is None:
            return None
        item.is_closed = True
        start = time.perf_counter()
        await self.db.commit()
        DB_QUERY_DURATION.labels(query_type="update_item").observe(time.perf_counter() - start)
        await self.db.refresh(item)
        return item
