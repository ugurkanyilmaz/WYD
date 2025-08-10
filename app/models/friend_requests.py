from sqlalchemy import Column, Integer, String, DateTime, ForeignKey, func
from . import Base

class FriendRequest(Base):
    __tablename__ = 'friend_requests'
    id = Column(Integer, primary_key=True)
    from_user = Column(Integer, ForeignKey('users.id', ondelete='CASCADE'))
    to_user = Column(Integer, ForeignKey('users.id', ondelete='CASCADE'))
    status = Column(String, default='pending')  # pending, accepted, rejected
    created_at = Column(DateTime(timezone=True), server_default=func.now())
