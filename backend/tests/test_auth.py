from __future__ import annotations

import base64
import os
import time
from typing import Any, Dict, Tuple

import pytest
from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.primitives.asymmetric import rsa
from fastapi.testclient import TestClient
from jwt import encode as jwt_encode

# Ensure environment is configured prior to importing the application.
os.environ.setdefault("DB_URL", "sqlite:///./test.db")
os.environ.setdefault("COGNITO_REGION", "us-east-1")
os.environ.setdefault("COGNITO_USER_POOL_ID", "test-pool")
os.environ.setdefault("COGNITO_APP_CLIENT_ID", "test-client")
os.environ.setdefault(
    "COGNITO_ISSUER",
    "https://cognito-idp.us-east-1.amazonaws.com/test-pool",
)

from app.core import auth as auth_utils
from main import app

client = TestClient(app)


def _int_to_base64(value: int) -> str:
    byte_length = (value.bit_length() + 7) // 8
    return base64.urlsafe_b64encode(value.to_bytes(byte_length, "big")).decode().rstrip("=")


def _generate_rsa_keypair(kid: str = "test-key") -> Tuple[str, Dict[str, Any]]:
    private_key = rsa.generate_private_key(public_exponent=65537, key_size=2048)
    public_numbers = private_key.public_key().public_numbers()

    jwk = {
        "kty": "RSA",
        "use": "sig",
        "kid": kid,
        "alg": "RS256",
        "n": _int_to_base64(public_numbers.n),
        "e": _int_to_base64(public_numbers.e),
    }

    private_pem = private_key.private_bytes(
        encoding=serialization.Encoding.PEM,
        format=serialization.PrivateFormat.PKCS8,
        encryption_algorithm=serialization.NoEncryption(),
    ).decode()

    return private_pem, jwk


@pytest.fixture(autouse=True)
def clear_jwk_cache() -> None:
    """
    Ensure each test runs with a clean JWKS cache.
    """

    auth_utils.get_jwk_client.cache_clear()


@pytest.fixture
def jwks(monkeypatch: pytest.MonkeyPatch) -> Tuple[str, Dict[str, Any]]:
    """
    Provide a dynamically generated JWKS and patch the PyJWT client to use it.
    """

    private_key, jwk = _generate_rsa_keypair()
    jwks_payload = {"keys": [jwk]}

    class _MockResponse:
        def __init__(self, payload: Dict[str, Any]):
            self._payload = payload

        def json(self) -> Dict[str, Any]:
            return self._payload

        def raise_for_status(self) -> None:
            return None

    def _mock_requests_get(*args: Any, **kwargs: Any) -> _MockResponse:  # noqa: D401
        return _MockResponse(jwks_payload)

    # Patch requests.get used internally by PyJWKClient.
    monkeypatch.setattr("jwt.api_jwk_client.requests.get", _mock_requests_get)

    return private_key, jwks_payload


def _issue_token(
    private_key: str,
    *,
    kid: str = "test-key",
    subject: str = "user-123",
    email: str = "user@example.com",
    expires_in: int = 300,
    issuer: str = "https://cognito-idp.us-east-1.amazonaws.com/test-pool",
    audience: str = "test-client",
) -> str:
    now = int(time.time())
    payload = {
        "sub": subject,
        "email": email,
        "cognito:username": subject,
        "token_use": "id",
        "iss": issuer,
        "aud": audience,
        "iat": now,
        "exp": now + expires_in,
    }
    headers = {"kid": kid}
    return jwt_encode(payload, private_key, algorithm="RS256", headers=headers)


def test_protected_endpoint_requires_auth() -> None:
    response = client.get("/v1/protected")
    assert response.status_code == 401
    assert response.json()["detail"] == "Authorization header missing"


def test_protected_endpoint_allows_valid_token(jwks: Tuple[str, Dict[str, Any]]) -> None:
    private_key, _ = jwks
    token = _issue_token(private_key)

    response = client.get("/v1/protected", headers={"Authorization": f"Bearer {token}"})

    assert response.status_code == 200
    body = response.json()
    assert body["message"] == "Access granted"
    assert body["user"]["user_id"] == "user-123"
    assert body["user"]["email"] == "user@example.com"


def test_protected_endpoint_rejects_expired_token(
    jwks: Tuple[str, Dict[str, Any]]
) -> None:
    private_key, _ = jwks
    token = _issue_token(private_key, expires_in=-10)

    response = client.get("/v1/protected", headers={"Authorization": f"Bearer {token}"})

    assert response.status_code == 401
    assert response.json()["detail"] == "Invalid authentication credentials"


def test_protected_endpoint_rejects_invalid_signature(
    jwks: Tuple[str, Dict[str, Any]]
) -> None:
    # Generate a token signed with a different key but same kid.
    other_private_key, _ = _generate_rsa_keypair()
    token = _issue_token(other_private_key)

    response = client.get("/v1/protected", headers={"Authorization": f"Bearer {token}"})

    assert response.status_code == 401
    assert response.json()["detail"] == "Invalid authentication credentials"

