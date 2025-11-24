"""
Deprecated migration placeholder.

This placeholder keeps the historical revision ID
`003_convert_status_columns_to_text` so existing databases that applied
the original migration remain compatible. The actual conversion logic
was removed in favor of preserving PostgreSQL enums.
"""
from alembic import op

# revision identifiers, used by Alembic.
revision = "003_convert_status_columns_to_text"
down_revision = "002_update_status_enums"
branch_labels = None
depends_on = None


def upgrade() -> None:
    """
    No-op placeholder. The original migration has been deprecated.
    """
    op.get_context()  # Access context to silence lint warnings.


def downgrade() -> None:
    """
    No-op placeholder. Downgrading is not supported.
    """
    op.get_context()

