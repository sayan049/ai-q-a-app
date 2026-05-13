# backend/tests/test_chat.py

import pytest
import json
from httpx import AsyncClient
from unittest.mock import patch, AsyncMock, MagicMock
from app.models.file_record import FileRecord, FileStatus, FileType


async def create_ready_file(user_id: str) -> FileRecord:
    """Helper to create a ready file record."""
    file_record = FileRecord(
        id="test-file-id-ready",
        user_id=user_id,
        filename="test_doc.pdf",
        original_filename="test_doc.pdf",
        file_type=FileType.PDF,
        mime_type="application/pdf",
        status=FileStatus.READY,
        size_bytes=1024,
        chunk_count=5,
    )
    await file_record.insert()
    return file_record


@pytest.mark.asyncio
async def test_ask_question_streaming(
    client: AsyncClient,
    test_user,
    auth_headers,
    mock_db,
    mock_vector_search,
):
    """Test that ask endpoint streams SSE response."""
    file_record = await create_ready_file(test_user.id)

    async def mock_stream(query, chunks, history=None):
        for token in ["Hello ", "world!"]:
            yield token

    with patch("app.api.chat.stream_answer", side_effect=mock_stream):
        response = await client.get(
            "/api/v1/chat/ask",
            params={"query": "What is machine learning?", "file_id": file_record.id},
            headers=auth_headers,
        )

    assert response.status_code == 200
    assert "text/event-stream" in response.headers.get("content-type", "")


@pytest.mark.asyncio
async def test_ask_file_not_found(
    client: AsyncClient,
    test_user,
    auth_headers,
    mock_db,
):
    """Test asking question for nonexistent file."""
    response = await client.get(
        "/api/v1/chat/ask",
        params={"query": "What is this?", "file_id": "nonexistent-id"},
        headers=auth_headers,
    )
    assert response.status_code == 404


@pytest.mark.asyncio
async def test_ask_file_still_processing(
    client: AsyncClient,
    test_user,
    auth_headers,
    mock_db,
):
    """Test asking question when file is still processing."""
    processing_file = FileRecord(
        id="processing-file-id",
        user_id=test_user.id,
        filename="processing.pdf",
        original_filename="processing.pdf",
        file_type=FileType.PDF,
        mime_type="application/pdf",
        status=FileStatus.PROCESSING,
        size_bytes=1024,
        chunk_count=0,
    )
    await processing_file.insert()

    response = await client.get(
        "/api/v1/chat/ask",
        params={"query": "What is this?", "file_id": "processing-file-id"},
        headers=auth_headers,
    )
    assert response.status_code == 202  # FileNotReadyError


@pytest.mark.asyncio
async def test_ask_empty_query(
    client: AsyncClient,
    test_user,
    auth_headers,
    mock_db,
):
    """Test asking with empty/whitespace query."""
    response = await client.get(
        "/api/v1/chat/ask",
        params={"query": "   ", "file_id": "some-file-id"},
        headers=auth_headers,
    )
    # FastAPI Query validation: min_length=1 after strip, should fail
    assert response.status_code in (400, 422)


@pytest.mark.asyncio
async def test_get_chat_history_empty(
    client: AsyncClient,
    test_user,
    auth_headers,
    mock_db,
):
    """Test getting empty chat history."""
    file_record = await create_ready_file(test_user.id)

    response = await client.get(
        f"/api/v1/chat/history/{file_record.id}",
        headers=auth_headers,
    )
    assert response.status_code == 200
    data = response.json()
    assert data["messages"] == []
    assert data["total"] == 0


@pytest.mark.asyncio
async def test_chat_unauthorized(client: AsyncClient, mock_db):
    """Test chat endpoints require authentication."""
    response = await client.get(
        "/api/v1/chat/ask",
        params={"query": "test", "file_id": "file-id"},
    )
    assert response.status_code == 401


@pytest.mark.asyncio
async def test_cache_hit(
    client: AsyncClient,
    test_user,
    auth_headers,
    mock_db,
    fake_redis,
):
    """Test that cached responses are returned."""
    file_record = await create_ready_file(test_user.id)

    # Pre-populate cache
    from app.services.cache_service import make_chat_cache_key, cache_set
    query = "What is machine learning?"
    cache_key = make_chat_cache_key(file_record.id, query)

    cached_data = {
        "full_response": "Machine learning is AI.",
        "timestamps": [],
        "sources": [],
        "message_id": "cached-msg-id",
    }
    await cache_set(cache_key, cached_data, ttl=3600)

    response = await client.get(
        "/api/v1/chat/ask",
        params={"query": query, "file_id": file_record.id},
        headers=auth_headers,
    )
    assert response.status_code == 200
    content = response.text
    assert "Machine learning is AI." in content
    assert "cached" in content


@pytest.mark.asyncio
async def test_clear_chat_history(
    client: AsyncClient,
    test_user,
    auth_headers,
    mock_db,
):
    """Test clearing chat history."""
    file_record = await create_ready_file(test_user.id)

    response = await client.delete(
        f"/api/v1/chat/history/{file_record.id}",
        headers=auth_headers,
    )
    assert response.status_code == 200