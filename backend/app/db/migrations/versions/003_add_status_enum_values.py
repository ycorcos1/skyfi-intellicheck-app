"""
Ensure company and analysis status enums contain required values.
"""
from alembic import op

# revision identifiers, used by Alembic.
revision = "003_add_status_enum_values"
down_revision = "002_update_status_enums"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Company status enum must include all four values
    op.execute("ALTER TYPE companystatus ADD VALUE IF NOT EXISTS 'pending'")
    op.execute("ALTER TYPE companystatus ADD VALUE IF NOT EXISTS 'approved'")
    op.execute("ALTER TYPE companystatus ADD VALUE IF NOT EXISTS 'suspicious'")
    op.execute("ALTER TYPE companystatus ADD VALUE IF NOT EXISTS 'fraudulent'")

    # Analysis status enum must include the simplified states
    op.execute("ALTER TYPE analysisstatus ADD VALUE IF NOT EXISTS 'pending'")
    op.execute("ALTER TYPE analysisstatus ADD VALUE IF NOT EXISTS 'in_progress'")
    op.execute("ALTER TYPE analysisstatus ADD VALUE IF NOT EXISTS 'complete'")


def downgrade() -> None:
    # PostgreSQL cannot drop individual enum values easily; no-op downgrade.
    pass

