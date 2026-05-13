# backend/tests/test_cache_service.py

import pytest
from unittest.mock import patch, AsyncMock


@pytest.fixture
def redis_client(fake_redis):
    return fake_redis


@pytest.mark.asyncio
async def test_cache_set_and_get(fake_redis):
    from app.services.cache_service import cache_set, cache_get
    await cache_set("test_key", {"data": "hello"}, ttl=60)
    result = await cache_get("test_key")
    assert result == {"data": "hello"}


@pytest.mark.asyncio
async def test_cache_get_missing(fake_redis):
    from app.services.cache_service import cache_get
    result = await cache_get("nonexistent_key")
    assert result is None


@pytest.mark.asyncio
async def test_cache_delete(fake_redis):
    from app.services.cache_service import cache_set, cache_delete, cache_get
    await cache_set("del_key", {"x": 1}, ttl=60)
    await cache_delete("del_key")
    result = await cache_get("del_key")
    assert result is None


@pytest.mark.asyncio
async def test_cache_set_overwrites(fake_redis):
    from app.services.cache_service import cache_set, cache_get
    await cache_set("over_key", {"v": 1}, ttl=60)
    await cache_set("over_key", {"v": 2}, ttl=60)
    result = await cache_get("over_key")
    assert result == {"v": 2}


@pytest.mark.asyncio
async def test_make_cache_key():
    from app.services.cache_service import make_cache_key
    key1 = make_cache_key("chat", "file1", "query1")
    key2 = make_cache_key("chat", "file1", "query1")
    key3 = make_cache_key("chat", "file1", "query2")
    assert key1 == key2
    assert key1 != key3


@pytest.mark.asyncio
async def test_make_chat_cache_key():
    from app.services.cache_service import make_chat_cache_key
    key1 = make_chat_cache_key("file-id-123", "what is ml?")
    key2 = make_chat_cache_key("file-id-123", "WHAT IS ML?")
    assert key1 == key2


@pytest.mark.asyncio
async def test_make_summary_cache_key():
    from app.services.cache_service import make_summary_cache_key
    key = make_summary_cache_key("file-id-123")
    assert "file-id-123" in key


@pytest.mark.asyncio
async def test_blacklist_token(fake_redis):
    from app.services.cache_service import blacklist_token, is_token_blacklisted
    jti = "test-jti-123"
    await blacklist_token(jti, ttl_seconds=3600)
    result = await is_token_blacklisted(jti)
    assert result is True


@pytest.mark.asyncio
async def test_token_not_blacklisted(fake_redis):
    from app.services.cache_service import is_token_blacklisted
    result = await is_token_blacklisted("unknown-jti")
    assert result is False


@pytest.mark.asyncio
async def test_cache_delete_pattern(fake_redis):
    from app.services.cache_service import cache_set, cache_delete_pattern, cache_get
    await cache_set("chat:file1:q1", {"a": 1}, ttl=60)
    await cache_set("chat:file1:q2", {"a": 2}, ttl=60)
    await cache_set("summary:file1", {"s": 1}, ttl=60)
    await cache_delete_pattern("chat:*")
    assert await cache_get("summary:file1") is not None


@pytest.mark.asyncio
async def test_cache_handles_complex_data(fake_redis):
    from app.services.cache_service import cache_set, cache_get
    data = {
        "full_response": "This is a long response",
        "timestamps": [{"start": 0.0, "end": 5.0, "text": "hello"}],
        "sources": [{"chunk_index": 0, "text_preview": "preview"}],
        "message_id": "msg-123",
    }
    await cache_set("complex_key", data, ttl=60)
    result = await cache_get("complex_key")
    assert result["full_response"] == "This is a long response"
    assert len(result["timestamps"]) == 1