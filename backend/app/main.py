# backend/app/main.py

# ── SSL Fix for Mac M4 + MongoDB Atlas ────────────────────────────────────────
import ssl
import certifi
import os

os.environ['SSL_CERT_FILE'] = certifi.where()
os.environ['REQUESTS_CA_BUNDLE'] = certifi.where()
# ─────────────────────────────────────────────────────────────────────────────

import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from fastapi.staticfiles import StaticFiles
from slowapi.errors import RateLimitExceeded

from app.config import settings
from app.api.router import api_router
from app.core.rate_limiter import limiter, rate_limit_exceeded_handler
from app.services.cache_service import get_redis, close_redis

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s | %(levelname)s | %(name)s | %(message)s",
)
logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    logger.info("🚀 Starting AI Q&A App...")

    # ── Connect MongoDB ───────────────────────────────────────────────────────
    try:
        from beanie import init_beanie
        from motor.motor_asyncio import AsyncIOMotorClient
        from app.models.user import User
        from app.models.file_record import FileRecord, ChunkMetadata
        from app.models.chat_message import ChatMessage

        client = AsyncIOMotorClient(
            settings.mongo_url,
            tlsCAFile=certifi.where(),
            serverSelectionTimeoutMS=30000,
        )
        await init_beanie(
            database=client[settings.mongo_db_name],
            document_models=[User, FileRecord, ChunkMetadata, ChatMessage],
        )
        logger.info("✅ MongoDB connected")
    except Exception as e:
        logger.error(f"❌ MongoDB connection failed: {e}")
        raise

    # ── Connect Redis ─────────────────────────────────────────────────────────
    try:
        redis = await get_redis()
        await redis.ping()
        logger.info("✅ Redis connected")
    except Exception as e:
        logger.warning(f"⚠️  Redis connection failed: {e}")

    # ── Ensure directories ────────────────────────────────────────────────────
    os.makedirs(settings.upload_dir, exist_ok=True)
    os.makedirs(settings.index_dir, exist_ok=True)
    logger.info(f"✅ Upload dir: {settings.upload_dir}")
    logger.info(f"✅ Index dir: {settings.index_dir}")
    logger.info("✅ App startup complete")

    yield

    logger.info("🛑 Shutting down...")
    await close_redis()
    logger.info("✅ Shutdown complete")


# ── Create App ────────────────────────────────────────────────────────────────
app = FastAPI(
    title=settings.app_name,
    description="AI-powered document and multimedia Q&A application",
    version="1.0.0",
    docs_url="/api/docs",
    redoc_url="/api/redoc",
    openapi_url="/api/openapi.json",
    lifespan=lifespan,
)

# ── Rate Limiter ──────────────────────────────────────────────────────────────
app.state.limiter = limiter
app.add_exception_handler(RateLimitExceeded, rate_limit_exceeded_handler)

# ── CORS ──────────────────────────────────────────────────────────────────────
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.allowed_origins_list,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ── Routers ───────────────────────────────────────────────────────────────────
app.include_router(api_router)

# ── Static Files ──────────────────────────────────────────────────────────────
if os.path.exists(settings.upload_dir):
    app.mount(
        "/uploads",
        StaticFiles(directory=settings.upload_dir),
        name="uploads",
    )


@app.exception_handler(Exception)
async def global_exception_handler(request: Request, exc: Exception):
    logger.error(f"Unhandled exception: {exc}", exc_info=True)
    return JSONResponse(
        status_code=500,
        content={
            "error": "Internal server error",
            "detail": str(exc) if settings.debug else "An unexpected error occurred",
        },
    )


@app.get("/health", tags=["Health"])
async def health_check():
    return {"status": "healthy", "app": settings.app_name, "version": "1.0.0"}


@app.get("/", tags=["Root"])
async def root():
    return {"message": f"Welcome to {settings.app_name}", "docs": "/api/docs"}