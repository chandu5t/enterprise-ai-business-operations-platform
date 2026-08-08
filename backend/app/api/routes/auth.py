"""
Authentication routes: register, login, me, logout.

Every handler here does exactly three things: rely on FastAPI/Pydantic
to have already validated the request, call into app.services for the
actual business logic, and translate the result (or a service-layer
exception) into an HTTP response. No password hashing, no token
creation, and no direct database queries happen in this file — that's
the entire point of the service layer (Step 3) and security utilities
(Step 1) existing separately.
"""

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.api.deps import get_current_user
from app.database.session import get_db
from app.models.user import User
from app.schemas.auth import LoginRequest, MessageResponse, Token
from app.schemas.user import UserCreate, UserResponse
from app.services.auth_service import authenticate_user, register_user
from app.services.exceptions import (
    EmailAlreadyExistsError,
    InactiveUserError,
    InvalidCredentialsError,
    OrganizationAlreadyExistsError,
)
from app.utils.security import create_access_token

router = APIRouter(prefix="/auth", tags=["Authentication"])


@router.post(
    "/register",
    response_model=UserResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Register a new user and their organization",
)
def register(user_in: UserCreate, db: Session = Depends(get_db)) -> User:
    try:
        return register_user(db, user_in)
    except (EmailAlreadyExistsError, OrganizationAlreadyExistsError) as exc:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT, detail=str(exc)
        ) from exc


@router.post(
    "/login",
    response_model=Token,
    summary="Exchange email/password for a JWT access token",
)
def login(credentials: LoginRequest, db: Session = Depends(get_db)) -> Token:
    try:
        user = authenticate_user(db, credentials.email, credentials.password)
    except InvalidCredentialsError as exc:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=str(exc),
            headers={"WWW-Authenticate": "Bearer"},
        ) from exc
    except InactiveUserError as exc:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN, detail=str(exc)
        ) from exc

    access_token = create_access_token(subject=str(user.id))
    return Token(access_token=access_token)


@router.get(
    "/me",
    response_model=UserResponse,
    summary="Get the currently authenticated user",
)
def read_current_user(current_user: User = Depends(get_current_user)) -> User:
    return current_user


@router.post(
    "/logout",
    response_model=MessageResponse,
    summary="Log out the current session",
)
def logout(current_user: User = Depends(get_current_user)) -> MessageResponse:
    """
    Log out the current session.

    JWTs are stateless by design: this endpoint does not (and cannot,
    without a server-side revocation list this MVP does not yet
    implement) invalidate the presented token. Its actual contract is:
    confirm the caller was authenticated, and signal the client to
    discard the token locally. Requiring a valid token to reach this
    endpoint at all (via get_current_user) is intentional — logging out
    with no valid session doesn't mean anything.

    A token-blocklist (e.g. Redis, keyed by JWT id) is a natural later
    addition if server-side revocation becomes a real requirement.
    """
    return MessageResponse(
        message=f"Logged out, {current_user.email}. Discard the access token client-side."
    )