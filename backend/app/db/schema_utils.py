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

            # Capture existing enum labels to avoid referencing removed values
            company_labels = [
                row[0]
                for row in autocommit_conn.execute(
                    text(
                        """
                        SELECT e.enumlabel
                        FROM pg_type t
                        JOIN pg_enum e ON t.oid = e.enumtypid
                        WHERE t.typname = 'companystatus'
                        """
                    )
                )
            ]
            analysis_labels = [
                row[0]
                for row in autocommit_conn.execute(
                    text(
                        """
                        SELECT e.enumlabel
                        FROM pg_type t
                        JOIN pg_enum e ON t.oid = e.enumtypid
                        WHERE t.typname = 'analysisstatus'
                        """
                    )
                )
            ]

            has_company_pending = "pending" in company_labels
            has_rejected_values = any(label in ("rejected", "revoked") for label in company_labels)
            has_analysis_pending = "pending" in analysis_labels
            has_legacy_analysis = any(label in ("completed", "failed", "incomplete") for label in analysis_labels)

            if has_company_pending and has_rejected_values:
                autocommit_conn.execute(
                    text(
                        "UPDATE companies SET status = 'suspicious' "
                        "WHERE status IN ('rejected', 'revoked')"
                    )
                )

            if has_analysis_pending and has_legacy_analysis:
                autocommit_conn.execute(
                    text(
                        "UPDATE companies SET analysis_status = 'complete' "
                        "WHERE analysis_status IN ('completed', 'failed', 'incomplete')"
                    )
                )

            # Risk-based normalization always safe
            autocommit_conn.execute(
                text("UPDATE companies SET status = 'fraudulent' WHERE risk_score >= 70")
            )
            autocommit_conn.execute(
                text(
                    "UPDATE companies SET status = 'suspicious' "
                    "WHERE status IN ('pending', 'approved') AND risk_score BETWEEN 31 AND 69"
                )
            )
            autocommit_conn.execute(
                text(
                    "UPDATE companies SET status = 'approved' "
                    "WHERE status IN ('pending', 'approved') AND analysis_status = 'complete' AND risk_score <= 30"
                )
            )
            autocommit_conn.execute(
                text(
                    "UPDATE companies SET status = 'suspicious' "
                    "WHERE analysis_status <> 'complete' AND status <> 'fraudulent'"
                )
            )

    except Exception:  # pragma: no cover - defensive; log and continue
        log.exception("Failed to ensure status schema")
        return

    _STATUS_SCHEMA_SYNCED = True

