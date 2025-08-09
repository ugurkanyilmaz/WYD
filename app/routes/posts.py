from fastapi import APIRouter, Depends, HTTPException
from ..schemas import PostIn, PostOut, CommentIn
from ..crud import create_post, create_comment, like_post
from typing import List

router = APIRouter()

@router.post('/', response_model=PostOut)
async def create(user_id: int = 1, payload: PostIn = None):
    post = await create_post(user_id, payload.content)
    return post

@router.post('/{post_id}/comment')
async def comment(post_id:int, payload: CommentIn, user_id:int = 1):
    c = await create_comment(user_id, post_id, payload.content, payload.parent_id)
    return {'id': c.id, 'post_id': c.post_id}

@router.post('/{post_id}/like')
async def like(post_id:int, user_id:int = 1):
    ok = await like_post(user_id, post_id)
    return {'liked': ok}
