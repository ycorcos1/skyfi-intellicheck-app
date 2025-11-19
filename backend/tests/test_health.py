from __future__ import annotations

import os

# Ensure required environment variables are configured before importing the app.
os.environ.setdefault("DB_URL", "sqlite:///./test.db")
os.environ.setdefault("COGNITO_REGION", "us-east-1")
os.environ.setdefault("COGNITO_USER_POOL_ID", "test-pool")
os.environ.setdefault("COGNITO_APP_CLIENT_ID", "test-client")
os.environ.setdefault(
    "COGNITO_ISSUER",
    "https://cognito-idp.us-east-1.amazonaws.com/test-pool",
)

from fastapi.testclient import TestClient

from main import app

client = TestClient(app)


def test_health_endpoint() -> None:
    response = client.get("/health")
    assert response.status_code == 200

    payload = response.json()
    assert payload["status"] in {"healthy", "degraded"}
    assert "database" in payload
    assert payload["environment"] == "development"


def test_version_endpoint() -> None:
    response = client.get("/version")
    assert response.status_code == 200

    payload = response.json()
    assert payload["api_version"] == "1.0.0"
    assert payload["environment"] == "development"

