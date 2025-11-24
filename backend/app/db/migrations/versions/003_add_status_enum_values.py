"""
Ensure company and analysis status enums contain required values.
"""
from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision = "003_add_status_enum_values"
down_revision = "002_update_status_enums"
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
    result = bind.execute(exists_stmt, {"enum_name": enum_name, "value": value})
    return result.scalar() is not None


def _add_enum_value(enum_name: str, value: str) -> None:
    bind = op.get_bind()
    if _enum_value_exists(bind, enum_name, value):
        return

    ctx = op.get_context()
    statement = sa.text(f"ALTER TYPE {enum_name} ADD VALUE :value")
    with ctx.autocommit_block():
        bind.execute(statement, {"value": value})


def upgrade() -> None:
    for value in ("pending", "approved", "suspicious", "fraudulent"):
        _add_enum_value("companystatus", value)

    for value in ("pending", "in_progress", "complete"):
        _add_enum_value("analysisstatus", value)


def downgrade() -> None:
    # PostgreSQL cannot drop individual enum values easily; no-op downgrade.
    pass

