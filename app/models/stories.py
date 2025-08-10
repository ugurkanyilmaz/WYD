from sqlalchemy import Column, Integer, String, Text, DateTime, Boolean, ForeignKey, func
from . import Base

class Story(Base):
    __tablename__ = 'stories'
    id = Column(Integer, primary_key=True)
    user_id = Column(Integer, ForeignKey('users.id', ondelete='CASCADE'), index=True, nullable=False)
    s3_key = Column(String, nullable=False)
    media_url = Column(String, nullable=True)
    caption = Column(Text, nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    expires_at = Column(DateTime(timezone=True), nullable=False, index=True)
    is_active = Column(Boolean, default=True, index=True)
