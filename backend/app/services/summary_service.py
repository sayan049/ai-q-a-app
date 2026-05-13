# backend/app/services/summary_service.py

import logging
from typing import Dict, Optional
from app.models.file_record import FileRecord, FileStatus, ChunkMetadata
from app.services import llm_service
from app.services import cache_service

logger = logging.getLogger(__name__)


async def get_or_create_summary(file_id: str, user_id: str) -> Dict:
    """
    Get cached summary or generate a new one.
    Returns: {summary, key_topics, word_count, cached}
    """
    # Check cache
    cache_key = cache_service.make_summary_cache_key(file_id)
    cached = await cache_service.cache_get(cache_key)
    if cached:
        logger.info(f"Summary cache hit for file {file_id}")
        cached["cached"] = True
        return cached

    # Get file record
    file_record = await FileRecord.find_one(
        FileRecord.id == file_id,
        FileRecord.user_id == user_id,
    )

    if not file_record:
        raise ValueError(f"File {file_id} not found")

    if file_record.status != FileStatus.READY:
        raise ValueError(f"File {file_id} is not ready (status: {file_record.status})")

    # Get all chunks for this file to build context
    chunks = await ChunkMetadata.find(
        ChunkMetadata.file_id == file_id,
        ChunkMetadata.user_id == user_id,
    ).sort(ChunkMetadata.chunk_index).to_list()

    if not chunks:
        return {
            "summary": "No content available for summarization.",
            "key_topics": [],
            "word_count": 0,
            "cached": False,
        }

    # Build full text from chunks (avoid duplicate overlap)
    full_text = " ".join(c.text for c in chunks[:20])  # Limit to first 20 chunks
    word_count = sum(c.word_count for c in chunks)

    # Generate summary
    file_type_str = file_record.file_type.value
    result = await llm_service.generate_summary(full_text, file_type_str)

    summary_data = {
        "summary": result.get("summary", ""),
        "key_topics": result.get("key_topics", []),
        "word_count": word_count,
        "cached": False,
    }

    # Cache for 1 hour
    await cache_service.cache_set(cache_key, summary_data, ttl=3600)

    return summary_data