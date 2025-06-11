# User model definition will be here.
from sqlalchemy import Column, String, Integer, DateTime, func
from sqlalchemy.orm import declarative_base

Base = declarative_base()

class User(Base):
    __tablename__ = "users"

    id = Column(Integer, primary_key=True, index=True)
    username = Column(String(30), unique=True, index=True, nullable=False)
    hashed_password = Column(String, nullable=False)
    profile_photo = Column(String, nullable=True)  # Optional: stores the path to the user's profile photo
    created_at = Column(DateTime(timezone=True), server_default=func.now())