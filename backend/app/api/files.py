# backend/app/api/files.py

import os
import logging
import uuid
from fastapi import APIRouter, Depends, UploadFile, File, BackgroundTasks, Request
from typing import List

from app.models.user import User
from app.models.file_record import FileRecord, FileStatus, FileType, ChunkMetadata
from app.models.schemas import (
    FileUploadResponse,
    FileRecordResponse,
    FileListResponse,
    MessageResponse,
)
from app.core.exceptions import (
    FileTooLargeError,
    UnsupportedFileTypeError,
    NotFoundError,
    AuthorizationError,
    DuplicateFileError,
)
from app.core.rate_limiter import limiter
from app.services.file_processor import process_file
from app.services.vector_service import vector_service
from app.services.cache_service import cache_delete_pattern
from app.utils.file_utils import (
    detect_file_type,
    get_safe_filename,
    get_upload_path,
    get_file_hash,
    cleanup_file,
)
from app.dependencies import get_current_user
from app.config import settings

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/files", tags=["Files"])


def _build_file_response(f: FileRecord) -> FileRecordResponse:
    """Helper to build FileRecordResponse from FileRecord."""
    return FileRecordResponse(
        id=f.id,
        user_id=f.user_id,
        filename=f.filename,
        original_filename=f.original_filename,
        file_type=f.file_type.value,
        status=f.status.value,
        size_bytes=f.size_bytes,
        upload_time=f.upload_time,
        processed_time=f.processed_time,
        chunk_count=f.chunk_count,
        duration=f.duration,
        page_count=f.page_count,
        error_message=f.error_message,
    )


@router.post("/upload", response_model=FileUploadResponse, status_code=202)
@limiter.limit("10/hour")
async def upload_file(
    request: Request,
    background_tasks: BackgroundTasks,
    file: UploadFile = File(...),
    current_user: User = Depends(get_current_user),
):
    """Upload a PDF, audio, or video file for processing."""

    # ── Validate filename ─────────────────────────────────────────────────────
    original_filename = file.filename or "uploaded_file"
    safe_filename = get_safe_filename(original_filename)

    # ── Validate MIME type ────────────────────────────────────────────────────
    mime_type = file.content_type or ""
    file_type_str = detect_file_type(safe_filename, mime_type)

    if not file_type_str:
        raise UnsupportedFileTypeError(
            mime_type or os.path.splitext(safe_filename)[1]
        )

    file_type_map = {
        "pdf":   FileType.PDF,
        "audio": FileType.AUDIO,
        "video": FileType.VIDEO,
    }
    file_type_enum = file_type_map[file_type_str]

    # ── Read and validate file size ───────────────────────────────────────────
    content = await file.read()
    file_size = len(content)

    if file_size == 0:
        raise UnsupportedFileTypeError("empty file")

    if file_size > settings.max_file_size_bytes:
        raise FileTooLargeError(settings.max_file_size_mb)

    # ── Create FileRecord in DB ───────────────────────────────────────────────
    file_id = str(uuid.uuid4())

    file_record = FileRecord(
        id=file_id,
        user_id=current_user.id,
        filename=safe_filename,
        original_filename=original_filename,
        file_type=file_type_enum,
        mime_type=mime_type,
        status=FileStatus.UPLOADING,
        size_bytes=file_size,
    )
    await file_record.insert()

    # ── Save file to disk ─────────────────────────────────────────────────────
    file_path = get_upload_path(current_user.id, file_id, safe_filename)

    try:
        with open(file_path, "wb") as f:
            f.write(content)
    except Exception as e:
        logger.error(f"Failed to save file: {e}")
        file_record.status = FileStatus.FAILED
        file_record.error_message = "Failed to save file to disk"
        await file_record.save()
        raise

    # ── Deduplication by hash ─────────────────────────────────────────────────
    try:
        file_hash = get_file_hash(file_path)
        file_record.file_hash = file_hash
        file_record.file_path = file_path

        existing = await FileRecord.find_one(
            FileRecord.user_id == current_user.id,
            FileRecord.file_hash == file_hash,
            FileRecord.id != file_id,
            FileRecord.status != FileStatus.FAILED,
        )
        if existing:
            cleanup_file(file_path)
            await file_record.delete()
            raise DuplicateFileError(existing.id)

        await file_record.save()

    except DuplicateFileError:
        raise
    except Exception as e:
        logger.warning(f"Hash computation failed: {e}")
        file_record.file_path = file_path
        await file_record.save()

    # ── Trigger background processing ─────────────────────────────────────────
    background_tasks.add_task(
        process_file,
        file_id=file_id,
        file_path=file_path,
        file_type=file_type_enum,
        user_id=current_user.id,
    )

    logger.info(
        f"File uploaded: {safe_filename} ({file_size} bytes) "
        f"by user {current_user.id}"
    )

    return FileUploadResponse(
        file_id=file_id,
        user_id=current_user.id,
        filename=safe_filename,
        file_type=file_type_str,
        status=FileStatus.PROCESSING.value,
        size_bytes=file_size,
        message="File uploaded successfully. Processing started in background.",
    )


@router.get("/list", response_model=FileListResponse)
async def list_files(
    current_user: User = Depends(get_current_user),
    limit: int = 50,
    skip: int = 0,
):
    """List all files uploaded by the current user."""
    files = await FileRecord.find(
        FileRecord.user_id == current_user.id,
    ).sort(-FileRecord.upload_time).skip(skip).limit(limit).to_list()

    total = await FileRecord.find(
        FileRecord.user_id == current_user.id
    ).count()

    return FileListResponse(
        files=[_build_file_response(f) for f in files],
        total=total,
    )


@router.get("/{file_id}", response_model=FileRecordResponse)
async def get_file(
    file_id: str,
    current_user: User = Depends(get_current_user),
):
    """Get metadata for a specific file."""
    file_record = await FileRecord.find_one(FileRecord.id == file_id)

    if not file_record:
        raise NotFoundError("File")

    if file_record.user_id != current_user.id:
        raise AuthorizationError("You don't have access to this file")

    return _build_file_response(file_record)


@router.delete("/{file_id}", response_model=MessageResponse)
async def delete_file(
    file_id: str,
    current_user: User = Depends(get_current_user),
):
    """Delete a file and all associated data."""
    file_record = await FileRecord.find_one(FileRecord.id == file_id)

    if not file_record:
        raise NotFoundError("File")

    if file_record.user_id != current_user.id:
        raise AuthorizationError("You don't have access to this file")

    # Delete physical file from disk
    if file_record.file_path and os.path.exists(file_record.file_path):
        cleanup_file(file_record.file_path)

    # Delete FAISS index
    vector_service.delete_index(file_id)

    # Delete chunks from MongoDB
    await ChunkMetadata.find(ChunkMetadata.file_id == file_id).delete()

    # Invalidate Redis cache
    await cache_delete_pattern(f"chat:*{file_id}*")
    await cache_delete_pattern(f"summary:{file_id}")

    # Delete file record
    await file_record.delete()

    logger.info(f"File {file_id} deleted by user {current_user.id}")

    return MessageResponse(message="File deleted successfully")