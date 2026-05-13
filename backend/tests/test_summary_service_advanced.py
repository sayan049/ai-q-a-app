# backend/tests/test_summary_service_advanced.py

import pytest
from unittest.mock import patch, AsyncMock, MagicMock


@pytest.mark.asyncio
async def test_summary_caches_result(test_user, mock_db):
    from app.services.summary_service import get_or_create_summary
    from app.services.cache_service import make_summary_cache_key, cache_get
    from app.models.file_record import FileRecord, FileStatus, FileType
    from app.models.file_record import ChunkMetadata

    file_record = FileRecord(
        id="cache-test-sum",
        user_id=test_user.id,
        filename="doc.pdf",
        original_filename="doc.pdf",
        file_type=FileType.PDF,
        mime_type="application/pdf",
        status=FileStatus.READY,
        size_bytes=1024,
        chunk_count=1,
    )
    await file_record.insert()

    chunk = ChunkMetadata(
        file_id="cache-test-sum",
        user_id=test_user.id,
        chunk_index=0,
        text="machine learning artificial intelligence",
        word_count=4,
    )
    await chunk.insert()

    mock_result = {"summary": "Cached test", "key_topics": ["ML"]}

    with patch(
        "app.services.summary_service.llm_service.generate_summary",
        return_value=mock_result,
    ):
        result1 = await get_or_create_summary("cache-test-sum", test_user.id)

    # Second call should hit cache
    result2 = await get_or_create_summary("cache-test-sum", test_user.id)

    assert result1["summary"] == "Cached test"
    assert result2["cached"] is True


@pytest.mark.asyncio
async def test_summary_word_count(test_user, mock_db):
    from app.services.summary_service import get_or_create_summary
    from app.models.file_record import FileRecord, FileStatus, FileType
    from app.models.file_record import ChunkMetadata

    file_record = FileRecord(
        id="word-count-sum",
        user_id=test_user.id,
        filename="doc.pdf",
        original_filename="doc.pdf",
        file_type=FileType.PDF,
        mime_type="application/pdf",
        status=FileStatus.READY,
        size_bytes=1024,
        chunk_count=2,
    )
    await file_record.insert()

    for i in range(2):
        chunk = ChunkMetadata(
            file_id="word-count-sum",
            user_id=test_user.id,
            chunk_index=i,
            text="word " * 10,
            word_count=10,
        )
        await chunk.insert()

    mock_result = {"summary": "Test", "key_topics": []}

    with patch(
        "app.services.summary_service.llm_service.generate_summary",
        return_value=mock_result,
    ):
        result = await get_or_create_summary("word-count-sum", test_user.id)

    assert result["word_count"] == 20


@pytest.mark.asyncio
async def test_summary_audio_file_type(test_user, mock_db):
    from app.services.summary_service import get_or_create_summary
    from app.models.file_record import FileRecord, FileStatus, FileType
    from app.models.file_record import ChunkMetadata

    file_record = FileRecord(
        id="audio-sum-test",
        user_id=test_user.id,
        filename="talk.mp3",
        original_filename="talk.mp3",
        file_type=FileType.AUDIO,
        mime_type="audio/mpeg",
        status=FileStatus.READY,
        size_bytes=2048,
        chunk_count=1,
        duration=60.0,
    )
    await file_record.insert()

    chunk = ChunkMetadata(
        file_id="audio-sum-test",
        user_id=test_user.id,
        chunk_index=0,
        text="hello world test audio content",
        word_count=5,
        start_time=0.0,
        end_time=10.0,
    )
    await chunk.insert()

    mock_result = {"summary": "Audio summary", "key_topics": ["audio"]}

    with patch(
        "app.services.summary_service.llm_service.generate_summary",
        return_value=mock_result,
    ) as mock_gen:
        result = await get_or_create_summary("audio-sum-test", test_user.id)

    # Verify it passes file_type to generate_summary
    mock_gen.assert_called_once()
    call_args = mock_gen.call_args
    assert "audio" in call_args[0][1]
    assert result["summary"] == "Audio summary"