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
    
    # Check current state for partial application
    check_new_company_enum = conn.execute(
        sa.text("SELECT EXISTS (SELECT 1 FROM pg_type WHERE typname = 'companystatus_new')")
    ).scalar()
    
    check_old_company_enum = conn.execute(
        sa.text("SELECT EXISTS (SELECT 1 FROM pg_type WHERE typname = 'companystatus')")
    ).scalar()
    
    # If partially applied (new enum exists but swap not complete), complete the swap
    if check_new_company_enum and check_old_company_enum:
        # Complete the migration by finishing the swap
        try:
            op.execute("DROP TYPE IF EXISTS companystatus")
        except Exception:
            pass
        try:
            op.execute("ALTER TYPE companystatus_new RENAME TO companystatus")
        except Exception:
            pass
        try:
            op.execute("DROP TYPE IF EXISTS analysisstatus")
        except Exception:
            pass
        try:
            op.execute("ALTER TYPE analysisstatus_new RENAME TO analysisstatus")
        except Exception:
            pass
        return

    # Normalize existing data before swapping enum definitions
    # Only update if old enum values still exist
    if check_old_company_enum:
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

    # Create new enum types with the desired values (only if they don't exist)
    if not check_new_company_enum:
        company_status_new = postgresql.ENUM(
            *NEW_COMPANY_STATUS_VALUES, name="companystatus_new"
        )
        company_status_new.create(conn)
    
    analysis_status_new_exists = conn.execute(
        sa.text("SELECT EXISTS (SELECT 1 FROM pg_type WHERE typname = 'analysisstatus_new')")
    ).scalar()
    
    if not analysis_status_new_exists:
        analysis_status_new = postgresql.ENUM(
            *NEW_ANALYSIS_STATUS_VALUES, name="analysisstatus_new"
        )
        analysis_status_new.create(conn)

    # Swap the status column to the new enum using explicit casting
    # Only if old enum still exists
    if check_old_company_enum:
        op.execute(
            """
            ALTER TABLE companies
            ALTER COLUMN status
            TYPE companystatus_new
            USING (
                CASE status::text
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
                CASE analysis_status::text
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
        op.execute("DROP TYPE IF EXISTS companystatus")
        op.execute("ALTER TYPE companystatus_new RENAME TO companystatus")

        op.execute("DROP TYPE IF EXISTS analysisstatus")
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

