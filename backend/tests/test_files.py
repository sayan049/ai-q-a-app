# backend/tests/test_files.py

import pytest
import io
from httpx import AsyncClient
from unittest.mock import patch, AsyncMock


@pytest.mark.asyncio
async def test_upload_pdf_success(
    client: AsyncClient,
    test_user,
    auth_headers,
    sample_pdf_bytes,
    mock_db,
):
    """Test successful PDF upload."""
    with patch("app.api.files.process_file", new_callable=AsyncMock):
        response = await client.post(
            "/api/v1/files/upload",
            headers=auth_headers,
            files={
                "file": ("test.pdf", io.BytesIO(sample_pdf_bytes), "application/pdf")
            },
        )

    assert response.status_code == 202
    data = response.json()
    assert "file_id" in data
    assert data["file_type"] == "pdf"
    assert data["status"] == "processing"


@pytest.mark.asyncio
async def test_upload_audio_success(
    client: AsyncClient,
    test_user,
    auth_headers,
    sample_audio_bytes,
    mock_db,
):
    """Test successful audio upload."""
    with patch("app.api.files.process_file", new_callable=AsyncMock):
        response = await client.post(
            "/api/v1/files/upload",
            headers=auth_headers,
            files={
                "file": ("test.wav", io.BytesIO(sample_audio_bytes), "audio/wav")
            },
        )

    assert response.status_code == 202
    data = response.json()
    assert data["file_type"] == "audio"


@pytest.mark.asyncio
async def test_upload_unsupported_type(
    client: AsyncClient,
    test_user,
    auth_headers,
    mock_db,
):
    """Test upload of unsupported file type."""
    response = await client.post(
        "/api/v1/files/upload",
        headers=auth_headers,
        files={
            "file": ("test.exe", io.BytesIO(b"fake exe content"), "application/octet-stream")
        },
    )
    assert response.status_code == 415


@pytest.mark.asyncio
async def test_upload_empty_file(
    client: AsyncClient,
    test_user,
    auth_headers,
    mock_db,
):
    """Test upload of empty file."""
    response = await client.post(
        "/api/v1/files/upload",
        headers=auth_headers,
        files={
            "file": ("empty.pdf", io.BytesIO(b""), "application/pdf")
        },
    )
    assert response.status_code == 415


@pytest.mark.asyncio
async def test_upload_unauthenticated(client: AsyncClient, sample_pdf_bytes):
    """Test upload without authentication."""
    response = await client.post(
        "/api/v1/files/upload",
        files={
            "file": ("test.pdf", io.BytesIO(sample_pdf_bytes), "application/pdf")
        },
    )
    assert response.status_code == 401


@pytest.mark.asyncio
async def test_list_files_empty(
    client: AsyncClient,
    test_user,
    auth_headers,
    mock_db,
):
    """Test listing files when none uploaded."""
    response = await client.get("/api/v1/files/list", headers=auth_headers)
    assert response.status_code == 200
    data = response.json()
    assert data["files"] == []
    assert data["total"] == 0


@pytest.mark.asyncio
async def test_list_files_with_uploads(
    client: AsyncClient,
    test_user,
    auth_headers,
    sample_pdf_bytes,
    mock_db,
):
    """Test listing files after upload."""
    with patch("app.api.files.process_file", new_callable=AsyncMock):
        await client.post(
            "/api/v1/files/upload",
            headers=auth_headers,
            files={"file": ("doc1.pdf", io.BytesIO(sample_pdf_bytes), "application/pdf")},
        )
        await client.post(
            "/api/v1/files/upload",
            headers=auth_headers,
            files={"file": ("doc2.pdf", io.BytesIO(sample_pdf_bytes), "application/pdf")},
        )

    response = await client.get("/api/v1/files/list", headers=auth_headers)
    assert response.status_code == 200
    data = response.json()
    # Note: duplicate detection might merge them
    assert data["total"] >= 1


@pytest.mark.asyncio
async def test_delete_file(
    client: AsyncClient,
    test_user,
    auth_headers,
    sample_pdf_bytes,
    mock_db,
):
    """Test file deletion."""
    with patch("app.api.files.process_file", new_callable=AsyncMock):
        upload_response = await client.post(
            "/api/v1/files/upload",
            headers=auth_headers,
            files={"file": ("todelete.pdf", io.BytesIO(sample_pdf_bytes), "application/pdf")},
        )
    file_id = upload_response.json()["file_id"]

    delete_response = await client.delete(
        f"/api/v1/files/{file_id}",
        headers=auth_headers,
    )
    assert delete_response.status_code == 200

    # Verify deleted
    get_response = await client.get(
        f"/api/v1/files/{file_id}",
        headers=auth_headers,
    )
    assert get_response.status_code == 404


@pytest.mark.asyncio
async def test_get_file_not_found(
    client: AsyncClient,
    test_user,
    auth_headers,
    mock_db,
):
    """Test getting nonexistent file."""
    response = await client.get(
        "/api/v1/files/nonexistent-file-id",
        headers=auth_headers,
    )
    assert response.status_code == 404