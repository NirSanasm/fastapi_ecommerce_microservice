"""
Redis Client for Cart Service

Handles all Redis operations for shopping cart management.
"""

from typing import Optional, Any
import json
import redis.asyncio as redis

from app.config import settings


class RedisClient:
    """
    Async Redis client wrapper for cart operations.
    
    TODO: Add connection pooling for production
    TODO: Add retry logic for failed connections
    """
    
    def __init__(self):
        self._redis: Optional[redis.Redis] = None
        self._is_connected = False
    
    @property
    def is_connected(self) -> bool:
        return self._is_connected
    
    async def connect(self) -> None:
        """Establish connection to Redis."""
        try:
            self._redis = redis.Redis.from_url(
                settings.redis_url,
                encoding="utf-8",
                decode_responses=True,
            )
            # Test connection
            await self._redis.ping()
            self._is_connected = True
            print("Connected to Redis")
        except Exception as e:
            print(f"Failed to connect to Redis: {e}")
            self._is_connected = False
    
    async def close(self) -> None:
        """Close Redis connection."""
        if self._redis:
            await self._redis.close()
            self._is_connected = False
    
    async def get(self, key: str) -> Optional[str]:
        """Get value by key."""
        if not self._redis:
            return None
        return await self._redis.get(key)
    
    async def set(
        self,
        key: str,
        value: str,
        expire_seconds: Optional[int] = None,
    ) -> bool:
        """Set key-value pair with optional expiration."""
        if not self._redis:
            return False
        await self._redis.set(key, value, ex=expire_seconds)
        return True
    
    async def delete(self, key: str) -> bool:
        """Delete a key."""
        if not self._redis:
            return False
        await self._redis.delete(key)
        return True
    
    async def exists(self, key: str) -> bool:
        """Check if key exists."""
        if not self._redis:
            return False
        return await self._redis.exists(key) > 0
    
    async def hget(self, name: str, key: str) -> Optional[str]:
        """Get value from hash."""
        if not self._redis:
            return None
        return await self._redis.hget(name, key)
    
    async def hset(self, name: str, key: str, value: str) -> bool:
        """Set value in hash."""
        if not self._redis:
            return False
        await self._redis.hset(name, key, value)
        return True
    
    async def hgetall(self, name: str) -> dict:
        """Get all key-value pairs from hash."""
        if not self._redis:
            return {}
        return await self._redis.hgetall(name)
    
    async def hdel(self, name: str, *keys: str) -> int:
        """Delete keys from hash."""
        if not self._redis:
            return 0
        return await self._redis.hdel(name, *keys)
    
    async def expire(self, key: str, seconds: int) -> bool:
        """Set expiration on a key."""
        if not self._redis:
            return False
        return await self._redis.expire(key, seconds)
    
    # Cart-specific helper methods
    
    def _cart_key(self, user_id: str) -> str:
        """Generate cart key for a user."""
        return f"cart:{user_id}"
    
    async def get_cart(self, user_id: str) -> dict:
        """Get user's cart."""
        data = await self.get(self._cart_key(user_id))
        if data:
            return json.loads(data)
        return {"items": [], "updated_at": None}
    
    async def save_cart(self, user_id: str, cart_data: dict) -> bool:
        """Save user's cart."""
        return await self.set(
            self._cart_key(user_id),
            json.dumps(cart_data),
            expire_seconds=settings.cart_ttl_seconds,
        )
    
    async def delete_cart(self, user_id: str) -> bool:
        """Delete user's cart."""
        return await self.delete(self._cart_key(user_id))
    
    async def cart_exists(self, user_id: str) -> bool:
        """Check if cart exists for user."""
        return await self.exists(self._cart_key(user_id))


# Global Redis client instance
redis_client = RedisClient()
