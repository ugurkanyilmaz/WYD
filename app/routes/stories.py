from fastapi import APIRouter, Depends, HTTPException, Form
from ..schemas.stories import StoryCreateIn, StoryOut
from ..crud import create_story, list_active_stories
from ..storage import generate_presigned_upload
from typing import List, Optional

router = APIRouter()

@router.post('/presign')
async def presign_story_upload(filename: str = Form(...), content_type: str = Form(...), current_user:dict = Depends(lambda: {'id': 1})):
    key = f'stories/{current_user["id"]}/{filename}'
    url = await generate_presigned_upload(key, content_type)
    return {'upload_url': url, 'key': key}

@router.post('/', response_model=StoryOut)
async def create(payload: StoryCreateIn, current_user:dict = Depends(lambda: {'id': 1})):
    story = await create_story(current_user['id'], payload.s3_key, payload.caption, payload.expires_in_seconds)
    return story

@router.get('/', response_model=List[StoryOut])
async def list_my(current_user:dict = Depends(lambda: {'id': 1})):
    return await list_active_stories(current_user['id'])

@router.get('/feed', response_model=List[StoryOut])
async def list_feed():
    return await list_active_stories()
