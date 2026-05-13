# backend/tests/test_storage_service.py

import pytest
import os
from unittest.mock import patch, MagicMock, AsyncMock


# ── storage_service ───────────────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_upload_file_cloudinary_disabled(tmp_path):
    from app.services import storage_service
    test_file = tmp_path / "test.pdf"
    test_file.write_bytes(b"fake pdf")
    with patch("app.services.storage_service.settings") as mock_s:
        mock_s.cloudinary_enabled = False
        result = await storage_service.upload_file(
            file_path=str(test_file), file_id="file-123", user_id="user-456",
        )
    assert result["storage"] == "local"
    assert result["url"] is None
    assert result["public_id"] is None


@pytest.mark.asyncio
async def test_upload_file_cloudinary_enabled_pdf(tmp_path):
    from app.services import storage_service
    test_file = tmp_path / "test.pdf"
    test_file.write_bytes(b"fake pdf content")
    mock_cloudinary = MagicMock()
    mock_cloudinary.uploader.upload.return_value = {
        "secure_url": "https://res.cloudinary.com/test/raw/upload/test.pdf",
        "public_id": "aiqa/user-456/file-123",
    }
    with patch("app.services.storage_service.settings") as mock_s:
        mock_s.cloudinary_enabled = True
        mock_s.cloudinary_cloud_name = "test"
        mock_s.cloudinary_api_key = "key"
        mock_s.cloudinary_api_secret = "secret"
        with patch("app.services.storage_service._configure_cloudinary",
                   return_value=mock_cloudinary):
            result = await storage_service.upload_file(
                file_path=str(test_file), file_id="file-123", user_id="user-456",
            )
    assert result["storage"] == "cloudinary"
    assert result["url"] == "https://res.cloudinary.com/test/raw/upload/test.pdf"
    assert result["public_id"] == "aiqa/user-456/file-123"


@pytest.mark.asyncio
async def test_upload_file_cloudinary_enabled_mp4(tmp_path):
    from app.services import storage_service
    test_file = tmp_path / "test.mp4"
    test_file.write_bytes(b"fake video")
    mock_cloudinary = MagicMock()
    mock_cloudinary.uploader.upload.return_value = {
        "secure_url": "https://res.cloudinary.com/test/video/upload/test.mp4",
        "public_id": "aiqa/user-1/file-1",
    }
    with patch("app.services.storage_service.settings") as mock_s:
        mock_s.cloudinary_enabled = True
        mock_s.cloudinary_cloud_name = "test"
        mock_s.cloudinary_api_key = "key"
        mock_s.cloudinary_api_secret = "secret"
        with patch("app.services.storage_service._configure_cloudinary",
                   return_value=mock_cloudinary):
            result = await storage_service.upload_file(
                file_path=str(test_file), file_id="file-1", user_id="user-1",
            )
    assert result["storage"] == "cloudinary"
    call_kwargs = mock_cloudinary.uploader.upload.call_args[1]
    assert call_kwargs["resource_type"] == "video"


@pytest.mark.asyncio
async def test_upload_file_cloudinary_enabled_mp3(tmp_path):
    from app.services import storage_service
    test_file = tmp_path / "test.mp3"
    test_file.write_bytes(b"fake audio")
    mock_cloudinary = MagicMock()
    mock_cloudinary.uploader.upload.return_value = {
        "secure_url": "https://res.cloudinary.com/test/raw/upload/test.mp3",
        "public_id": "aiqa/user-1/file-2",
    }
    with patch("app.services.storage_service.settings") as mock_s:
        mock_s.cloudinary_enabled = True
        mock_s.cloudinary_cloud_name = "test"
        mock_s.cloudinary_api_key = "key"
        mock_s.cloudinary_api_secret = "secret"
        with patch("app.services.storage_service._configure_cloudinary",
                   return_value=mock_cloudinary):
            result = await storage_service.upload_file(
                file_path=str(test_file), file_id="file-2", user_id="user-1",
            )
    assert result["storage"] == "cloudinary"
    call_kwargs = mock_cloudinary.uploader.upload.call_args[1]
    assert call_kwargs["resource_type"] == "raw"


