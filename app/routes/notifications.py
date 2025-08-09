from fastapi import APIRouter, Depends, HTTPException
from ..crud import create_notification
from typing import List

router = APIRouter()

@router.get('/my')
async def my_notifications(user_id:int = 1):
    # placeholder - fetch from DB
    return []

@router.post('/send')
async def send_notification(user_id:int, message:str):
    n = await create_notification(user_id, message)
    return {'id': n.id}
