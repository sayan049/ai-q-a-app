# backend/app/services/cache_service.py

import json
import hashlib
import logging
from typing import Optional, Any
import redis.asyncio as redis
from app.config import settings

logger = logging.getLogger(__name__)

_redis_client: Optional[redis.Redis] = None


async def get_redis() -> redis.Redis:
    global _redis_client
    if _redis_client is None:
        _redis_client = redis.from_url(
            settings.redis_url,
            encoding="utf-8",
            decode_responses=True,
        )
    return _redis_client


async def close_redis():
    global _redis_client
    if _redis_client:
        await _redis_client.close()
        _redis_client = None


def make_cache_key(prefix: str, *args) -> str:
    """Create a consistent cache key from prefix and args."""
    combined = ":".join(str(a) for a in args)
    hash_val = hashlib.md5(combined.encode()).hexdigest()
    return f"{prefix}:{hash_val}"


def make_chat_cache_key(file_id: str, query: str) -> str:
    return make_cache_key("chat", file_id, query.lower().strip())


def make_summary_cache_key(file_id: str) -> str:
    return f"summary:{file_id}"


async def cache_get(key: str) -> Optional[Any]:
    """Get a value from Redis cache. Returns None if not found."""
    try:
        client = await get_redis()
        value = await client.get(key)
        if value:
            return json.loads(value)
    except Exception as e:
        logger.warning(f"Cache get failed for key {key}: {e}")
    return None


async def cache_set(key: str, value: Any, ttl: int = 3600) -> bool:
    """Set a value in Redis cache with TTL in seconds."""
    try:
        client = await get_redis()
        serialized = json.dumps(value, default=str)
        await client.setex(key, ttl, serialized)
        return True
    except Exception as e:
        logger.warning(f"Cache set failed for key {key}: {e}")
        return False


async def cache_delete(key: str) -> bool:
    """Delete a key from Redis cache."""
    try:
        client = await get_redis()
        await client.delete(key)
        return True
    except Exception as e:
        logger.warning(f"Cache delete failed for key {key}: {e}")
        return False


async def cache_delete_pattern(pattern: str) -> int:
    """Delete all keys matching a pattern. Returns count deleted."""
    try:
        client = await get_redis()
        keys = await client.keys(pattern)
        if keys:
            return await client.delete(*keys)
    except Exception as e:
        logger.warning(f"Cache delete pattern failed for {pattern}: {e}")
    return 0


async def blacklist_token(jti: str, ttl_seconds: int) -> bool:
    """Blacklist a refresh token by its JTI."""
    try:
        client = await get_redis()
        await client.setex(f"blacklist:{jti}", ttl_seconds, "1")
        return True
    except Exception as e:
        logger.warning(f"Token blacklist failed: {e}")
        return False


async def is_token_blacklisted(jti: str) -> bool:
    """Check if a refresh token JTI is blacklisted."""
    try:
        client = await get_redis()
        result = await client.get(f"blacklist:{jti}")
        return result is not None
    except Exception as e:
        logger.warning(f"Token blacklist check failed: {e}")
        return False