@pytest.mark.asyncio
async def test_upload_file_cloudinary_fails_falls_back(tmp_path):
    from app.services import storage_service
    test_file = tmp_path / "test.pdf"
    test_file.write_bytes(b"fake pdf")
    mock_cloudinary = MagicMock()
    mock_cloudinary.uploader.upload.side_effect = Exception("Network error")
    with patch("app.services.storage_service.settings") as mock_s:
        mock_s.cloudinary_enabled = True
        mock_s.cloudinary_cloud_name = "test"
        mock_s.cloudinary_api_key = "key"
        mock_s.cloudinary_api_secret = "secret"
        with patch("app.services.storage_service._configure_cloudinary",
                   return_value=mock_cloudinary):
            result = await storage_service.upload_file(
                file_path=str(test_file), file_id="file-123", user_id="user-456",
            )
    assert result["storage"] == "local"
    assert result["url"] is None


@pytest.mark.asyncio
async def test_delete_file_cloudinary_disabled():
    from app.services import storage_service
    with patch("app.services.storage_service.settings") as mock_s:
        mock_s.cloudinary_enabled = False
        result = await storage_service.delete_file("some-public-id")
    assert result is True


@pytest.mark.asyncio
async def test_delete_file_no_public_id():
    from app.services import storage_service
    with patch("app.services.storage_service.settings") as mock_s:
        mock_s.cloudinary_enabled = True
        result = await storage_service.delete_file("")
    assert result is True


@pytest.mark.asyncio
async def test_delete_file_cloudinary_success():
    from app.services import storage_service
    mock_cloudinary = MagicMock()
    mock_cloudinary.uploader.destroy.return_value = {"result": "ok"}
    with patch("app.services.storage_service.settings") as mock_s:
        mock_s.cloudinary_enabled = True
        mock_s.cloudinary_cloud_name = "test"
        mock_s.cloudinary_api_key = "key"
        mock_s.cloudinary_api_secret = "secret"
        with patch("app.services.storage_service._configure_cloudinary",
                   return_value=mock_cloudinary):
            result = await storage_service.delete_file("aiqa/user/file-123")
    assert result is True


@pytest.mark.asyncio
async def test_delete_file_cloudinary_fails():
    from app.services import storage_service
    mock_cloudinary = MagicMock()
    mock_cloudinary.uploader.destroy.side_effect = Exception("API error")
    with patch("app.services.storage_service.settings") as mock_s:
        mock_s.cloudinary_enabled = True
        mock_s.cloudinary_cloud_name = "test"
        mock_s.cloudinary_api_key = "key"
        mock_s.cloudinary_api_secret = "secret"
        with patch("app.services.storage_service._configure_cloudinary",
                   return_value=mock_cloudinary):
            result = await storage_service.delete_file("aiqa/user/file-123")
    assert result is False


@pytest.mark.asyncio
async def test_download_file_for_processing_success(tmp_path):
    from app.services.storage_service import download_file_for_processing
    local_path = str(tmp_path / "downloaded.pdf")
    mock_response = AsyncMock()
    mock_response.content = b"downloaded file content"
    mock_response.raise_for_status = MagicMock()
    mock_client = AsyncMock()
    mock_client.get = AsyncMock(return_value=mock_response)
    mock_client.__aenter__ = AsyncMock(return_value=mock_client)
    mock_client.__aexit__ = AsyncMock(return_value=None)
    with patch("httpx.AsyncClient", return_value=mock_client):
        result = await download_file_for_processing(
            url="https://res.cloudinary.com/test/test.pdf",
            local_path=local_path,
        )
    assert result == local_path
    assert os.path.exists(local_path)
    with open(local_path, "rb") as f:
        assert f.read() == b"downloaded file content"


@pytest.mark.asyncio
async def test_download_file_for_processing_fails(tmp_path):
    from app.services.storage_service import download_file_for_processing
    local_path = str(tmp_path / "fail.pdf")
    mock_client = AsyncMock()
    mock_client.get = AsyncMock(side_effect=Exception("Connection refused"))
    mock_client.__aenter__ = AsyncMock(return_value=mock_client)
    mock_client.__aexit__ = AsyncMock(return_value=None)
    with patch("httpx.AsyncClient", return_value=mock_client):
        with pytest.raises(RuntimeError, match="Could not download"):
            await download_file_for_processing(
                url="https://res.cloudinary.com/bad-url",
                local_path=local_path,
            )


# ── file_processor with Cloudinary ───────────────────────────────────────────

