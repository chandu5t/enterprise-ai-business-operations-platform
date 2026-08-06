Step 1 — Create the folder structure (PowerShell)

Run this from wherever you want the project (e.g. C:\Projects\):

powershell
New-Item -ItemType Directory -Force -Path "enterprise-ai-platform"
Set-Location "enterprise-ai-platform"

New-Item -ItemType Directory -Force -Path "backend\app\config"
New-Item -ItemType Directory -Force -Path "backend\app\api"
New-Item -ItemType Directory -Force -Path "backend\app\agents"
New-Item -ItemType Directory -Force -Path "backend\app\workflows"
New-Item -ItemType Directory -Force -Path "backend\app\rag"
New-Item -ItemType Directory -Force -Path "backend\app\memory"
New-Item -ItemType Directory -Force -Path "backend\app\database"
New-Item -ItemType Directory -Force -Path "backend\app\models"
New-Item -ItemType Directory -Force -Path "backend\app\schemas"
New-Item -ItemType Directory -Force -Path "backend\app\services"
New-Item -ItemType Directory -Force -Path "backend\app\utils"
New-Item -ItemType Directory -Force -Path "backend\tests"

# Empty __init__.py files (make these Python packages)
New-Item -ItemType File -Force -Path "backend\app\__init__.py"
New-Item -ItemType File -Force -Path "backend\app\config\__init__.py"
New-Item -ItemType File -Force -Path "backend\app\api\__init__.py"
New-Item -ItemType File -Force -Path "backend\app\agents\__init__.py"
New-Item -ItemType File -Force -Path "backend\app\workflows\__init__.py"
New-Item -ItemType File -Force -Path "backend\app\rag\__init__.py"
New-Item -ItemType File -Force -Path "backend\app\memory\__init__.py"
New-Item -ItemType File -Force -Path "backend\app\database\__init__.py"
New-Item -ItemType File -Force -Path "backend\app\models\__init__.py"
New-Item -ItemType File -Force -Path "backend\app\schemas\__init__.py"
New-Item -ItemType File -Force -Path "backend\app\services\__init__.py"
New-Item -ItemType File -Force -Path "backend\app\utils\__init__.py"
New-Item -ItemType File -Force -Path "backend\tests\__init__.py"

Write-Host "Folder structure created." -ForegroundColor Green

All 13 __init__.py files are intentionally empty — they just mark each folder as a Python package so imports like from app.config.settings import get_settings work. Now open the project in VS Code (code .) and create the remaining files below.

Get exact content of settings.py
Get exact content of settings.py
Get exact content of settings.py
Done
backend/app/config/settings.py
python
"""
Application configuration.

All runtime configuration is loaded from environment variables via
pydantic-settings. This gives us validation at startup (the app refuses
to boot with missing/invalid config) instead of failing later at
first use, and gives every other module a single typed source of truth
instead of scattered os.environ calls.
"""

from functools import lru_cache

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Typed application settings, populated from environment variables / .env file."""

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=True,
        extra="ignore",
    )

    # --- Application ---
    APP_NAME: str = "Enterprise AI Business Operations Platform"
    APP_ENV: str = Field(default="development")  # development | staging | production
    DEBUG: bool = Field(default=True)
    API_V1_PREFIX: str = "/api"

    # --- CORS ---
    CORS_ORIGINS: list[str] = Field(default=["http://localhost:3000"])

    # --- Database (wired in Module 2) ---
    DATABASE_URL: str = Field(
        default="postgresql+psycopg2://postgres:postgres@localhost:5432/enterprise_ai_platform"
    )

    # --- Auth (wired in Module 3) ---
    JWT_SECRET: str = Field(default="change-me-in-env-file")
    JWT_ALGORITHM: str = Field(default="HS256")
    JWT_EXPIRE_MINUTES: int = Field(default=60 * 24)

    # --- AI Providers (wired in later modules) ---
    GOOGLE_API_KEY: str = Field(default="")
    TAVILY_API_KEY: str = Field(default="")

    # --- Gmail (wired in Email Agent module) ---
    GMAIL_CLIENT_ID: str = Field(default="")
    GMAIL_CLIENT_SECRET: str = Field(default="")
    GMAIL_REFRESH_TOKEN: str = Field(default="")

    # --- Observability (wired in later modules) ---
    LANGSMITH_API_KEY: str = Field(default="")
    LANGSMITH_PROJECT: str = Field(default="enterprise-ai-platform")
    LANGCHAIN_TRACING_V2: bool = Field(default=False)


@lru_cache
def get_settings() -> Settings:
    """Cached settings accessor — settings are read once per process."""
    return Settings()
backend/app/main.py
python
"""
FastAPI application entrypoint.

