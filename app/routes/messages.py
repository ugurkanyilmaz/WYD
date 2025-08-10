from fastapi import APIRouter, Depends
from ..schemas.messages import MessageIn, MessageOut
from ..crud import send_message, list_dialog
from typing import List

router = APIRouter()

@router.post('/', response_model=MessageOut)
async def send(payload: MessageIn, current_user:dict = Depends(lambda: {'id': 1})):
    m = await send_message(current_user['id'], payload.recipient_id, payload.content)
    return m

@router.get('/{peer_id}', response_model=List[MessageOut])
async def dialog(peer_id:int, current_user:dict = Depends(lambda: {'id': 1})):
    return await list_dialog(current_user['id'], peer_id)
