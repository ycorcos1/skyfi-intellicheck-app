"""
Rename company and analysis status enum labels to lowercase.
"""
from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision = "004_lowercase_status_enum_values"
down_revision = "003_add_status_enum_values"
branch_labels = None
depends_on = None


def _enum_value_exists(bind, enum_name: str, value: str) -> bool:
    exists_stmt = sa.text(
        """
        SELECT 1
        FROM pg_type t
        JOIN pg_enum e ON t.oid = e.enumtypid
        WHERE t.typname = :enum_name AND e.enumlabel = :value
        LIMIT 1
        """
    )
    return bind.execute(exists_stmt, {"enum_name": enum_name, "value": value}).scalar() is not None


def _rename_enum_value(enum_name: str, old: str, new: str) -> None:
    bind = op.get_bind()
    if not _enum_value_exists(bind, enum_name, old):
        # Already renamed (or legacy value missing)
        return
    op.execute(f"ALTER TYPE {enum_name} RENAME VALUE '{old}' TO '{new}'")


def upgrade() -> None:
    # Company status enum values
    _rename_enum_value("companystatus", "PENDING", "pending")
    _rename_enum_value("companystatus", "APPROVED", "approved")
    _rename_enum_value("companystatus", "SUSPICIOUS", "suspicious")
    _rename_enum_value("companystatus", "FRAUDULENT", "fraudulent")

    # Analysis status enum values
    _rename_enum_value("analysisstatus", "PENDING", "pending")
    _rename_enum_value("analysisstatus", "IN_PROGRESS", "in_progress")
    _rename_enum_value("analysisstatus", "COMPLETE", "complete")


def downgrade() -> None:
    # Revert to uppercase values if needed
    _rename_enum_value("analysisstatus", "complete", "COMPLETE")
    _rename_enum_value("analysisstatus", "in_progress", "IN_PROGRESS")
    _rename_enum_value("analysisstatus", "pending", "PENDING")

    _rename_enum_value("companystatus", "fraudulent", "FRAUDULENT")
    _rename_enum_value("companystatus", "suspicious", "SUSPICIOUS")
    _rename_enum_value("companystatus", "approved", "APPROVED")
    _rename_enum_value("companystatus", "pending", "PENDING")

