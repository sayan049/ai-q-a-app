# backend/tests/test_final_boost.py

import pytest
import json
from unittest.mock import patch, MagicMock, AsyncMock


# ── summary_service.py lines 20-69 ───────────────────────────────────────────

@pytest.mark.asyncio
async def test_summary_service_direct_call(test_user, mock_db, fake_redis):
    from app.services import summary_service, cache_service
    from app.models.file_record import FileRecord, FileStatus, FileType, ChunkMetadata

    cache_service._redis_client = fake_redis
    file_id = "direct-sum-test"

    await FileRecord(
        id=file_id, user_id=test_user.id, filename="direct.pdf",
        original_filename="direct.pdf", file_type=FileType.PDF,
        mime_type="application/pdf", status=FileStatus.READY,
        size_bytes=1024, chunk_count=3,
    ).insert()

    for i in range(3):
        await ChunkMetadata(
            file_id=file_id, user_id=test_user.id, chunk_index=i,
            text=f"chunk {i} machine learning deep learning python",
            word_count=7,
        ).insert()

    with patch(
        "app.services.summary_service.llm_service.generate_summary",
        return_value={"summary": "Direct summary", "key_topics": ["ML"]},
    ):
        result = await summary_service.get_or_create_summary(file_id, test_user.id)
        assert result["summary"] == "Direct summary"
        assert result["cached"] is False
        assert result["word_count"] == 21

    # Second call — cache hit (lines 20-23)
    result2 = await summary_service.get_or_create_summary(file_id, test_user.id)
    assert result2["cached"] is True
    assert result2["summary"] == "Direct summary"


@pytest.mark.asyncio
async def test_summary_service_not_found_direct(test_user, mock_db, fake_redis):
    from app.services import summary_service, cache_service
    cache_service._redis_client = fake_redis
    with pytest.raises(ValueError, match="not found"):
        await summary_service.get_or_create_summary("ghost-file-id", test_user.id)


@pytest.mark.asyncio
async def test_summary_service_not_ready_direct(test_user, mock_db, fake_redis):
    from app.services import summary_service, cache_service
    from app.models.file_record import FileRecord, FileStatus, FileType

    cache_service._redis_client = fake_redis
    await FileRecord(
        id="not-ready-direct", user_id=test_user.id, filename="nr.pdf",
        original_filename="nr.pdf", file_type=FileType.PDF,
        mime_type="application/pdf", status=FileStatus.PROCESSING,
        size_bytes=512, chunk_count=0,
    ).insert()

    with pytest.raises(ValueError, match="not ready"):
        await summary_service.get_or_create_summary("not-ready-direct", test_user.id)


@pytest.mark.asyncio
async def test_summary_service_no_chunks_direct(test_user, mock_db, fake_redis):
    from app.services import summary_service, cache_service
    from app.models.file_record import FileRecord, FileStatus, FileType

    cache_service._redis_client = fake_redis
    await FileRecord(
        id="no-chunks-direct", user_id=test_user.id, filename="nc.pdf",
        original_filename="nc.pdf", file_type=FileType.PDF,
        mime_type="application/pdf", status=FileStatus.READY,
        size_bytes=512, chunk_count=0,
    ).insert()

    result = await summary_service.get_or_create_summary("no-chunks-direct", test_user.id)
    assert "No content" in result["summary"]
    assert result["word_count"] == 0
    assert result["cached"] is False


@pytest.mark.asyncio
async def test_summary_service_audio_type(test_user, mock_db, fake_redis):
    from app.services import summary_service, cache_service
    from app.models.file_record import FileRecord, FileStatus, FileType, ChunkMetadata

    cache_service._redis_client = fake_redis
    file_id = "audio-type-direct"

    await FileRecord(
        id=file_id, user_id=test_user.id, filename="audio.mp3",
        original_filename="audio.mp3", file_type=FileType.AUDIO,
        mime_type="audio/mpeg", status=FileStatus.READY,
        size_bytes=2048, chunk_count=1, duration=30.0,
    ).insert()

    await ChunkMetadata(
        file_id=file_id, user_id=test_user.id, chunk_index=0,
        text="audio content machine learning", word_count=4,
        start_time=0.0, end_time=10.0,
    ).insert()

    with patch(
        "app.services.summary_service.llm_service.generate_summary",
        return_value={"summary": "Audio sum", "key_topics": ["audio"]},
    ) as mock_gen:
        result = await summary_service.get_or_create_summary(file_id, test_user.id)

    assert result["summary"] == "Audio sum"
    assert mock_gen.call_args[0][1] == "audio"


