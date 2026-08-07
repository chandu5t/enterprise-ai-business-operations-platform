"""
Declarative base for all ORM models.

Every model in app/models inherits from Base. Alembic's env.py imports
Base.metadata as the single source of truth for autogenerating migrations,
so every new model must be imported somewhere Alembic can see it — that
place is app/models/__init__.py.
"""

from sqlalchemy.orm import DeclarativeBase


class Base(DeclarativeBase):
    pass