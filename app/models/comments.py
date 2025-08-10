from sqlalchemy import Column, Integer, Text, DateTime, ForeignKey, func
from . import Base

class Comment(Base):
    __tablename__ = 'comments'
    id = Column(Integer, primary_key=True, index=True)
    post_id = Column(Integer, ForeignKey('posts.id', ondelete='CASCADE'))
    author_id = Column(Integer, ForeignKey('users.id', ondelete='CASCADE'))
    parent_id = Column(Integer, ForeignKey('comments.id', ondelete='CASCADE'), nullable=True)
    content = Column(Text, nullable=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
