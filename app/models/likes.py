from sqlalchemy import Table, Column, Integer, ForeignKey, UniqueConstraint
from . import Base

likes_table = Table(
    'likes', Base.metadata,
    Column('id', Integer, primary_key=True),
    Column('user_id', Integer, ForeignKey('users.id', ondelete='CASCADE')),
    Column('post_id', Integer, ForeignKey('posts.id', ondelete='CASCADE')),
    UniqueConstraint('user_id','post_id', name='uix_user_post_like')
)
