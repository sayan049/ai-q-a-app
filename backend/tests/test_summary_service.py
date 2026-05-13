# backend/tests/test_summary_service.py

import pytest
from unittest.mock import patch, AsyncMock, MagicMock


@pytest.mark.asyncio
async def test_get_or_create_summary_success(test_user, mock_db):
    from app.services.summary_service import get_or_create_summary
    from app.models.file_record import FileRecord, FileStatus, FileType, ChunkMetadata

    file_record = FileRecord(
        id="sum-svc-file",
        user_id=test_user.id,
        filename="test.pdf",
        original_filename="test.pdf",
        file_type=FileType.PDF,
        mime_type="application/pdf",
        status=FileStatus.READY,
        size_bytes=1024,
        chunk_count=2,
    )
    await file_record.insert()

    for i in range(2):
        chunk = ChunkMetadata(
            file_id="sum-svc-file",
            user_id=test_user.id,
            chunk_index=i,
            text=f"chunk {i} machine learning artificial intelligence",
            word_count=6,
        )
        await chunk.insert()

    mock_result = {
        "summary": "This is a test summary.",
        "key_topics": ["machine learning", "AI"],
    }

    with patch(
        "app.services.summary_service.llm_service.generate_summary",
        return_value=mock_result,
    ):
        result = await get_or_create_summary("sum-svc-file", test_user.id)

    assert result["summary"] == "This is a test summary."
    assert "machine learning" in result["key_topics"]
    assert result["cached"] is False


@pytest.mark.asyncio
async def test_get_or_create_summary_cached(test_user, mock_db):
    from app.services.summary_service import get_or_create_summary
    from app.services.cache_service import make_summary_cache_key, cache_set
    from app.models.file_record import FileRecord, FileStatus, FileType

    file_record = FileRecord(
        id="cached-svc-file",
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

    cache_key = make_summary_cache_key("cached-svc-file")
    await cache_set(cache_key, {
        "summary": "Cached summary",
        "key_topics": ["cached topic"],
        "word_count": 50,
        "cached": True,
    }, ttl=3600)

    result = await get_or_create_summary("cached-svc-file", test_user.id)

    assert result["summary"] == "Cached summary"
    assert result["cached"] is True


@pytest.mark.asyncio
async def test_get_or_create_summary_file_not_found(test_user, mock_db):
    from app.services.summary_service import get_or_create_summary

    with pytest.raises(ValueError, match="not found"):
        await get_or_create_summary("nonexistent-file", test_user.id)


@pytest.mark.asyncio
async def test_get_or_create_summary_not_ready(test_user, mock_db):
    from app.services.summary_service import get_or_create_summary
    from app.models.file_record import FileRecord, FileStatus, FileType

    file_record = FileRecord(
        id="processing-svc-file",
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

    with pytest.raises(ValueError, match="not ready"):
        await get_or_create_summary("processing-svc-file", test_user.id)


@pytest.mark.asyncio
async def test_get_or_create_summary_no_chunks(test_user, mock_db):
    from app.services.summary_service import get_or_create_summary
    from app.models.file_record import FileRecord, FileStatus, FileType

    file_record = FileRecord(
        id="empty-chunks-svc",
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

    result = await get_or_create_summary("empty-chunks-svc", test_user.id)
    assert "No content" in result["summary"]
    assert result["word_count"] == 0