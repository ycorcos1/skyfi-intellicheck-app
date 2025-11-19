from __future__ import annotations

from typing import Any, Dict

from fastapi import APIRouter
from sqlalchemy import text

from app.core.database import get_session_local
from config import get_settings

router = APIRouter()
settings = get_settings()


@router.get("/health", tags=["health"])
def health_check() -> Dict[str, Any]:
    """
    Health check endpoint that validates application and database connectivity.
    Returns a `degraded` status if the database connection fails but the API is reachable.
    Always returns 200 status code so ALB health checks pass even if DB is down.
    
    Note: Does not use Depends(get_db) to avoid 500 errors if database connection fails.
    Instead, handles database connection failures gracefully.
    """
    database_status = "healthy"

    # Try to get a database session manually to handle connection failures gracefully
    # This ensures we always return 200, even if the database is unreachable
    try:
        session_local = get_session_local()
        db = session_local()
        try:
            db.execute(text("SELECT 1"))
        except Exception as exc:  # pylint: disable=broad-exception-caught
            database_status = f"unhealthy: {exc}"
        finally:
            db.close()
    except Exception as exc:  # pylint: disable=broad-exception-caught
        # Database connection/session creation failed - this is OK for health checks
        database_status = f"unhealthy: {exc}"

    overall_status = "healthy" if database_status == "healthy" else "degraded"

    # Always return 200 - ALB health check requires 200 status
    # The status field indicates actual health, but HTTP status is always 200
    return {
        "status": overall_status,
        "database": database_status,
        "environment": settings.environment,
    }


@router.get("/version", tags=["health"])
def version_info() -> Dict[str, Any]:
    """
    Return API version and optional build metadata for observability.
    """
    response: Dict[str, Any] = {
        "api_version": settings.api_version,
        "environment": settings.environment,
    }

    if settings.git_sha:
        response["git_sha"] = settings.git_sha
    if settings.build_timestamp:
        response["build_timestamp"] = settings.build_timestamp

    return response



