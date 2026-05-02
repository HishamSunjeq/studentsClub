"""quiz_session_questions table — persists the picked questions per session

Revision ID: 0006
Revises: 0005
Create Date: 2026-05-02
"""

import sqlalchemy as sa
from alembic import op

revision = "0006"
down_revision = "0005"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "quiz_session_questions",
        sa.Column(
            "id",
            sa.UUID(),
            nullable=False,
            server_default=sa.text("gen_random_uuid()"),
        ),
        sa.Column("session_id", sa.UUID(), nullable=False),
        sa.Column("question_id", sa.UUID(), nullable=False),
        sa.Column("position", sa.SmallInteger(), nullable=False),
        sa.PrimaryKeyConstraint("id"),
        sa.ForeignKeyConstraint(["session_id"], ["quiz_sessions.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["question_id"], ["questions.id"], ondelete="CASCADE"),
        sa.UniqueConstraint("session_id", "position", name="uq_qsq_session_position"),
        sa.UniqueConstraint("session_id", "question_id", name="uq_qsq_session_question"),
    )
    op.create_index(
        "ix_quiz_session_questions_session_id", "quiz_session_questions", ["session_id"]
    )


def downgrade() -> None:
    op.drop_table("quiz_session_questions")
