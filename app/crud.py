from .models import AsyncSessionLocal, User, Post, Comment, FriendRequest, Notification, likes_table
from passlib.context import CryptContext
from .auth import create_access_token
from sqlalchemy.future import select, insert, update, delete
from sqlalchemy import select as sql_select, func
from sqlalchemy.exc import IntegrityError

pwd_ctx = CryptContext(schemes=['bcrypt'], deprecated='auto')

async def create_user(payload):
    async with AsyncSessionLocal() as session:
        user = User(
            username=payload.username,
            name=payload.name,
            surname=payload.surname,
            email=payload.email,
            phone_number=payload.phone_number,
            hashed_password=pwd_ctx.hash(payload.password),
            display_name=payload.display_name,
        )
        session.add(user)
        await session.commit()
        await session.refresh(user)
        return user

async def authenticate_user(username, password):
    async with AsyncSessionLocal() as session:
        q = await session.execute(select(User).where(User.username == username))
        user = q.scalars().first()
        if not user or not pwd_ctx.verify(password, user.hashed_password):
            return None
        token = create_access_token({'id': user.id, 'username': user.username})
        return {'access_token': token, 'token_type': 'bearer'}

async def get_user_by_id(user_id: int):
    async with AsyncSessionLocal() as session:
        q = await session.execute(select(User).where(User.id==user_id))
        return q.scalars().first()

# posts
async def create_post(author_id: int, content: str):
    async with AsyncSessionLocal() as session:
        post = Post(author_id=author_id, content=content)
        session.add(post)
        await session.commit()
        await session.refresh(post)
        return post

# comments (threading)
async def create_comment(author_id: int, post_id: int, content: str, parent_id: int = None):
    async with AsyncSessionLocal() as session:
        c = Comment(author_id=author_id, post_id=post_id, content=content, parent_id=parent_id)
        session.add(c)
        await session.commit()
        await session.refresh(c)
        return c

# likes (idempotent)
async def like_post(user_id: int, post_id: int):
    async with AsyncSessionLocal() as session:
        try:
            await session.execute(insert(likes_table).values(user_id=user_id, post_id=post_id))
            await session.commit()
            return True
        except IntegrityError:
            await session.rollback()
            return False

# friendships
async def send_friend_request(from_user:int, to_user:int):
    async with AsyncSessionLocal() as session:
        fr = FriendRequest(from_user=from_user, to_user=to_user)
        session.add(fr)
        await session.commit()
        await session.refresh(fr)
        return fr

async def accept_friend_request(request_id:int):
    async with AsyncSessionLocal() as session:
        q = await session.execute(select(FriendRequest).where(FriendRequest.id==request_id))
        fr = q.scalars().first()
        if not fr:
            return None
        fr.status='accepted'
        session.add(fr)
        await session.commit()
        return fr

# notifications (write to DB and push to Kafka via producer in routes)
async def create_notification(user_id:int, payload:str):
    async with AsyncSessionLocal() as session:
        n = Notification(user_id=user_id, payload=payload)
        session.add(n)
        await session.commit()
        await session.refresh(n)
        return n
