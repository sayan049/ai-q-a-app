# backend/tests/test_file_processor.py

import pytest
from unittest.mock import patch, AsyncMock, MagicMock
from datetime import datetime


@pytest.fixture
async def file_record(test_user, mock_db):
    from app.models.file_record import FileRecord, FileStatus, FileType
    record = FileRecord(
        id="proc-file-id",
        user_id=test_user.id,
        filename="test.pdf",
        original_filename="test.pdf",
        file_type=FileType.PDF,
        mime_type="application/pdf",
        status=FileStatus.UPLOADING,
        size_bytes=1024,
    )
    await record.insert()
    return record


@pytest.fixture
async def audio_file_record(test_user, mock_db):
    from app.models.file_record import FileRecord, FileStatus, FileType
    record = FileRecord(
        id="proc-audio-id",
        user_id=test_user.id,
        filename="test.mp3",
        original_filename="test.mp3",
        file_type=FileType.AUDIO,
        mime_type="audio/mpeg",
        status=FileStatus.UPLOADING,
        size_bytes=2048,
    )
    await record.insert()
    return record


@pytest.mark.asyncio
async def test_process_pdf_file(file_record, test_user, mock_db, tmp_path):
    from app.services.file_processor import process_file
    from app.models.file_record import FileRecord, FileStatus, FileType

    pdf_path = str(tmp_path / "test.pdf")
    with open(pdf_path, "wb") as f:
        f.write(b"fake pdf")

    mock_pages = [{"page_num": 1, "text": "Machine learning content here for testing", "word_count": 7}]
    mock_full_text = "Machine learning content here for testing"

    with patch("app.services.file_processor.get_pdf_metadata", return_value={"page_count": 1}):
        with patch("app.services.file_processor.extract_text_from_pdf", return_value=(mock_pages, mock_full_text)):
            with patch("app.services.file_processor.vector_service") as mock_vs:
                mock_vs.add_chunks.return_value = 1
                await process_file(
                    file_id=file_record.id,
                    file_path=pdf_path,
                    file_type=FileType.PDF,
                    user_id=test_user.id,
                )

    updated = await FileRecord.find_one(FileRecord.id == file_record.id)
    assert updated.status == FileStatus.READY
    assert updated.chunk_count >= 1


@pytest.mark.asyncio
async def test_process_audio_file(audio_file_record, test_user, mock_db, tmp_path):
    from app.services.file_processor import process_file
    from app.models.file_record import FileRecord, FileStatus, FileType

    audio_path = str(tmp_path / "test.mp3")
    with open(audio_path, "wb") as f:
        f.write(b"fake audio")

    mock_segments = [
        {"text": "Hello world machine learning", "start": 0.0, "end": 5.0},
        {"text": "Deep learning neural networks python", "start": 5.0, "end": 10.0},
        {"text": "Real world applications artificial intelligence", "start": 10.0, "end": 15.0},
    ]

    with patch("app.services.file_processor.transcribe", return_value=(mock_segments, "full text")):
        with patch("app.services.file_processor.vector_service") as mock_vs:
            mock_vs.add_chunks.return_value = 3
            await process_file(
                file_id=audio_file_record.id,
                file_path=audio_path,
                file_type=FileType.AUDIO,
                user_id=test_user.id,
            )

    updated = await FileRecord.find_one(FileRecord.id == audio_file_record.id)
    assert updated.status == FileStatus.READY
    assert updated.duration == 15.0


@pytest.mark.asyncio
async def test_process_file_no_segments(audio_file_record, test_user, mock_db, tmp_path):
    from app.services.file_processor import process_file
    from app.models.file_record import FileRecord, FileStatus, FileType

    audio_path = str(tmp_path / "silence.mp3")
    with open(audio_path, "wb") as f:
        f.write(b"silence")

    with patch("app.services.file_processor.transcribe", return_value=([], "")):
        await process_file(
            file_id=audio_file_record.id,
            file_path=audio_path,
            file_type=FileType.AUDIO,
            user_id=test_user.id,
        )

    updated = await FileRecord.find_one(FileRecord.id == audio_file_record.id)
    assert updated.status == FileStatus.READY
    assert updated.chunk_count == 0


@pytest.mark.asyncio
async def test_process_file_not_found(test_user, mock_db, tmp_path):
    from app.services.file_processor import process_file
    from app.models.file_record import FileType

    # Should not raise — just log error
    await process_file(
        file_id="nonexistent-id",
        file_path=str(tmp_path / "fake.pdf"),
        file_type=FileType.PDF,
        user_id=test_user.id,
    )


@pytest.mark.asyncio
async def test_process_pdf_extraction_fails(file_record, test_user, mock_db, tmp_path):
    from app.services.file_processor import process_file
    from app.models.file_record import FileRecord, FileStatus, FileType

    pdf_path = str(tmp_path / "bad.pdf")
    with open(pdf_path, "wb") as f:
        f.write(b"not a pdf")

    with patch("app.services.file_processor.get_pdf_metadata", return_value={"page_count": 0}):
        with patch("app.services.file_processor.extract_text_from_pdf",
                   side_effect=ValueError("Cannot open PDF")):
            await process_file(
                file_id=file_record.id,
                file_path=pdf_path,
                file_type=FileType.PDF,
                user_id=test_user.id,
            )

    updated = await FileRecord.find_one(FileRecord.id == file_record.id)
    assert updated.status == FileStatus.FAILED
    assert "Cannot open PDF" in updated.error_message