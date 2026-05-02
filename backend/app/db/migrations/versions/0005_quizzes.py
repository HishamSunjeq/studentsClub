"""quiz_sessions and quiz_attempts tables

Revision ID: 0005
Revises: 0004
Create Date: 2026-05-02
"""

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision = "0005"
down_revision = "0004"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.execute(
        "CREATE TYPE quiz_session_status AS ENUM ('in_progress', 'completed', 'abandoned')"
    )

    op.create_table(
        "quiz_sessions",
        sa.Column(
            "id",
            sa.UUID(),
            nullable=False,
            server_default=sa.text("gen_random_uuid()"),
        ),
        sa.Column("user_id", sa.UUID(), nullable=False),
        sa.Column("subject_id", sa.UUID(), nullable=False),
        sa.Column(
            "status",
            postgresql.ENUM(
                "in_progress", "completed", "abandoned",
                name="quiz_session_status",
                create_type=False,
            ),
            nullable=False,
            server_default="in_progress",
        ),
        sa.Column("total_questions", sa.Integer(), nullable=False),
        sa.Column("score", sa.Integer(), nullable=False, server_default="0"),
        sa.Column(
            "completed_at",
            sa.DateTime(timezone=True),
            nullable=True,
        ),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.text("now()"),
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.text("now()"),
        ),
        sa.PrimaryKeyConstraint("id"),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["subject_id"], ["subjects.id"], ondelete="CASCADE"),
    )
    op.create_index("ix_quiz_sessions_user_id", "quiz_sessions", ["user_id"])
    op.create_index("ix_quiz_sessions_subject_id", "quiz_sessions", ["subject_id"])
    op.create_index("ix_quiz_sessions_status", "quiz_sessions", ["status"])
    op.execute("""
        CREATE TRIGGER set_quiz_sessions_updated_at
        BEFORE UPDATE ON quiz_sessions
        FOR EACH ROW EXECUTE FUNCTION set_updated_at()
    """)

    op.create_table(
        "quiz_attempts",
        sa.Column(
            "id",
            sa.UUID(),
            nullable=False,
            server_default=sa.text("gen_random_uuid()"),
        ),
        sa.Column("session_id", sa.UUID(), nullable=False),
        sa.Column("question_id", sa.UUID(), nullable=False),
        sa.Column("selected_choice_id", sa.UUID(), nullable=False),
        sa.Column("is_correct", sa.Boolean(), nullable=False),
        sa.Column(
            "answered_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.text("now()"),
        ),
        sa.PrimaryKeyConstraint("id"),
        sa.ForeignKeyConstraint(["session_id"], ["quiz_sessions.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["question_id"], ["questions.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["selected_choice_id"], ["question_choices.id"], ondelete="CASCADE"),
    )
    op.create_index("ix_quiz_attempts_session_id", "quiz_attempts", ["session_id"])
    op.create_index("ix_quiz_attempts_question_id", "quiz_attempts", ["question_id"])


def downgrade() -> None:
    op.execute("DROP TRIGGER IF EXISTS set_quiz_sessions_updated_at ON quiz_sessions")
    op.drop_table("quiz_attempts")
    op.drop_table("quiz_sessions")
    op.execute("DROP TYPE quiz_session_status")
