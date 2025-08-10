from sqlalchemy import Column, Integer, String, DateTime, ForeignKey, Boolean, func
from . import Base

class SessionToken(Base):
    __tablename__ = 'session_tokens'
    id = Column(Integer, primary_key=True)
    user_id = Column(Integer, ForeignKey('users.id', ondelete='CASCADE'), index=True, nullable=False)
    device_id = Column(String(255), nullable=True)
    token_hash = Column(String(128), unique=True, nullable=False, index=True)
    user_agent = Column(String(255), nullable=True)
    ip = Column(String(64), nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    expires_at = Column(DateTime(timezone=True), nullable=False)
    revoked_at = Column(DateTime(timezone=True), nullable=True)
