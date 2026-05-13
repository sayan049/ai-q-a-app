# backend/tests/test_cache_service_advanced.py

import pytest
import json
from unittest.mock import patch, AsyncMock


@pytest.mark.asyncio
async def test_get_redis_returns_client(fake_redis):
    """Test get_redis returns a redis client."""
    from app.services.cache_service import get_redis
    client = await get_redis()
    assert client is not None


@pytest.mark.asyncio
async def test_cache_set_with_complex_types(fake_redis):
    """Test caching with nested data structures."""
    from app.services.cache_service import cache_set, cache_get

    data = {
        "list": [1, 2, 3],
        "nested": {"key": "value"},
        "number": 42.5,
        "boolean": True,
    }
    await cache_set("complex", data, ttl=60)
    result = await cache_get("complex")
    assert result["list"] == [1, 2, 3]
    assert result["nested"]["key"] == "value"
    assert result["number"] == 42.5
    assert result["boolean"] is True


@pytest.mark.asyncio
async def test_cache_get_returns_none_on_error():
    """Test cache_get returns None when Redis fails."""
    from app.services.cache_service import cache_get

    mock_redis = AsyncMock()
    mock_redis.get.side_effect = Exception("Redis connection failed")

    with patch("app.services.cache_service.get_redis", return_value=mock_redis):
        result = await cache_get("any_key")
    assert result is None


@pytest.mark.asyncio
async def test_cache_set_returns_false_on_error():
    """Test cache_set returns False when Redis fails."""
    from app.services.cache_service import cache_set

    mock_redis = AsyncMock()
    mock_redis.setex.side_effect = Exception("Redis connection failed")

    with patch("app.services.cache_service.get_redis", return_value=mock_redis):
        result = await cache_set("any_key", {"data": "value"}, ttl=60)
    assert result is False


@pytest.mark.asyncio
async def test_cache_delete_returns_false_on_error():
    """Test cache_delete returns False when Redis fails."""
    from app.services.cache_service import cache_delete

    mock_redis = AsyncMock()
    mock_redis.delete.side_effect = Exception("Redis error")

    with patch("app.services.cache_service.get_redis", return_value=mock_redis):
        result = await cache_delete("any_key")
    assert result is False


@pytest.mark.asyncio
async def test_blacklist_token_returns_false_on_error():
    """Test blacklist_token returns False when Redis fails."""
    from app.services.cache_service import blacklist_token

    mock_redis = AsyncMock()
    mock_redis.setex.side_effect = Exception("Redis error")

    with patch("app.services.cache_service.get_redis", return_value=mock_redis):
        result = await blacklist_token("jti-123", 3600)
    assert result is False


@pytest.mark.asyncio
async def test_is_token_blacklisted_returns_false_on_error():
    """Test is_token_blacklisted returns False when Redis fails."""
    from app.services.cache_service import is_token_blacklisted

    mock_redis = AsyncMock()
    mock_redis.get.side_effect = Exception("Redis error")

    with patch("app.services.cache_service.get_redis", return_value=mock_redis):
        result = await is_token_blacklisted("jti-123")
    assert result is False


@pytest.mark.asyncio
async def test_cache_delete_pattern_returns_zero_on_error():
    """Test cache_delete_pattern returns 0 when Redis fails."""
    from app.services.cache_service import cache_delete_pattern

    mock_redis = AsyncMock()
    mock_redis.keys.side_effect = Exception("Redis error")

    with patch("app.services.cache_service.get_redis", return_value=mock_redis):
        result = await cache_delete_pattern("chat:*")
    assert result == 0


@pytest.mark.asyncio
async def test_close_redis(fake_redis):
    """Test close_redis clears the client."""
    from app.services import cache_service

    cache_service._redis_client = fake_redis
    await cache_service.close_redis()
    assert cache_service._redis_client is None


@pytest.mark.asyncio
async def test_make_cache_key_consistent():
    """Same inputs always produce same key."""
    from app.services.cache_service import make_cache_key
    k1 = make_cache_key("prefix", "a", "b", "c")
    k2 = make_cache_key("prefix", "a", "b", "c")
    k3 = make_cache_key("prefix", "a", "b", "d")
    assert k1 == k2
    assert k1 != k3
    assert k1.startswith("prefix:")
    
    
@pytest.mark.asyncio
async def test_cache_get_parses_json(fake_redis):
    """Test cache correctly deserializes stored JSON."""
    from app.services.cache_service import cache_set, cache_get

    original = {"key": "value", "num": 42, "lst": [1, 2, 3]}
    await cache_set("json_test", original, ttl=60)
    result = await cache_get("json_test")
    assert result == original


@pytest.mark.asyncio
async def test_cache_delete_nonexistent(fake_redis):
    """Test deleting nonexistent key doesn't raise."""
    from app.services.cache_service import cache_delete
    result = await cache_delete("nonexistent_key_xyz")
    assert result is True


@pytest.mark.asyncio
async def test_multiple_blacklisted_tokens(fake_redis):
    """Test multiple tokens can be blacklisted."""
    from app.services.cache_service import blacklist_token, is_token_blacklisted

    for i in range(5):
        await blacklist_token(f"jti-{i}", ttl_seconds=3600)

    for i in range(5):
        assert await is_token_blacklisted(f"jti-{i}") is True

    assert await is_token_blacklisted("jti-999") is False