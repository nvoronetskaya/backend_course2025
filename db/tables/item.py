from db.database import Base
from sqlalchemy import Column, Integer, String, Text

class Item(Base):
    __tablename__ = "items"
    id = Column(Integer, primary_key=True, index=True)
    title = Column(String, nullable=False)
    description = Column(Text, nullable=False)
    images_qty = Column(Integer, nullable=False)
    category = Column(Integer, nullable=False)
