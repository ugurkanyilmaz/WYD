from fastapi import APIRouter, Depends, HTTPException, Form
from ..schemas.users import RegisterIn, TokenOut, UserOut, RefreshIn
from ..schemas.friendships import AreFriendsOut, ActionOkOut, FriendRequestOut
from ..crud import (
    create_user, 
    authenticate_user, 
    get_user_by_id, 
    send_friend_request, 
    accept_friend_request, 
    refresh_access_token, 
    revoke_refresh_token, 
    create_friendship, 
    are_friends, 
    list_friends
)
from ..auth import decode_token, get_current_user
from ..cache import (
    cache_user_data, 
    get_cached_user_data, 
    invalidate_user_cache, 
    cache_user_friends, 
    get_cached_user_friends, 
    invalidate_friends_cache, 
    check_rate_limit
)
from ..queue_manager import enqueue_friend_request, enqueue_user_activity
from ..core import MONGO

router = APIRouter()


@router.post('/register', response_model=UserOut)
async def register(payload: RegisterIn):
    user = await create_user(payload)
    
    # Cache user data immediately
    user_dict = {
        "id": user.id,
        "username": user.username,
        "name": user.name,
        "surname": user.surname,
        "email": user.email,
        "phone_number": user.phone_number,
        "display_name": user.display_name,
        "profile_picture_url": user.profile_picture_url
    }
    await cache_user_data(user.id, user_dict, ttl=1800)
    
    # Queue user activity logging
    await enqueue_user_activity(user.id, "user_registered", {"email": user.email})
    
    return user


@router.post('/login', response_model=TokenOut)
async def login(
    username: str = Form(...), 
    password: str = Form(...), 
    device_id: str = Form(None)
):
    token = await authenticate_user(username, password, device_id=device_id)
    if not token:
        raise HTTPException(status_code=401, detail='Invalid credentials')
    
    # Queue user activity logging
    user_data = decode_token(token.access_token)
    if user_data:
        await enqueue_user_activity(
            user_data['id'], 
            "user_logged_in", 
            {"device_id": device_id}
        )
    
    return token


@router.post('/refresh', response_model=TokenOut)
async def refresh(payload: RefreshIn):
    token = await refresh_access_token(payload.refresh_token)
    if not token:
        raise HTTPException(status_code=401, detail='Invalid refresh token')
    return token


@router.post('/logout', response_model=ActionOkOut)
async def logout(
    refresh_token: str = Form(None), 
    current_user: dict = Depends(get_current_user)
):
    if refresh_token:
        await revoke_refresh_token(refresh_token)
    
    # Queue user activity logging
    await enqueue_user_activity(current_user['id'], "user_logged_out", {})
    
    return {'ok': True}


@router.post('/me/privacy', response_model=ActionOkOut)
async def set_privacy(
    mode: str, 
    current_user: dict = Depends(get_current_user)
):
    if mode not in ['public', 'private']:
        raise HTTPException(400, 'mode must be public or private')
    if not MONGO:
        raise HTTPException(503, 'storage unavailable')
    
    # Store in MongoDB
    await MONGO.social_app.user_privacy.update_one(
        {'user_id': current_user['id']}, 
        {'$set': {'mode': mode}}, 
        upsert=True
    )
    
    # Invalidate user cache
    await invalidate_user_cache(current_user['id'])
    
    # Queue user activity logging
    await enqueue_user_activity(
        current_user['id'], 
        "privacy_updated", 
        {"mode": mode}
    )
    
    return {'ok': True}


@router.post('/{user_id}/friend-request', response_model=FriendRequestOut)
async def friend_request(
    user_id: int, 
    current_user: dict = Depends(get_current_user)
):
    # Rate limiting - max 20 friend requests per hour
    if not await check_rate_limit(
        current_user['id'], 
        "friend_request", 
        limit=20, 
        window=3600
    ):
        raise HTTPException(429, "Rate limit exceeded. Too many friend requests.")
    
    # Check if users are already friends
    if await are_friends(current_user['id'], user_id):
        raise HTTPException(400, "Users are already friends")
    
    # Send friend request (database operation)
    fr = await send_friend_request(current_user['id'], user_id)
    
    # Queue notification processing for high performance
    await enqueue_friend_request(current_user['id'], user_id, "send_request")
    
    # Queue user activity logging
    await enqueue_user_activity(
        current_user['id'], 
        "friend_request_sent", 
        {"to_user_id": user_id}
    )
    
    return fr


@router.post('/friend-request/{request_id}/accept', response_model=ActionOkOut)
async def accept_request(
    request_id: int, 
    current_user: dict = Depends(get_current_user)
):
    # Rate limiting - max 50 accepts per hour
    if not await check_rate_limit(
        current_user['id'], 
        "accept_friend_request", 
        limit=50, 
        window=3600
    ):
        raise HTTPException(429, "Rate limit exceeded. Too many operations.")
    
    fr = await accept_friend_request(request_id)
    if not fr or fr.to_user != current_user['id']:
        raise HTTPException(404, 'Not found')
    
    # Create friendship both ways as single ordered row (database operation)
    await create_friendship(fr.from_user, fr.to_user)
    
    # Queue notification and analytics processing for high performance
    await enqueue_friend_request(fr.from_user, fr.to_user, "accept_request")
    
    # Queue user activity logging
    await enqueue_user_activity(
        current_user['id'], 
        "friend_request_accepted", 
        {"from_user_id": fr.from_user}
    )
    
    # Invalidate friends cache for both users
    await invalidate_friends_cache(fr.from_user)
    await invalidate_friends_cache(fr.to_user)
    
    return {'ok': True}


@router.get('/{other_id}/are-friends', response_model=AreFriendsOut)
async def check_friend(
    other_id: int, 
    current_user: dict = Depends(get_current_user)
):
    # Check cache first
    cache_key = f"friendship:{min(current_user['id'], other_id)}:{max(current_user['id'], other_id)}"
    cached_result = await get_cached_user_data(cache_key)
    if cached_result is not None:
        return {'friends': cached_result}
    
    # Get from database if not cached
    friends_status = await are_friends(current_user['id'], other_id)
    
    # Cache the result for 5 minutes
    await cache_user_data(cache_key, friends_status, ttl=300)
    
    return {'friends': friends_status}


@router.get('/me/friends', response_model=list[UserOut])
async def my_friends(current_user: dict = Depends(get_current_user)):
    # Check cache first for high performance
    cached_friends = await get_cached_user_friends(current_user['id'])
    if cached_friends:
        return cached_friends
    
    # Get from database if not cached
    friends = await list_friends(current_user['id'])
    
    # Cache the result for 10 minutes
    await cache_user_friends(current_user['id'], friends, ttl=600)
    
    # Log user activity
    await enqueue_user_activity(current_user['id'], "viewed_friends_list", {})
    
    return friends


@router.get('/{user_id}', response_model=UserOut)
async def get_user_profile(user_id: int):
    # Check cache first for high performance
    cached_user = await get_cached_user_data(user_id)
    if cached_user:
        return cached_user
    
    # Get from database if not cached
    user = await get_user_by_id(user_id)
    if not user:
        raise HTTPException(404, 'User not found')
    
    # Cache the user data for 30 minutes
    user_dict = {
        "id": user.id,
        "username": user.username,
        "name": user.name,
        "surname": user.surname,
        "email": user.email,
        "phone_number": user.phone_number,
        "display_name": user.display_name,
        "profile_picture_url": user.profile_picture_url,
        "bio": user.bio
    }
    await cache_user_data(user_id, user_dict, ttl=1800)
    
    return user
