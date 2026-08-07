"""
Database engine and session management.

A single SQLAlchemy Engine is created once per process and reused
everywhere — engines manage their own connection pool internally, so
creating one per request would exhaust Postgres's connection limit.
Each request gets its own Session via the get_db() dependency, which
is always closed after the request completes, even on error.
"""

from collections.abc import Generator

from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker

from app.config.settings import get_settings

settings = get_settings()

engine = create_engine(
    settings.DATABASE_URL,
    pool_pre_ping=True,  # detects stale connections (e.g. after a DB restart) before use
    pool_size=5,
    max_overflow=10,
)

SessionLocal = sessionmaker(
    bind=engine,
    autoflush=False,
    autocommit=False,
    expire_on_commit=False,
)

def get_db() -> Generator[Session, None, None]:
    """FastAPI dependency that yields a DB session and guarantees it is closed."""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()