"""
Update company and analysis status enums to align with simplified status model.
"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision = "002_update_status_enums"
down_revision = "001_initial_schema"
branch_labels = None
depends_on = None


NEW_COMPANY_STATUS_VALUES = ("pending", "approved", "suspicious", "fraudulent")
NEW_ANALYSIS_STATUS_VALUES = ("pending", "in_progress", "complete")

OLD_COMPANY_STATUS_VALUES = ("pending", "approved", "rejected", "fraudulent", "revoked")
OLD_ANALYSIS_STATUS_VALUES = ("pending", "in_progress", "completed", "failed", "incomplete")


def upgrade() -> None:
    conn = op.get_bind()

    # Normalize existing data before swapping enum definitions
    conn.execute(
        sa.text(
            """
            UPDATE companies
            SET status = 'suspicious'
            WHERE status IN ('rejected', 'revoked')
            """
        )
    )

    # Companies with failed or incomplete analyses should become suspicious
    conn.execute(
        sa.text(
            """
            UPDATE companies
            SET status = 'suspicious'
            WHERE analysis_status IN ('failed', 'incomplete')
              AND status != 'fraudulent'
            """
        )
    )

    # Apply risk-based status adjustments for completed analyses
    conn.execute(
        sa.text(
            """
            UPDATE companies
            SET status = 'fraudulent'
            WHERE risk_score >= 70
              AND analysis_status IN ('completed', 'failed', 'incomplete')
            """
        )
    )

    conn.execute(
        sa.text(
            """
            UPDATE companies
            SET status = 'suspicious'
            WHERE risk_score BETWEEN 31 AND 69
              AND analysis_status IN ('completed', 'failed', 'incomplete')
              AND status != 'fraudulent'
            """
        )
    )

    conn.execute(
        sa.text(
            """
            UPDATE companies
            SET status = 'approved'
            WHERE risk_score <= 30
              AND analysis_status = 'completed'
              AND status = 'pending'
            """
        )
    )

    # Create new enum types with the desired values
    company_status_new = postgresql.ENUM(
        *NEW_COMPANY_STATUS_VALUES, name="companystatus_new"
    )
    analysis_status_new = postgresql.ENUM(
        *NEW_ANALYSIS_STATUS_VALUES, name="analysisstatus_new"
    )
    company_status_new.create(conn)
    analysis_status_new.create(conn)

    # Swap the status column to the new enum using explicit casting
    op.execute(
        """
        ALTER TABLE companies
        ALTER COLUMN status
        TYPE companystatus_new
        USING (
            CASE status
                WHEN 'pending' THEN 'pending'
                WHEN 'approved' THEN 'approved'
                WHEN 'fraudulent' THEN 'fraudulent'
                ELSE 'suspicious'
            END
        )::companystatus_new
        """
    )

    # Swap the analysis_status column to the new enum
    op.execute(
        """
        ALTER TABLE companies
        ALTER COLUMN analysis_status
        TYPE analysisstatus_new
        USING (
            CASE analysis_status
                WHEN 'pending' THEN 'pending'
                WHEN 'in_progress' THEN 'in_progress'
                ELSE 'complete'
            END
        )::analysisstatus_new
        """
    )

    # Update defaults
    op.execute(
        "ALTER TABLE companies ALTER COLUMN status SET DEFAULT 'pending'::companystatus_new"
    )
    op.execute(
        "ALTER TABLE companies ALTER COLUMN analysis_status SET DEFAULT 'pending'::analysisstatus_new"
    )

    # Drop old enums and rename new ones
    op.execute("DROP TYPE companystatus")
    op.execute("ALTER TYPE companystatus_new RENAME TO companystatus")

    op.execute("DROP TYPE analysisstatus")
    op.execute("ALTER TYPE analysisstatus_new RENAME TO analysisstatus")


def downgrade() -> None:
    conn = op.get_bind()

    # Recreate old enum types
    company_status_old = postgresql.ENUM(
        *OLD_COMPANY_STATUS_VALUES, name="companystatus_old"
    )
    analysis_status_old = postgresql.ENUM(
        *OLD_ANALYSIS_STATUS_VALUES, name="analysisstatus_old"
    )
    company_status_old.create(conn)
    analysis_status_old.create(conn)

    # Revert company status values
    op.execute(
        """
        ALTER TABLE companies
        ALTER COLUMN status
        TYPE companystatus_old
        USING (
            CASE status
                WHEN 'pending' THEN 'pending'
                WHEN 'approved' THEN 'approved'
                WHEN 'fraudulent' THEN 'fraudulent'
                WHEN 'suspicious' THEN 'rejected'
                ELSE 'pending'
            END
        )::companystatus_old
        """
    )

    # Revert analysis status values
    op.execute(
        """
        ALTER TABLE companies
        ALTER COLUMN analysis_status
        TYPE analysisstatus_old
        USING (
            CASE analysis_status
                WHEN 'pending' THEN 'pending'
                WHEN 'in_progress' THEN 'in_progress'
                WHEN 'complete' THEN 'completed'
                ELSE 'pending'
            END
        )::analysisstatus_old
        """
    )

    # Restore defaults
    op.execute(
        "ALTER TABLE companies ALTER COLUMN status SET DEFAULT 'pending'::companystatus_old"
    )
    op.execute(
        "ALTER TABLE companies ALTER COLUMN analysis_status SET DEFAULT 'pending'::analysisstatus_old"
    )

    # Drop new enums and rename old ones back
    op.execute("DROP TYPE companystatus")
    op.execute("ALTER TYPE companystatus_old RENAME TO companystatus")

    op.execute("DROP TYPE analysisstatus")
    op.execute("ALTER TYPE analysisstatus_old RENAME TO analysisstatus")

