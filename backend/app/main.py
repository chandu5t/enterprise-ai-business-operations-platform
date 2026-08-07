"""
FastAPI application entrypoint.

This module only wires the application together (middleware, routers,
startup/shutdown hooks). It must never contain business logic — that
lives in app/services and is invoked by routers under app/api.
"""

import logging
from contextlib import asynccontextmanager

from fastapi import Depends, FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from sqlalchemy import text
from sqlalchemy.orm import Session

from app.config.settings import get_settings
from app.database.session import get_db

settings = get_settings()

logging.basicConfig(
    level=logging.DEBUG if settings.DEBUG else logging.INFO,
    format="%(asctime)s | %(levelname)s | %(name)s | %(message)s",
)
logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(_: FastAPI):
    logger.info("Starting %s in '%s' mode", settings.APP_NAME, settings.APP_ENV)
    yield
    logger.info("Shutting down %s", settings.APP_NAME)


app = FastAPI(
    title=settings.APP_NAME,
    version="0.1.0",
    description="AI Business Assistant — multi-agent workflow automation platform.",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.CORS_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/health", tags=["System"])
async def health_check(db: Session = Depends(get_db)) -> JSONResponse:
    """
    Readiness probe used by Docker, Railway, and local dev checks.

    Beyond confirming the process is alive, this actually queries the
    database — a process that's up but can't reach Postgres is not
    actually ready to serve traffic, and callers (load balancers,
    orchestrators, Docker's HEALTHCHECK) need to know that via a
    non-2xx status, not a misleadingly cheerful 200.
    """
    payload = {
        "status": "ok",
        "service": settings.APP_NAME,
        "environment": settings.APP_ENV,
        "database": "connected",
    }

    try:
        db.execute(text("SELECT 1"))
    except Exception as exc:  # noqa: BLE001 — any DB failure means "not ready"
        logger.error("Health check failed: database unreachable — %s", exc)
        payload["status"] = "degraded"
        payload["database"] = "disconnected"
        return JSONResponse(status_code=503, content=payload)

    return JSONResponse(status_code=200, content=payload)