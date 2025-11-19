from __future__ import annotations

from typing import Any, Dict, Generator, Optional

from sqlalchemy import create_engine
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import Session, sessionmaker

from app.core.config import get_settings

settings = get_settings()

# Configure engine options based on database type
def _get_engine_options() -> Dict[str, Any]:
    """Get engine options - called lazily to avoid blocking on import."""
    options: Dict[str, Any] = {
        "pool_pre_ping": True,  # Verify connections before using them
        "echo": False,  # Set to True for SQL query logging in development
    }
    
    if not settings.db_url.startswith("sqlite"):
        # PostgreSQL connection pooling for RDS
        options.update({
            "pool_size": 10,  # Number of connections to maintain
            "max_overflow": 20,  # Additional connections beyond pool_size
            "connect_args": {
                "connect_timeout": 5,  # 5 second connection timeout to avoid hanging
            },
        })
    else:
        options["connect_args"] = {"check_same_thread": False}
    
    return options

# Lazy initialization - only create engine when first accessed
_engine: Optional[Any] = None
_SessionLocal: Optional[sessionmaker] = None


def _get_engine():
    """Get or create the database engine (lazy initialization)."""
    global _engine
    if _engine is None:
        try:
            engine_options = _get_engine_options()
            _engine = create_engine(settings.db_url, **engine_options)
        except Exception as e:
            # Log error but don't crash - allow app to start
            import sys
            print(f"WARNING: Database engine creation failed: {e}", file=sys.stderr)
            sys.stderr.flush()
            # Re-raise to let health check handle it gracefully
            raise
    return _engine


def _get_session_local():
    """Get or create the session maker (lazy initialization)."""
    global _SessionLocal
    if _SessionLocal is None:
        _SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=_get_engine())
    return _SessionLocal


# For backwards compatibility - these will be created on first access
class _LazyEngine:
    """Lazy wrapper for engine that only creates it when accessed."""
    def __getattr__(self, name):
        return getattr(_get_engine(), name)

class _LazySessionLocal:
    """Lazy wrapper for SessionLocal that only creates it when accessed."""
    def __call__(self, *args, **kwargs):
        return _get_session_local()(*args, **kwargs)

engine = _LazyEngine()
SessionLocal = _LazySessionLocal()

Base = declarative_base()


def get_db() -> Generator[Session, None, None]:
    """
    Dependency function for FastAPI to get database session.
    
    Usage:
        @app.get("/endpoint")
        def endpoint(db: Session = Depends(get_db)):
            # Use db session here
    """
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
