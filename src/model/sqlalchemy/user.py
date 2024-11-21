
from sqlalchemy import Column, Integer, String
from sqlalchemy.orm import declarative_base

from database import Base

class UserModel(Base):
    __tablename__ = "users"
    id = Column(Integer, primary_key=True, index=True)
    name = Column(String, index=True)
    age = Column(Integer)