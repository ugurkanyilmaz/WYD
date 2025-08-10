"""
High-Performance Cache Manager
Handles caching with Redis for scalability and performance
"""
import json
import pickle
from typing import Any, Optional, List, Dict
from datetime import datetime, timedelta
import hashlib
from .core import REDIS
import logging

logger = logging.getLogger(__name__)

class CacheManager:
    """
    High-performance cache manager using Redis
    Supports complex caching strategies for scalability
    """
    
    def __init__(self):
        self.default_ttl = 3600  # 1 hour default TTL
        
    def _make_key(self, key: str, prefix: str = "") -> str:
        """Generate cache key with prefix"""
        if prefix:
            return f"{prefix}:{key}"
        return key
        
    async def set(self, key: str, value: Any, ttl: int = None, prefix: str = "") -> bool:
        """Set cache value with TTL"""
        if not REDIS:
            return False
            
        cache_key = self._make_key(key, prefix)
        ttl = ttl or self.default_ttl
        
        try:
            # Serialize complex objects
            if isinstance(value, (dict, list)):
                value = json.dumps(value)
            elif not isinstance(value, (str, int, float, bytes)):
                value = pickle.dumps(value)
                
            await REDIS.setex(cache_key, ttl, value)
            return True
        except Exception as e:
            logger.error(f"Cache set failed for key {cache_key}: {str(e)}")
            return False
    
    async def get(self, key: str, prefix: str = "") -> Optional[Any]:
        """Get cache value"""
        if not REDIS:
            return None
            
        cache_key = self._make_key(key, prefix)
        
        try:
            value = await REDIS.get(cache_key)
            if value is None:
                return None
                
            # Try to deserialize JSON first
            try:
                return json.loads(value)
            except (json.JSONDecodeError, TypeError):
                pass
                
            # Try to deserialize pickle
            try:
                return pickle.loads(value)
            except:
                pass
                
            # Return as string
            return value.decode() if isinstance(value, bytes) else value
            
        except Exception as e:
            logger.error(f"Cache get failed for key {cache_key}: {str(e)}")
            return None
    
    async def delete(self, key: str, prefix: str = "") -> bool:
        """Delete cache key"""
        if not REDIS:
            return False
            
        cache_key = self._make_key(key, prefix)
        
        try:
            result = await REDIS.delete(cache_key)
            return result > 0
        except Exception as e:
            logger.error(f"Cache delete failed for key {cache_key}: {str(e)}")
            return False
    
    async def exists(self, key: str, prefix: str = "") -> bool:
        """Check if cache key exists"""
        if not REDIS:
            return False
            
        cache_key = self._make_key(key, prefix)
        
        try:
            result = await REDIS.exists(cache_key)
            return result > 0
        except Exception as e:
            logger.error(f"Cache exists check failed for key {cache_key}: {str(e)}")
            return False
    
    async def increment(self, key: str, amount: int = 1, prefix: str = "") -> Optional[int]:
        """Increment cache value atomically"""
        if not REDIS:
            return None
            
        cache_key = self._make_key(key, prefix)
        
        try:
            return await REDIS.incrby(cache_key, amount)
        except Exception as e:
            logger.error(f"Cache increment failed for key {cache_key}: {str(e)}")
            return None
    
    async def set_list(self, key: str, values: List[Any], ttl: int = None, prefix: str = "") -> bool:
        """Set list in cache"""
        if not REDIS:
            return False
            
        cache_key = self._make_key(key, prefix)
        ttl = ttl or self.default_ttl
        
        try:
            # Clear existing list
            await REDIS.delete(cache_key)
            
            # Add all values
            for value in values:
                if isinstance(value, (dict, list)):
                    value = json.dumps(value)
                await REDIS.lpush(cache_key, value)
                
            # Set TTL
            await REDIS.expire(cache_key, ttl)
            return True
        except Exception as e:
            logger.error(f"Cache set_list failed for key {cache_key}: {str(e)}")
            return False
    
    async def get_list(self, key: str, prefix: str = "") -> List[Any]:
        """Get list from cache"""
        if not REDIS:
            return []
            
        cache_key = self._make_key(key, prefix)
        
        try:
            values = await REDIS.lrange(cache_key, 0, -1)
            result = []
            
            for value in values:
                try:
                    # Try JSON first
                    result.append(json.loads(value))
                except:
                    # Keep as string
                    result.append(value.decode() if isinstance(value, bytes) else value)
                    
            return result
        except Exception as e:
            logger.error(f"Cache get_list failed for key {cache_key}: {str(e)}")
            return []
    
    async def set_hash(self, key: str, data: Dict[str, Any], ttl: int = None, prefix: str = "") -> bool:
        """Set hash in cache"""
        if not REDIS:
            return False
            
        cache_key = self._make_key(key, prefix)
        ttl = ttl or self.default_ttl
        
        try:
            # Convert values to strings
            hash_data = {}
            for k, v in data.items():
                if isinstance(v, (dict, list)):
                    hash_data[k] = json.dumps(v)
                else:
                    hash_data[k] = str(v)
                    
            await REDIS.hmset(cache_key, hash_data)
            await REDIS.expire(cache_key, ttl)
            return True
        except Exception as e:
            logger.error(f"Cache set_hash failed for key {cache_key}: {str(e)}")
            return False
    
    async def get_hash(self, key: str, prefix: str = "") -> Dict[str, Any]:
        """Get hash from cache"""
        if not REDIS:
            return {}
            
        cache_key = self._make_key(key, prefix)
        
        try:
            data = await REDIS.hgetall(cache_key)
            result = {}
            
            for k, v in data.items():
                k = k.decode() if isinstance(k, bytes) else k
                v = v.decode() if isinstance(v, bytes) else v
                
                try:
                    # Try JSON first
                    result[k] = json.loads(v)
                except:
                    # Keep as string
                    result[k] = v
                    
            return result
        except Exception as e:
            logger.error(f"Cache get_hash failed for key {cache_key}: {str(e)}")
            return {}

