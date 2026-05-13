# backend/app/api/summary.py

import logging
from fastapi import APIRouter, Depends

from app.models.user import User
from app.models.file_record import FileRecord
from app.models.schemas import SummaryResponse
from app.core.exceptions import NotFoundError, AuthorizationError
from app.services.summary_service import get_or_create_summary
from app.dependencies import get_current_user

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/summary", tags=["Summary"])


@router.get("/{file_id}", response_model=SummaryResponse)
async def get_summary(
    file_id: str,
    current_user: User = Depends(get_current_user),
):
    """Get AI-generated summary of a file's content."""
    file_record = await FileRecord.find_one(FileRecord.id == file_id)

    if not file_record:
        raise NotFoundError("File")

    if file_record.user_id != current_user.id:
        raise AuthorizationError("You don't have access to this file")

    try:
        result = await get_or_create_summary(file_id, current_user.id)
    except ValueError as e:
        from fastapi import HTTPException
        raise HTTPException(status_code=400, detail=str(e))

    return SummaryResponse(
        file_id=file_id,
        filename=file_record.original_filename,
        summary=result["summary"],
        key_topics=result.get("key_topics", []),
        word_count=result.get("word_count", 0),
        cached=result.get("cached", False),
    )