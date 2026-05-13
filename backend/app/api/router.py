# backend/app/api/router.py

from fastapi import APIRouter
from app.api import auth, files, chat, summary

api_router = APIRouter(prefix="/api/v1")

api_router.include_router(auth.router)
api_router.include_router(files.router)
api_router.include_router(chat.router)
api_router.include_router(summary.router)