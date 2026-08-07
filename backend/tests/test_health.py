"""
Tests for the system health-check endpoint.

/health now checks real database connectivity (Module 2), so this test
requires a reachable Postgres database — the same one the app itself
would use. It exercises the exact behavior Docker's HEALTHCHECK and any
future deploy/readiness gate depend on.
"""

from fastapi.testclient import TestClient

from app.main import app

client = TestClient(app)


def test_health_check_returns_ok_when_database_reachable():
    response = client.get("/health")

    assert response.status_code == 200

    body = response.json()
    assert body["status"] == "ok"
    assert body["database"] == "connected"
    assert "service" in body
    assert "environment" in body


def test_docs_endpoint_is_available():
    response = client.get("/docs")

    assert response.status_code == 200