@pytest.mark.asyncio
async def test_summary_video_file(test_user, mock_db, fake_redis):
    from app.services import summary_service, cache_service
    from app.models.file_record import FileRecord, FileStatus, FileType, ChunkMetadata

    cache_service._redis_client = fake_redis
    file_id = "boost-video-sum"

    await FileRecord(
        id=file_id, user_id=test_user.id, filename="talk.mp4",
        original_filename="talk.mp4", file_type=FileType.VIDEO,
        mime_type="video/mp4", status=FileStatus.READY,
        size_bytes=4096, chunk_count=2, duration=120.0,
    ).insert()

    for i in range(2):
        await ChunkMetadata(
            file_id=file_id, user_id=test_user.id, chunk_index=i,
            text=f"Video chunk {i} content about deep learning",
            word_count=7, start_time=float(i*30), end_time=float((i+1)*30),
        ).insert()

    with patch(
        "app.services.summary_service.llm_service.generate_summary",
        return_value={"summary": "Video summary", "key_topics": ["deep learning"]},
    ) as mock_gen:
        result = await summary_service.get_or_create_summary(file_id, test_user.id)

    assert result["summary"] == "Video summary"
    assert "video" in mock_gen.call_args[0][1]


# ── cache_service.py lines 53-54, 66, 77, 88-89, 100, 111 ───────────────────

@pytest.mark.asyncio
async def test_cache_service_all_return_paths(fake_redis):
    from app.services import cache_service
    cache_service._redis_client = fake_redis

    # lines 53-54: cache_get returns parsed json
    await fake_redis.set("direct:key", '{"val": 99}')
    result = await cache_service.cache_get("direct:key")
    assert result == {"val": 99}

    # line 66: cache_set returns True
    ok = await cache_service.cache_set("new:key", {"x": 1}, ttl=60)
    assert ok is True

    # line 77: cache_delete returns True
    ok = await cache_service.cache_delete("new:key")
    assert ok is True

    # lines 88-89: cache_delete_pattern returns count
    await cache_service.cache_set("pat:a", {"a": 1}, ttl=60)
    await cache_service.cache_set("pat:b", {"b": 2}, ttl=60)
    deleted = await cache_service.cache_delete_pattern("pat:*")
    assert deleted >= 2

    # line 100: blacklist_token returns True
    ok = await cache_service.blacklist_token("jti-xyz", 3600)
    assert ok is True

    # line 111: is_token_blacklisted returns True/False
    assert await cache_service.is_token_blacklisted("jti-xyz") is True
    assert await cache_service.is_token_blacklisted("unknown") is False


@pytest.mark.asyncio
async def test_get_redis_singleton(fake_redis):
    from app.services import cache_service
    cache_service._redis_client = None

    with patch("redis.asyncio.from_url") as mock_from_url:
        mock_from_url.return_value = fake_redis
        c1 = await cache_service.get_redis()
        c2 = await cache_service.get_redis()
        assert c1 is c2
        mock_from_url.assert_called_once()

    cache_service._redis_client = None


@pytest.mark.asyncio
async def test_cache_delete_pattern_with_keys(fake_redis):
    from app.services.cache_service import cache_set, cache_delete_pattern, cache_get
    await cache_set("prefix:key1", {"a": 1}, ttl=60)
    await cache_set("prefix:key2", {"b": 2}, ttl=60)
    await cache_set("other:key3", {"c": 3}, ttl=60)
    deleted = await cache_delete_pattern("prefix:*")
    assert deleted >= 2
    assert await cache_get("other:key3") is not None


# ── vector_service.py lines 144-146, 169, 181, 206-207 ──────────────────────

