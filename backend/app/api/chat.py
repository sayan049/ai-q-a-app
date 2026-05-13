# backend/app/api/chat.py

import json
import logging
import uuid
from typing import AsyncGenerator

from fastapi import APIRouter, Depends, Request, Query
from sse_starlette.sse import EventSourceResponse

from app.models.user import User
from app.models.file_record import FileRecord, FileStatus
from app.models.chat_message import ChatMessage, MessageRole, TimestampRef, SourceRef
from app.models.schemas import (
    ChatHistoryResponse,
    ChatMessageResponse,
    TimestampInfo,
    SourceInfo,
)
from app.core.exceptions import (
    NotFoundError,
    AuthorizationError,
    FileNotReadyError,
    LLMServiceError,
)
from app.core.rate_limiter import limiter
from app.services.vector_service import vector_service
from app.services.llm_service import stream_answer, extract_timestamps_from_chunks
from app.services.cache_service import (
    make_chat_cache_key,
    cache_get,
    cache_set,
)
from app.dependencies import get_current_user

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/chat", tags=["Chat"])


@router.get("/ask")
@limiter.limit("50/hour")
async def ask_question(
    request: Request,
    query: str = Query(min_length=1, max_length=2000),
    file_id: str = Query(...),
    current_user: User = Depends(get_current_user),
):
    """Stream AI answer via SSE. Checks Redis cache first."""

    query = query.strip()
    if not query:
        from fastapi import HTTPException
        raise HTTPException(status_code=400, detail="Query cannot be empty")

    file_record = await FileRecord.find_one(FileRecord.id == file_id)
    if not file_record:
        raise NotFoundError("File")
    if file_record.user_id != current_user.id:
        raise AuthorizationError("You don't have access to this file")
    if file_record.status in (FileStatus.PROCESSING, FileStatus.UPLOADING):
        raise FileNotReadyError()
    if file_record.status == FileStatus.FAILED:
        raise LLMServiceError("File processing failed. Please re-upload.")

    # ── Cache check ───────────────────────────────────────────────────────────
    cache_key = make_chat_cache_key(file_id, query)
    cached_result = await cache_get(cache_key)

    async def generate_cached() -> AsyncGenerator:
        full_response = cached_result.get("full_response", "")
        words = full_response.split()
        chunk_size = 3
        for i in range(0, len(words), chunk_size):
            chunk = " ".join(words[i:i + chunk_size])
            if i + chunk_size < len(words):
                chunk += " "
            yield {
                "event": "message",
                "data": json.dumps({"token": chunk, "done": False}),
            }
        yield {
            "event": "message",
            "data": json.dumps({
                "done":          True,
                "full_response": full_response,
                "timestamps":    cached_result.get("timestamps", []),
                "sources":       cached_result.get("sources", []),
                "message_id":    cached_result.get("message_id", ""),
                "cached":        True,
            }),
        }

    if cached_result:
        logger.info(f"Cache hit: '{query[:40]}' (file: {file_id})")
        return EventSourceResponse(generate_cached())

    # ── Vector search ─────────────────────────────────────────────────────────
    chunks = vector_service.search(file_id, query, top_k=5)

    # ── Chat history ──────────────────────────────────────────────────────────
    history_docs = await ChatMessage.find(
        ChatMessage.file_id == file_id,
        ChatMessage.user_id == current_user.id,
    ).sort(ChatMessage.created_at).limit(10).to_list()

    chat_history = [
        {"role": msg.role.value, "content": msg.content}
        for msg in history_docs
    ]

    # ── Timestamps + sources ──────────────────────────────────────────────────
    timestamps = extract_timestamps_from_chunks(chunks)
    sources = [
        {
            "chunk_index":  c.get("chunk_index", 0),
            "text_preview": c["text"][:150],
            "page_num":     c.get("page_num"),
            "start_time":   c.get("start_time"),
        }
        for c in chunks
    ]

    # ── Stream ────────────────────────────────────────────────────────────────
    message_id = str(uuid.uuid4())
    full_response_parts: list[str] = []

    async def generate_stream() -> AsyncGenerator:
        # Save user message
        await ChatMessage(
            id=str(uuid.uuid4()),
            user_id=current_user.id,
            file_id=file_id,
            role=MessageRole.USER,
            content=query,
        ).insert()

        try:
            async for token in stream_answer(query, chunks, chat_history):
                full_response_parts.append(token)
                yield {
                    "event": "message",
                    "data": json.dumps({"token": token, "done": False}),
                }

            full_response = "".join(full_response_parts)

            # Save AI message
            await ChatMessage(
                id=message_id,
                user_id=current_user.id,
                file_id=file_id,
                role=MessageRole.ASSISTANT,
                content=full_response,
                timestamps=[
                    TimestampRef(start=t["start"], end=t["end"], text=t["text"])
                    for t in timestamps
                ],
                sources=[
                    SourceRef(
                        chunk_index=s["chunk_index"],
                        text_preview=s["text_preview"],
                        page_num=s.get("page_num"),
                        start_time=s.get("start_time"),
                    )
                    for s in sources
                ],
            ).insert()

            # Cache
            await cache_set(cache_key, {
                "full_response": full_response,
                "timestamps":    timestamps,
                "sources":       sources,
                "message_id":    message_id,
            }, ttl=3600)

            yield {
                "event": "message",
                "data": json.dumps({
                    "done":          True,
                    "full_response": full_response,
                    "timestamps":    timestamps,
                    "sources":       sources,
                    "message_id":    message_id,
                    "cached":        False,
                }),
            }

        except Exception as e:
            logger.error(f"Streaming error: {e}")
            yield {
                "event": "message",
                "data": json.dumps({"error": str(e), "done": True}),
            }

    return EventSourceResponse(generate_stream())


