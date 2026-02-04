from sqlalchemy import select
from db.tables.seller import Seller

class SellerRepository:
    def __init__(self, db):
        self.db = db

    async def get_seller(self, id):
        return await self.db.execute(select(Seller).where(Seller.id == id).limit(1))

    async def create_seller(self, seller):
        db_seller = Seller(is_verified_seller=seller.is_verified_seller)
        self.db.add(db_seller)
        await self.db.commit()
        await self.db.refresh(db_seller)
        seller.id = db_seller.id
        return seller
