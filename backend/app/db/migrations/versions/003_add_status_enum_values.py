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


def _add_enum_value(enum_name: str, value: str) -> None:
    ctx = op.get_context()
    bind = op.get_bind()
    statement = sa.text(
        f"ALTER TYPE {enum_name} ADD VALUE IF NOT EXISTS :value"
    ).bindparams(value=value)
    with ctx.autocommit_block():
        bind.execute(statement)


def upgrade() -> None:
    for value in ("pending", "approved", "suspicious", "fraudulent"):
        _add_enum_value("companystatus", value)

    for value in ("pending", "in_progress", "complete"):
        _add_enum_value("analysisstatus", value)


def downgrade() -> None:
    # PostgreSQL cannot drop individual enum values easily; no-op downgrade.
    pass

