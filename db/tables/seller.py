from db.database import Base
from sqlalchemy import Column, Integer, Boolean

class Seller(Base):
    __tablename__ = "sellers"
    id = Column(Integer, primary_key=True, index=True)
    is_verified_seller = Column(Boolean, nullable=False)
