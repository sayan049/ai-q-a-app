# backend/app/services/storage_service.py

import os
import logging
import httpx
from app.config import settings

logger = logging.getLogger(__name__)


def _configure_cloudinary():
    """Configure and return cloudinary module."""
    import cloudinary
    import cloudinary.uploader
    import cloudinary.api

    cloudinary.config(
        cloud_name=settings.cloudinary_cloud_name,
        api_key=settings.cloudinary_api_key,
        api_secret=settings.cloudinary_api_secret,
        secure=True,
    )
    return cloudinary


async def upload_file(
    file_path: str,
    file_id: str,
    user_id: str,
) -> dict:
    """
    Upload a file to Cloudinary if configured, otherwise use local storage.

    Returns:
        {
            "url": "https://res.cloudinary.com/...",
            "public_id": "aiqa/user_id/file_id",
            "storage": "cloudinary" or "local",
        }
    """
    if not settings.cloudinary_enabled:
        logger.info("Cloudinary not configured — using local storage")
        return {
            "url": None,
            "public_id": None,
            "storage": "local",
        }

    try:
        cloudinary = _configure_cloudinary()

        public_id   = f"aiqa/{user_id}/{file_id}"
        ext         = file_path.rsplit(".", 1)[-1].lower() if "." in file_path else ""

        # Determine resource type
        if ext in ("mp4", "webm", "avi", "mov", "mkv"):
            resource_type = "video"
        elif ext in ("mp3", "wav", "ogg", "flac", "m4a", "aiff"):
            resource_type = "raw"   # Cloudinary uses "raw" for audio
        else:
            resource_type = "raw"   # PDF and others

        logger.info(f"Uploading to Cloudinary: {public_id} ({resource_type})")

        result = cloudinary.uploader.upload(
            file_path,
            public_id=public_id,
            resource_type=resource_type,
            overwrite=True,
        )

        url = result.get("secure_url", "")
        logger.info(f"✅ Cloudinary upload success: {url}")

        return {
            "url": url,
            "public_id": result.get("public_id", public_id),
            "storage": "cloudinary",
        }

    except Exception as e:
        logger.error(f"❌ Cloudinary upload failed: {e} — falling back to local")
        return {
            "url": None,
            "public_id": None,
            "storage": "local",
        }


async def delete_file(public_id: str) -> bool:
    """
    Delete a file from Cloudinary by its public_id.
    Returns True if deleted successfully.
    """
    if not settings.cloudinary_enabled or not public_id:
        return True

    try:
        cloudinary = _configure_cloudinary()

        # Try all resource types
        for resource_type in ("raw", "video", "image"):
            try:
                result = cloudinary.uploader.destroy(
                    public_id,
                    resource_type=resource_type,
                )
                if result.get("result") == "ok":
                    logger.info(f"✅ Deleted from Cloudinary: {public_id}")
                    return True
            except Exception:
                continue

        return False

    except Exception as e:
        logger.error(f"Cloudinary delete failed: {e}")
        return False


async def download_file_for_processing(url: str, local_path: str) -> str:
    """
    Download a file from Cloudinary URL to a local temp path for AI processing.
    Returns the local path.
    """
    try:
        os.makedirs(os.path.dirname(local_path), exist_ok=True)

        async with httpx.AsyncClient(timeout=120) as client:
            response = await client.get(url)
            response.raise_for_status()

            with open(local_path, "wb") as f:
                f.write(response.content)

        logger.info(f"✅ Downloaded from Cloudinary → {local_path}")
        return local_path

    except Exception as e:
        logger.error(f"❌ Cloudinary download failed: {e}")
        raise RuntimeError(f"Could not download file for processing: {str(e)}")