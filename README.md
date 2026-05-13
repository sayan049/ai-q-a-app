````markdown
# 🧠 AI-Powered Document & Multimedia Q&A Web Application

<div align="center">

![Python](https://img.shields.io/badge/Python-3.11-blue?style=for-the-badge&logo=python)
![FastAPI](https://img.shields.io/badge/FastAPI-0.111-green?style=for-the-badge&logo=fastapi)
![React](https://img.shields.io/badge/React-18-61DAFB?style=for-the-badge&logo=react)
![MongoDB](https://img.shields.io/badge/MongoDB-Atlas-47A248?style=for-the-badge&logo=mongodb)
![Docker](https://img.shields.io/badge/Docker-Compose-2496ED?style=for-the-badge&logo=docker)
![Coverage](https://img.shields.io/badge/Coverage-97%25-brightgreen?style=for-the-badge)

**A full-stack, production-ready AI application that lets users upload PDFs, audio, and video files, then chat with an AI that answers questions based on the content — with real-time streaming, timestamp seeking, and semantic vector search.**

[Live Demo](#-live-demo) • [Quick Start](#-quick-start) • [API Docs](#-api-documentation) • [Architecture](#-architecture) • [Testing](#-testing)

</div>

---

# 🚀 Live Demo

| Resource | URL |
|---|---|
| **Live Application** | https://aiqa-frontend.onrender.com |
| **API Documentation** | https://aiqa-backend.onrender.com/api/docs |
| **Walkthrough Video** | YouTube / Google Drive Link |

> ⚠️ **Note:** The backend is hosted on Render's free tier. Please allow **30-60 seconds** for the initial cold start.

---

# ✨ Features

## 📄 Document Intelligence
- Upload **PDF** files and ask questions about their content
- AI provides answers with **page number references**
- One-click **AI Summary** with key topic extraction

## 🎵 Audio & Video Intelligence
- Upload **MP3, WAV, MP4, WebM** and more
- Local **OpenAI Whisper** transcription (zero cost, high accuracy)
- AI answers include **clickable `[MM:SS]` timestamp chips**
- Click a timestamp → media player **jumps to that exact moment**

## ⚡ Performance & UX
- **Real-time SSE Streaming** — token-by-token "typing" effect
- **Redis Caching** — identical questions answered instantly
- **FAISS Vector Search** — semantic retrieval, not just keyword matching
- **Futuristic Dark UI** — Glassmorphism design with Framer Motion animations

## 🔐 Security
- **JWT Authentication** — Access + Refresh token rotation
- **GitHub OAuth** — One-click social login
- **Rate Limiting** — Per-user request limits via `slowapi`
- **File Deduplication** — SHA256 hash prevents duplicate uploads

---

# 🏗️ Architecture

```text
┌─────────────────────────────────────────────────────────────────┐
│                        User Browser                             │
└─────────────────────────┬───────────────────────────────────────┘
                          │ HTTP :80
┌─────────────────────────▼───────────────────────────────────────┐
│                    Nginx (Reverse Proxy)                        │
│                  /api/* → Backend / → Frontend                 │
└──────────────┬──────────────────────────┬───────────────────────┘
               │                          │
┌──────────────▼──────────┐   ┌──────────▼──────────────────────┐
│   FastAPI Backend :8000 │   │  React Frontend (Nginx :80)     │
│                          │   │  Built with Vite (Production)   │
│ ┌─────────────────────┐ │   └──────────────────────────────────┘
│ │   File Processing   │ │
│ │ ┌───────────────┐   │ │   ┌─────────────────────────────────┐
│ │ │ PDF → PyMuPDF│   │ │   │         MongoDB Atlas           │
│ │ │ Audio→Whisper│   │ │   │ Users, Files, Chunks, Messages  │
│ │ │ Video→ffmpeg │   │ │   └─────────────────────────────────┘
│ │ └───────────────┘   │ │
│ └─────────────────────┘ │   ┌─────────────────────────────────┐
│ ┌─────────────────────┐ │   │          Redis Cache            │
│ │    Vector Service   │ │   │ Q&A Cache + Token Blacklist     │
│ │  FAISS + ST Model   │ │   └─────────────────────────────────┘
│ └─────────────────────┘ │
│ ┌─────────────────────┐ │   ┌─────────────────────────────────┐
│ │     LLM Service     │ │   │      Groq API (Llama 3.3)      │
│ │   Groq → Ollama     │ │   │   + Local Ollama Fallback      │
│ └─────────────────────┘ │   └─────────────────────────────────┘
└──────────────────────────┘
```

---

# 🆓 Tech Stack (100% Free)

## Backend

| Component | Technology | Purpose |
|---|---|---|
| Framework | FastAPI 0.111 | REST API + SSE Streaming |
| LLM | Groq API (Llama 3.3 70B) | AI Question Answering |
| LLM Fallback | Ollama (Local) | Offline/Rate-limit fallback |
| Transcription | OpenAI Whisper (Local) | Audio/Video to Text |
| Vector Search | FAISS (Facebook AI) | Semantic Similarity Search |
| Embeddings | sentence-transformers | Text Vectorization |
| Database | MongoDB Atlas | Document Storage |
| Cache | Redis | Response Caching |
| Auth | JWT + python-jose | Secure Authentication |
| PDF Parsing | PyMuPDF (fitz) | Text Extraction |
| Audio/Video | ffmpeg + pydub | Media Processing |
| Rate Limiting | slowapi | Request Throttling |

## Frontend

| Component | Technology | Purpose |
|---|---|---|
| Framework | React 18 + Vite | UI Framework |
| Styling | Tailwind CSS | Utility-first CSS |
| Animations | Framer Motion | UI Animations |
| State | Zustand | Global State Management |
| HTTP | Axios | API Client |
| Streaming | EventSource (SSE) | Real-time Chat |
| Audio | Wavesurfer.js | Waveform Visualization |
| Icons | Lucide React | Icon Library |

## Infrastructure

| Component | Technology | Purpose |
|---|---|---|
| Containerization | Docker + Docker Compose | Multi-container Setup |
| Reverse Proxy | Nginx | Traffic Routing + SSE |
| CI/CD | GitHub Actions | Automated Testing + Build |
| Cloud DB | MongoDB Atlas (M0 Free) | Production Database |

---

# 🚀 Quick Start

## Option 1: Docker Compose (Recommended)

### Prerequisites
- Docker Desktop

```bash
# 1. Clone the repository
git clone https://github.com/YOUR_USERNAME/ai-qa-app.git
cd ai-qa-app

# 2. Create environment file
cp backend/.env.example .env
```

Edit the `.env` file:

```env
MONGO_URL=mongodb+srv://<user>:<password>@cluster.mongodb.net/aiqa_db
GROQ_API_KEY=gsk_your_groq_key_here
JWT_SECRET=your-secret-key-here
```

```bash
# 3. Launch all services
docker compose up --build

# 4. Open the application
open http://localhost
```

That's it! The full application is now running at:

```text
http://localhost
```

---

## Option 2: Local Development

### Prerequisites
- Python 3.11
- Node.js 20
- ffmpeg
- Redis

---

## Backend Setup

```bash
cd backend

# Create and activate virtual environment
python3.11 -m venv venv
source venv/bin/activate

# Install dependencies
pip install -r requirements.txt

# Configure environment
cp .env.example .env

# Start the backend
uvicorn app.main:app --reload --port 8000
```

---

## Frontend Setup

```bash
cd frontend

# Install dependencies
npm install

# Start development server
npm run dev
```

Open:

```text
http://localhost:5173
```

---

# 🧪 Testing

The application has a comprehensive test suite achieving **97% code coverage**.

## Run Tests Locally

```bash
cd backend
source venv/bin/activate

# Run all tests
pytest tests/ -v

# Run with coverage report
pytest tests/ --cov=app --cov-config=.coveragerc --cov-report=term-missing

# Open HTML coverage report
open htmlcov/index.html
```

---

## Run Tests via Docker

```bash
docker compose -f docker-compose.test.yml up --build --exit-code-from backend_test
```

---

## Coverage Report

| Module | Coverage |
|---|---|
| app/api/ | 95%+ |
| app/core/ | 97%+ |
| app/services/llm_service.py | 100% |
| app/services/transcription.py | 96% |
| app/services/vector_service.py | 94% |
| app/models/ | 100% |
| app/utils/ | 98%+ |
| TOTAL | 97% |

---

# 📡 API Documentation

Full interactive API documentation:

- Local: `http://localhost:8000/api/docs`
- Production: `https://aiqa-backend.onrender.com/api/docs`

---

# 🔐 Authentication Endpoints

| Method | Endpoint | Auth | Description |
|---|---|---|---|
| POST | `/api/v1/auth/register` | ❌ | Create a new account |
| POST | `/api/v1/auth/login` | ❌ | Login and get JWT tokens |
| POST | `/api/v1/auth/refresh` | ❌ | Refresh access token |
| POST | `/api/v1/auth/logout` | ✅ | Invalidate refresh token |
| GET | `/api/v1/auth/me` | ✅ | Get current user profile |
| GET | `/api/v1/auth/oauth/github` | ❌ | GitHub OAuth redirect |

---

# 📁 File Management Endpoints

| Method | Endpoint | Auth | Description |
|---|---|---|---|
| POST | `/api/v1/files/upload` | ✅ | Upload PDF/Audio/Video |
| GET | `/api/v1/files/list` | ✅ | List all user files |
| GET | `/api/v1/files/{id}` | ✅ | Get file metadata |
| DELETE | `/api/v1/files/{id}` | ✅ | Delete file and data |

---

# 💬 Chat & Summary Endpoints

| Method | Endpoint | Auth | Description |
|---|---|---|---|
| GET | `/api/v1/chat/ask` | ✅ | SSE Stream — AI Q&A |
| GET | `/api/v1/chat/history/{file_id}` | ✅ | Get chat history |
| DELETE | `/api/v1/chat/history/{file_id}` | ✅ | Clear chat history |
| GET | `/api/v1/summary/{file_id}` | ✅ | Get AI summary |

---

# ⏱️ Rate Limits

| Endpoint | Limit |
|---|---|
| `/api/v1/files/upload` | 10 requests/hour |
| `/api/v1/chat/ask` | 50 requests/hour |
| `/api/v1/auth/login` | 10 requests/minute |

---

# 📁 Project Structure

```text
ai-qa-app/
├── .github/
│   └── workflows/
│       ├── ci.yml
│       └── cd.yml
│
├── backend/
│   ├── app/
│   │   ├── api/
│   │   │   ├── auth.py
│   │   │   ├── files.py
│   │   │   ├── chat.py
│   │   │   └── summary.py
│   │   ├── core/
│   │   │   ├── auth.py
│   │   │   ├── exceptions.py
│   │   │   └── rate_limiter.py
│   │   ├── services/
│   │   │   ├── llm_service.py
│   │   │   ├── transcription.py
│   │   │   ├── vector_service.py
│   │   │   ├── file_processor.py
│   │   │   ├── cache_service.py
│   │   │   ├── pdf_service.py
│   │   │   └── summary_service.py
│   │   ├── models/
│   │   │   ├── user.py
│   │   │   ├── file_record.py
│   │   │   ├── chat_message.py
│   │   │   └── schemas.py
│   │   └── utils/
│   │       ├── file_utils.py
│   │       └── text_chunker.py
│   │
│   ├── tests/
│   ├── Dockerfile
│   ├── requirements.txt
│   └── .coveragerc
│
├── frontend/
│   ├── src/
│   │   ├── pages/
│   │   │   ├── LandingPage.jsx
│   │   │   └── Dashboard.jsx
│   │   ├── components/
│   │   │   ├── chat/
│   │   │   ├── upload/
│   │   │   ├── media/
│   │   │   ├── layout/
│   │   │   └── common/
│   │   ├── store/
│   │   ├── hooks/
│   │   └── api/
│   │
│   ├── nginx.conf
│   └── Dockerfile
│
├── nginx/
│   └── nginx.conf
│
├── docker-compose.yml
├── docker-compose.test.yml
└── README.md
```

---

# 🔄 File Processing Pipeline

```text
User Uploads File
       │
       ▼
┌─────────────────┐
│  Validate File  │
└────────┬────────┘
         │
         ▼
┌─────────────────┐
│  Save to Disk   │
└────────┬────────┘
         │
    ┌────┴──────────────┐
    │                   │
    ▼                   ▼
  PDF              Audio / Video
    │                   │
    ▼                   ▼
PyMuPDF          ffmpeg (extract audio)
Extract Text          │
    │                  ▼
    │            OpenAI Whisper
    │            Transcribe
    │                   │
    └──────┬────────────┘
           │
           ▼
┌─────────────────────┐
│  Semantic Chunking  │
└──────────┬──────────┘
           │
           ▼
┌─────────────────────┐
│ Generate Embeddings │
└──────────┬──────────┘
           │
           ▼
┌─────────────────────┐
│   Save FAISS Index  │
└──────────┬──────────┘
           │
           ▼
┌─────────────────────┐
│  Save to MongoDB    │
└──────────┬──────────┘
           │
           ▼
      Status → "ready"
```

---

# 💬 Chat Flow

```text
User asks a question
       │
       ▼
┌─────────────────────┐
│  Check Redis Cache  │
└──────────┬──────────┘
           │ Cache miss
           ▼
┌─────────────────────┐
│ FAISS Vector Search │
└──────────┬──────────┘
           │
           ▼
┌─────────────────────┐
│  Build LLM Prompt   │
└──────────┬──────────┘
           │
           ▼
┌─────────────────────┐
│   Groq API Stream   │
└──────────┬──────────┘
           │
           ▼
┌─────────────────────┐
│   Cache in Redis    │
└──────────┬──────────┘
           │
           ▼
┌─────────────────────┐
│  Save to MongoDB    │
└──────────┬──────────┘
           │
           ▼
AI Response with timestamp chips
```

---

# 🌍 Environment Variables

| Variable | Required | Description |
|---|---|---|
| MONGO_URL | ✅ | MongoDB Atlas connection string |
| MONGO_DB_NAME | ✅ | Database name |
| GROQ_API_KEY | ✅ | Groq API key |
| JWT_SECRET | ✅ | JWT signing secret |
| REDIS_URL | ✅ | Redis connection URL |
| ALLOWED_ORIGINS | ✅ | Allowed frontend origins |
| GITHUB_CLIENT_ID | ❌ | GitHub OAuth client ID |
| GITHUB_CLIENT_SECRET | ❌ | GitHub OAuth secret |
| OLLAMA_BASE_URL | ❌ | Ollama server URL |
| OLLAMA_MODEL | ❌ | Ollama model |
| MAX_FILE_SIZE_MB | ❌ | Maximum upload size |
| DEBUG | ❌ | Debug mode |

---

# 🧩 Bonus Features Implemented

| Bonus | Implementation | Details |
|---|---|---|
| ✅ Vector Search | FAISS + sentence-transformers | all-MiniLM-L6-v2 |
| ✅ Real-time Streaming | SSE | Token-by-token streaming |
| ✅ Multi-user Auth | JWT + GitHub OAuth | Secure login |
| ✅ Rate Limiting | slowapi middleware | Per-user limits |
| ✅ Redis Caching | Redis TTL cache | 1-hour cache |

---

# 🔧 Docker Commands

```bash
# Start everything
docker compose up --build

# Start without rebuilding
docker compose up

# Start in background
docker compose up -d

# View logs
docker compose logs -f

# View backend logs
docker compose logs -f backend

# Stop everything
docker compose down

# Remove volumes
docker compose down -v

# Run isolated tests
docker compose -f docker-compose.test.yml up --build --exit-code-from backend_test
```

---

# 📊 CI/CD Pipeline

```text
Push to main / Pull Request
         │
         ▼
┌─────────────────┐
│   CI Pipeline   │
│                 │
│  Lint Check     │
│  Run Tests      │
│  Build Docker   │
└────────┬────────┘
         │
         ▼
┌─────────────────┐
│   CD Pipeline   │
│                 │
│ Build Images    │
│ Deploy Status   │
└─────────────────┘
```

---

# 👨‍💻 Author

**Sayan Patra**

- GitHub
- LinkedIn

---

# 📄 License

This project is built as part of an SDE-1 programming assignment and is open for review.
````
