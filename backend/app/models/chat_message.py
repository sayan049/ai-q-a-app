# backend/app/models/chat_message.py

from beanie import Document
from pydantic import BaseModel, Field
from datetime import datetime
from typing import Optional, List
from enum import Enum
import uuid


class MessageRole(str, Enum):
    USER = "user"
    ASSISTANT = "assistant"
    SYSTEM = "system"


class TimestampRef(BaseModel):
    start: float
    end: float
    text: str


class SourceRef(BaseModel):
    chunk_index: int
    text_preview: str
    page_num: Optional[int] = None
    start_time: Optional[float] = None


class ChatMessage(Document):
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    user_id: str
    file_id: str
    role: MessageRole
    content: str
    timestamps: List[TimestampRef] = Field(default_factory=list)
    sources: List[SourceRef] = Field(default_factory=list)
    created_at: datetime = Field(default_factory=datetime.utcnow)
    tokens_used: Optional[int] = None

    class Settings:
        name = "chat_messages"