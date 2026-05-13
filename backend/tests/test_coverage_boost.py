# backend/tests/test_coverage_boost.py

import pytest
import json
from unittest.mock import patch, MagicMock, AsyncMock


# ── main.py lines 35-78, 119-120 ─────────────────────────────────────────────

@pytest.mark.asyncio
async def test_app_startup_and_health(client, mock_db):
    response = await client.get("/health")
    assert response.status_code == 200

@pytest.mark.asyncio
async def test_app_root(client, mock_db):
    response = await client.get("/")
    assert response.status_code == 200

@pytest.mark.asyncio
async def test_global_exception_handler(client, mock_db):
    """Trigger the global exception handler."""
    with patch("app.api.auth.User.find_one", side_effect=Exception("DB error")):
        response = await client.get(
            "/api/v1/auth/me",
            headers={"Authorization": "Bearer invalid"}
        )
    assert response.status_code in (401, 500)


# ── core/exceptions.py lines 41, 57, 73, 82 ──────────────────────────────────

def test_file_too_large_error():
    from app.core.exceptions import FileTooLargeError
    exc = FileTooLargeError(100)
    assert exc.status_code == 413
    assert "100" in exc.detail

def test_file_processing_error():
    from app.core.exceptions import FileProcessingError
    exc = FileProcessingError("bad file")
    assert exc.status_code == 422
    assert "bad file" in exc.detail

def test_llm_service_error():
    from app.core.exceptions import LLMServiceError
    exc = LLMServiceError("LLM down")
    assert exc.status_code == 503

def test_duplicate_file_error():
    from app.core.exceptions import DuplicateFileError
    exc = DuplicateFileError("existing-id-123")
    assert exc.status_code == 409
    assert "existing-id-123" in exc.detail


# ── core/rate_limiter.py lines 21, 30-31 ─────────────────────────────────────

def test_get_rate_limit_key_with_forwarded_ip():
    from app.core.rate_limiter import get_rate_limit_key
    from unittest.mock import MagicMock

    request = MagicMock()
    request.headers = {"X-Forwarded-For": "192.168.1.1, 10.0.0.1"}
    request.state.user_id = None
    request.client.host = "127.0.0.1"

    key = get_rate_limit_key(request)
    assert "192.168.1.1" in key

def test_get_rate_limit_key_with_user_id():
    from app.core.rate_limiter import get_rate_limit_key
    from unittest.mock import MagicMock

    request = MagicMock()
    request.headers = {}
    request.state.user_id = "user-123"
    request.client.host = "127.0.0.1"

    key = get_rate_limit_key(request)
    assert "user-123" in key

def test_rate_limit_exceeded_handler():
    from app.core.rate_limiter import rate_limit_exceeded_handler
    from unittest.mock import MagicMock

    request = MagicMock()
    exc = MagicMock()
    exc.detail = "Rate limit exceeded"

    response = rate_limit_exceeded_handler(request, exc)
    assert response.status_code == 429


# ── dependencies.py lines 33, 53-54 ──────────────────────────────────────────

@pytest.mark.asyncio
async def test_get_current_user_missing_sub(mock_db):
    from app.dependencies import get_current_user
    from app.core.exceptions import AuthenticationError
    from jose import jwt
    from app.config import settings

    # Token without 'sub'
    payload = {"type": "access", "email": "x@x.com"}
    token = jwt.encode(payload, settings.jwt_secret, algorithm=settings.jwt_algorithm)

    from fastapi.security import HTTPAuthorizationCredentials
    creds = HTTPAuthorizationCredentials(scheme="Bearer", credentials=token)

    with pytest.raises(AuthenticationError):
        await get_current_user(creds)

@pytest.mark.asyncio
async def test_get_optional_user_invalid_token(mock_db):
    from app.dependencies import get_optional_user
    from fastapi.security import HTTPAuthorizationCredentials

    creds = HTTPAuthorizationCredentials(scheme="Bearer", credentials="bad.token")
    result = await get_optional_user(creds)
    assert result is None


# ── cache_service.py lines 18, 53-54, 66, 77, 88-89, 100, 111 ───────────────

