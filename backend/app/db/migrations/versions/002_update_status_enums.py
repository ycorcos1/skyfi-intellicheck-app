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

    # Check if migration already fully applied by checking if new enum values exist
    check_suspicious_exists = conn.execute(
        sa.text("""
            SELECT EXISTS (
                SELECT 1 FROM pg_enum e
                JOIN pg_type t ON e.enumtypid = t.oid
                WHERE t.typname = 'companystatus' AND e.enumlabel = 'suspicious'
            )
        """)
    ).scalar()
    
    check_complete_exists = conn.execute(
        sa.text("""
            SELECT EXISTS (
                SELECT 1 FROM pg_enum e
                JOIN pg_type t ON e.enumtypid = t.oid
                WHERE t.typname = 'analysisstatus' AND e.enumlabel = 'complete'
            )
        """)
    ).scalar()
    
    # If migration already fully applied, skip
    if check_suspicious_exists and check_complete_exists:
        # Migration already applied, just ensure new enum types are cleaned up if they exist
        check_new_company_enum = conn.execute(
            sa.text("SELECT EXISTS (SELECT 1 FROM pg_type WHERE typname = 'companystatus_new')")
        ).scalar()
        if check_new_company_enum:
            try:
                op.execute("DROP TYPE IF EXISTS companystatus_new")
            except Exception:
                pass
            try:
                op.execute("DROP TYPE IF EXISTS analysisstatus_new")
            except Exception:
                pass
        return
    
    # Create new enum types (if they already exist, checkfirst prevents errors)
    company_status_new = postgresql.ENUM(
        *NEW_COMPANY_STATUS_VALUES, name="companystatus_new"
    )
    company_status_new.create(conn, checkfirst=True)

    analysis_status_new = postgresql.ENUM(
        *NEW_ANALYSIS_STATUS_VALUES, name="analysisstatus_new"
    )
    analysis_status_new.create(conn, checkfirst=True)

    # Alter columns to use the new enum types while mapping old values
    op.execute(
        """
        ALTER TABLE companies
        ALTER COLUMN status
        TYPE companystatus_new
        USING (
            CASE status::text
                WHEN 'approved' THEN 'approved'
                WHEN 'fraudulent' THEN 'fraudulent'
                WHEN 'rejected' THEN 'suspicious'
                WHEN 'revoked' THEN 'suspicious'
                ELSE 'pending'
            END
        )::companystatus_new
        """
    )

    op.execute(
        """
        ALTER TABLE companies
        ALTER COLUMN analysis_status
        TYPE analysisstatus_new
        USING (
            CASE analysis_status::text
                WHEN 'pending' THEN 'pending'
                WHEN 'in_progress' THEN 'in_progress'
                ELSE 'complete'
            END
        )::analysisstatus_new
        """
    )

    # Update defaults for new enums (will be adjusted after rename automatically)
    op.execute(
        "ALTER TABLE companies ALTER COLUMN status SET DEFAULT 'pending'::companystatus_new"
    )
    op.execute(
        "ALTER TABLE companies ALTER COLUMN analysis_status SET DEFAULT 'pending'::analysisstatus_new"
    )

    # Remove old enums and rename new ones to maintain schema compatibility
    op.execute("DROP TYPE IF EXISTS companystatus")
    op.execute("ALTER TYPE companystatus_new RENAME TO companystatus")

    op.execute("DROP TYPE IF EXISTS analysisstatus")
    op.execute("ALTER TYPE analysisstatus_new RENAME TO analysisstatus")

    # Reset defaults to point at the renamed enums
    op.execute("ALTER TABLE companies ALTER COLUMN status SET DEFAULT 'pending'::companystatus")
    op.execute("ALTER TABLE companies ALTER COLUMN analysis_status SET DEFAULT 'pending'::analysisstatus")

    # Now that columns accept new values, normalize statuses with business rules
    conn.execute(
        sa.text(
            """
            UPDATE companies
            SET status = 'fraudulent'
            WHERE risk_score >= 70
            """
        )
    )

    conn.execute(
        sa.text(
            """
            UPDATE companies
            SET status = 'approved'
            WHERE status = 'pending'
              AND analysis_status = 'complete'
              AND risk_score <= 30
            """
        )
    )

    conn.execute(
        sa.text(
            """
            UPDATE companies
            SET status = 'suspicious'
            WHERE risk_score BETWEEN 31 AND 69
              AND status != 'fraudulent'
            """
        )
    )

    conn.execute(
        sa.text(
            """
            UPDATE companies
            SET status = 'suspicious'
            WHERE analysis_status != 'complete'
              AND status != 'fraudulent'
            """
        )
    )


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

