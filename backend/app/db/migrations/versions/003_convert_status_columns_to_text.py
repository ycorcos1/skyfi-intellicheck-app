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
    # Convert status column if still using enum
    op.execute(
        """
        DO $$
        BEGIN
            IF EXISTS (
                SELECT 1
                FROM information_schema.columns
                WHERE table_name = 'companies'
                  AND column_name = 'status'
                  AND data_type = 'USER-DEFINED'
                  AND udt_name = 'companystatus'
            ) THEN
                ALTER TABLE companies ALTER COLUMN status DROP DEFAULT;
                ALTER TABLE companies ALTER COLUMN status TYPE TEXT USING status::text;
                ALTER TABLE companies ALTER COLUMN status SET DEFAULT 'pending';
            END IF;
        END;
        $$;
        """
    )

    # Convert analysis_status column if still using enum
    op.execute(
        """
        DO $$
        BEGIN
            IF EXISTS (
                SELECT 1
                FROM information_schema.columns
                WHERE table_name = 'companies'
                  AND column_name = 'analysis_status'
                  AND data_type = 'USER-DEFINED'
                  AND udt_name = 'analysisstatus'
            ) THEN
                ALTER TABLE companies ALTER COLUMN analysis_status DROP DEFAULT;
                ALTER TABLE companies ALTER COLUMN analysis_status TYPE TEXT USING analysis_status::text;
                ALTER TABLE companies ALTER COLUMN analysis_status SET DEFAULT 'pending';
            END IF;
        END;
        $$;
        """
    )

    # Remove enum types if they still exist
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

    # Only convert back to enums if columns are text
    op.execute(
        """
        DO $$
        BEGIN
            IF EXISTS (
                SELECT 1
                FROM information_schema.columns
                WHERE table_name = 'companies'
                  AND column_name = 'status'
                  AND data_type = 'text'
            ) THEN
                ALTER TABLE companies ALTER COLUMN status DROP DEFAULT;
                ALTER TABLE companies
                ALTER COLUMN status
                TYPE companystatus
                USING (
                    CASE
                        WHEN status IN ('pending', 'approved', 'suspicious', 'fraudulent') THEN status
                        ELSE 'pending'
                    END
                )::companystatus;
                ALTER TABLE companies ALTER COLUMN status SET DEFAULT 'pending'::companystatus;
            END IF;
        END;
        $$;
        """
    )

    op.execute(
        """
        DO $$
        BEGIN
            IF EXISTS (
                SELECT 1
                FROM information_schema.columns
                WHERE table_name = 'companies'
                  AND column_name = 'analysis_status'
                  AND data_type = 'text'
            ) THEN
                ALTER TABLE companies ALTER COLUMN analysis_status DROP DEFAULT;
                ALTER TABLE companies
                ALTER COLUMN analysis_status
                TYPE analysisstatus
                USING (
                    CASE
                        WHEN analysis_status IN ('pending', 'in_progress', 'complete') THEN analysis_status
                        ELSE 'pending'
                    END
                )::analysisstatus;
                ALTER TABLE companies ALTER COLUMN analysis_status SET DEFAULT 'pending'::analysisstatus;
            END IF;
        END;
        $$;
        """
    )

