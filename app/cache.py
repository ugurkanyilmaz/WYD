from .core import REDIS
import json
from typing import Optional

async def set_profile_cache(user_id:int, profile:dict, ttl:int=300):
    key = f'profile:{user_id}'
    await REDIS.set(key, json.dumps(profile), ex=ttl)

async def get_profile_cache(user_id:int) -> Optional[dict]:
    key = f'profile:{user_id}'
    raw = await REDIS.get(key)
    if raw:
        try:
            return json.loads(raw)
        except Exception:
            return None
    return None

async def invalidate_profile_cache(user_id:int):
    key = f'profile:{user_id}'
    await REDIS.delete(key)
