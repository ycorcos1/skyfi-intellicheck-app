from __future__ import annotations

from functools import lru_cache
from typing import Any, Dict

from fastapi import Depends, HTTPException, Request, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from jwt import InvalidTokenError, PyJWKClient, decode as jwt_decode

from config import get_settings

settings = get_settings()
security_scheme = HTTPBearer(auto_error=False)


@lru_cache
def get_jwk_client() -> PyJWKClient:
    """
    Lazily instantiate and cache a PyJWKClient for fetching Cognito JWKS.
    """

    jwks_url = f"{settings.cognito_issuer_url}/.well-known/jwks.json"
    return PyJWKClient(jwks_url)


def verify_token(token: str) -> Dict[str, Any]:
    """
    Validate a Cognito-issued JWT and return its payload.
    """
    import logging
    logger = logging.getLogger(__name__)

    jwk_client = get_jwk_client()

    try:
        signing_key = jwk_client.get_signing_key_from_jwt(token)
    except Exception as exc:  # pylint: disable=broad-exception-caught
        logger.error("Failed to get signing key from JWT: %s", str(exc))
        logger.error("Cognito issuer URL: %s", settings.cognito_issuer_url)
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid authentication credentials",
        ) from exc

    decode_kwargs: Dict[str, Any] = {
        "algorithms": ["RS256"],
        "issuer": settings.cognito_issuer_url,
        "options": {"verify_aud": bool(settings.cognito_app_client_id)},
    }

    if settings.cognito_app_client_id:
        decode_kwargs["audience"] = settings.cognito_app_client_id

    try:
        payload: Dict[str, Any] = jwt_decode(token, signing_key.key, **decode_kwargs)
        logger.debug("Token validated successfully for user: %s", payload.get("sub"))
    except InvalidTokenError as exc:
        logger.error("Token validation failed: %s", str(exc))
        logger.error("Expected issuer: %s", settings.cognito_issuer_url)
        logger.error("Expected audience: %s", settings.cognito_app_client_id)
        # Try to decode without verification to see what's in the token
        try:
            from jwt import decode as jwt_decode_unverified
            unverified = jwt_decode_unverified(token, options={"verify_signature": False})
            logger.error("Token issuer: %s", unverified.get("iss"))
            logger.error("Token audience: %s", unverified.get("aud"))
            logger.error("Token client_id: %s", unverified.get("client_id"))
        except Exception:
            pass
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid authentication credentials",
        ) from exc

    return payload


async def get_current_user(
    request: Request,
    credentials: HTTPAuthorizationCredentials | None = Depends(security_scheme),
) -> Dict[str, Any]:
    """
    FastAPI dependency that enforces Cognito JWT authentication.
    """

    if credentials is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Authorization header missing",
        )

    token = credentials.credentials
    payload = verify_token(token)

    user_context = {
        "user_id": payload.get("sub"),
        "username": payload.get("cognito:username") or payload.get("email"),
        "email": payload.get("email"),
        "claims": payload,
    }

    request.state.user = user_context
    return user_context


def get_authenticated_user(request: Request) -> Dict[str, Any]:
    """
    Retrieve the authenticated user context stored on the request.
    """

    user_context = getattr(request.state, "user", None)
    if not user_context:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Authentication context missing",
        )

    return user_context

