"""
Password hashing and JWT token utilities.

Deliberately side-effect-free: no DB access, no FastAPI imports. This is
what makes it independently unit-testable and safely reusable from both
the auth service layer (Step 2) and the get_current_user dependency
(Step 4) with no circular-import risk.
"""

from datetime import datetime, timedelta, timezone

from jose import jwt
from passlib.context import CryptContext

from app.config.settings import get_settings

settings = get_settings()

_pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")


def hash_password(plain_password: str) -> str:
    """Hash a plaintext password with bcrypt. Never store plaintext passwords."""
    return _pwd_context.hash(plain_password)


def verify_password(plain_password: str, hashed_password: str) -> bool:
    """Check a plaintext password against a bcrypt hash."""
    return _pwd_context.verify(plain_password, hashed_password)


def create_access_token(subject: str, expires_delta: timedelta | None = None) -> str:
    """
    Create a signed JWT access token.

    `subject` is the user's id (as a string), stored in the standard
    `sub` claim per RFC 7519 so any JWT-aware tooling interprets it
    correctly. Using the id rather than the email means a future email
    change won't invalidate tokens already issued.
    """
    expire = datetime.now(timezone.utc) + (
        expires_delta or timedelta(minutes=settings.JWT_EXPIRE_MINUTES)
    )
    to_encode = {
        "sub": subject,
        "exp": expire,
        "iat": datetime.now(timezone.utc),
    }
    return jwt.encode(to_encode, settings.JWT_SECRET, algorithm=settings.JWT_ALGORITHM)


def decode_access_token(token: str) -> dict:
    """
    Decode and verify a JWT access token.

    Raises jose.exceptions.JWTError if the token is expired, malformed,
    or has an invalid signature. Callers (the get_current_user dependency
    in Step 4) are responsible for translating that into an HTTP 401.
    """
    return jwt.decode(token, settings.JWT_SECRET, algorithms=[settings.JWT_ALGORITHM])