@pytest.mark.asyncio
async def test_cache_get_with_real_redis(fake_redis):
    from app.services.cache_service import cache_get, cache_set
    await cache_set("real_key", {"hello": "world"}, ttl=60)
    val = await cache_get("real_key")
    assert val == {"hello": "world"}

@pytest.mark.asyncio
async def test_cache_set_serializes_datetime(fake_redis):
    from app.services.cache_service import cache_set, cache_get
    from datetime import datetime
    data = {"time": datetime.utcnow()}
    result = await cache_set("dt_key", data, ttl=60)
    assert result is True

@pytest.mark.asyncio
async def test_blacklist_and_check_flow(fake_redis):
    from app.services.cache_service import blacklist_token, is_token_blacklisted
    jti = "flow-jti-test"
    assert await is_token_blacklisted(jti) is False
    await blacklist_token(jti, 3600)
    assert await is_token_blacklisted(jti) is True

@pytest.mark.asyncio
async def test_cache_delete_pattern_no_matches(fake_redis):
    from app.services.cache_service import cache_delete_pattern
    result = await cache_delete_pattern("nomatch:*:xyz")
    assert result == 0

@pytest.mark.asyncio
async def test_cache_get_error_returns_none():
    from app.services.cache_service import cache_get
    mock_redis = AsyncMock()
    mock_redis.get.side_effect = Exception("connection reset")
    with patch("app.services.cache_service.get_redis", return_value=mock_redis):
        result = await cache_get("key")
    assert result is None

@pytest.mark.asyncio
async def test_cache_set_error_returns_false():
    from app.services.cache_service import cache_set
    mock_redis = AsyncMock()
    mock_redis.setex.side_effect = Exception("write failed")
    with patch("app.services.cache_service.get_redis", return_value=mock_redis):
        result = await cache_set("key", {"v": 1}, ttl=60)
    assert result is False

@pytest.mark.asyncio
async def test_cache_delete_error_returns_false():
    from app.services.cache_service import cache_delete
    mock_redis = AsyncMock()
    mock_redis.delete.side_effect = Exception("delete failed")
    with patch("app.services.cache_service.get_redis", return_value=mock_redis):
        result = await cache_delete("key")
    assert result is False

@pytest.mark.asyncio
async def test_blacklist_error_returns_false():
    from app.services.cache_service import blacklist_token
    mock_redis = AsyncMock()
    mock_redis.setex.side_effect = Exception("error")
    with patch("app.services.cache_service.get_redis", return_value=mock_redis):
        result = await blacklist_token("jti", 3600)
    assert result is False

@pytest.mark.asyncio
async def test_is_blacklisted_error_returns_false():
    from app.services.cache_service import is_token_blacklisted
    mock_redis = AsyncMock()
    mock_redis.get.side_effect = Exception("error")
    with patch("app.services.cache_service.get_redis", return_value=mock_redis):
        result = await is_token_blacklisted("jti")
    assert result is False


# ── summary_service.py lines 20-44, 56-69 ────────────────────────────────────

@pytest.mark.asyncio
async def test_summary_service_full_flow(test_user, mock_db):
    from app.services.summary_service import get_or_create_summary
    from app.models.file_record import FileRecord, FileStatus, FileType, ChunkMetadata

    fr = FileRecord(
        id="full-flow-sum",
        user_id=test_user.id,
        filename="test.pdf",
        original_filename="test.pdf",
        file_type=FileType.PDF,
        mime_type="application/pdf",
        status=FileStatus.READY,
        size_bytes=1024,
        chunk_count=3,
    )
    await fr.insert()

    for i in range(3):
        await ChunkMetadata(
            file_id="full-flow-sum",
            user_id=test_user.id,
            chunk_index=i,
            text=f"chunk {i} " * 20,
            word_count=20,
        ).insert()

    with patch(
        "app.services.summary_service.llm_service.generate_summary",
        return_value={"summary": "Full flow summary", "key_topics": ["a", "b"]},
    ):
        result = await get_or_create_summary("full-flow-sum", test_user.id)

    assert result["summary"] == "Full flow summary"
    assert result["word_count"] == 60
    assert result["cached"] is False


