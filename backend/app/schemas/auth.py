"""Pydantic schemas for authentication requests/responses."""

from pydantic import BaseModel, EmailStr


class LoginRequest(BaseModel):
    """Request body for POST /auth/login. JSON, not OAuth2 form-encoding —
    kept consistent with the rest of this API's JSON-only contract."""

    email: EmailStr
    password: str


class Token(BaseModel):
    """Response body for a successful login — what the frontend stores
    and sends back as `Authorization: Bearer <access_token>`."""

    access_token: str
    token_type: str = "bearer"


class MessageResponse(BaseModel):
    """Generic message-only response body, e.g. for POST /auth/logout."""

    message: str


class TokenPayload(BaseModel):
    """Shape of a decoded JWT's claims, used internally by the
    get_current_user dependency (Step 4) to validate structure before
    looking the user up."""

    sub: str
    exp: int
    iat: int