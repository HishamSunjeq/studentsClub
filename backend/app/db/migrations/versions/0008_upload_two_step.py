"""upload two-step flow: rename finalized→uploaded, add extracting/ready states,
extracted_text on uploads; add generating/generation_failed states + generation_settings on question_sets

Revision ID: 0008
Revises: 0007
Create Date: 2026-05-08
"""

import sqlalchemy as sa
from alembic import op

revision = "0008"
down_revision = "0007"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # ---------- upload_status: pending|finalized|failed → pending|uploaded|extracting|ready|failed ----------
    # Postgres ENUMs can't easily ADD VALUE inside a transaction, and we need to rename
    # an existing value too — so we cast to TEXT, drop+recreate the type, backfill, and cast back.
    op.execute("ALTER TABLE uploads ALTER COLUMN status DROP DEFAULT")
    op.execute("ALTER TABLE uploads ALTER COLUMN status TYPE TEXT USING status::TEXT")
    op.execute("UPDATE uploads SET status = 'uploaded' WHERE status = 'finalized'")
    op.execute("DROP TYPE upload_status")
    op.execute(
        "CREATE TYPE upload_status AS ENUM ('pending','uploaded','extracting','ready','failed')"
    )
    op.execute(
        "ALTER TABLE uploads ALTER COLUMN status TYPE upload_status USING status::upload_status"
    )
    op.execute("ALTER TABLE uploads ALTER COLUMN status SET DEFAULT 'pending'")

    # Existing rows that had the old `finalized` status had already been through the full
    # legacy pipeline (extraction + AI). Promote them to `ready` so the new management UI
    # treats them as fully processed (extracted_text remains NULL — re-extract is a Phase C
    # feature; the new UI will gracefully degrade for these rows).
    op.execute("UPDATE uploads SET status = 'ready' WHERE status = 'uploaded'")

    # ---------- new columns on uploads ----------
    op.add_column("uploads", sa.Column("extracted_text", sa.Text(), nullable=True))
    op.add_column(
        "uploads",
        sa.Column("extracted_at", sa.DateTime(timezone=True), nullable=True),
    )
    op.add_column("uploads", sa.Column("extraction_error", sa.Text(), nullable=True))

    # ---------- question_set_status: add generating + generation_failed ----------
    op.execute("ALTER TABLE question_sets ALTER COLUMN status DROP DEFAULT")
    op.execute(
        "ALTER TABLE question_sets ALTER COLUMN status TYPE TEXT USING status::TEXT"
    )
    op.execute("DROP TYPE question_set_status")
    op.execute(
        "CREATE TYPE question_set_status AS ENUM "
        "('generating','generation_failed','draft','published','rejected')"
    )
    op.execute(
        "ALTER TABLE question_sets ALTER COLUMN status TYPE question_set_status "
        "USING status::question_set_status"
    )
    op.execute("ALTER TABLE question_sets ALTER COLUMN status SET DEFAULT 'draft'")

    # ---------- new columns on question_sets ----------
    op.add_column(
        "question_sets",
        sa.Column(
            "generation_settings",
            sa.dialects.postgresql.JSONB(),
            nullable=False,
            server_default=sa.text("'{}'::jsonb"),
        ),
    )
    op.add_column(
        "question_sets", sa.Column("generation_error", sa.Text(), nullable=True)
    )


def downgrade() -> None:
    op.drop_column("question_sets", "generation_error")
    op.drop_column("question_sets", "generation_settings")
    op.execute("ALTER TABLE question_sets ALTER COLUMN status DROP DEFAULT")
    op.execute(
        "ALTER TABLE question_sets ALTER COLUMN status TYPE TEXT USING status::TEXT"
    )
    op.execute(
        "UPDATE question_sets SET status = 'draft' WHERE status IN ('generating','generation_failed')"
    )
    op.execute("DROP TYPE question_set_status")
    op.execute(
        "CREATE TYPE question_set_status AS ENUM ('draft','published','rejected')"
    )
    op.execute(
        "ALTER TABLE question_sets ALTER COLUMN status TYPE question_set_status "
        "USING status::question_set_status"
    )
    op.execute("ALTER TABLE question_sets ALTER COLUMN status SET DEFAULT 'draft'")

    op.drop_column("uploads", "extraction_error")
    op.drop_column("uploads", "extracted_at")
    op.drop_column("uploads", "extracted_text")

    op.execute("ALTER TABLE uploads ALTER COLUMN status DROP DEFAULT")
    op.execute("ALTER TABLE uploads ALTER COLUMN status TYPE TEXT USING status::TEXT")
    op.execute(
        "UPDATE uploads SET status = 'finalized' "
        "WHERE status IN ('uploaded','extracting','ready')"
    )
    op.execute("DROP TYPE upload_status")
    op.execute("CREATE TYPE upload_status AS ENUM ('pending','finalized','failed')")
    op.execute(
        "ALTER TABLE uploads ALTER COLUMN status TYPE upload_status "
        "USING status::upload_status"
    )
    op.execute("ALTER TABLE uploads ALTER COLUMN status SET DEFAULT 'pending'")
