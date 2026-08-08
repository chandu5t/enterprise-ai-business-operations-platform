"""
Custom exceptions raised by the service layer.

Routers (app/api) catch these and translate them into HTTP responses.
The service layer itself never imports FastAPI or knows about status
codes — that's what keeps business logic testable independently of the
web framework, and keeps "no business logic in routers" true in both
directions.
"""


class ServiceError(Exception):
    """Base class for all service-layer errors."""


class EmailAlreadyExistsError(ServiceError):
    """Raised when registering with an email that's already in use."""


class OrganizationAlreadyExistsError(ServiceError):
    """Raised when registering with an organization name that's already taken."""


class InvalidCredentialsError(ServiceError):
    """Raised when a login's email/password don't match any account.

    Deliberately used for BOTH "no such email" and "wrong password" —
    see auth_service.authenticate_user for why.
    """


class InactiveUserError(ServiceError):
    """Raised when credentials are correct but the account has been deactivated."""