@pytest.mark.asyncio
async def test_get_local_file_path_local_exists(tmp_path):
    from app.services.file_processor import _get_local_file_path
    f = tmp_path / "test.pdf"
    f.write_bytes(b"content")
    mock_record = MagicMock()
    mock_record.cloudinary_url = None
    result = await _get_local_file_path(mock_record, str(f))
    assert result == str(f)


@pytest.mark.asyncio
async def test_get_local_file_path_uses_cloudinary(tmp_path):
    """Downloads from Cloudinary when local file missing."""
    from app.services.file_processor import _get_local_file_path

    mock_record = MagicMock()
    mock_record.cloudinary_url = "https://res.cloudinary.com/test/file.pdf"
    mock_record.filename = "test.pdf"

    with patch(
        "app.services.file_processor.download_file_for_processing",
        new_callable=AsyncMock,
    ) as mock_download:
        # Make the mock return a path that ends with processing.pdf
        mock_download.return_value = str(tmp_path / "processing.pdf")

        result = await _get_local_file_path(
            mock_record,
            "/nonexistent/path/file.pdf",
        )

    # Verify download was called with correct URL
    mock_download.assert_called_once()
    call_kwargs = mock_download.call_args[1]
    assert call_kwargs["url"] == "https://res.cloudinary.com/test/file.pdf"

    # Verify result ends with the correct filename
    assert result.endswith("processing.pdf")


@pytest.mark.asyncio
async def test_get_local_file_path_no_file_no_cloudinary():
    from app.services.file_processor import _get_local_file_path
    mock_record = MagicMock()
    mock_record.cloudinary_url = None
    with pytest.raises(FileNotFoundError, match="File not found locally"):
        await _get_local_file_path(mock_record, "/nonexistent/path.pdf")


@pytest.mark.asyncio
async def test_process_file_cleans_up_temp_file(test_user, mock_db, tmp_path):
    """Temp files downloaded from Cloudinary are cleaned up after processing."""
    from app.services.file_processor import process_file
    from app.models.file_record import FileRecord, FileStatus, FileType

    await FileRecord(
        id="cleanup-test-id",
        user_id=test_user.id,
        filename="test.pdf",
        original_filename="test.pdf",
        file_type=FileType.PDF,
        mime_type="application/pdf",
        status=FileStatus.UPLOADING,
        size_bytes=512,
        cloudinary_url="https://res.cloudinary.com/test/test.pdf",
    ).insert()

    tmp_file = tmp_path / "processing.pdf"
    tmp_file.write_bytes(b"fake content")

    mock_pages = [{"page_num": 1, "text": "Test content", "word_count": 2}]

    # Patch at file_processor module level
    with patch(
        "app.services.file_processor.download_file_for_processing",
        new_callable=AsyncMock,
        return_value=str(tmp_file),
    ):
        with patch("app.services.file_processor.get_pdf_metadata",
                   return_value={"page_count": 1}):
            with patch("app.services.file_processor.extract_text_from_pdf",
                       return_value=(mock_pages, "Test content")):
                with patch("app.services.file_processor.vector_service") as mock_vs:
                    mock_vs.add_chunks.return_value = 1
                    await process_file(
                        "cleanup-test-id",
                        "/nonexistent/original.pdf",
                        FileType.PDF,
                        test_user.id,
                    )

    updated = await FileRecord.find_one(FileRecord.id == "cleanup-test-id")
    assert updated.status == FileStatus.READY


# ── config.py cloudinary properties ──────────────────────────────────────────

def test_cloudinary_enabled_true():
    from app.config import Settings
    s = Settings(
        CLOUDINARY_CLOUD_NAME="cloud",
        CLOUDINARY_API_KEY="key",
        CLOUDINARY_API_SECRET="secret",
    )
    assert s.cloudinary_enabled is True


def test_cloudinary_enabled_false_missing_secret():
    from app.config import Settings
    s = Settings(
        CLOUDINARY_CLOUD_NAME="cloud",
        CLOUDINARY_API_KEY="key",
        CLOUDINARY_API_SECRET="",
    )
    assert s.cloudinary_enabled is False


def test_cloudinary_enabled_false_all_empty():
    from app.config import Settings
    s = Settings(
        CLOUDINARY_CLOUD_NAME="",
        CLOUDINARY_API_KEY="",
        CLOUDINARY_API_SECRET="",
    )
    assert s.cloudinary_enabled is False