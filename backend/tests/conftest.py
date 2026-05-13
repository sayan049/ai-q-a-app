# backend/tests/conftest.py

import asyncio
import pytest
import pytest_asyncio
from httpx import AsyncClient, ASGITransport
from unittest.mock import AsyncMock, MagicMock, patch
from typing import AsyncGenerator


# ── Event Loop ────────────────────────────────────────────────────────────────

@pytest.fixture(scope="session")
def event_loop():
    """Create event loop for the test session."""
    loop = asyncio.new_event_loop()
    yield loop
    loop.close()


# ── Mock Settings ─────────────────────────────────────────────────────────────

@pytest.fixture(autouse=True)
def mock_settings(tmp_path):
    """Override settings for tests."""
    with patch("app.config.settings") as mock_s:
        mock_s.mongo_url = "mongodb://localhost:27017"
        mock_s.mongo_db_name = "test_aiqa_db"
        mock_s.redis_url = "redis://localhost:6379"
        mock_s.jwt_secret = "test-secret-key-for-testing-only"
        mock_s.jwt_algorithm = "HS256"
        mock_s.access_token_expire_minutes = 15
        mock_s.refresh_token_expire_days = 7
        mock_s.groq_api_key = "test-groq-key"
        mock_s.github_client_id = "test-github-id"
        mock_s.github_client_secret = "test-github-secret"
        mock_s.github_redirect_uri = "http://localhost:8000/api/v1/auth/oauth/github/callback"
        mock_s.ollama_base_url = "http://localhost:11434"
        mock_s.ollama_model = "llama3"
        mock_s.max_file_size_mb = 500
        mock_s.max_file_size_bytes = 500 * 1024 * 1024
        mock_s.upload_dir = str(tmp_path / "uploads")
        mock_s.index_dir = str(tmp_path / "indexes")
        mock_s.debug = True
        mock_s.app_name = "Test AI Q&A App"
        mock_s.allowed_origins = "http://localhost:3000"
        mock_s.allowed_origins_list = ["http://localhost:3000"]
        import os
        os.makedirs(mock_s.upload_dir, exist_ok=True)
        os.makedirs(mock_s.index_dir, exist_ok=True)
        yield mock_s


# ── Fake Redis ────────────────────────────────────────────────────────────────

@pytest.fixture
def fake_redis():
    """In-memory Redis for testing."""
    import fakeredis.aioredis
    return fakeredis.aioredis.FakeRedis(decode_responses=True)


@pytest.fixture(autouse=True)
def mock_redis(fake_redis):
    """Patch Redis client with fakeredis."""
    with patch("app.services.cache_service._redis_client", fake_redis):
        yield fake_redis


# ── Mock MongoDB ──────────────────────────────────────────────────────────────

@pytest_asyncio.fixture
async def mock_db():
    """Setup test MongoDB using mongomock."""
    import mongomock_motor
    from beanie import init_beanie
    from app.models.user import User
    from app.models.file_record import FileRecord, ChunkMetadata
    from app.models.chat_message import ChatMessage

    client = mongomock_motor.AsyncMongoMockClient()
    await init_beanie(
        database=client["test_db"],
        document_models=[User, FileRecord, ChunkMetadata, ChatMessage],
    )
    yield client
    # Cleanup
    await User.find_all().delete()
    await FileRecord.find_all().delete()
    await ChunkMetadata.find_all().delete()
    await ChatMessage.find_all().delete()


# ── Test App & Client ─────────────────────────────────────────────────────────

@pytest_asyncio.fixture
async def test_app(mock_db):
    """Create test FastAPI app with mocked dependencies."""
    from app.main import app
    yield app


@pytest_asyncio.fixture
async def client(test_app) -> AsyncGenerator[AsyncClient, None]:
    """Async test client."""
    async with AsyncClient(
        transport=ASGITransport(app=test_app),
        base_url="http://test",
    ) as ac:
        yield ac


# ── Test User & Auth Fixtures ─────────────────────────────────────────────────

