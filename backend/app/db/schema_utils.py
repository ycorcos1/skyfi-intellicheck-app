import logging
from sqlalchemy import text
from sqlalchemy.engine import Engine

_STATUS_SCHEMA_SYNCED = False


def _enum_labels(connection, enum_name: str) -> list[str]:
    try:
        result = connection.execute(
            text(
                """
                SELECT e.enumlabel
                FROM pg_type t
                JOIN pg_enum e ON t.oid = e.enumtypid
                WHERE t.typname = :enum_name
                """
            ),
            {"enum_name": enum_name},
        )
        return [row[0] for row in result]
    except Exception:
        return []


def _rename_enum_value(connection, enum_name: str, old: str, new: str, log: logging.Logger) -> None:
    if old == new:
        return
    current_labels = _enum_labels(connection, enum_name)
    if old not in current_labels or new in current_labels:
        return
    try:
        connection.execute(text(f"ALTER TYPE {enum_name} RENAME VALUE '{old}' TO '{new}'"))
        log.info("Renamed enum value", extra={"enum": enum_name, "old": old, "new": new})
    except Exception:
        log.warning("Failed to rename enum value %s -> %s for %s", old, new, enum_name, exc_info=True)


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

            # Rename legacy uppercase enum labels to lowercase (idempotent)
            _rename_enum_value(autocommit_conn, "companystatus", "PENDING", "pending", log)
            _rename_enum_value(autocommit_conn, "companystatus", "APPROVED", "approved", log)
            _rename_enum_value(autocommit_conn, "companystatus", "SUSPICIOUS", "suspicious", log)
            _rename_enum_value(autocommit_conn, "companystatus", "FRAUDULENT", "fraudulent", log)

            _rename_enum_value(autocommit_conn, "analysisstatus", "PENDING", "pending", log)
            _rename_enum_value(autocommit_conn, "analysisstatus", "IN_PROGRESS", "in_progress", log)
            _rename_enum_value(autocommit_conn, "analysisstatus", "COMPLETE", "complete", log)

            # Ensure enum values exist (PostgreSQL 9.6+ supports IF NOT EXISTS)
            # Attempt to add enum values, but swallow errors if the enum is missing (older schema).
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
                try:
                    autocommit_conn.execute(text(stmt))
                except Exception:
                    # Ignore missing enum type or other non-critical failures.
                    log.debug("Enum alteration failed (ignored): %s", stmt, exc_info=True)

            # Determine current enum labels, ignoring errors
            company_labels = _enum_labels(autocommit_conn, "companystatus")
            analysis_labels = _enum_labels(autocommit_conn, "analysisstatus")

            has_company_pending = "pending" in company_labels
            if has_company_pending and any(label in ("rejected", "revoked") for label in company_labels):
                try:
                    autocommit_conn.execute(
                        text(
                            "UPDATE companies SET status = 'suspicious' "
                            "WHERE status IN ('rejected', 'revoked')"
                        )
                    )
                except Exception:
                    log.warning("Failed to normalize legacy company statuses", exc_info=True)

            has_analysis_pending = "pending" in analysis_labels
            if has_analysis_pending and any(label in ("completed", "failed", "incomplete") for label in analysis_labels):
                try:
                    autocommit_conn.execute(
                        text(
                            "UPDATE companies SET analysis_status = 'complete' "
                            "WHERE analysis_status IN ('completed', 'failed', 'incomplete')"
                        )
                    )
                except Exception:
                    log.warning("Failed to normalize legacy analysis statuses", exc_info=True)

            # Risk-based normalization always safe
            try:
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
            except Exception:
                log.warning("Failed to run risk-based status normalization", exc_info=True)

    except Exception:  # pragma: no cover - defensive; log and continue
        log.exception("Failed to ensure status schema")
        return

    _STATUS_SCHEMA_SYNCED = True

