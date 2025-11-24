import logging
from sqlalchemy import text
from sqlalchemy.engine import Engine

_STATUS_SCHEMA_SYNCED = False


def ensure_status_schema(engine: Engine, logger: logging.Logger | None = None) -> None:
    """
    Make sure the companystatus and analysisstatus enums contain the expected values and
    normalize any legacy rows to the new status model.
    """
    global _STATUS_SCHEMA_SYNCED
    if _STATUS_SCHEMA_SYNCED:
        return

    log = logger or logging.getLogger(__name__)

    try:
        with engine.connect() as connection:
            autocommit_conn = connection.execution_options(isolation_level="AUTOCOMMIT")

            # Ensure enum values exist (PostgreSQL 9.6+ supports IF NOT EXISTS)
            enum_statements = [
                "ALTER TYPE companystatus ADD VALUE IF NOT EXISTS 'pending'",
                "ALTER TYPE companystatus ADD VALUE IF NOT EXISTS 'approved'",
                "ALTER TYPE companystatus ADD VALUE IF NOT EXISTS 'suspicious'",
                "ALTER TYPE companystatus ADD VALUE IF NOT EXISTS 'fraudulent'",
                "ALTER TYPE analysisstatus ADD VALUE IF NOT EXISTS 'pending'",
                "ALTER TYPE analysisstatus ADD VALUE IF NOT EXISTS 'in_progress'",
                "ALTER TYPE analysisstatus ADD VALUE IF NOT EXISTS 'complete'",
            ]

            for stmt in enum_statements:
                autocommit_conn.execute(text(stmt))

            # Normalize legacy status values
            data_updates = [
                "UPDATE companies SET status = 'suspicious' WHERE status IN ('rejected', 'revoked')",
                "UPDATE companies SET analysis_status = 'complete' WHERE analysis_status IN ('completed', 'failed', 'incomplete')",
                "UPDATE companies SET status = 'fraudulent' WHERE risk_score >= 70",
                (
                    "UPDATE companies SET status = 'suspicious' "
                    "WHERE status IN ('pending', 'approved') AND risk_score BETWEEN 31 AND 69"
                ),
                (
                    "UPDATE companies SET status = 'approved' "
                    "WHERE status IN ('pending', 'approved') AND analysis_status = 'complete' AND risk_score <= 30"
                ),
                (
                    "UPDATE companies SET status = 'suspicious' "
                    "WHERE analysis_status <> 'complete' AND status <> 'fraudulent'"
                ),
            ]

            for stmt in data_updates:
                autocommit_conn.execute(text(stmt))

    except Exception:  # pragma: no cover - defensive; log and continue
        log.exception("Failed to ensure status schema")
        return

    _STATUS_SCHEMA_SYNCED = True