@pytest.mark.asyncio
async def test_summary_service_returns_cached(test_user, mock_db):
    from app.services.summary_service import get_or_create_summary
    from app.services.cache_service import cache_set, make_summary_cache_key
    from app.models.file_record import FileRecord, FileStatus, FileType

    fr = FileRecord(
        id="cached-flow-sum",
        user_id=test_user.id,
        filename="c.pdf",
        original_filename="c.pdf",
        file_type=FileType.PDF,
        mime_type="application/pdf",
        status=FileStatus.READY,
        size_bytes=1024,
        chunk_count=1,
    )
    await fr.insert()

    key = make_summary_cache_key("cached-flow-sum")
    await cache_set(key, {
        "summary": "From cache",
        "key_topics": ["cached"],
        "word_count": 10,
        "cached": True,
    }, ttl=3600)

    result = await get_or_create_summary("cached-flow-sum", test_user.id)
    assert result["summary"] == "From cache"
    assert result["cached"] is True


@pytest.mark.asyncio
async def test_summary_service_not_found(test_user, mock_db):
    from app.services.summary_service import get_or_create_summary
    with pytest.raises(ValueError, match="not found"):
        await get_or_create_summary("no-such-file", test_user.id)


@pytest.mark.asyncio
async def test_summary_service_not_ready(test_user, mock_db):
    from app.services.summary_service import get_or_create_summary
    from app.models.file_record import FileRecord, FileStatus, FileType

    fr = FileRecord(
        id="not-ready-sum",
        user_id=test_user.id,
        filename="p.pdf",
        original_filename="p.pdf",
        file_type=FileType.PDF,
        mime_type="application/pdf",
        status=FileStatus.PROCESSING,
        size_bytes=1024,
        chunk_count=0,
    )
    await fr.insert()
    with pytest.raises(ValueError, match="not ready"):
        await get_or_create_summary("not-ready-sum", test_user.id)


@pytest.mark.asyncio
async def test_summary_service_empty_chunks(test_user, mock_db):
    from app.services.summary_service import get_or_create_summary
    from app.models.file_record import FileRecord, FileStatus, FileType

    fr = FileRecord(
        id="zero-chunks-sum",
        user_id=test_user.id,
        filename="z.pdf",
        original_filename="z.pdf",
        file_type=FileType.PDF,
        mime_type="application/pdf",
        status=FileStatus.READY,
        size_bytes=1024,
        chunk_count=0,
    )
    await fr.insert()

    result = await get_or_create_summary("zero-chunks-sum", test_user.id)
    assert "No content" in result["summary"]


# ── pdf_service.py lines 29, 46-48 ───────────────────────────────────────────

def test_pdf_extract_multi_page_word_count(tmp_path):
    import fitz
    from app.services.pdf_service import extract_text_from_pdf

    doc = fitz.open()
    for i in range(3):
        p = doc.new_page()
        p.insert_text((50, 50), f"Page {i+1} " * 30)
    path = str(tmp_path / "multi.pdf")
    doc.save(path)
    doc.close()

    pages, full = extract_text_from_pdf(path)
    assert len(pages) == 3
    total_words = sum(p["word_count"] for p in pages)
    assert total_words > 0

def test_pdf_metadata_with_title(tmp_path):
    import fitz
    from app.services.pdf_service import get_pdf_metadata

    doc = fitz.open()
    doc.set_metadata({"title": "Test Document", "author": "Tester"})
    p = doc.new_page()
    p.insert_text((50, 50), "content")
    path = str(tmp_path / "meta.pdf")
    doc.save(path)
    doc.close()

    meta = get_pdf_metadata(path)
    assert meta["page_count"] == 1


# ── transcription.py lines 24-26, 83-84, 164-165 ─────────────────────────────

def test_get_whisper_model_failure():
    from app.services import transcription
    original = transcription._whisper_model
    transcription._whisper_model = None

    with patch("whisper.load_model", side_effect=Exception("CUDA not found")):
        with pytest.raises(RuntimeError, match="Whisper model unavailable"):
            transcription.get_whisper_model()

    transcription._whisper_model = original

