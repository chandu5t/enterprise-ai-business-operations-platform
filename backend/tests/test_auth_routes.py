"""
Integration tests for the auth router: POST /auth/register, POST
/auth/login, GET /auth/me, POST /auth/logout — exercised as real HTTP
calls against the actual FastAPI app via TestClient.
"""

import pytest
from fastapi.testclient import TestClient

from app.database.session import get_db
from app.main import app
from app.models.user import User


@pytest.fixture
def client(db_session):
    """TestClient wired to the same rolled-back-per-test db_session the
    rest of the suite uses, so state from one test never leaks into
    another despite reusing the same running app instance."""

    def _override_get_db():
        yield db_session

    app.dependency_overrides[get_db] = _override_get_db
    with TestClient(app) as test_client:
        yield test_client
    app.dependency_overrides.clear()


def _register_payload(**overrides):
    defaults = dict(
        email="alice@example.com",
        password="supersecret123",
        full_name="Alice Example",
        organization_name="Acme Corp",
    )
    defaults.update(overrides)
    return defaults


# --- POST /auth/register --------------------------------------------------


def test_register_returns_201_and_user_data(client):
    response = client.post("/auth/register", json=_register_payload())

    assert response.status_code == 201
    body = response.json()
    assert body["email"] == "alice@example.com"
    assert body["full_name"] == "Alice Example"
    assert body["role"] == "admin"
    assert body["is_active"] is True
    assert "id" in body
    assert "organization_id" in body


def test_register_response_never_includes_password_fields(client):
    response = client.post("/auth/register", json=_register_payload())

    body = response.json()
    assert "password" not in body
    assert "hashed_password" not in body


def test_register_duplicate_email_returns_409(client):
    client.post(
        "/auth/register", json=_register_payload(organization_name="Org One")
    )

    response = client.post(
        "/auth/register", json=_register_payload(organization_name="Org Two")
    )

    assert response.status_code == 409


def test_register_duplicate_organization_name_returns_409(client):
    client.post(
        "/auth/register", json=_register_payload(email="alice@example.com")
    )

    response = client.post(
        "/auth/register", json=_register_payload(email="bob@example.com")
    )

    assert response.status_code == 409


def test_register_rejects_short_password_with_422(client):
    response = client.post(
        "/auth/register", json=_register_payload(password="short")
    )

    assert response.status_code == 422


def test_register_rejects_invalid_email_with_422(client):
    response = client.post(
        "/auth/register", json=_register_payload(email="not-an-email")
    )

    assert response.status_code == 422


# --- POST /auth/login -------------------------------------------------------


def test_login_with_correct_credentials_returns_token(client):
    client.post("/auth/register", json=_register_payload())

    response = client.post(
        "/auth/login",
        json={"email": "alice@example.com", "password": "supersecret123"},
    )

    assert response.status_code == 200
    body = response.json()
    assert "access_token" in body
    assert body["token_type"] == "bearer"


def test_login_with_wrong_password_returns_401(client):
    client.post("/auth/register", json=_register_payload())

    response = client.post(
        "/auth/login",
        json={"email": "alice@example.com", "password": "wrong-password"},
    )

    assert response.status_code == 401


def test_login_with_unknown_email_returns_401(client):
    response = client.post(
        "/auth/login",
        json={"email": "nobody@example.com", "password": "whatever123"},
    )

    assert response.status_code == 401


def test_login_inactive_user_returns_403(client, db_session):
    client.post("/auth/register", json=_register_payload())

    user = (
        db_session.query(User).filter(User.email == "alice@example.com").first()
    )
    user.is_active = False
    db_session.flush()

    response = client.post(
        "/auth/login",
        json={"email": "alice@example.com", "password": "supersecret123"},
    )

    assert response.status_code == 403


# --- GET /auth/me ------------------------------------------------------------


def test_me_with_valid_token_returns_current_user(client):
    client.post("/auth/register", json=_register_payload())
    login_response = client.post(
        "/auth/login",
        json={"email": "alice@example.com", "password": "supersecret123"},
    )
    token = login_response.json()["access_token"]

    response = client.get(
        "/auth/me", headers={"Authorization": f"Bearer {token}"}
    )

    assert response.status_code == 200
    assert response.json()["email"] == "alice@example.com"


def test_me_without_token_returns_401(client):
    response = client.get("/auth/me")

    assert response.status_code == 401


# --- POST /auth/logout ---------------------------------------------------------


def test_logout_with_valid_token_returns_200(client):
    client.post("/auth/register", json=_register_payload())
    login_response = client.post(
        "/auth/login",
        json={"email": "alice@example.com", "password": "supersecret123"},
    )
    token = login_response.json()["access_token"]

    response = client.post(
        "/auth/logout", headers={"Authorization": f"Bearer {token}"}
    )

    assert response.status_code == 200
    assert "message" in response.json()


def test_logout_without_token_returns_401(client):
    response = client.post("/auth/logout")

    assert response.status_code == 401


# --- End-to-end flow -------------------------------------------------------


def test_full_register_login_me_flow(client):
    register_response = client.post("/auth/register", json=_register_payload())
    assert register_response.status_code == 201
    registered_id = register_response.json()["id"]

    login_response = client.post(
        "/auth/login",
        json={"email": "alice@example.com", "password": "supersecret123"},
    )
    assert login_response.status_code == 200
    token = login_response.json()["access_token"]

    me_response = client.get(
        "/auth/me", headers={"Authorization": f"Bearer {token}"}
    )
    assert me_response.status_code == 200
    assert me_response.json()["id"] == registered_id