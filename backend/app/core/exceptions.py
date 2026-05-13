# backend/app/core/exceptions.py

from fastapi import HTTPException, status


class AuthenticationError(HTTPException):
    def __init__(self, detail: str = "Could not validate credentials"):
        super().__init__(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=detail,
            headers={"WWW-Authenticate": "Bearer"},
        )


class AuthorizationError(HTTPException):
    def __init__(self, detail: str = "Not enough permissions"):
        super().__init__(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=detail,
        )


class NotFoundError(HTTPException):
    def __init__(self, resource: str = "Resource"):
        super().__init__(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"{resource} not found",
        )


class ValidationError(HTTPException):
    def __init__(self, detail: str):
        super().__init__(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=detail,
        )


class FileTooLargeError(HTTPException):
    def __init__(self, max_mb: int = 500):
        super().__init__(
            status_code=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE,
            detail=f"File too large. Maximum size is {max_mb}MB",
        )


class UnsupportedFileTypeError(HTTPException):
    def __init__(self, file_type: str = ""):
        super().__init__(
            status_code=status.HTTP_415_UNSUPPORTED_MEDIA_TYPE,
            detail=f"Unsupported file type: {file_type}. Allowed: PDF, MP3, MP4, WAV, WEBM, OGG",
        )


class FileProcessingError(HTTPException):
    def __init__(self, detail: str = "File processing failed"):
        super().__init__(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=detail,
        )


class FileNotReadyError(HTTPException):
    def __init__(self):
        super().__init__(
            status_code=status.HTTP_202_ACCEPTED,
            detail="File is still being processed. Please wait.",
        )


class RateLimitExceeded(HTTPException):
    def __init__(self, retry_after: int = 60):
        super().__init__(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail="Rate limit exceeded",
            headers={"Retry-After": str(retry_after)},
        )


class LLMServiceError(HTTPException):
    def __init__(self, detail: str = "LLM service unavailable"):
        super().__init__(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail=detail,
        )


class DuplicateFileError(HTTPException):
    def __init__(self, existing_file_id: str):
        super().__init__(
            status_code=status.HTTP_409_CONFLICT,
            detail=f"File already uploaded. Existing file ID: {existing_file_id}",
        )