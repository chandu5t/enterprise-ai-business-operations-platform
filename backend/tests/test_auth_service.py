"""
Integration tests for app.services.auth_service — register_user and
authenticate_user, exercised against a real PostgreSQL database via
the db_session fixture (see tests/conftest.py).
"""

import pytest

from app.models.organization import Organization
from app.models.user import UserRole
from app.schemas.user import UserCreate
from app.services.auth_service import authenticate_user, register_user
from app.services.exceptions import (
    EmailAlreadyExistsError,
    InactiveUserError,
    InvalidCredentialsError,
    OrganizationAlreadyExistsError,
)
from app.utils.security import verify_password


def _valid_user_create(**overrides) -> UserCreate:
    defaults = dict(
        email="alice@example.com",
        password="supersecret123",
        full_name="Alice Example",
        organization_name="Acme Corp",
    )
    defaults.update(overrides)
    return UserCreate(**defaults)


# --- register_user ---------------------------------------------------


def test_register_user_creates_organization_and_admin_user(db_session):
    user = register_user(db_session, _valid_user_create())

    assert user.id is not None
    assert user.email == "alice@example.com"
    assert user.full_name == "Alice Example"
    assert user.role == UserRole.ADMIN
    assert user.is_active is True
    assert user.organization is not None
    assert user.organization.name == "Acme Corp"


def test_register_user_hashes_the_password(db_session):
    user = register_user(db_session, _valid_user_create())

    assert user.hashed_password != "supersecret123"
    assert verify_password("supersecret123", user.hashed_password) is True


def test_register_user_duplicate_email_raises(db_session):
    register_user(
        db_session,
        _valid_user_create(organization_name="Org One"),
    )

    with pytest.raises(EmailAlreadyExistsError):
        register_user(
            db_session,
            _valid_user_create(organization_name="Org Two"),
        )


def test_register_user_duplicate_organization_name_raises(db_session):
    register_user(
        db_session,
        _valid_user_create(),
    )

    with pytest.raises(OrganizationAlreadyExistsError):
        register_user(
            db_session,
            _valid_user_create(email="bob@example.com"),
        )


def test_register_user_duplicate_email_does_not_create_orphan_organization(
    db_session,
):
    """
    A failed registration must not leave a half-created Organization
    behind.
    """
    register_user(
        db_session,
        _valid_user_create(organization_name="Org One"),
    )

    with pytest.raises(EmailAlreadyExistsError):
        register_user(
            db_session,
            _valid_user_create(
                organization_name="Should Not Exist",
            ),
        )

    orphan = (
        db_session.query(Organization)
        .filter(Organization.name == "Should Not Exist")
        .first()
    )

    assert orphan is None


# --- authenticate_user -------------------------------------------------


def test_authenticate_user_with_correct_credentials(db_session):
    register_user(
        db_session,
        _valid_user_create(),
    )

    user = authenticate_user(
        db_session,
        "alice@example.com",
        "supersecret123",
    )

    assert user.email == "alice@example.com"


def test_authenticate_user_with_wrong_password_raises(db_session):
    register_user(
        db_session,
        _valid_user_create(),
    )

    with pytest.raises(InvalidCredentialsError):
        authenticate_user(
            db_session,
            "alice@example.com",
            "wrong-password",
        )


def test_authenticate_user_with_unknown_email_raises_same_error_as_wrong_password(
    db_session,
):
    # Same exception type for both cases prevents email enumeration.
    with pytest.raises(InvalidCredentialsError):
        authenticate_user(
            db_session,
            "nobody@example.com",
            "whatever",
        )


def test_authenticate_user_inactive_account_raises(db_session):
    user = register_user(
        db_session,
        _valid_user_create(),
    )

    user.is_active = False
    db_session.flush()

    with pytest.raises(InactiveUserError):
        authenticate_user(
            db_session,
            "alice@example.com",
            "supersecret123",
        )