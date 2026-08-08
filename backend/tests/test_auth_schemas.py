"""
Unit tests for the auth/user Pydantic schemas — pure validation logic,
no database or HTTP client needed.
"""

import pytest
from pydantic import ValidationError

from app.schemas import LoginRequest, Token, UserCreate, UserResponse


def test_user_create_accepts_valid_payload():
    user = UserCreate(
        email="alice@example.com",
        password="supersecret123",
        full_name="Alice Example",
        organization_name="Acme Corp",
    )

    assert user.email == "alice@example.com"
    assert user.organization_name == "Acme Corp"


def test_user_create_rejects_invalid_email():
    with pytest.raises(ValidationError):
        UserCreate(
            email="not-an-email",
            password="supersecret123",
            full_name="Alice Example",
            organization_name="Acme Corp",
        )


def test_user_create_rejects_short_password():
    with pytest.raises(ValidationError):
        UserCreate(
            email="alice@example.com",
            password="short",  # under the 8-char minimum
            full_name="Alice Example",
            organization_name="Acme Corp",
        )


def test_user_create_rejects_empty_full_name():
    with pytest.raises(ValidationError):
        UserCreate(
            email="alice@example.com",
            password="supersecret123",
            full_name="",
            organization_name="Acme Corp",
        )


def test_user_response_has_no_password_field():
    # UserResponse must never be able to carry a password/hash — this
    # asserts the field simply doesn't exist on the schema.
    assert "hashed_password" not in UserResponse.model_fields
    assert "password" not in UserResponse.model_fields


def test_login_request_accepts_valid_payload():
    login = LoginRequest(email="alice@example.com", password="whatever")
    assert login.email == "alice@example.com"


def test_login_request_rejects_invalid_email():
    with pytest.raises(ValidationError):
        LoginRequest(email="not-an-email", password="whatever")


def test_token_defaults_token_type_to_bearer():
    token = Token(access_token="abc.def.ghi")
    assert token.token_type == "bearer"