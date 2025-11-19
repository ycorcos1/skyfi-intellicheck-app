from __future__ import annotations

import time
from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware

from app.api import api_router
from app.api.v1.endpoints import health
from app.core.logging import (
    setup_structured_logging,
    set_correlation_id,
    get_correlation_id,
    generate_correlation_id,
    get_logger
)
from app.core.metrics import get_metrics_client
from config import get_settings

settings = get_settings()

# Set up structured logging
setup_structured_logging(
    service_name="api",
    level="INFO",
    environment=settings.environment
)
logger = get_logger(__name__)

app = FastAPI(
    title="SkyFi IntelliCheck API",
    version=settings.api_version,
    description="Backend service for SkyFi's enterprise verification platform.",
    docs_url="/docs",
    redoc_url="/redoc",
)

# Allow all origins for now; will be tightened once frontend domain is known.
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Request logging and metrics middleware
@app.middleware("http")
async def logging_middleware(request: Request, call_next):
    """Middleware for request logging, correlation ID tracking, and metrics."""
    # Extract or generate correlation ID
    correlation_id = request.headers.get("X-Correlation-ID") or generate_correlation_id()
    set_correlation_id(correlation_id)
    request.state.correlation_id = correlation_id
    
    # Record start time
    start_time = time.time()
    
    # Process request
    try:
        response = await call_next(request)
        duration_ms = (time.time() - start_time) * 1000
        
        # Record metrics
        metrics = get_metrics_client()
        metrics.record_api_request(
            endpoint=request.url.path,
            method=request.method,
            status_code=response.status_code,
            duration_ms=duration_ms,
            correlation_id=correlation_id
        )
        
        # Log request
        logger.info(
            "API Request",
            extra={
                "method": request.method,
                "path": request.url.path,
                "status_code": response.status_code,
                "duration_ms": duration_ms,
                "query_params": str(request.query_params) if request.query_params else None,
            }
        )
        
        # Add correlation ID to response headers
        response.headers["X-Correlation-ID"] = correlation_id
        return response
        
    except Exception as e:
        duration_ms = (time.time() - start_time) * 1000
        
        # Record error metrics
        metrics = get_metrics_client()
        metrics.record_api_request(
            endpoint=request.url.path,
            method=request.method,
            status_code=500,
            duration_ms=duration_ms,
            correlation_id=correlation_id
        )
        
        # Log error
        logger.error(
            "API Request Error",
            extra={
                "method": request.method,
                "path": request.url.path,
                "duration_ms": duration_ms,
                "error": str(e),
            },
            exc_info=True
        )
        raise

# Health and version endpoints (no auth required)
app.include_router(health.router)

# Versioned API placeholder (will be populated in subsequent PRs)
app.include_router(api_router)


@app.on_event("startup")
def on_startup() -> None:
    """
    Application startup hook.
    """
    logger.info(
        "Starting SkyFi IntelliCheck API",
        extra={
            "version": settings.api_version,
            "environment": settings.environment,
        }
    )


@app.get("/", include_in_schema=False)
def root() -> dict[str, str]:
    """
    Simple root endpoint pointing to documentation for convenience.
    """
    return {
        "message": "SkyFi IntelliCheck API is running.",
        "docs_url": "/docs",
        "health_url": "/health",
    }


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(
        "main:app",
        host=settings.host,
        port=settings.port,
        reload=settings.environment == "development",
    )