@router.get("/history/{file_id}", response_model=ChatHistoryResponse)
async def get_chat_history(
    file_id: str,
    limit: int = 50,
    skip: int = 0,
    current_user: User = Depends(get_current_user),
):
    """Get chat history for a specific file."""
    file_record = await FileRecord.find_one(FileRecord.id == file_id)
    if not file_record:
        raise NotFoundError("File")
    if file_record.user_id != current_user.id:
        raise AuthorizationError("You don't have access to this file")

    messages = await ChatMessage.find(
        ChatMessage.file_id == file_id,
        ChatMessage.user_id == current_user.id,
    ).sort(ChatMessage.created_at).skip(skip).limit(limit).to_list()

    total = await ChatMessage.find(
        ChatMessage.file_id == file_id,
        ChatMessage.user_id == current_user.id,
    ).count()

    return ChatHistoryResponse(
        messages=[
            ChatMessageResponse(
                id=msg.id,
                role=msg.role.value,
                content=msg.content,
                timestamps=[
                    TimestampInfo(start=t.start, end=t.end, text=t.text)
                    for t in msg.timestamps
                ],
                sources=[
                    SourceInfo(
                        chunk_index=s.chunk_index,
                        text_preview=s.text_preview,
                        page_num=s.page_num,
                        start_time=s.start_time,
                    )
                    for s in msg.sources
                ],
                created_at=msg.created_at,
            )
            for msg in messages
        ],
        total=total,
    )


@router.delete("/history/{file_id}")
async def clear_chat_history(
    file_id: str,
    current_user: User = Depends(get_current_user),
):
    """Clear chat history for a specific file."""
    file_record = await FileRecord.find_one(FileRecord.id == file_id)
    if not file_record:
        raise NotFoundError("File")
    if file_record.user_id != current_user.id:
        raise AuthorizationError("You don't have access to this file")

    delete_result = await ChatMessage.find(
        ChatMessage.file_id == file_id,
        ChatMessage.user_id == current_user.id,
    ).delete()

    # Convert DeleteResult to plain int — fixes PydanticSerializationError
    deleted_count = int(delete_result.deleted_count) if delete_result else 0

    return {"message": "Chat history cleared", "deleted_count": deleted_count}