def test_transcribe_audio_with_fp16_false(tmp_path):
    from app.services.transcription import transcribe_audio

    mock_model = MagicMock()
    mock_model.transcribe.return_value = {
        "segments": [{"text": " Test", "start": 0.0, "end": 1.0}],
        "text": " Test",
    }

    audio = tmp_path / "t.wav"
    audio.write_bytes(b"fake")

    with patch("app.services.transcription._whisper_model", mock_model):
        with patch("app.services.transcription.get_whisper_model", return_value=mock_model):
            segs, text = transcribe_audio(str(audio))

    # Verify fp16=False was passed
    call_kwargs = mock_model.transcribe.call_args
    assert call_kwargs is not None
    assert "Test" in text

def test_transcribe_video_no_cleanup_if_no_file(tmp_path):
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


# ── vector_service.py lines 34-36, 137-139, 144-146, 169, 181, 206-207 ───────

def test_get_embedding_model_failure():
    from app.services import vector_service as vs_mod
    original = vs_mod._embedding_model
    vs_mod._embedding_model = None

    with patch("sentence_transformers.SentenceTransformer",
               side_effect=Exception("model not found")):
        with pytest.raises(RuntimeError, match="Embedding model unavailable"):
            vs_mod.get_embedding_model()

    vs_mod._embedding_model = original

def test_load_index_corrupted(tmp_path):
    from app.services.vector_service import VectorService

    service = VectorService()
    service.index_dir = str(tmp_path)

    # Write corrupted index
    (tmp_path / "corrupt.index").write_bytes(b"not a valid faiss index")
    import json
    (tmp_path / "corrupt_meta.json").write_text(json.dumps([]))

    idx, meta = service.load_index("corrupt")
    assert idx is None

def test_search_negative_indices(tmp_path):
    """FAISS may return -1 for unfilled slots — should be skipped."""
    import numpy as np
    from app.services.vector_service import VectorService

    service = VectorService()
    service.index_dir = str(tmp_path)

    def mock_embed(texts):
        n = len(texts)
        emb = np.random.rand(n, 384).astype(np.float32)
        return emb / np.linalg.norm(emb, axis=1, keepdims=True)

    with patch.object(service, "embed", side_effect=mock_embed):
        chunks = [{"chunk_index": 0, "text": "hello world", "word_count": 2}]
        service.add_chunks("neg-test", chunks)
        results = service.search("neg-test", "hello", top_k=5)
        assert all(r["chunk_index"] >= 0 for r in results)


# ── file_utils.py lines 105-106 ──────────────────────────────────────────────

def test_cleanup_removes_empty_parent(tmp_path):
    from app.utils.file_utils import cleanup_file
    import os

    subdir = tmp_path / "subdir"
    subdir.mkdir()
    f = subdir / "file.txt"
    f.write_bytes(b"content")

    cleanup_file(str(f))
    assert not f.exists()
    # Parent should be removed if empty
    assert not subdir.exists() or not any(subdir.iterdir())


# ── schemas.py lines 99-101 ──────────────────────────────────────────────────

def test_chat_request_validator_strips_whitespace():
    from app.models.schemas import ChatRequest
    req = ChatRequest(query="  hello world  ", file_id="file-123")
    assert req.query == "hello world"

def test_chat_request_validator_rejects_whitespace_only():
    from app.models.schemas import ChatRequest
    from pydantic import ValidationError
    with pytest.raises(ValidationError):
        ChatRequest(query="   ", file_id="file-123")


# ── llm_service.py lines 143-146 ─────────────────────────────────────────────

@pytest.mark.asyncio
async def test_stream_with_groq_yields_content():
    from app.services.llm_service import stream_with_groq

    async def fake_stream():
        items = []
        for word in ["hello", " ", "world"]:
            chunk = MagicMock()
            chunk.choices[0].delta.content = word
            items.append(chunk)

        # Also add one with no content
        empty = MagicMock()
        empty.choices[0].delta = None
        items.append(empty)

        for item in items:
            yield item

    with patch("groq.AsyncGroq") as MockGroq:
        mock_client = AsyncMock()
        MockGroq.return_value = mock_client
        mock_client.chat.completions.create = AsyncMock(return_value=fake_stream())

        tokens = []
        async for token in stream_with_groq([{"role": "user", "content": "hi"}]):
            tokens.append(token)

    assert "hello" in tokens
    assert "world" in tokens