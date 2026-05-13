# backend/app/config.py

from pydantic_settings import BaseSettings
from pydantic import Field
from functools import lru_cache
import os


class Settings(BaseSettings):
    # App
    app_name: str = Field(default="AI Q&A App", alias="APP_NAME")
    debug: bool = Field(default=False, alias="DEBUG")
    allowed_origins: str = Field(
        default="http://localhost:3000,http://localhost:5173,http://localhost",
        alias="ALLOWED_ORIGINS"
    )

    # MongoDB
    mongo_url: str = Field(
        default="mongodb://admin:secret@localhost:27017",
        alias="MONGO_URL"
    )
    mongo_db_name: str = Field(default="aiqa_db", alias="MONGO_DB_NAME")

    # Redis
    redis_url: str = Field(default="redis://localhost:6379", alias="REDIS_URL")

    # JWT
    jwt_secret: str = Field(default="change-this-secret", alias="JWT_SECRET")
    jwt_algorithm: str = Field(default="HS256", alias="JWT_ALGORITHM")
    access_token_expire_minutes: int = Field(
        default=15, alias="ACCESS_TOKEN_EXPIRE_MINUTES"
    )
    refresh_token_expire_days: int = Field(
        default=7, alias="REFRESH_TOKEN_EXPIRE_DAYS"
    )

    # Groq
    groq_api_key: str = Field(default="", alias="GROQ_API_KEY")

    # GitHub OAuth
    github_client_id: str = Field(default="", alias="GITHUB_CLIENT_ID")
    github_client_secret: str = Field(default="", alias="GITHUB_CLIENT_SECRET")
    github_redirect_uri: str = Field(
        default="http://localhost:8000/api/v1/auth/oauth/github/callback",
        alias="GITHUB_REDIRECT_URI"
    )

    # Ollama fallback
    ollama_base_url: str = Field(
        default="http://localhost:11434", alias="OLLAMA_BASE_URL"
    )
    ollama_model: str = Field(default="llama3", alias="OLLAMA_MODEL")

    # File settings
    max_file_size_mb: int = Field(default=500, alias="MAX_FILE_SIZE_MB")
    upload_dir: str = Field(default="./uploads", alias="UPLOAD_DIR")
    index_dir: str = Field(default="./indexes", alias="INDEX_DIR")

    # ── Cloudinary (Free file storage) ───────────────────────────────────────
    cloudinary_cloud_name: str = Field(default="", alias="CLOUDINARY_CLOUD_NAME")
    cloudinary_api_key: str = Field(default="", alias="CLOUDINARY_API_KEY")
    cloudinary_api_secret: str = Field(default="", alias="CLOUDINARY_API_SECRET")

    class Config:
        env_file = ".env"
        populate_by_name = True
        extra = "ignore"

    @property
    def allowed_origins_list(self) -> list[str]:
        return [origin.strip() for origin in self.allowed_origins.split(",")]

    @property
    def max_file_size_bytes(self) -> int:
        return self.max_file_size_mb * 1024 * 1024

    @property
    def cloudinary_enabled(self) -> bool:
        """Returns True if all Cloudinary credentials are configured."""
        return bool(
            self.cloudinary_cloud_name
            and self.cloudinary_api_key
            and self.cloudinary_api_secret
        )


@lru_cache()
def get_settings() -> Settings:
    return Settings()


settings = get_settings()

# Ensure directories exist
os.makedirs(settings.upload_dir, exist_ok=True)
os.makedirs(settings.index_dir, exist_ok=True)