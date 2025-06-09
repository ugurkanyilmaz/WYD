# User model definition will be here.
from sqlalchemy import Column, Integer, String, DateTime, func
from app.core.database import Base  # <-- note this import!

class User(Base):
    __tablename__ = "users"

    id = Column(Integer, primary_key=True, index=True)
    username = Column(String(30), unique=True, index=True, nullable=False)
    hashed_password = Column(String, nullable=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
