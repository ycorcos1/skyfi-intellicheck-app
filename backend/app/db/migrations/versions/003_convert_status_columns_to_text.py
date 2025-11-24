"""
Convert company status columns to text.
"""
from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision = "003_convert_status_columns_to_text"
down_revision = "002_update_status_enums"
branch_labels = None
depends_on = None

NEW_COMPANY_STATUS_VALUES = ("pending", "approved", "suspicious", "fraudulent")
NEW_ANALYSIS_STATUS_VALUES = ("pending", "in_progress", "complete")


def upgrade() -> None:
    # Drop existing defaults to avoid casting issues
    op.execute("ALTER TABLE companies ALTER COLUMN status DROP DEFAULT")
    op.execute("ALTER TABLE companies ALTER COLUMN analysis_status DROP DEFAULT")

    # Convert enum columns to text
    op.execute("ALTER TABLE companies ALTER COLUMN status TYPE TEXT USING status::text")
    op.execute(
        "ALTER TABLE companies ALTER COLUMN analysis_status TYPE TEXT USING analysis_status::text"
    )

    # Reinstate defaults
    op.execute("ALTER TABLE companies ALTER COLUMN status SET DEFAULT 'pending'")
    op.execute("ALTER TABLE companies ALTER COLUMN analysis_status SET DEFAULT 'pending'")

    # Remove old enum types if they still exist
    op.execute("DROP TYPE IF EXISTS companystatus CASCADE")
    op.execute("DROP TYPE IF EXISTS analysisstatus CASCADE")


def downgrade() -> None:
    # Recreate enum types
    conn = op.get_bind()

    company_status_enum = sa.Enum(
        *NEW_COMPANY_STATUS_VALUES, name="companystatus"
    )
    analysis_status_enum = sa.Enum(
        *NEW_ANALYSIS_STATUS_VALUES, name="analysisstatus"
    )

    company_status_enum.create(conn, checkfirst=True)
    analysis_status_enum.create(conn, checkfirst=True)

    # Drop defaults before casting back
    op.execute("ALTER TABLE companies ALTER COLUMN status DROP DEFAULT")
    op.execute("ALTER TABLE companies ALTER COLUMN analysis_status DROP DEFAULT")

    # Cast string columns back to enum values, falling back to pending if unexpected value
    op.execute(
        """
        ALTER TABLE companies
        ALTER COLUMN status
        TYPE companystatus
        USING (
            CASE
                WHEN status IN ('pending', 'approved', 'suspicious', 'fraudulent') THEN status
                ELSE 'pending'
            END
        )::companystatus
        """
    )

    op.execute(
        """
        ALTER TABLE companies
        ALTER COLUMN analysis_status
        TYPE analysisstatus
        USING (
            CASE
                WHEN analysis_status IN ('pending', 'in_progress', 'complete') THEN analysis_status
                ELSE 'pending'
            END
        )::analysisstatus
        """
    )

    # Reinstate defaults
    op.execute(
        "ALTER TABLE companies ALTER COLUMN status SET DEFAULT 'pending'::companystatus"
    )
    op.execute(
        "ALTER TABLE companies ALTER COLUMN analysis_status SET DEFAULT 'pending'::analysisstatus"
    )

