from fastapi import APIRouter, Depends, HTTPException, UploadFile, File, Form
from ..schemas.users import RegisterIn, TokenOut, UserOut, RefreshIn
from ..schemas.friendships import AreFriendsOut, ActionOkOut
from ..crud import create_user, authenticate_user, get_user_by_id, send_friend_request, accept_friend_request, create_notification, refresh_access_token, revoke_refresh_token, create_friendship, are_friends, list_friends
from ..auth import create_access_token, decode_token, get_current_user
from ..cache import invalidate_profile_cache, set_profile_cache
from typing import Optional
from ..core import MONGO

router = APIRouter()

@router.post('/register', response_model=UserOut)
async def register(payload: RegisterIn):
    user = await create_user(payload)
    return user

@router.post('/login', response_model=TokenOut)
async def login(username: str = Form(...), password: str = Form(...), device_id: str | None = Form(None)):
    token = await authenticate_user(username, password, device_id=device_id)
    if not token:
        raise HTTPException(status_code=401, detail='Invalid credentials')
    return token

@router.post('/refresh', response_model=TokenOut)
async def refresh(payload: RefreshIn):
    token = await refresh_access_token(payload.refresh_token)
    if not token:
        raise HTTPException(status_code=401, detail='Invalid refresh token')
    return token

@router.post('/logout', response_model=ActionOkOut)
async def logout(payload: RefreshIn):
    ok = await revoke_refresh_token(payload.refresh_token)
    return {'ok': bool(ok)}

@router.get('/{user_id}', response_model=UserOut)
async def get_profile(user_id: int):
    user = await get_user_by_id(user_id)
    if not user:
        raise HTTPException(404, 'Not found')
    return user

# Media listing disabled temporarily
# @router.get('/{user_id}/media')
# async def get_profile_media(user_id:int, current_user:dict = Depends(lambda: {'id': 1})):
#     ...

@router.post('/me/privacy', response_model=ActionOkOut)
async def set_privacy(mode:str, current_user:dict = Depends(get_current_user)):
    if mode not in ('public','private'):
        raise HTTPException(400, 'mode must be public or private')
    if not MONGO:
        raise HTTPException(503, 'storage unavailable')
    await MONGO.wyd.users.update_one({'_id': current_user['id']}, {'$set': {'privacy': mode}}, upsert=True)
    return {'ok': True}

@router.post('/{user_id}/friend-request', response_model=ActionOkOut)
async def friend_request(user_id:int, current_user:dict = Depends(get_current_user)):
    fr = await send_friend_request(current_user['id'], user_id)
    # produce notification
    await create_notification(user_id, f'Friend request from {current_user["id"]}')
    return {'ok': True}

@router.post('/friend-request/{request_id}/accept', response_model=ActionOkOut)
async def accept_request(request_id:int, current_user:dict = Depends(get_current_user)):
    fr = await accept_friend_request(request_id)
    if not fr or fr.to_user != current_user['id']:
        raise HTTPException(404, 'Not found')
    # create friendship both ways as single ordered row
    await create_friendship(fr.from_user, fr.to_user)
    await create_notification(fr.from_user, f'Friend request accepted by {fr.to_user}')
    return {'ok': True}

@router.get('/{other_id}/are-friends', response_model=AreFriendsOut)
async def check_friend(other_id:int, current_user:dict = Depends(get_current_user)):
    return {'friends': await are_friends(current_user['id'], other_id)}

@router.get('/me/friends', response_model=list[UserOut])
async def my_friends(current_user:dict = Depends(get_current_user)):
    return await list_friends(current_user['id'])

# moved to /api/media endpoints

# OAuth endpoints removed; only username/password auth supported.
