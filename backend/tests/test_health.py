"""
Tests for the system health-check endpoint.

This is the first real test in the suite — it verifies the FastAPI app
boots and its liveness endpoint responds correctly. This is deliberately
not a placeholder: it's the same behavior the Dockerfile's HEALTHCHECK
and the CI pipeline's future deploy checks will depend on, so it earns
its place in the suite from day one. Every subsequent test file placed
in this directory is auto-discovered by pytest without any CI changes.
"""

from fastapi.testclient import TestClient

from app.main import app

client = TestClient(app)


def test_health_check_returns_ok():
    response = client.get("/health")

    assert response.status_code == 200

    body = response.json()
    assert body["status"] == "ok"
    assert "service" in body
    assert "environment" in body


def test_docs_endpoint_is_available():
    response = client.get("/docs")

    assert response.status_code == 200