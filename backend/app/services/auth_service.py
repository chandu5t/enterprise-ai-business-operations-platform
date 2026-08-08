"""
Auth service layer: registration and authentication business logic.

Routers (app/api, added in Step 5) call these functions and translate
the exceptions they raise into HTTP responses. This module has no
FastAPI/HTTP awareness at all, which is what makes it independently
unit-testable and reusable (e.g. from a future CLI or admin script)
without dragging in the web framework.
"""

from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.models.organization import Organization
from app.models.user import User, UserRole
from app.schemas.user import UserCreate
from app.services.exceptions import (
    EmailAlreadyExistsError,
    InactiveUserError,
    InvalidCredentialsError,
    OrganizationAlreadyExistsError,
)
from app.utils.security import hash_password, verify_password


def register_user(db: Session, user_in: UserCreate) -> User:
    """
    Register a new user together with the brand-new Organization they belong to.

    Both existence checks below run up front so callers get a specific,
    actionable error (EmailAlreadyExistsError vs
    OrganizationAlreadyExistsError) instead of a generic database error.
    They are NOT the actual guarantee against a race between two
    simultaneous registrations, though — the IntegrityError fallback on
    commit is what closes that window, since the DB's unique constraints
    are enforced atomically and the pre-checks above are not.
    """
    if db.query(User).filter(User.email == user_in.email).first() is not None:
        raise EmailAlreadyExistsError(
            f"Email '{user_in.email}' is already registered."
        )

    if (
        db.query(Organization)
        .filter(Organization.name == user_in.organization_name)
        .first()
        is not None
    ):
        raise OrganizationAlreadyExistsError(
            f"Organization '{user_in.organization_name}' already exists."
        )

    organization = Organization(name=user_in.organization_name)
    db.add(organization)
    db.flush()  # populate organization.id without committing yet

    user = User(
        organization_id=organization.id,
        email=user_in.email,
        hashed_password=hash_password(user_in.password),
        full_name=user_in.full_name,
        role=UserRole.ADMIN,  # the registering user administers their new org
    )
    db.add(user)

    try:
        db.commit()
    except IntegrityError as exc:
        db.rollback()
        # Covers the race window between the pre-checks above and this
        # insert (e.g. two near-simultaneous registrations with the same
        # email or organization name).
        raise EmailAlreadyExistsError(
            f"Email '{user_in.email}' is already registered."
        ) from exc

    db.refresh(user)
    return user


def authenticate_user(db: Session, email: str, password: str) -> User:
    """
    Verify a login attempt and return the authenticated User.

    Raises the same InvalidCredentialsError for both "no such email" and
    "wrong password" — distinguishing them would let a caller enumerate
    which email addresses are registered.
    """
    user = db.query(User).filter(User.email == email).first()

    if user is None or not verify_password(password, user.hashed_password):
        raise InvalidCredentialsError("Incorrect email or password.")

    if not user.is_active:
        raise InactiveUserError("This account has been deactivated.")

    return user