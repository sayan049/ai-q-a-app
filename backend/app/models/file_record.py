# backend/app/models/file_record.py

from beanie import Document
from pydantic import Field
from datetime import datetime
from typing import Optional, List
from enum import Enum
import uuid


class FileStatus(str, Enum):
    UPLOADING = "uploading"
    PROCESSING = "processing"
    READY = "ready"
    FAILED = "failed"


class FileType(str, Enum):
    PDF = "pdf"
    AUDIO = "audio"
    VIDEO = "video"


class ChunkMetadata(Document):
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    file_id: str
    user_id: str
    chunk_index: int
    text: str
    start_time: Optional[float] = None   # seconds (audio/video)
    end_time: Optional[float] = None     # seconds (audio/video)
    page_num: Optional[int] = None       # PDF pages
    word_count: int = 0

    class Settings:
        name = "chunks"


class FileRecord(Document):
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    user_id: str
    filename: str
    original_filename: str
    file_type: FileType
    mime_type: str
    status: FileStatus = FileStatus.UPLOADING
    size_bytes: int
    upload_time: datetime = Field(default_factory=datetime.utcnow)
    processed_time: Optional[datetime] = None
    error_message: Optional[str] = None

    # Content metadata
    chunk_count: int = 0
    duration: Optional[float] = None      # seconds (audio/video)
    page_count: Optional[int] = None      # PDF

    # File path on disk
    file_path: str = ""

    # Content hash for dedup
    file_hash: Optional[str] = None

    class Settings:
        name = "file_records"