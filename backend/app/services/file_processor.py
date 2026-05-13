# backend/app/services/file_processor.py

import os
import logging
import tempfile
from datetime import datetime
from typing import Optional

from app.models.file_record import FileRecord, FileStatus, FileType, ChunkMetadata
from app.services.pdf_service import extract_text_from_pdf, get_pdf_metadata
from app.services.transcription import transcribe
from app.services.vector_service import vector_service
from app.utils.text_chunker import (
    chunk_pdf_pages,
    chunk_segments_with_timestamps,
    chunk_text,
)
from app.utils.file_utils import get_file_hash

logger = logging.getLogger(__name__)


async def _get_local_file_path(file_record: FileRecord, file_path: str) -> str:
    """
    If the file is stored on Cloudinary, download it to a temp location.
    If it's local and exists, use it directly.
    Returns a valid local file path for processing.
    """
    # Case 1: Local file exists — use it directly
    if os.path.exists(file_path):
        logger.info(f"Using local file: {file_path}")
        return file_path

    # Case 2: File is on Cloudinary — download it
    if file_record.cloudinary_url:
        logger.info(f"Downloading from Cloudinary: {file_record.cloudinary_url}")
        from app.services.storage_service import download_file_for_processing

        ext = file_record.filename.rsplit(".", 1)[-1] if "." in file_record.filename else "bin"
        tmp_dir = tempfile.mkdtemp()
        local_path = os.path.join(tmp_dir, f"processing.{ext}")

        await download_file_for_processing(
            url=file_record.cloudinary_url,
            local_path=local_path,
        )
        return local_path

    raise FileNotFoundError(
        f"File not found locally ({file_path}) and no Cloudinary URL available."
    )


async def process_file(
    file_id: str,
    file_path: str,
    file_type: FileType,
    user_id: str,
):
    """
    Background task: process uploaded file.
    Supports both local storage and Cloudinary storage.
    Updates FileRecord status throughout.
    """
    logger.info(f"Starting processing: {file_id} (type: {file_type.value})")

    file_record = await FileRecord.find_one(FileRecord.id == file_id)
    if not file_record:
        logger.error(f"FileRecord {file_id} not found")
        return

    # Track if we created a temp file that needs cleanup
    temp_file_path = None

    try:
        file_record.status = FileStatus.PROCESSING
        await file_record.save()

        # ── Resolve local file path (download from Cloudinary if needed) ──────
        resolved_path = await _get_local_file_path(file_record, file_path)

        # Track temp files for cleanup
        if resolved_path != file_path:
            temp_file_path = resolved_path
            logger.info(f"Using temp file for processing: {resolved_path}")

        chunks = []

        # ── PDF ───────────────────────────────────────────────────────────────
        if file_type == FileType.PDF:
            logger.info(f"Extracting PDF text: {resolved_path}")

            meta = get_pdf_metadata(resolved_path)
            file_record.page_count = meta.get("page_count", 0)

            pages, full_text = extract_text_from_pdf(resolved_path)

            chunks = chunk_pdf_pages(pages, chunk_size=500, overlap=50)

            logger.info(f"PDF: {len(pages)} pages → {len(chunks)} chunks")

        # ── Audio / Video ─────────────────────────────────────────────────────
        elif file_type in (FileType.AUDIO, FileType.VIDEO):
            logger.info(f"Transcribing {file_type.value}: {resolved_path}")

            segments, full_text = transcribe(resolved_path, file_type.value)

            if not segments:
                logger.warning(f"No speech detected: {resolved_path}")
                file_record.status         = FileStatus.READY
                file_record.chunk_count    = 0
                file_record.processed_time = datetime.utcnow()
                await file_record.save()
                return

            file_record.duration = round(segments[-1]["end"], 2)

            chunks = chunk_segments_with_timestamps(
                segments,
                chunk_size=40,
                overlap=5,
            )

            logger.info(
                f"Transcription: {len(segments)} segments → {len(chunks)} chunks "
                f"(duration: {file_record.duration}s)"
            )

        else:
            raise ValueError(f"Unknown file type: {file_type}")

        if not chunks:
            raise ValueError("No content extracted from file")

        # ── FAISS Index ───────────────────────────────────────────────────────
        logger.info(f"Building FAISS index: {file_id} ({len(chunks)} chunks)")
        num_indexed = vector_service.add_chunks(file_id, chunks)
        logger.info(f"FAISS indexed: {num_indexed} vectors")

        # ── Save Chunks to MongoDB ────────────────────────────────────────────
        chunk_docs = [
            ChunkMetadata(
                file_id=file_id,
                user_id=user_id,
                chunk_index=c.get("chunk_index", i),
                text=c["text"],
                start_time=c.get("start_time"),
                end_time=c.get("end_time"),
                page_num=c.get("page_num"),
                word_count=c.get("word_count", 0),
            )
            for i, c in enumerate(chunks)
        ]

        if chunk_docs:
            await ChunkMetadata.insert_many(chunk_docs)
            logger.info(f"Saved {len(chunk_docs)} chunks to MongoDB")

        # ── Update FileRecord ─────────────────────────────────────────────────
        file_record.status         = FileStatus.READY
        file_record.chunk_count    = len(chunks)
        file_record.processed_time = datetime.utcnow()
        file_record.error_message  = None
        await file_record.save()

        logger.info(f"✅ Done: {file_id} — {len(chunks)} chunks ready")

    except Exception as e:
        logger.error(f"❌ Processing failed: {file_id} — {e}", exc_info=True)
        try:
            file_record.status        = FileStatus.FAILED
            file_record.error_message = str(e)[:500]
            await file_record.save()
        except Exception as save_err:
            logger.error(f"Failed to save error status: {save_err}")

    finally:
        # ── Cleanup temp file if we downloaded from Cloudinary ────────────────
        if temp_file_path and os.path.exists(temp_file_path):
            try:
                os.remove(temp_file_path)
                # Remove temp dir too
                tmp_dir = os.path.dirname(temp_file_path)
                if os.path.exists(tmp_dir) and not os.listdir(tmp_dir):
                    os.rmdir(tmp_dir)
                logger.info(f"Cleaned up temp file: {temp_file_path}")
            except Exception as cleanup_err:
                logger.warning(f"Failed to cleanup temp file: {cleanup_err}")