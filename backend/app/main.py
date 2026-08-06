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