# Global cache manager instance
cache = CacheManager()

# User-specific cache functions
async def cache_user_data(user_id: int, user_data: Dict, ttl: int = 1800):
    """Cache user data for 30 minutes"""
    return await cache.set(str(user_id), user_data, ttl, "user")

async def get_cached_user_data(user_id: int) -> Optional[Dict]:
    """Get cached user data"""
    return await cache.get(str(user_id), "user")

async def invalidate_user_cache(user_id: int):
    """Invalidate user cache"""
    await cache.delete(str(user_id), "user")

# Friends cache functions
async def cache_user_friends(user_id: int, friends_list: List[Dict], ttl: int = 600):
    """Cache user friends list for 10 minutes"""
    return await cache.set_list(f"friends:{user_id}", friends_list, ttl)

async def get_cached_user_friends(user_id: int) -> List[Dict]:
    """Get cached friends list"""
    return await cache.get_list(f"friends:{user_id}")

async def invalidate_friends_cache(user_id: int):
    """Invalidate friends cache"""
    await cache.delete(f"friends:{user_id}")

# Messages cache functions
async def cache_conversation(user1_id: int, user2_id: int, messages: List[Dict], ttl: int = 300):
    """Cache conversation for 5 minutes"""
    # Create consistent conversation key
    conv_key = f"conv:{min(user1_id, user2_id)}:{max(user1_id, user2_id)}"
    return await cache.set_list(conv_key, messages, ttl)

async def get_cached_conversation(user1_id: int, user2_id: int) -> List[Dict]:
    """Get cached conversation"""
    conv_key = f"conv:{min(user1_id, user2_id)}:{max(user1_id, user2_id)}"
    return await cache.get_list(conv_key)

async def invalidate_conversation_cache(user1_id: int, user2_id: int):
    """Invalidate conversation cache"""
    conv_key = f"conv:{min(user1_id, user2_id)}:{max(user1_id, user2_id)}"
    await cache.delete(conv_key)

# Session management functions
async def set_session(session_token: str, user_data: Dict, ttl: int = 7200):
    """Cache session data"""
    await cache.set(session_token, user_data, ttl, "session")

async def get_session(session_token: str) -> Optional[Dict]:
    """Get cached session data"""
    return await cache.get(session_token, "session")

async def invalidate_session(session_token: str):
    """Remove session from cache"""
    await cache.delete(session_token, "session")

# Message/Conversation caching functions
async def cache_conversation(conversation_key: str, messages: List[Dict], ttl: int = 300):
    """Cache conversation messages"""
    await cache.set_list(conversation_key, messages, ttl, "conversation")

async def get_cached_conversation(conversation_key: str) -> List[Dict]:
    """Get cached conversation"""
    return await cache.get_list(conversation_key, "conversation")

async def invalidate_conversation(conversation_key: str):
    """Remove conversation from cache"""
    await cache.delete(conversation_key, "conversation")

async def cache_message_data(message_id: int, message_data: Dict, ttl: int = 1800):
    """Cache individual message data"""
    await cache.set(f"message:{message_id}", message_data, ttl, "message")

async def get_cached_message(message_id: int) -> Optional[Dict]:
    """Get cached message data"""
    return await cache.get(f"message:{message_id}", "message")

# Rate limiting functions
async def check_rate_limit(user_id: int, action: str, limit: int = 100, window: int = 3600) -> bool:
    """Check if user is within rate limit"""
    key = f"rate_limit:{user_id}:{action}"
    
    current = await cache.get(key, "rate")
    if current is None:
        await cache.set(key, 1, window, "rate")
        return True
        
    if int(current) >= limit:
        return False
        
    await cache.increment(key, 1, "rate")
    return True

# Legacy functions for backwards compatibility
async def set_profile_cache(user_id: int, profile: dict, ttl: int = 300):
    """Legacy profile cache function"""
    return await cache_user_data(user_id, profile, ttl)

async def get_profile_cache(user_id: int) -> Optional[dict]:
    """Legacy profile cache function"""
    return await get_cached_user_data(user_id)

async def invalidate_profile_cache(user_id: int):
    """Legacy profile cache function"""
    await invalidate_user_cache(user_id)
