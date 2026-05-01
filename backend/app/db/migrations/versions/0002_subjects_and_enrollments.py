"""subjects and enrollments

Revision ID: 0002
Revises: 0001
Create Date: 2026-05-01

"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "0002"
down_revision: str | None = "0001"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    # subjects
    op.create_table(
        "subjects",
        sa.Column("id", sa.UUID(), nullable=False, server_default=sa.text("gen_random_uuid()")),
        sa.Column("name", sa.Text(), nullable=False),
        sa.Column("code", sa.Text(), nullable=False),
        sa.Column("college", sa.Text(), nullable=False),
        sa.Column("academic_year", sa.SmallInteger(), nullable=False),
        sa.Column("description", sa.Text(), nullable=True),
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
        sa.UniqueConstraint("college", "code", "academic_year"),
    )
    op.create_index("ix_subjects_college_year", "subjects", ["college", "academic_year"])

    op.execute("""
        CREATE TRIGGER subjects_set_updated_at
        BEFORE UPDATE ON subjects
        FOR EACH ROW EXECUTE FUNCTION set_updated_at()
    """)

    # enrollments
    op.create_table(
        "enrollments",
        sa.Column("id", sa.UUID(), nullable=False, server_default=sa.text("gen_random_uuid()")),
        sa.Column("user_id", sa.UUID(), nullable=False),
        sa.Column("subject_id", sa.UUID(), nullable=False),
        sa.Column(
            "enrolled_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.text("now()"),
        ),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["subject_id"], ["subjects.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("user_id", "subject_id"),
    )
    op.create_index("ix_enrollments_user_id", "enrollments", ["user_id"])
    op.create_index("ix_enrollments_subject_id", "enrollments", ["subject_id"])


def downgrade() -> None:
    op.drop_table("enrollments")
    op.execute("DROP TRIGGER IF EXISTS subjects_set_updated_at ON subjects")
    op.drop_index("ix_subjects_college_year", table_name="subjects")
    op.drop_table("subjects")
