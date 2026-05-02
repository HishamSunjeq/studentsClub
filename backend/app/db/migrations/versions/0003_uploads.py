"""uploads table

Revision ID: 0003
Revises: 0002
Create Date: 2026-05-01
"""

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision = "0003"
down_revision = "0002"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.execute("CREATE TYPE upload_status AS ENUM ('pending', 'finalized', 'failed')")

    op.create_table(
        "uploads",
        sa.Column(
            "id",
            sa.UUID(),
            nullable=False,
            server_default=sa.text("gen_random_uuid()"),
        ),
        sa.Column("user_id", sa.UUID(), nullable=False),
        sa.Column("subject_id", sa.UUID(), nullable=True),
        sa.Column("original_filename", sa.Text(), nullable=False),
        sa.Column("content_type", sa.String(120), nullable=False),
        sa.Column("size_bytes", sa.Integer(), nullable=False),
        sa.Column("s3_key", sa.Text(), nullable=False),
        sa.Column(
            "status",
            postgresql.ENUM("pending", "finalized", "failed", name="upload_status", create_type=False),
            nullable=False,
            server_default="pending",
        ),
        sa.Column("finalized_at", sa.DateTime(timezone=True), nullable=True),
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
        sa.ForeignKeyConstraint(["subject_id"], ["subjects.id"], ondelete="SET NULL"),
        sa.UniqueConstraint("s3_key", name="uq_uploads_s3_key"),
    )
    op.create_index("ix_uploads_user_id", "uploads", ["user_id"])
    op.create_index("ix_uploads_subject_id", "uploads", ["subject_id"])
    op.create_index("ix_uploads_status", "uploads", ["status"])

    op.execute("""
        CREATE TRIGGER set_uploads_updated_at
        BEFORE UPDATE ON uploads
        FOR EACH ROW EXECUTE FUNCTION set_updated_at()
    """)


def downgrade() -> None:
    op.drop_table("uploads")
    op.execute("DROP TYPE upload_status")
