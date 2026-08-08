"""
Shared pytest fixtures for database-backed tests.

Tests run against a real PostgreSQL database (DATABASE_URL from the
environment/.env — the same database the app itself would use), not
SQLite. SQLite doesn't support our PostgreSQL-specific column types
(UUID, native ENUM), so a "works on SQLite" test would give false
confidence about a schema that only ever runs on Postgres in practice.

Isolation strategy: create all tables once per test session, then wrap
each individual test in a SAVEPOINT that's rolled back afterward. This
keeps tests fast (no per-test schema rebuild) and fully isolated (no
test's data leaks into another) without needing a separate database
per test run.
"""

from collections.abc import Generator

import pytest
from sqlalchemy import create_engine, event
from sqlalchemy.orm import Session

from app.config.settings import get_settings
from app.database.base import Base
from app.models import Document, Organization, User, Workflow  # noqa: F401


@pytest.fixture(scope="session")
def db_engine():
    """Create all tables once for the test session, drop them at the end.

    Uses settings.TEST_DATABASE_URL — a database dedicated to the test
    suite, separate from DATABASE_URL. This fixture drops every table
    at teardown; running it against the same database local dev or a
    running server depends on would wipe that data out from under it.
    """
    settings = get_settings()
    engine = create_engine(settings.TEST_DATABASE_URL)

    Base.metadata.create_all(bind=engine)
    yield engine
    Base.metadata.drop_all(bind=engine)
    engine.dispose()


@pytest.fixture
def db_session(db_engine) -> Generator[Session, None, None]:
    """
    Yield a Session wrapped in an outer transaction + inner SAVEPOINT,
    so nothing a test writes persists into the next test — including
    when the code under test itself triggers a rollback (e.g. a test
    that intentionally provokes an IntegrityError). This is the pattern
    SQLAlchemy's own docs recommend for joining a Session to an
    externally-managed test transaction: a plain connection.begin() is
    NOT enough, because a failed flush aborts the DBAPI transaction out
    from under it. A SAVEPOINT, restarted after each end, survives that.
    """
    connection = db_engine.connect()
    outer_transaction = connection.begin()
    session = Session(bind=connection)

    nested = connection.begin_nested()

    @event.listens_for(session, "after_transaction_end")
    def _restart_savepoint(sess, trans):
        nonlocal nested
        if not nested.is_active:
            nested = connection.begin_nested()

    try:
        yield session
    finally:
        session.close()
        outer_transaction.rollback()
        connection.close()