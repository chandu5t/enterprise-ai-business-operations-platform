"""
Import schemas here so other modules can do `from app.schemas import
UserCreate` instead of reaching into individual submodules — mirrors the
pattern already used in app/models/__init__.py.
"""

from app.schemas.auth import LoginRequest, Token, TokenPayload
from app.schemas.user import UserBase, UserCreate, UserResponse

__all__ = [
    "LoginRequest",
    "Token",
    "TokenPayload",
    "UserBase",
    "UserCreate",
    "UserResponse",
]