def test_add_chunks_saves_metadata_correctly(tmp_path):
    import numpy as np
    from app.services.vector_service import VectorService

    service = VectorService()
    service.index_dir = str(tmp_path)

    def mock_embed(texts):
        n = len(texts)
        emb = np.random.rand(n, 384).astype(np.float32)
        return emb / np.linalg.norm(emb, axis=1, keepdims=True)

    chunks = [
        {"chunk_index": 0, "text": "first chunk", "start_time": 0.0, "end_time": 10.0, "word_count": 2},
        {"chunk_index": 1, "text": "second chunk", "page_num": 2, "word_count": 2},
    ]

    with patch.object(service, "embed", side_effect=mock_embed):
        count = service.add_chunks("meta-test", chunks)

    assert count == 2
    meta_path = tmp_path / "meta-test_meta.json"
    with open(meta_path) as f:
        meta = json.load(f)
    assert meta[0]["start_time"] == 0.0
    assert meta[1]["page_num"] == 2


def test_search_returns_empty_for_empty_index(tmp_path):
    import numpy as np
    import faiss
    from app.services.vector_service import VectorService

    service = VectorService()
    service.index_dir = str(tmp_path)

    index = faiss.IndexFlatIP(384)
    faiss.write_index(index, str(tmp_path / "empty-meta.index"))
    (tmp_path / "empty-meta_meta.json").write_text("[]")

    def mock_embed(texts):
        n = len(texts)
        emb = np.random.rand(n, 384).astype(np.float32)
        return emb / np.linalg.norm(emb, axis=1, keepdims=True)

    with patch.object(service, "embed", side_effect=mock_embed):
        results = service.search("empty-meta", "query", top_k=5)
    assert results == []


def test_delete_only_meta_file(tmp_path):
    from app.services.vector_service import VectorService
    service = VectorService()
    service.index_dir = str(tmp_path)
    (tmp_path / "only-meta_meta.json").write_text("[]")
    result = service.delete_index("only-meta")
    assert result is True
    assert not (tmp_path / "only-meta_meta.json").exists()


# ── file_processor.py lines 87, 90, 131-132 ──────────────────────────────────

@pytest.mark.asyncio
async def test_process_video_file(test_user, mock_db, tmp_path):
    from app.services.file_processor import process_file
    from app.models.file_record import FileRecord, FileStatus, FileType

    await FileRecord(
        id="video-proc-id", user_id=test_user.id, filename="video.mp4",
        original_filename="video.mp4", file_type=FileType.VIDEO,
        mime_type="video/mp4", status=FileStatus.UPLOADING, size_bytes=4096,
    ).insert()

    video_path = str(tmp_path / "video.mp4")
    with open(video_path, "wb") as f:
        f.write(b"fake video")

    segments = [
        {"text": "hello world machine", "start": 0.0, "end": 5.0},
        {"text": "learning deep neural", "start": 5.0, "end": 10.0},
        {"text": "networks python code", "start": 10.0, "end": 15.0},
    ]

    with patch("app.services.file_processor.transcribe", return_value=(segments, "full")):
        with patch("app.services.file_processor.vector_service") as mock_vs:
            mock_vs.add_chunks.return_value = 3
            await process_file("video-proc-id", video_path, FileType.VIDEO, test_user.id)

    updated = await FileRecord.find_one(FileRecord.id == "video-proc-id")
    assert updated.status == FileStatus.READY


@pytest.mark.asyncio
async def test_process_file_extraction_fails(test_user, mock_db, tmp_path):
    from app.services.file_processor import process_file
    from app.models.file_record import FileRecord, FileStatus, FileType

    await FileRecord(
        id="save-error-id", user_id=test_user.id, filename="err.pdf",
        original_filename="err.pdf", file_type=FileType.PDF,
        mime_type="application/pdf", status=FileStatus.UPLOADING, size_bytes=512,
    ).insert()

    # Create the actual file so _get_local_file_path passes
    err_path = tmp_path / "err.pdf"
    err_path.write_bytes(b"fake pdf content")

    with patch("app.services.file_processor.get_pdf_metadata", return_value={"page_count": 1}):
        with patch("app.services.file_processor.extract_text_from_pdf",
                   side_effect=ValueError("corrupted")):
            await process_file(
                "save-error-id", str(err_path), FileType.PDF, test_user.id
            )

    updated = await FileRecord.find_one(FileRecord.id == "save-error-id")
    assert updated.status == FileStatus.FAILED
    assert "corrupted" in updated.error_message

# ── transcription.py lines 83-84, 164-165 ────────────────────────────────────

