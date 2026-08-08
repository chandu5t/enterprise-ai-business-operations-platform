"""
Import service-layer functions here so routers can do
`from app.services import register_user` instead of reaching into
individual submodules — mirrors the pattern used in app/models and
app/schemas.
"""

from app.services.auth_service import authenticate_user, register_user
from app.services.exceptions import (
    EmailAlreadyExistsError,
    InactiveUserError,
    InvalidCredentialsError,
    OrganizationAlreadyExistsError,
    ServiceError,
)

__all__ = [
    "authenticate_user",
    "register_user",
    "EmailAlreadyExistsError",
    "InactiveUserError",
    "InvalidCredentialsError",
    "OrganizationAlreadyExistsError",
    "ServiceError",
]