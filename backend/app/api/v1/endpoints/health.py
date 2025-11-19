from __future__ import annotations

from typing import Any, Dict

from fastapi import APIRouter, Depends
from sqlalchemy import text
from sqlalchemy.orm import Session

from app.core.database import get_db
from config import get_settings

router = APIRouter()
settings = get_settings()


@router.get("/health", tags=["health"])
def health_check(db: Session = Depends(get_db)) -> Dict[str, Any]:
    """
    Health check endpoint that validates application and database connectivity.
    Returns a `degraded` status if the database connection fails but the API is reachable.
    """
    database_status = "healthy"

    try:
        db.execute(text("SELECT 1"))
    except Exception as exc:  # pylint: disable=broad-exception-caught
        database_status = f"unhealthy: {exc}"

    overall_status = "healthy" if database_status == "healthy" else "degraded"

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