This module only wires the application together (middleware, routers,
startup/shutdown hooks). It must never contain business logic — that
lives in app/services and is invoked by routers under app/api.
"""

import logging

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.config.settings import get_settings

settings = get_settings()

logging.basicConfig(
    level=logging.DEBUG if settings.DEBUG else logging.INFO,
    format="%(asctime)s | %(levelname)s | %(name)s | %(message)s",
)
logger = logging.getLogger(__name__)

app = FastAPI(
    title=settings.APP_NAME,
    version="0.1.0",
    description="AI Business Assistant — multi-agent workflow automation platform.",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.CORS_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.on_event("startup")
async def on_startup() -> None:
    logger.info("Starting %s in '%s' mode", settings.APP_NAME, settings.APP_ENV)


@app.get("/health", tags=["System"])
async def health_check() -> dict:
    """Liveness/readiness probe used by Docker, Railway, and local dev checks."""
    return {
        "status": "ok",
        "service": settings.APP_NAME,
        "environment": settings.APP_ENV,
    }
backend/requirements.txt
# --- Module 1: Core API framework ---
fastapi==0.115.6
uvicorn[standard]==0.34.0
pydantic==2.10.4
pydantic-settings==2.7.1
python-dotenv==1.0.1

# NOTE: Additional dependencies (SQLAlchemy, Alembic, LangGraph, LangChain,
# FAISS, Gmail API, etc.) are added incrementally in their respective modules
# so this file always reflects exactly what the current codebase needs.
backend/.env.example
# --- Application ---
APP_ENV=development
DEBUG=true

# --- CORS (comma-will-be-parsed-as-JSON-array; use JSON list syntax) ---
CORS_ORIGINS=["http://localhost:3000"]

# --- Database ---
DATABASE_URL=postgresql+psycopg2://postgres:postgres@localhost:5432/enterprise_ai_platform

# --- Auth ---
JWT_SECRET=replace-with-a-long-random-secret
JWT_ALGORITHM=HS256
JWT_EXPIRE_MINUTES=1440

# --- AI Providers ---
GOOGLE_API_KEY=
TAVILY_API_KEY=

# --- Gmail API ---
GMAIL_CLIENT_ID=
GMAIL_CLIENT_SECRET=
GMAIL_REFRESH_TOKEN=

# --- Observability ---
LANGSMITH_API_KEY=
LANGSMITH_PROJECT=enterprise-ai-platform
LANGCHAIN_TRACING_V2=false
backend/Dockerfile
dockerfile
FROM python:3.11-slim

WORKDIR /app

# System deps needed by later modules (psycopg2, faiss, sentence-transformers)
# are installed now so we don't have to rebuild the base layer repeatedly
# as we add functionality module by module.
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    libpq-dev \
    curl \
    && rm -rf /var/lib/apt/lists/*

COPY requirements.txt .
RUN pip install --no-cache-dir --upgrade pip \
    && pip install --no-cache-dir -r requirements.txt

COPY . .

EXPOSE 8000

HEALTHCHECK --interval=30s --timeout=5s --start-period=10s --retries=3 \
    CMD curl -f http://localhost:8000/health || exit 1

CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
backend/.dockerignore
.venv/
__pycache__/
*.pyc
.env
.pytest_cache/
.git/
*.egg-info/
docker-compose.yml (project root)
yaml
services:
  postgres:
    image: postgres:16-alpine
    container_name: eabop-postgres
    restart: unless-stopped
    environment:
      POSTGRES_USER: postgres
      POSTGRES_PASSWORD: postgres
      POSTGRES_DB: enterprise_ai_platform
    ports:
      - "5432:5432"
    volumes:
      - postgres_data:/var/lib/postgresql/data
    healthcheck:
      test: ["CMD-SHELL", "pg_isready -U postgres"]
      interval: 5s
      timeout: 5s
      retries: 5

  backend:
    build:
      context: ./backend
      dockerfile: Dockerfile
    container_name: eabop-backend
    restart: unless-stopped
    env_file:
      - ./backend/.env
    environment:
      # Overrides .env's DATABASE_URL so the backend talks to the
      # 'postgres' service name (Docker's internal DNS) instead of localhost.
      DATABASE_URL: postgresql+psycopg2://postgres:postgres@postgres:5432/enterprise_ai_platform
    ports:
      - "8000:8000"
    depends_on:
      postgres:
        condition: service_healthy
    volumes:
      - ./backend:/app

  # frontend service is added in Module 12 once the Next.js app exists.

volumes:
  postgres_data:
.gitignore (project root)
# Python
__pycache__/
*.pyc
.venv/
*.egg-info/
.pytest_cache/

# Env files
.env
.env.local

# Node / Next.js (added in Module 12)
node_modules/
.next/
out/

# FAISS index files (added in Module 7)
*.faiss
*.pkl

# OS
.DS_Store

# IDE
.vscode/
.idea/
README.md (project root)

Same content as before — status table, tech stack, Windows run instructions, folder structure, and architecture principles. (Already correct from the last message — no changes needed here.)

Step 2 — Run and verify on Windows (PowerShell)

Option A — Docker Compose (recommended, matches your verified Docker setup):

powershell
Set-Location backend
Copy-Item .env.example .env
Set-Location ..
docker compose up --build

Wait for Application startup complete in the logs, then in a browser or a new PowerShell window:

powershell
Invoke-WebRequest -Uri http://localhost:8000/health -UseBasicParsing | Select-Object -ExpandProperty Content

Expected output:

{"status":"ok","service":"Enterprise AI Business Operations Platform","environment":"development"}

Also open http://localhost:8000/docs in your browser — you should see the Swagger UI.

To stop everything:

powershell
docker compose down

Option B — Backend only, no Docker:

powershell
Set-Location backend
python -m venv .venv
.venv\Scripts\Activate.ps1
pip install -r requirements.txt
Copy-Item .env.example .env
uvicorn app.main:app --reload

If Activate.ps1 is blocked: run PowerShell as Administrator once, execute Set-ExecutionPolicy -ExecutionPolicy RemoteSigned -Scope CurrentUser, then retry activation in a normal terminal.> 

Module 1 completed successfully.

