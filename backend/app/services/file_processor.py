# backend/app/services/file_processor.py

import os
import logging
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


async def process_file(
    file_id: str,
    file_path: str,
    file_type: FileType,
    user_id: str,
):
    """
    Background task: process uploaded file.
    Updates FileRecord status throughout.
    """
    logger.info(f"Starting processing: {file_id} (type: {file_type.value})")

    file_record = await FileRecord.find_one(FileRecord.id == file_id)
    if not file_record:
        logger.error(f"FileRecord {file_id} not found")
        return

    try:
        file_record.status = FileStatus.PROCESSING
        await file_record.save()

        chunks = []

        # ── PDF ───────────────────────────────────────────────────────────────
        if file_type == FileType.PDF:
            logger.info(f"Extracting PDF text: {file_path}")

            meta = get_pdf_metadata(file_path)
            file_record.page_count = meta.get("page_count", 0)

            pages, full_text = extract_text_from_pdf(file_path)

            chunks = chunk_pdf_pages(pages, chunk_size=500, overlap=50)

            logger.info(f"PDF: {len(pages)} pages → {len(chunks)} chunks")

        # ── Audio / Video ─────────────────────────────────────────────────────
        elif file_type in (FileType.AUDIO, FileType.VIDEO):
            logger.info(f"Transcribing {file_type.value}: {file_path}")

            segments, full_text = transcribe(file_path, file_type.value)

            if not segments:
                logger.warning(f"No speech detected: {file_path}")
                file_record.status         = FileStatus.READY
                file_record.chunk_count    = 0
                file_record.processed_time = datetime.utcnow()
                await file_record.save()
                return

            file_record.duration = round(segments[-1]["end"], 2)

            # 40 words ≈ 12-15 seconds per chunk → precise timestamps
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