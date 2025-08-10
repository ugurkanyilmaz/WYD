from sqlalchemy import Column, Integer, DateTime, ForeignKey, UniqueConstraint, func
from . import Base

class Friendship(Base):
    __tablename__ = 'friendships'
    id = Column(Integer, primary_key=True)
    user_id = Column(Integer, ForeignKey('users.id', ondelete='CASCADE'), index=True, nullable=False)
    friend_id = Column(Integer, ForeignKey('users.id', ondelete='CASCADE'), index=True, nullable=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    __table_args__ = (
        UniqueConstraint('user_id', 'friend_id', name='uix_friend_pair'),
    )
