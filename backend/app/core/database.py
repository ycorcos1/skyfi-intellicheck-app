from __future__ import annotations

from typing import Any, Dict, Generator

from sqlalchemy import create_engine
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import Session, sessionmaker

from app.core.config import get_settings

settings = get_settings()

# Configure engine options based on database type
engine_options: Dict[str, Any] = {
    "pool_pre_ping": True,  # Verify connections before using them
    "echo": False,  # Set to True for SQL query logging in development
}

# PostgreSQL/RDS requires connection pooling; SQLite does not support it
if settings.db_url.startswith("sqlite"):
    engine_options["connect_args"] = {"check_same_thread": False}
else:
    # PostgreSQL connection pooling for RDS
    engine_options.update({
        "pool_size": 10,  # Number of connections to maintain
        "max_overflow": 20,  # Additional connections beyond pool_size
    })

engine = create_engine(settings.db_url, **engine_options)

SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

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
