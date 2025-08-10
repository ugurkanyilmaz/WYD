import os
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
from sqlalchemy.orm import declarative_base, sessionmaker

DATABASE_URL = os.getenv('DATABASE_URL') or 'postgresql+asyncpg://social:socialpass@postgres:5432/socialdb'
if DATABASE_URL.startswith('postgresql://') and not DATABASE_URL.startswith('postgresql+asyncpg://'):
    DATABASE_URL = DATABASE_URL.replace('postgresql://', 'postgresql+asyncpg://', 1)

engine = create_async_engine(DATABASE_URL, future=True, echo=False)
AsyncSessionLocal = sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)
Base = declarative_base()

# Import models to register tables
from .users import User  # noqa: F401,E402
from .friend_requests import FriendRequest  # noqa: F401,E402
from .notifications import Notification  # noqa: F401,E402
from .session_tokens import SessionToken  # noqa: F401,E402
from .messages import Message  # noqa: F401,E402
from .friendships import Friendship  # noqa: F401,E402
