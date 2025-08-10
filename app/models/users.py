from sqlalchemy import Column, Integer, String, Boolean, DateTime, func
from . import Base

class User(Base):
    __tablename__ = 'users'
    id = Column(Integer, primary_key=True, index=True)
    username = Column(String(150), unique=True, index=True, nullable=False)
    name = Column(String(150), nullable=False)
    surname = Column(String(150), nullable=False)
    email = Column(String, unique=True, index=True, nullable=False)
    phone_number = Column(String(50), unique=True, index=True, nullable=False)
    hashed_password = Column(String, nullable=False)
    display_name = Column(String, nullable=True)
    profile_picture_url = Column(String, nullable=True)
    blocked = Column(Boolean, default=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
