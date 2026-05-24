"""Phase 9: record which backend/strategy produced an upload's text.

Revision ID: 0015
Revises: 0014
"""

from alembic import op
import sqlalchemy as sa

revision = "0015"
down_revision = "0014"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column("uploads", sa.Column("extraction_backend", sa.Text(), nullable=True))
    op.add_column("uploads", sa.Column("extraction_strategy", sa.Text(), nullable=True))


def downgrade() -> None:
    op.drop_column("uploads", "extraction_strategy")
    op.drop_column("uploads", "extraction_backend")
