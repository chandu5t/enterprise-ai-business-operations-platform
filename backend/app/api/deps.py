"""
Authentication dependencies for protected routes.

This is the seam between HTTP and the rest of the app: it parses the
incoming Authorization header, delegates signature/expiry verification
to app.utils.security, loads the corresponding User from the database,
and translates any failure into the correct HTTP status code. Routers
depend on get_current_user and never touch tokens, headers, or the User
lookup directly.
"""

import uuid

from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from jose import JWTError
from pydantic import ValidationError
from sqlalchemy.orm import Session

from app.database.session import get_db
from app.models.user import User
from app.schemas.auth import TokenPayload
from app.utils.security import decode_access_token

# auto_error=False so *we* control the status code. FastAPI's HTTPBearer
# raises 403 for a missing header by default — we want 401 for that,
# since a missing/invalid token is an authentication failure, not an
# authorization one. See the 401-vs-403 split in get_current_user below.
_bearer_scheme = HTTPBearer(auto_error=False)


def get_current_user(
    credentials: HTTPAuthorizationCredentials | None = Depends(_bearer_scheme),
    db: Session = Depends(get_db),
) -> User:
    """
    Resolve the currently authenticated User from a Bearer token.

    Raises:
        401 Unauthorized — missing/malformed header, invalid signature,
                            expired token, malformed subject claim, or
                            the token is valid but no matching user exists.
        403 Forbidden     — the token is valid and the user exists, but
                            their account has been deactivated.
    """
    unauthorized = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Could not validate credentials.",
        headers={"WWW-Authenticate": "Bearer"},
    )

    if credentials is None:
        raise unauthorized

    try:
        payload = decode_access_token(credentials.credentials)
        token_data = TokenPayload(**payload)
        user_id = uuid.UUID(token_data.sub)
    except (JWTError, ValidationError, ValueError) as exc:
        raise unauthorized from exc

    user = db.get(User, user_id)
    if user is None:
        raise unauthorized

    if not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="This account has been deactivated.",
        )

    return user