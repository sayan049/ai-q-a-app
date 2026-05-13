# backend/app/models/schemas.py

from pydantic import BaseModel, EmailStr, Field, field_validator
from typing import Optional, List, Any
from datetime import datetime
from enum import Enum


# ─── Auth Schemas ──────────────────────────────────────────────────────────────

class UserRegisterRequest(BaseModel):
    email: EmailStr
    username: str = Field(min_length=3, max_length=50)
    password: str = Field(min_length=8, max_length=100)

    @field_validator("username")
    @classmethod
    def username_alphanumeric(cls, v):
        if not v.replace("_", "").replace("-", "").isalnum():
            raise ValueError(
                "Username must be alphanumeric (underscores/hyphens allowed)"
            )
        return v


class UserLoginRequest(BaseModel):
    email: EmailStr
    password: str


class TokenResponse(BaseModel):
    access_token: str
    refresh_token: str
    token_type: str = "bearer"
    expires_in: int


class RefreshTokenRequest(BaseModel):
    refresh_token: str


class UserResponse(BaseModel):
    id: str
    email: str
    username: str
    avatar_url: Optional[str] = None
    created_at: datetime
    is_active: bool

    model_config = {"from_attributes": True}


# ─── File Schemas ──────────────────────────────────────────────────────────────

class FileUploadResponse(BaseModel):
    file_id: str
    user_id: str
    filename: str
    file_type: str
    status: str
    size_bytes: int
    message: str
    cloudinary_url: Optional[str] = None   # ← NEW
    storage_type: str = "local"             # ← NEW


class FileRecordResponse(BaseModel):
    id: str
    user_id: str
    filename: str
    original_filename: str
    file_type: str
    status: str
    size_bytes: int
    upload_time: datetime
    processed_time: Optional[datetime] = None
    chunk_count: int
    duration: Optional[float] = None
    page_count: Optional[int] = None
    error_message: Optional[str] = None
    cloudinary_url: Optional[str] = None   # ← NEW
    storage_type: str = "local"             # ← NEW

    model_config = {"from_attributes": True}


class FileListResponse(BaseModel):
    files: List[FileRecordResponse]
    total: int


# ─── Chat Schemas ──────────────────────────────────────────────────────────────

class ChatRequest(BaseModel):
    query: str = Field(min_length=1, max_length=2000)
    file_id: str
    include_history: bool = True

    @field_validator("query")
    @classmethod
    def query_not_whitespace(cls, v):
        if not v.strip():
            raise ValueError("Query cannot be empty or whitespace")
        return v.strip()


class TimestampInfo(BaseModel):
    start: float
    end: float
    text: str


class SourceInfo(BaseModel):
    chunk_index: int
    text_preview: str
    page_num: Optional[int] = None
    start_time: Optional[float] = None


class ChatMessageResponse(BaseModel):
    id: str
    role: str
    content: str
    timestamps: List[TimestampInfo] = []
    sources: List[SourceInfo] = []
    created_at: datetime


class ChatHistoryResponse(BaseModel):
    messages: List[ChatMessageResponse]
    total: int


# ─── Summary Schemas ───────────────────────────────────────────────────────────

class SummaryResponse(BaseModel):
    file_id: str
    filename: str
    summary: str
    key_topics: List[str] = []
    word_count: int
    cached: bool = False


# ─── SSE Event Schemas ─────────────────────────────────────────────────────────

class SSETokenEvent(BaseModel):
    token: str
    done: bool = False


class SSEDoneEvent(BaseModel):
    done: bool = True
    full_response: str
    timestamps: List[TimestampInfo] = []
    sources: List[SourceInfo] = []
    message_id: str


class SSEErrorEvent(BaseModel):
    error: str
    done: bool = True


# ─── Generic Schemas ───────────────────────────────────────────────────────────

class MessageResponse(BaseModel):
    message: str
    detail: Optional[Any] = None


class ErrorResponse(BaseModel):
    error: str
    detail: Optional[Any] = None
    status_code: int