@pytest_asyncio.fixture
async def test_user(mock_db):
    """Create a test user in the database."""
    from app.models.user import User
    from app.core.auth import hash_password

    user = User(
        id="test-user-id-123",
        email="test@example.com",
        username="testuser",
        hashed_password=hash_password("TestPassword123"),
        is_active=True,
        is_verified=True,
    )
    await user.insert()
    return user


@pytest.fixture
def test_user_token(test_user):
    """Generate a valid JWT for test user."""
    from app.core.auth import create_access_token
    return create_access_token(test_user.id, test_user.email)


@pytest.fixture
def auth_headers(test_user_token):
    """HTTP headers with JWT for authenticated requests."""
    return {"Authorization": f"Bearer {test_user_token}"}


# ── Test File Fixtures ────────────────────────────────────────────────────────

@pytest.fixture
def sample_pdf_bytes(tmp_path):
    """Create a minimal valid PDF file."""
    import fitz
    doc = fitz.open()
    page = doc.new_page()
    page.insert_text((50, 50), "This is a test PDF document. It contains sample text for testing.")
    page.insert_text((50, 100), "Machine learning is a subset of artificial intelligence.")
    page.insert_text((50, 150), "Python is a popular programming language.")
    pdf_path = str(tmp_path / "test.pdf")
    doc.save(pdf_path)
    doc.close()
    with open(pdf_path, "rb") as f:
        return f.read()


@pytest.fixture
def sample_audio_bytes():
    """Create a minimal WAV file."""
    import struct
    import wave
    import io

    buffer = io.BytesIO()
    with wave.open(buffer, 'w') as wav_file:
        wav_file.setnchannels(1)
        wav_file.setsampwidth(2)
        wav_file.setframerate(16000)
        # 1 second of silence
        frames = struct.pack('<' + 'h' * 16000, *([0] * 16000))
        wav_file.writeframes(frames)

    return buffer.getvalue()


# ── Mock External Services ────────────────────────────────────────────────────

@pytest.fixture
def mock_whisper():
    """Mock Whisper model to avoid loading the actual model."""
    mock_model = MagicMock()
    mock_model.transcribe.return_value = {
        "segments": [
            {"text": " Hello world", "start": 0.0, "end": 2.5},
            {"text": " This is a test", "start": 2.5, "end": 5.0},
            {"text": " Machine learning is fascinating", "start": 5.0, "end": 8.0},
        ],
        "text": " Hello world This is a test Machine learning is fascinating",
    }

    with patch("app.services.transcription._whisper_model", mock_model):
        with patch("app.services.transcription.get_whisper_model", return_value=mock_model):
            yield mock_model


@pytest.fixture
def mock_groq_stream():
    """Mock Groq streaming response."""
    async def mock_stream_answer(query, context_chunks, chat_history=None):
        tokens = ["This ", "is ", "a ", "test ", "answer ", "from ", "the ", "AI."]
        for token in tokens:
            yield token

    with patch("app.services.llm_service.stream_answer", side_effect=mock_stream_answer):
        yield


@pytest.fixture
def mock_vector_search():
    """Mock vector search results."""
    mock_results = [
        {
            "chunk_index": 0,
            "text": "Machine learning is a subset of artificial intelligence.",
            "score": 0.95,
            "start_time": 0.0,
            "end_time": 5.0,
            "page_num": None,
        },
        {
            "chunk_index": 1,
            "text": "Python is widely used in data science.",
            "score": 0.87,
            "start_time": 5.0,
            "end_time": 10.0,
            "page_num": None,
        },
    ]

    with patch.object(
        __import__("app.services.vector_service", fromlist=["vector_service"]).vector_service,
        "search",
        return_value=mock_results,
    ):
        yield mock_results
        
# Add to backend/tests/conftest.py

@pytest_asyncio.fixture(autouse=True)
def set_cache_client(fake_redis):
    """Ensure every test uses fake_redis as the cache client."""
    from app.services import cache_service
    original = cache_service._redis_client
    cache_service._redis_client = fake_redis
    yield
    cache_service._redis_client = original