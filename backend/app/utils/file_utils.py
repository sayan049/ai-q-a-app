# backend/app/utils/file_utils.py

import os
import hashlib
import mimetypes
from pathlib import Path
from typing import Tuple, Optional
from app.config import settings


ALLOWED_MIME_TYPES = {
    # PDF
    "application/pdf": "pdf",
    # Audio
    "audio/mpeg": "audio",
    "audio/mp3": "audio",
    "audio/wav": "audio",
    "audio/x-wav": "audio",
    "audio/wave": "audio",
    "audio/ogg": "audio",
    "audio/webm": "audio",
    "audio/mp4": "audio",
    "audio/flac": "audio",
    # Video
    "video/mp4": "video",
    "video/webm": "video",
    "video/ogg": "video",
    "video/avi": "video",
    "video/quicktime": "video",
    "video/x-msvideo": "video",
}

ALLOWED_EXTENSIONS = {
    ".pdf": "pdf",
    ".mp3": "audio",
    ".wav": "audio",
    ".ogg": "audio",
    ".webm": "audio",
    ".flac": "audio",
    ".m4a": "audio",
    ".mp4": "video",
    ".avi": "video",
    ".mov": "video",
    ".mkv": "video",
}


def detect_file_type(filename: str, mime_type: str) -> Optional[str]:
    """
    Returns 'pdf', 'audio', or 'video' based on mime type and extension.
    Returns None if not allowed.
    """
    # Check MIME type first
    if mime_type in ALLOWED_MIME_TYPES:
        return ALLOWED_MIME_TYPES[mime_type]

    # Fallback to extension
    ext = Path(filename).suffix.lower()
    if ext in ALLOWED_EXTENSIONS:
        return ALLOWED_EXTENSIONS[ext]

    return None


def get_safe_filename(filename: str) -> str:
    """Sanitize filename to prevent path traversal."""
    # Remove any path components
    filename = os.path.basename(filename)
    # Replace dangerous characters
    safe_chars = set("abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789.-_")
    sanitized = "".join(c if c in safe_chars else "_" for c in filename)
    return sanitized or "uploaded_file"


def get_file_hash(file_path: str) -> str:
    """Compute SHA256 hash of file for deduplication."""
    sha256 = hashlib.sha256()
    with open(file_path, "rb") as f:
        for block in iter(lambda: f.read(65536), b""):
            sha256.update(block)
    return sha256.hexdigest()


def get_upload_path(user_id: str, file_id: str, filename: str) -> str:
    """
    Returns absolute path for uploaded file.
    Structure: uploads/{user_id}/{file_id}/original.{ext}
    """
    ext = Path(filename).suffix.lower()
    dir_path = os.path.join(settings.upload_dir, user_id, file_id)
    os.makedirs(dir_path, exist_ok=True)
    return os.path.join(dir_path, f"original{ext}")


def cleanup_file(file_path: str) -> bool:
    """Delete a file from disk. Returns True if deleted."""
    try:
        if os.path.exists(file_path):
            os.remove(file_path)
            # Try to remove empty parent directory
            parent = os.path.dirname(file_path)
            if os.path.exists(parent) and not os.listdir(parent):
                os.rmdir(parent)
            return True
    except OSError:
        pass
    return False


def format_file_size(size_bytes: int) -> str:
    """Human-readable file size."""
    if size_bytes < 1024:
        return f"{size_bytes} B"
    elif size_bytes < 1024 ** 2:
        return f"{size_bytes / 1024:.1f} KB"
    elif size_bytes < 1024 ** 3:
        return f"{size_bytes / (1024**2):.1f} MB"
    else:
        return f"{size_bytes / (1024**3):.1f} GB"