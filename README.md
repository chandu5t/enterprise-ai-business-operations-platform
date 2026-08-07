# Enterprise AI Business Operations Platform (MVP)

A multi-agent AI system, orchestrated with LangGraph, that acts as an AI
Business Assistant: researching companies, retrieving internal knowledge via
RAG, drafting personalized outreach, pausing for human approval, and sending
email — end to end.

## Status

🚧 Under active, incremental development. See build log below.

| Module | Status |
|---|---|
| 1. Repo scaffold + Docker + FastAPI skeleton | ✅ Done |
| 2. Database layer (SQLAlchemy + Alembic) | ✅ Done |
| 3. Authentication (JWT) | ⬜ Next |
| 4. BusinessState & schemas | ⬜ |
| 5. LangGraph skeleton | ⬜ |
| 6. Research Agent | ⬜ |
| 7. RAG pipeline + Knowledge Agent | ⬜ |
| 8. Personalization Agent | ⬜ |
| 9. Human Approval | ⬜ |
| 10. Email Agent | ⬜ |
| 11. Workflow orchestration API + LangSmith | ⬜ |
| 12. Frontend scaffold | ⬜ |
| 13. Frontend core pages | ⬜ |
| 14. Full Dockerization + deployment | ⬜ |
| 15. Testing & polish | ⬜ |

## Tech Stack

**Backend:** FastAPI, SQLAlchemy, Alembic, PostgreSQL
**AI:** LangGraph, LangChain, Google Gemini, FAISS, Sentence Transformers
**Frontend:** Next.js, TypeScript, Tailwind CSS
**Observability:** LangSmith
**Infra:** Docker, Docker Compose

## Running Locally on Windows 11 (Module 1)

Commands below are for **PowerShell** (VS Code's default integrated terminal).
CMD equivalents are noted where they differ.

### Option A — Docker Compose (recommended)

```powershell
cd backend
copy .env.example .env
cd ..
docker compose up --build
```
*(CMD: `copy` works the same; nothing else changes.)*

Then check:
- `GET http://localhost:8000/health` → `{"status": "ok", ...}`
- Swagger UI: `http://localhost:8000/docs`

### Option B — Backend only, no Docker

```powershell
cd backend
python -m venv .venv
.venv\Scripts\Activate.ps1
pip install -r requirements.txt
copy .env.example .env
uvicorn app.main:app --reload
```

**CMD equivalent** (only the activation line differs):
```cmd
cd backend
python -m venv .venv
.venv\Scripts\activate.bat
pip install -r requirements.txt
copy .env.example .env
uvicorn app.main:app --reload
```

> **PowerShell execution policy:** if `Activate.ps1` is blocked, run PowerShell
> as Administrator once and execute:
> `Set-ExecutionPolicy -ExecutionPolicy RemoteSigned -Scope CurrentUser`
> then retry activation in a normal (non-admin) terminal.

### Database migrations (Module 2)

With Docker Compose, migrations run automatically on container start — no
manual step needed.

Running the backend without Docker (Option B above), apply migrations
manually after activating the virtualenv and starting Postgres:

```powershell
alembic upgrade head
```

To create a new migration after changing a model:
```powershell
alembic revision --autogenerate -m "describe your change"
alembic upgrade head
```

## Repository Structure

```
enterprise-ai-platform/
├── backend/
│   └── app/
│       ├── main.py        # FastAPI entrypoint
│       ├── config/        # Settings (env-driven)
│       ├── api/            # Routers (added as features land)
│       ├── agents/         # LangGraph agent implementations
│       ├── workflows/      # LangGraph graph definitions
│       ├── rag/             # Document loading, chunking, FAISS
│       ├── memory/         # Short/long-term memory
│       ├── database/        # DB session/engine
│       ├── models/          # SQLAlchemy ORM models
│       ├── schemas/         # Pydantic request/response schemas
│       ├── services/        # Business logic (never in routers)
│       └── utils/
├── frontend/                # Added in Module 12
├── docker-compose.yml
└── README.md
```

## Architecture Principles

- **No business logic in API routes** — routers call `services/`, services call `agents/`/`database/`.
- **Shared `BusinessState`** — agents communicate by reading/writing one Pydantic state object via LangGraph, never by passing raw prompts to each other.
- **Human-in-the-loop by default** — no outbound email is ever sent without explicit approval.