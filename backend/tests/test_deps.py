"""
Tests for app.api.deps.get_current_user.

Exercised as real HTTP calls against a minimal throwaway FastAPI app
with one protected route — this verifies the exact status codes and
headers a real protected route returns (header parsing, dependency
injection, everything), not just the Python function called directly.
"""

import uuid
from datetime import timedelta

import pytest
from fastapi import Depends, FastAPI
from fastapi.testclient import TestClient

from app.api.deps import get_current_user
from app.database.session import get_db
from app.models.user import User
from app.schemas.user import UserCreate
from app.services.auth_service import register_user
from app.utils.security import create_access_token

_test_app = FastAPI()


@_test_app.get("/protected")
def _protected_route(current_user: User = Depends(get_current_user)):
    return {"email": current_user.email, "id": str(current_user.id)}


@pytest.fixture
def client(db_session):
    """TestClient wired to the same rolled-back-per-test db_session the
    rest of the suite uses, so users registered in a test are visible
    to get_current_user's lookup within that same test."""

    def _override_get_db():
        yield db_session

    _test_app.dependency_overrides[get_db] = _override_get_db
    with TestClient(_test_app) as test_client:
        yield test_client
    _test_app.dependency_overrides.clear()


@pytest.fixture
def registered_user(db_session) -> User:
    return register_user(
        db_session,
        UserCreate(
            email="alice@example.com",
            password="supersecret123",
            full_name="Alice Example",
            organization_name="Acme Corp",
        ),
    )


def test_valid_token_returns_current_user(client, registered_user):
    token = create_access_token(subject=str(registered_user.id))

    response = client.get(
        "/protected", headers={"Authorization": f"Bearer {token}"}
    )

    assert response.status_code == 200
    assert response.json()["email"] == "alice@example.com"


def test_missing_authorization_header_returns_401(client):
    response = client.get("/protected")

    assert response.status_code == 401
    assert response.headers.get("www-authenticate") == "Bearer"


def test_malformed_authorization_header_returns_401(client):
    # Doesn't match the "Bearer <token>" scheme at all.
    response = client.get(
        "/protected", headers={"Authorization": "not-a-bearer-token"}
    )

    assert response.status_code == 401


def test_tampered_token_signature_returns_401(client, registered_user):
    token = create_access_token(subject=str(registered_user.id))
    tampered = token[:-1] + ("A" if token[-1] != "A" else "B")

    response = client.get(
        "/protected", headers={"Authorization": f"Bearer {tampered}"}
    )

    assert response.status_code == 401


def test_expired_token_returns_401(client, registered_user):
    token = create_access_token(
        subject=str(registered_user.id), expires_delta=timedelta(seconds=-1)
    )

    response = client.get(
        "/protected", headers={"Authorization": f"Bearer {token}"}
    )

    assert response.status_code == 401


def test_token_for_nonexistent_user_returns_401(client):
    # Well-formed, validly signed token — just for a user id that was
    # never registered (e.g. the account was deleted after the token
    # was issued).
    token = create_access_token(subject=str(uuid.uuid4()))

    response = client.get(
        "/protected", headers={"Authorization": f"Bearer {token}"}
    )

    assert response.status_code == 401


def test_token_with_malformed_subject_returns_401(client):
    token = create_access_token(subject="not-a-valid-uuid")

    response = client.get(
        "/protected", headers={"Authorization": f"Bearer {token}"}
    )

    assert response.status_code == 401


def test_inactive_user_returns_403(client, registered_user, db_session):
    registered_user.is_active = False
    db_session.flush()

    token = create_access_token(subject=str(registered_user.id))

    response = client.get(
        "/protected", headers={"Authorization": f"Bearer {token}"}
    )

    assert response.status_code == 403