from sqlalchemy import select
from db.tables.item import Item as DbItem

class ItemRepository:
    def __init__(self, db):
        self.db = db

    async def get_item(self, id):
        return await self.db.execute(select(DbItem).where(DbItem.id == id).limit(1))

    async def create_item(self, item):
        db_item = DbItem(
            title = item.title,
            description = item.description,
            category = item.category,
            images_qty = item.images_qty
        )
        self.db.add(db_item)
        await self.db.commit()
        await self.db.refresh(db_item)
        item.id = db_item.id
        return item
