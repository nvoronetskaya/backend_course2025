from db.database import Base
from sqlalchemy import Column, Integer, Text, Boolean


class Account(Base):
    __tablename__ = "account"
    id = Column(Integer, primary_key=True, index=True)
    login = Column(Text, nullable=False)
    password = Column(Text, nullable=False)
    is_blocked = Column(Boolean, nullable=False, default=False, server_default="false")
