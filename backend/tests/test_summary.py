# backend/tests/test_summary.py

import pytest
from httpx import AsyncClient
from unittest.mock import patch, AsyncMock
from app.models.file_record import FileRecord, FileStatus, FileType
from app.models.file_record import ChunkMetadata


@pytest.mark.asyncio
async def test_get_summary_success(
    client: AsyncClient,
    test_user,
    auth_headers,
    mock_db,
):
    """Test successful summary generation."""
    # Create ready file
    file_record = FileRecord(
        id="summary-test-file",
        user_id=test_user.id,
        filename="summary_test.pdf",
        original_filename="summary_test.pdf",
        file_type=FileType.PDF,
        mime_type="application/pdf",
        status=FileStatus.READY,
        size_bytes=2048,
        chunk_count=3,
    )
    await file_record.insert()

    # Create chunks
    for i in range(3):
        chunk = ChunkMetadata(
            file_id="summary-test-file",
            user_id=test_user.id,
            chunk_index=i,
            text=f"This is chunk {i}. Machine learning is fascinating. AI helps humans.",
            word_count=12,
        )
        await chunk.insert()

    mock_result = {
        "summary": "This document discusses machine learning and AI.",
        "key_topics": ["machine learning", "AI", "technology"],
    }

    with patch("app.services.summary_service.llm_service.generate_summary", return_value=mock_result):
        response = await client.get(
            "/api/v1/summary/summary-test-file",
            headers=auth_headers,
        )

    assert response.status_code == 200
    data = response.json()
    assert "summary" in data
    assert "key_topics" in data
    assert data["file_id"] == "summary-test-file"


@pytest.mark.asyncio
async def test_get_summary_not_found(
    client: AsyncClient,
    test_user,
    auth_headers,
    mock_db,
):
    """Test summary for nonexistent file."""
    response = await client.get(
        "/api/v1/summary/nonexistent-file-id",
        headers=auth_headers,
    )
    assert response.status_code == 404


@pytest.mark.asyncio
async def test_get_summary_cached(
    client: AsyncClient,
    test_user,
    auth_headers,
    mock_db,
):
    """Test that cached summaries are returned."""
    file_record = FileRecord(
        id="cached-summary-file",
        user_id=test_user.id,
        filename="cached.pdf",
        original_filename="cached.pdf",
        file_type=FileType.PDF,
        mime_type="application/pdf",
        status=FileStatus.READY,
        size_bytes=1024,
        chunk_count=1,
    )
    await file_record.insert()

    # Pre-populate cache
    from app.services.cache_service import make_summary_cache_key, cache_set
    cache_key = make_summary_cache_key("cached-summary-file")
    await cache_set(cache_key, {
        "summary": "Cached summary content.",
        "key_topics": ["topic1"],
        "word_count": 100,
        "cached": True,
    }, ttl=3600)

    response = await client.get(
        "/api/v1/summary/cached-summary-file",
        headers=auth_headers,
    )
    assert response.status_code == 200
    data = response.json()
    assert data["cached"] is True
    assert data["summary"] == "Cached summary content."


@pytest.mark.asyncio
async def test_get_summary_unauthorized(client: AsyncClient, mock_db):
    """Test summary requires authentication."""
    response = await client.get("/api/v1/summary/some-file-id")
    assert response.status_code == 401
    
    # Add these to backend/tests/test_summary.py

@pytest.mark.asyncio
async def test_get_summary_file_processing(
    client: AsyncClient,
    test_user,
    auth_headers,
    mock_db,
):
    """Test summary for file still processing returns 400."""
    from app.models.file_record import FileRecord, FileStatus, FileType
    file_record = FileRecord(
        id="processing-summary-file",
        user_id=test_user.id,
        filename="processing.pdf",
        original_filename="processing.pdf",
        file_type=FileType.PDF,
        mime_type="application/pdf",
        status=FileStatus.PROCESSING,
        size_bytes=1024,
        chunk_count=0,
    )
    await file_record.insert()

    response = await client.get(
        "/api/v1/summary/processing-summary-file",
        headers=auth_headers,
    )
    assert response.status_code == 400


@pytest.mark.asyncio
async def test_get_summary_no_chunks(
    client: AsyncClient,
    test_user,
    auth_headers,
    mock_db,
):
    """Test summary with no chunks returns empty summary."""
    from app.models.file_record import FileRecord, FileStatus, FileType
    file_record = FileRecord(
        id="no-chunks-file",
        user_id=test_user.id,
        filename="empty.pdf",
        original_filename="empty.pdf",
        file_type=FileType.PDF,
        mime_type="application/pdf",
        status=FileStatus.READY,
        size_bytes=1024,
        chunk_count=0,
    )
    await file_record.insert()

    response = await client.get(
        "/api/v1/summary/no-chunks-file",
        headers=auth_headers,
    )
    assert response.status_code == 200
    data = response.json()
    assert "No content" in data["summary"]


@pytest.mark.asyncio
async def test_get_summary_wrong_user(
    client: AsyncClient,
    test_user,
    mock_db,
):
    """Test summary access denied for wrong user."""
    from app.models.file_record import FileRecord, FileStatus, FileType
    from app.core.auth import create_access_token

    # Create another user
    from app.models.user import User
    from app.core.auth import hash_password
    other_user = User(
        id="other-user-id",
        email="other@example.com",
        username="otheruser",
        hashed_password=hash_password("OtherPass123"),
        is_active=True,
    )
    await other_user.insert()

    file_record = FileRecord(
        id="other-user-file",
        user_id=other_user.id,
        filename="private.pdf",
        original_filename="private.pdf",
        file_type=FileType.PDF,
        mime_type="application/pdf",
        status=FileStatus.READY,
        size_bytes=1024,
        chunk_count=1,
    )
    await file_record.insert()

    # Try to access with test_user
    other_token = create_access_token(test_user.id, test_user.email)
    response = await client.get(
        "/api/v1/summary/other-user-file",
        headers={"Authorization": f"Bearer {other_token}"},
    )
    assert response.status_code == 403