from fastapi import APIRouter, WebSocket, WebSocketDisconnect, Depends, Query
from ..auth import decode_token
from ..ws_manager import RedisPubSubManager

router = APIRouter()

manager = RedisPubSubManager()

@router.websocket('/chat')
async def chat_ws(websocket: WebSocket, token: str = Query(None)):
    user = None
    if token:
        user = decode_token(token)
    if not user:
        await websocket.close(code=1008)
        return
    user_id = user.get('id')
    await manager.connect(user_id, websocket)
    try:
        while True:
            data = await websocket.receive_json()
            # route message: publish to Kafka or Redis
            # echo example:
            await manager.send_personal(user_id, {'echo': data})
    except WebSocketDisconnect:
        await manager.disconnect(user_id, websocket)
