from fastapi import APIRouter, Depends, HTTPException
from ..schemas.messages import MessageIn, MessageOut
from ..crud import send_message, list_dialog
from ..cache import (
    cache_message_data, 
    get_cached_conversation, 
    cache_conversation, 
    check_rate_limit
)
from ..queue_manager import enqueue_message, enqueue_user_activity
from typing import List
from ..auth import get_current_user

router = APIRouter()

@router.post('/', response_model=MessageOut)
async def send(payload: MessageIn, current_user: dict = Depends(get_current_user)):
    # Rate limiting - max 100 messages per hour
    if not await check_rate_limit(
        current_user['id'], 
        "send_message", 
        limit=100, 
        window=3600
    ):
        raise HTTPException(429, "Rate limit exceeded. Too many messages.")
    
    # Send message (database operation)
    m = await send_message(current_user['id'], payload.recipient_id, payload.content)
    
    # Queue message processing for delivery and notifications
    await enqueue_message(
        current_user['id'], 
        payload.recipient_id, 
        payload.content,
        m.id
    )
    
    # Queue user activity logging
    await enqueue_user_activity(
        current_user['id'], 
        "message_sent", 
        {"recipient_id": payload.recipient_id, "message_id": m.id}
    )
    
    return m

@router.get('/{peer_id}', response_model=List[MessageOut])
async def dialog(peer_id: int, current_user: dict = Depends(get_current_user)):
    # Check cache first for high performance
    conversation_key = f"{min(current_user['id'], peer_id)}:{max(current_user['id'], peer_id)}"
    cached_messages = await get_cached_conversation(conversation_key)
    if cached_messages:
        return cached_messages
    
    # Get from database if not cached
    messages = await list_dialog(current_user['id'], peer_id)
    
    # Cache the conversation for 5 minutes
    await cache_conversation(conversation_key, messages, ttl=300)
    
    # Queue user activity logging
    await enqueue_user_activity(
        current_user['id'], 
        "viewed_conversation", 
        {"peer_id": peer_id}
    )
    
    return messages
