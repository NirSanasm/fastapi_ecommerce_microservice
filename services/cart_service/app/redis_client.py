"""
Redis Client for Cart Service

Handles all Redis operations for shopping cart management with connection pooling
and resilient connection handling.
"""

from typing import Optional, Any
import json
import logging
import redis.asyncio as redis
from redis.asyncio.connection import ConnectionPool

from app.config import settings

logger = logging.getLogger(__name__)


class RedisClient:
    """
    Async Redis client wrapper for cart operations with connection pooling.
    """
    
    def __init__(self):
        self._redis: Optional[redis.Redis] = None
        self._pool: Optional[ConnectionPool] = None
        self._is_connected = False
    
    @property
    def is_connected(self) -> bool:
        return self._is_connected
    
    async def connect(self) -> None:
        """Establish connection to Redis using a connection pool."""
        try:
            self._pool = ConnectionPool.from_url(
                settings.redis_url,
                encoding="utf-8",
                decode_responses=True,
                max_connections=50,
                socket_timeout=5.0,
                socket_connect_timeout=5.0,
                retry_on_timeout=True,
            )
            self._redis = redis.Redis(connection_pool=self._pool)
            # Test connection
            await self._redis.ping()
            self._is_connected = True
            logger.info("Connected to Redis with connection pooling")
        except Exception as e:
            logger.error(f"Failed to connect to Redis: {e}")
            self._is_connected = False
    
    async def close(self) -> None:
        """Close Redis connection and release pool."""
        if self._redis:
            await self._redis.close()
        if self._pool:
            await self._pool.disconnect()
        self._is_connected = False
        logger.info("Redis connection closed")
    
    async def get(self, key: str) -> Optional[str]:
        """Get value by key."""
        if not self._redis:
            return None
        try:
            return await self._redis.get(key)
        except Exception as e:
            logger.error(f"Redis get error for key '{key}': {e}")
            return None
    
    async def set(
        self,
        key: str,
        value: str,
        expire_seconds: Optional[int] = None,
    ) -> bool:
        """Set key-value pair with optional expiration."""
        if not self._redis:
            return False
        try:
            await self._redis.set(key, value, ex=expire_seconds)
            return True
        except Exception as e:
            logger.error(f"Redis set error for key '{key}': {e}")
            return False
    
    async def delete(self, key: str) -> bool:
        """Delete a key."""
        if not self._redis:
            return False
        try:
            await self._redis.delete(key)
            return True
        except Exception as e:
            logger.error(f"Redis delete error for key '{key}': {e}")
            return False
    
    async def exists(self, key: str) -> bool:
        """Check if key exists."""
        if not self._redis:
            return False
        try:
            return (await self._redis.exists(key)) > 0
        except Exception as e:
            logger.error(f"Redis exists error for key '{key}': {e}")
            return False
    
    async def hget(self, name: str, key: str) -> Optional[str]:
        """Get value from hash."""
        if not self._redis:
            return None
        try:
            return await self._redis.hget(name, key)
        except Exception as e:
            logger.error(f"Redis hget error for hash '{name}': {e}")
            return None
    
    async def hset(self, name: str, key: str, value: str) -> bool:
        """Set value in hash."""
        if not self._redis:
            return False
        try:
            await self._redis.hset(name, key, value)
            return True
        except Exception as e:
            logger.error(f"Redis hset error for hash '{name}': {e}")
            return False
    
    async def hgetall(self, name: str) -> dict:
        """Get all key-value pairs from hash."""
        if not self._redis:
            return {}
        try:
            return await self._redis.hgetall(name)
        except Exception as e:
            logger.error(f"Redis hgetall error for hash '{name}': {e}")
            return {}
    
    async def hdel(self, name: str, *keys: str) -> int:
        """Delete keys from hash."""
        if not self._redis:
            return 0
        try:
            return await self._redis.hdel(name, *keys)
        except Exception as e:
            logger.error(f"Redis hdel error for hash '{name}': {e}")
            return 0
    
    async def expire(self, key: str, seconds: int) -> bool:
        """Set expiration on a key."""
        if not self._redis:
            return False
        try:
            return await self._redis.expire(key, seconds)
        except Exception as e:
            logger.error(f"Redis expire error for key '{key}': {e}")
            return False
    
    # Cart-specific helper methods
    
    def _cart_key(self, user_id: str) -> str:
        """Generate cart key for a user or guest."""
        if user_id.startswith("cart:"):
            return user_id
        return f"cart:{user_id}"
    
    async def get_cart(self, user_id: str) -> dict:
        """Get user's or guest's cart."""
        data = await self.get(self._cart_key(user_id))
        if data:
            try:
                return json.loads(data)
            except json.JSONDecodeError:
                logger.error(f"Corrupted cart JSON for user '{user_id}'")
        return {"items": [], "updated_at": None}
    
    async def save_cart(self, user_id: str, cart_data: dict) -> bool:
        """Save user's or guest's cart."""
        return await self.set(
            self._cart_key(user_id),
            json.dumps(cart_data),
            expire_seconds=settings.cart_ttl_seconds,
        )
    
    async def delete_cart(self, user_id: str) -> bool:
        """Delete user's or guest's cart."""
        return await self.delete(self._cart_key(user_id))
    
    async def cart_exists(self, user_id: str) -> bool:
        """Check if cart exists for user or guest."""
        return await self.exists(self._cart_key(user_id))


# Global Redis client instance
redis_client = RedisClient()
