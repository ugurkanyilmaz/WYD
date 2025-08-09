from fastapi import APIRouter, Depends, HTTPException, UploadFile, File, Form
from ..schemas import RegisterIn, TokenOut, UserOut
from ..crud import create_user, authenticate_user, get_user_by_id, send_friend_request, accept_friend_request, create_notification
from ..auth import create_access_token, decode_token
from ..storage import generate_presigned_upload
from ..cache import invalidate_profile_cache, set_profile_cache
from ..auth import get_oauth_redirect
from typing import Optional

router = APIRouter()

@router.post('/register', response_model=UserOut)
async def register(payload: RegisterIn):
    user = await create_user(payload)
    return user

@router.post('/login', response_model=TokenOut)
async def login(username: str = Form(...), password: str = Form(...)):
    token = await authenticate_user(username, password)
    if not token:
        raise HTTPException(status_code=401, detail='Invalid credentials')
    return token

@router.get('/{user_id}', response_model=UserOut)
async def get_profile(user_id: int):
    user = await get_user_by_id(user_id)
    if not user:
        raise HTTPException(404, 'Not found')
    return user

@router.post('/{user_id}/friend-request')
async def friend_request(user_id:int, current_user:dict = Depends(lambda: {'id': 1})):
    fr = await send_friend_request(current_user['id'], user_id)
    # produce notification
    await create_notification(user_id, f'Friend request from {current_user["id"]}')
    return {'ok': True, 'request_id': fr.id}

@router.post('/avatar/presign')
async def presign_avatar(filename: str = Form(...), content_type: str = Form(...), current_user:dict = Depends(lambda: {'id': 1})):
    key = f'avatars/{current_user["id"]}/{filename}'
    url = await generate_presigned_upload(key, content_type)
    # invalidate profile cache after client uploads and notifies backend
    await invalidate_profile_cache(current_user['id'])
    return {'upload_url': url, 'key': key}

# OAuth redirect example
@router.get('/oauth/{provider}')
async def oauth_redirect(provider: str, redirect_uri: Optional[str] = None):
    if not redirect_uri:
        redirect_uri = 'https://example.com/oauth/callback'
    return {'url': get_oauth_redirect(provider, redirect_uri)}
