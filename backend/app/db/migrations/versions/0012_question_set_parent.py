"""Phase 6 replay: parent_question_set_id on question_sets.

Revision ID: 0012
Revises: 0011
"""

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import UUID

revision = "0012"
down_revision = "0011"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "question_sets",
        sa.Column("parent_question_set_id", UUID(as_uuid=True), nullable=True),
    )
    op.create_foreign_key(
        "fk_question_sets_parent",
        "question_sets",
        "question_sets",
        ["parent_question_set_id"],
        ["id"],
        ondelete="SET NULL",
    )
    op.create_index(
        "ix_question_sets_parent_id",
        "question_sets",
        ["parent_question_set_id"],
    )


def downgrade() -> None:
    op.drop_index("ix_question_sets_parent_id", table_name="question_sets")
    op.drop_constraint("fk_question_sets_parent", "question_sets", type_="foreignkey")
    op.drop_column("question_sets", "parent_question_set_id")
