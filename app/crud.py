from .models import AsyncSessionLocal
from .models.users import User
from .models.friend_requests import FriendRequest
from .models.notifications import Notification
from .models.session_tokens import SessionToken
from .models.messages import Message
from .models.friendships import Friendship
from passlib.context import CryptContext
from .auth import create_access_token, generate_refresh_token, hash_token
from sqlalchemy import select, func
from sqlalchemy.exc import IntegrityError
from datetime import datetime, timedelta
from collections import defaultdict

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

async def authenticate_user(username, password, device_id: str | None = None, user_agent: str | None = None, ip: str | None = None):
    async with AsyncSessionLocal() as session:
        q = await session.execute(select(User).where(User.username == username))
        user = q.scalars().first()
        if not user or not pwd_ctx.verify(password, user.hashed_password):
            return None
        access = create_access_token({'id': user.id, 'username': user.username})
        refresh = generate_refresh_token()
        token_hash = hash_token(refresh)
        expires_at = datetime.utcnow() + timedelta(days=30)
        st = SessionToken(user_id=user.id, device_id=device_id, token_hash=token_hash, user_agent=user_agent, ip=ip, expires_at=expires_at)
        session.add(st)
        await session.commit()
        return {'access_token': access, 'token_type': 'bearer', 'refresh_token': refresh}

async def refresh_access_token(refresh_token: str):
    async with AsyncSessionLocal() as session:
        token_hash = hash_token(refresh_token)
        q = await session.execute(select(SessionToken).where(SessionToken.token_hash == token_hash, SessionToken.revoked_at.is_(None), SessionToken.expires_at > datetime.utcnow()))
        st = q.scalars().first()
        if not st:
            return None
        uq = await session.execute(select(User).where(User.id == st.user_id))
        user = uq.scalars().first()
        if not user:
            return None
        access = create_access_token({'id': user.id, 'username': user.username})
        return {'access_token': access, 'token_type': 'bearer'}

async def revoke_refresh_token(refresh_token: str):
    async with AsyncSessionLocal() as session:
        token_hash = hash_token(refresh_token)
        q = await session.execute(select(SessionToken).where(SessionToken.token_hash == token_hash, SessionToken.revoked_at.is_(None)))
        st = q.scalars().first()
        if not st:
            return False
        st.revoked_at = datetime.utcnow()
        session.add(st)
        await session.commit()
        return True

async def get_user_by_id(user_id: int):
    async with AsyncSessionLocal() as session:
        q = await session.execute(select(User).where(User.id==user_id))
        return q.scalars().first()

## comments/likes removed

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

async def create_friendship(user_a:int, user_b:int):
    # store ordered pair to keep uniqueness
    a, b = sorted([user_a, user_b])
    async with AsyncSessionLocal() as session:
        try:
            f = Friendship(user_id=a, friend_id=b)
            session.add(f)
            await session.commit()
            await session.refresh(f)
            return f
        except IntegrityError:
            await session.rollback()
            # already friends
            res = await session.execute(select(Friendship).where(Friendship.user_id==a, Friendship.friend_id==b))
            return res.scalars().first()

async def are_friends(user_a:int, user_b:int) -> bool:
    a, b = sorted([user_a, user_b])
    async with AsyncSessionLocal() as session:
        res = await session.execute(select(Friendship).where(Friendship.user_id==a, Friendship.friend_id==b))
        return res.scalars().first() is not None

async def list_friends(user_id:int):
    async with AsyncSessionLocal() as session:
        # friends are rows where (user_id==me) or (friend_id==me)
        res1 = await session.execute(select(Friendship.friend_id).where(Friendship.user_id==user_id))
        res2 = await session.execute(select(Friendship.user_id).where(Friendship.friend_id==user_id))
        ids = set([*res1.scalars().all(), *res2.scalars().all()])
        if not ids:
            return []
        users = await session.execute(select(User).where(User.id.in_(ids)))
        return users.scalars().all()

# notifications (write to DB and push to Kafka via producer in routes)
async def create_notification(user_id:int, payload:str):
    async with AsyncSessionLocal() as session:
        n = Notification(user_id=user_id, payload=payload)
        session.add(n)
        await session.commit()
        await session.refresh(n)
        return n

# stories deprecated in favor of media feature

# messaging
async def send_message(sender_id:int, recipient_id:int, content:str):
    async with AsyncSessionLocal() as session:
        m = Message(sender_id=sender_id, recipient_id=recipient_id, content=content)
        session.add(m)
        await session.commit()
        await session.refresh(m)
        return m

async def list_dialog(user_id:int, peer_id:int):
    async with AsyncSessionLocal() as session:
        q = select(Message).where(
            ((Message.sender_id==user_id) & (Message.recipient_id==peer_id)) |
            ((Message.sender_id==peer_id) & (Message.recipient_id==user_id))
        ).order_by(Message.created_at.asc())
        res = await session.execute(q)
        return res.scalars().all()

# Profile Management
async def update_profile_picture(user_id: int, picture_url: str):
    """Update user's profile picture URL"""
    async with AsyncSessionLocal() as session:
        q = await session.execute(select(User).where(User.id == user_id))
        user = q.scalars().first()
        if not user:
            return None
        
        user.profile_picture_url = picture_url
        await session.commit()
        await session.refresh(user)
        return user

async def remove_profile_picture(user_id: int):
    """Remove user's profile picture"""
    async with AsyncSessionLocal() as session:
        q = await session.execute(select(User).where(User.id == user_id))
        user = q.scalars().first()
        if not user:
            return None
        
        old_url = user.profile_picture_url
        user.profile_picture_url = None
        await session.commit()
        await session.refresh(user)
        return user, old_url

async def update_user_bio(user_id: int, bio: str):
    """Update user's bio"""
    async with AsyncSessionLocal() as session:
        q = await session.execute(select(User).where(User.id == user_id))
        user = q.scalars().first()
        if not user:
            return None
        
        user.bio = bio
        await session.commit()
        await session.refresh(user)
        return user

async def update_user_display_name(user_id: int, display_name: str):
    """Update user's display name"""
    async with AsyncSessionLocal() as session:
        q = await session.execute(select(User).where(User.id == user_id))
        user = q.scalars().first()
        if not user:
            return None
        
        user.display_name = display_name
        await session.commit()
        await session.refresh(user)
        return user

async def get_user_profile(user_id: int):
    """Get user profile with full information"""
    async with AsyncSessionLocal() as session:
        q = await session.execute(select(User).where(User.id == user_id))
        return q.scalars().first()
