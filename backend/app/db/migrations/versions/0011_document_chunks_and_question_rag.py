"""document_chunks + question RAG columns + question_embeddings_meta.

Phase 3 of the AI overhaul.

- `document_chunks`: lightweight metadata for each chunk; the actual
  vectors live in Qdrant. Source of truth for chunk text.
- `questions`: add quality_score, source_chunk_ids, prompt_version_id,
  auto_rejected.
- `question_embeddings_meta`: pure metadata; Qdrant holds the vector.

Revision ID: 0011
Revises: 0010
Create Date: 2026-05-24
"""

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision = "0011"
down_revision = "0010"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "document_chunks",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True, server_default=sa.text("gen_random_uuid()")),
        sa.Column("upload_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("uploads.id", ondelete="CASCADE"), nullable=False),
        sa.Column("subject_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("subjects.id", ondelete="SET NULL"), nullable=True),
        sa.Column("position", sa.Integer(), nullable=False),
        sa.Column("section_title", sa.Text(), nullable=True),
        sa.Column("text", sa.Text(), nullable=False),
        sa.Column("contextual_summary", sa.Text(), nullable=True),
        sa.Column("token_count", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("doc_type", sa.Text(), nullable=True),
        sa.Column("language", sa.Text(), nullable=True),
        sa.Column("embedding_model", sa.Text(), nullable=True),
        sa.Column("embedding_version", sa.Text(), nullable=True),
        sa.Column("meta", postgresql.JSONB(), nullable=False, server_default=sa.text("'{}'::jsonb")),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
    )
    op.create_index("ix_document_chunks_upload_id", "document_chunks", ["upload_id"])
    op.create_index("ix_document_chunks_subject_id", "document_chunks", ["subject_id"])
    op.create_index("ix_document_chunks_upload_position", "document_chunks", ["upload_id", "position"], unique=True)

    # ---- questions: RAG columns -------------------------------------------
    op.add_column(
        "questions",
        sa.Column("quality_score", sa.Numeric(3, 1), nullable=True),
    )
    op.add_column(
        "questions",
        sa.Column(
            "source_chunk_ids",
            postgresql.ARRAY(postgresql.UUID(as_uuid=True)),
            nullable=False,
            server_default=sa.text("'{}'::uuid[]"),
        ),
    )
    op.add_column(
        "questions",
        sa.Column("prompt_version_id", postgresql.UUID(as_uuid=True), nullable=True),
    )
    op.add_column(
        "questions",
        sa.Column("auto_rejected", sa.Boolean(), nullable=False, server_default="false"),
    )

    # ---- question_embeddings_meta -----------------------------------------
    op.create_table(
        "question_embeddings_meta",
        sa.Column("question_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("questions.id", ondelete="CASCADE"), primary_key=True),
        sa.Column("subject_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("subjects.id", ondelete="SET NULL"), nullable=True),
        sa.Column("embedding_model", sa.Text(), nullable=False),
        sa.Column("embedding_version", sa.Text(), nullable=False),
        sa.Column("indexed_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
    )


def downgrade() -> None:
    op.drop_table("question_embeddings_meta")
    op.drop_column("questions", "auto_rejected")
    op.drop_column("questions", "prompt_version_id")
    op.drop_column("questions", "source_chunk_ids")
    op.drop_column("questions", "quality_score")

    op.drop_index("ix_document_chunks_upload_position", table_name="document_chunks")
    op.drop_index("ix_document_chunks_subject_id", table_name="document_chunks")
    op.drop_index("ix_document_chunks_upload_id", table_name="document_chunks")
    op.drop_table("document_chunks")
