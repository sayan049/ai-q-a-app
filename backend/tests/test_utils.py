# backend/tests/test_utils.py

import pytest
import os
from unittest.mock import patch


# ── file_utils ────────────────────────────────────────────────────────────────

def test_detect_file_type_pdf():
    from app.utils.file_utils import detect_file_type
    assert detect_file_type("doc.pdf", "application/pdf") == "pdf"


def test_detect_file_type_audio_mp3():
    from app.utils.file_utils import detect_file_type
    assert detect_file_type("audio.mp3", "audio/mpeg") == "audio"


def test_detect_file_type_audio_wav():
    from app.utils.file_utils import detect_file_type
    assert detect_file_type("audio.wav", "audio/wav") == "audio"


def test_detect_file_type_video_mp4():
    from app.utils.file_utils import detect_file_type
    assert detect_file_type("video.mp4", "video/mp4") == "video"


def test_detect_file_type_by_extension():
    from app.utils.file_utils import detect_file_type
    assert detect_file_type("file.mp3", "application/octet-stream") == "audio"
    assert detect_file_type("file.mp4", "application/octet-stream") == "video"
    assert detect_file_type("file.pdf", "application/octet-stream") == "pdf"


def test_detect_file_type_unsupported():
    from app.utils.file_utils import detect_file_type
    result = detect_file_type("file.exe", "application/octet-stream")
    assert result is None


def test_get_safe_filename():
    from app.utils.file_utils import get_safe_filename
    assert get_safe_filename("normal.pdf") == "normal.pdf"
    assert get_safe_filename("../../etc/passwd") == "passwd"
    assert get_safe_filename("file with spaces.mp3") == "file_with_spaces.mp3"


def test_get_safe_filename_special_chars():
    from app.utils.file_utils import get_safe_filename
    result = get_safe_filename("my file (1).pdf")
    assert ".." not in result
    assert "/" not in result


def test_format_file_size():
    from app.utils.file_utils import format_file_size
    assert format_file_size(500) == "500 B"
    assert format_file_size(1024) == "1.0 KB"
    assert format_file_size(1024 * 1024) == "1.0 MB"
    assert format_file_size(1024 * 1024 * 1024) == "1.0 GB"


def test_get_file_hash(tmp_path):
    from app.utils.file_utils import get_file_hash
    f = tmp_path / "test.txt"
    f.write_bytes(b"hello world")
    hash1 = get_file_hash(str(f))
    hash2 = get_file_hash(str(f))
    assert hash1 == hash2
    assert len(hash1) == 64  # SHA256 hex


def test_get_file_hash_different_files(tmp_path):
    from app.utils.file_utils import get_file_hash
    f1 = tmp_path / "a.txt"
    f2 = tmp_path / "b.txt"
    f1.write_bytes(b"content a")
    f2.write_bytes(b"content b")
    assert get_file_hash(str(f1)) != get_file_hash(str(f2))


def test_cleanup_file(tmp_path):
    from app.utils.file_utils import cleanup_file
    f = tmp_path / "to_delete.txt"
    f.write_bytes(b"delete me")
    assert f.exists()
    result = cleanup_file(str(f))
    assert result is True
    assert not f.exists()


def test_cleanup_file_not_exists(tmp_path):
    from app.utils.file_utils import cleanup_file
    result = cleanup_file(str(tmp_path / "nonexistent.txt"))
    assert result is False


def test_get_upload_path(tmp_path):
    from app.utils.file_utils import get_upload_path
    with patch("app.utils.file_utils.settings") as mock_settings:
        mock_settings.upload_dir = str(tmp_path)
        path = get_upload_path("user-123", "file-456", "test.pdf")
    assert "user-123" in path
    assert "file-456" in path
    assert path.endswith("original.pdf")


# ── core/auth ────────────────────────────────────────────────────────────────

def test_hash_and_verify_password():
    from app.core.auth import hash_password, verify_password
    pwd = "MySecurePassword123"
    hashed = hash_password(pwd)
    assert hashed != pwd
    assert verify_password(pwd, hashed)
    assert not verify_password("WrongPassword", hashed)


def test_create_access_token():
    from app.core.auth import create_access_token, verify_access_token
    token = create_access_token("user-123", "test@example.com")
    assert isinstance(token, str)
    payload = verify_access_token(token)
    assert payload["sub"] == "user-123"
    assert payload["email"] == "test@example.com"
    assert payload["type"] == "access"


def test_create_refresh_token():
    from app.core.auth import create_refresh_token, verify_refresh_token
    token, jti = create_refresh_token("user-123")
    assert isinstance(token, str)
    assert isinstance(jti, str)
    payload = verify_refresh_token(token)
    assert payload["sub"] == "user-123"
    assert payload["type"] == "refresh"
    assert payload["jti"] == jti


def test_invalid_token_raises():
    from app.core.auth import verify_access_token
    from jose import JWTError
    with pytest.raises(JWTError):
        verify_access_token("invalid.token.here")


def test_wrong_token_type_raises():
    from app.core.auth import create_refresh_token, verify_access_token
    from jose import JWTError
    token, _ = create_refresh_token("user-123")
    with pytest.raises(JWTError):
        verify_access_token(token)


# ── llm_service helpers ───────────────────────────────────────────────────────

def test_format_timestamp_zero():
    from app.services.llm_service import format_timestamp
    assert format_timestamp(0) == "00:00"


def test_format_timestamp_minutes():
    from app.services.llm_service import format_timestamp
    assert format_timestamp(90) == "01:30"
    assert format_timestamp(3600) == "60:00"


def test_format_timestamp_none():
    from app.services.llm_service import format_timestamp
    assert format_timestamp(None) == ""


def test_build_context_no_timestamps():
    from app.services.llm_service import build_context_string
    chunks = [{"text": "Hello world", "start_time": None, "end_time": None, "page_num": None}]
    ctx = build_context_string(chunks)
    assert "Hello world" in ctx
    assert "Excerpt 1" in ctx


def test_build_context_empty():
    from app.services.llm_service import build_context_string
    ctx = build_context_string([])
    assert "No relevant context" in ctx


def test_extract_timestamps_empty():
    from app.services.llm_service import extract_timestamps_from_chunks
    result = extract_timestamps_from_chunks([])
    assert result == []


def test_extract_timestamps_no_time():
    from app.services.llm_service import extract_timestamps_from_chunks
    chunks = [{"text": "hello", "start_time": None, "end_time": None}]
    result = extract_timestamps_from_chunks(chunks)
    assert result == []


def test_extract_timestamps_deduplication():
    from app.services.llm_service import extract_timestamps_from_chunks
    chunks = [
        {"text": "chunk 1", "start_time": 0.0,  "end_time": 5.0,  "score": 0.9},
        {"text": "chunk 2", "start_time": 0.0,  "end_time": 5.0,  "score": 0.8},  # exact duplicate
        {"text": "chunk 3", "start_time": 30.0, "end_time": 40.0, "score": 0.7},
    ]
    result = extract_timestamps_from_chunks(chunks)
    starts = [r["start"] for r in result]
    # 0.0 appears twice but only once in result
    assert starts.count(0.0) == 1
    assert 30.0 in starts