def test_transcribe_audio_with_duration(tmp_path):
    from app.services.transcription import transcribe_audio

    mock_model = MagicMock()
    mock_model.transcribe.return_value = {
        "segments": [
            {"text": " Hello world", "start": 0.0, "end": 5.0},
            {"text": " Goodbye world", "start": 5.0, "end": 10.0},
        ],
        "text": " Hello world Goodbye world",
    }

    audio = tmp_path / "audio.mp3"
    audio.write_bytes(b"fake")

    with patch("app.services.transcription._whisper_model", mock_model):
        with patch("app.services.transcription.get_whisper_model", return_value=mock_model):
            with patch("app.services.transcription.probe_audio_duration", return_value=10.0):
                segs, text = transcribe_audio(str(audio))

    assert len(segs) == 2
    assert "Hello world" in text


def test_transcribe_audio_without_duration(tmp_path):
    from app.services.transcription import transcribe_audio

    mock_model = MagicMock()
    mock_model.transcribe.return_value = {
        "segments": [{"text": " Test", "start": 0.0, "end": 2.0}],
        "text": " Test",
    }

    audio = tmp_path / "a.wav"
    audio.write_bytes(b"fake")

    with patch("app.services.transcription._whisper_model", mock_model):
        with patch("app.services.transcription.get_whisper_model", return_value=mock_model):
            with patch("app.services.transcription.probe_audio_duration", return_value=None):
                segs, text = transcribe_audio(str(audio))

    assert segs[0]["text"] == "Test"


def test_transcribe_video_no_cleanup_if_audio_missing(tmp_path):
    from app.services.transcription import transcribe

    video = str(tmp_path / "v.mp4")
    audio = str(tmp_path / "v_audio.wav")

    with patch("app.services.transcription.extract_audio_from_video", return_value=audio):
        with patch("app.services.transcription.transcribe_audio",
                   return_value=([{"text": "hi", "start": 0.0, "end": 1.0}], "hi")):
            with patch("os.path.exists", return_value=False):
                with patch("os.remove") as mock_rm:
                    transcribe(video, "video")
                    mock_rm.assert_not_called()


# ── pdf_service.py lines 29, 46-48 ───────────────────────────────────────────

def test_pdf_blank_page_skipped(tmp_path):
    import fitz
    from app.services.pdf_service import extract_text_from_pdf

    doc = fitz.open()
    p1 = doc.new_page()
    p1.insert_text((50, 50), "Real content on page one here.")
    doc.new_page()  # blank
    path = str(tmp_path / "mixed.pdf")
    doc.save(path)
    doc.close()

    pages, full_text = extract_text_from_pdf(path)
    assert len(pages) >= 1
    assert "Real content" in full_text


def test_pdf_word_count_accuracy(tmp_path):
    import fitz
    from app.services.pdf_service import extract_text_from_pdf

    doc = fitz.open()
    p = doc.new_page()
    p.insert_text((50, 50), "one two three four five")
    path = str(tmp_path / "words.pdf")
    doc.save(path)
    doc.close()

    pages, _ = extract_text_from_pdf(path)
    assert pages[0]["word_count"] >= 5


# ── file_utils.py ─────────────────────────────────────────────────────────────

def test_cleanup_file_oserror(tmp_path):
    from app.utils.file_utils import cleanup_file

    f = tmp_path / "locked.txt"
    f.write_bytes(b"data")

    with patch("os.remove", side_effect=OSError("permission denied")):
        result = cleanup_file(str(f))

    assert result is False


# ── schemas.py ────────────────────────────────────────────────────────────────

def test_username_special_chars_rejected():
    from app.models.schemas import UserRegisterRequest
    from pydantic import ValidationError
    with pytest.raises(ValidationError):
        UserRegisterRequest(
            email="test@test.com",
            username="user name!",
            password="Password123",
        )


def test_username_valid_chars():
    from app.models.schemas import UserRegisterRequest
    req = UserRegisterRequest(
        email="test@test.com",
        username="valid_user-123",
        password="Password123",
    )
    assert req.username == "valid_user-123"


# ── core/exceptions.py line 73 ───────────────────────────────────────────────

def test_file_not_ready_error():
    from app.core.exceptions import FileNotReadyError
    exc = FileNotReadyError()
    assert exc.status_code == 202
    assert "still being processed" in exc.detail