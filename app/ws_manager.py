from typing import Dict, Set
from fastapi import WebSocket
import asyncio
from .core import REDIS

class RedisPubSubManager:
    def __init__(self):
        self.connections: Dict[int, Set[WebSocket]] = {}
        self.pubsub_task = None

    async def connect(self, user_id:int, websocket:WebSocket):
        await websocket.accept()
        self.connections.setdefault(user_id, set()).add(websocket)
        # Optionally set presence in Redis
        await REDIS.set(f'presence:{user_id}', 'online', ex=60)

    async def disconnect(self, user_id:int, websocket:WebSocket):
        self.connections.get(user_id, set()).discard(websocket)
        if not self.connections.get(user_id):
            await REDIS.delete(f'presence:{user_id}')

    async def send_personal(self, user_id:int, message:dict):
        ws_set = self.connections.get(user_id, set())
        for ws in list(ws_set):
            try:
                await ws.send_json(message)
            except Exception:
                await self.disconnect(user_id, ws)

    async def broadcast(self, message:dict):
        for uid, ws_set in self.connections.items():
            for ws in list(ws_set):
                try:
                    await ws.send_json(message)
                except Exception:
                    await self.disconnect(uid, ws)

    # Redis pub/sub listener to route messages between app instances
    async def start_redis_listener(self):
        pubsub = REDIS.pubsub()
        await pubsub.subscribe('ws_events')
        async for item in pubsub.listen():
            if item and item.get('type') == 'message':
                try:
                    data = item.get('data')
                    # publish to local websockets as needed
                except Exception:
                    pass
