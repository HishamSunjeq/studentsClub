"""question_sets, questions, question_choices tables

Revision ID: 0004
Revises: 0003
Create Date: 2026-05-01
"""

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision = "0004"
down_revision = "0003"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.execute(
        "CREATE TYPE question_set_status AS ENUM ('draft', 'published', 'rejected')"
    )
    op.execute(
        "CREATE TYPE question_difficulty AS ENUM ('easy', 'medium', 'hard')"
    )

    op.create_table(
        "question_sets",
        sa.Column(
            "id",
            sa.UUID(),
            nullable=False,
            server_default=sa.text("gen_random_uuid()"),
        ),
        sa.Column("upload_id", sa.UUID(), nullable=False),
        sa.Column("subject_id", sa.UUID(), nullable=True),
        sa.Column("created_by", sa.UUID(), nullable=False),
        sa.Column("title", sa.Text(), nullable=False),
        sa.Column(
            "status",
            postgresql.ENUM(
                "draft", "published", "rejected",
                name="question_set_status",
                create_type=False,
            ),
            nullable=False,
            server_default="draft",
        ),
        sa.Column("ai_model", sa.Text(), nullable=False),
        sa.Column("tokens_used", sa.Integer(), nullable=False, server_default="0"),
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
        sa.ForeignKeyConstraint(["upload_id"], ["uploads.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["subject_id"], ["subjects.id"], ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["created_by"], ["users.id"], ondelete="CASCADE"),
    )
    op.create_index("ix_question_sets_upload_id", "question_sets", ["upload_id"])
    op.create_index("ix_question_sets_subject_id", "question_sets", ["subject_id"])
    op.create_index("ix_question_sets_status", "question_sets", ["status"])
    op.execute("""
        CREATE TRIGGER set_question_sets_updated_at
        BEFORE UPDATE ON question_sets
        FOR EACH ROW EXECUTE FUNCTION set_updated_at()
    """)

    op.create_table(
        "questions",
        sa.Column(
            "id",
            sa.UUID(),
            nullable=False,
            server_default=sa.text("gen_random_uuid()"),
        ),
        sa.Column("question_set_id", sa.UUID(), nullable=False),
        sa.Column("text", sa.Text(), nullable=False),
        sa.Column("explanation", sa.Text(), nullable=True),
        sa.Column(
            "difficulty",
            postgresql.ENUM(
                "easy", "medium", "hard",
                name="question_difficulty",
                create_type=False,
            ),
            nullable=False,
            server_default="medium",
        ),
        sa.Column("source_excerpt", sa.Text(), nullable=True),
        sa.Column(
            "is_active",
            sa.Boolean(),
            nullable=False,
            server_default="true",
        ),
        sa.Column("position", sa.SmallInteger(), nullable=False),
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
        sa.ForeignKeyConstraint(
            ["question_set_id"], ["question_sets.id"], ondelete="CASCADE"
        ),
    )
    op.create_index("ix_questions_question_set_id", "questions", ["question_set_id"])
    op.execute("""
        CREATE TRIGGER set_questions_updated_at
        BEFORE UPDATE ON questions
        FOR EACH ROW EXECUTE FUNCTION set_updated_at()
    """)

    op.create_table(
        "question_choices",
        sa.Column(
            "id",
            sa.UUID(),
            nullable=False,
            server_default=sa.text("gen_random_uuid()"),
        ),
        sa.Column("question_id", sa.UUID(), nullable=False),
        sa.Column("text", sa.Text(), nullable=False),
        sa.Column("is_correct", sa.Boolean(), nullable=False),
        sa.Column("position", sa.SmallInteger(), nullable=False),
        sa.PrimaryKeyConstraint("id"),
        sa.ForeignKeyConstraint(
            ["question_id"], ["questions.id"], ondelete="CASCADE"
        ),
    )
    op.create_index(
        "ix_question_choices_question_id", "question_choices", ["question_id"]
    )


def downgrade() -> None:
    op.drop_table("question_choices")
    op.drop_table("questions")
    op.drop_table("question_sets")
    op.execute("DROP TYPE question_set_status")
    op.execute("DROP TYPE question_difficulty")
