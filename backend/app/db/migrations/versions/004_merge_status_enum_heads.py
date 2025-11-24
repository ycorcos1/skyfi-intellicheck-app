"""
Merge heads for status enum migrations.
"""
from alembic import op

# revision identifiers, used by Alembic.
revision = "004_merge_status_enum_heads"
down_revision = ("003_add_status_enum_values", "003_status_enum_placeholder")
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.get_context()


def downgrade() -> None:
    op.get_context()

