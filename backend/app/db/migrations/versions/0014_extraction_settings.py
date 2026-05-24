"""Phase 9 extraction config: extraction_settings (single-row, seeded).

Revision ID: 0014
Revises: 0013
"""

import uuid

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import ARRAY, UUID

revision = "0014"
down_revision = "0013"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "extraction_settings",
        sa.Column("id", UUID(as_uuid=True), primary_key=True),
        sa.Column("backend", sa.Text(), nullable=False, server_default="unstructured"),
        sa.Column("strategy", sa.Text(), nullable=False, server_default="auto"),
        sa.Column(
            "ocr_languages",
            ARRAY(sa.Text()),
            nullable=False,
            server_default="{eng,ara}",
        ),
        sa.Column("extract_tables", sa.Boolean(), nullable=False, server_default="true"),
        sa.Column("hi_res_model_name", sa.Text(), nullable=True),
        sa.Column("max_characters", sa.Integer(), nullable=True),
        sa.Column(
            "updated_by",
            UUID(as_uuid=True),
            sa.ForeignKey("users.id", ondelete="SET NULL"),
            nullable=True,
        ),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
    )

    # Seed the single config row.
    op.execute(
        sa.text(
            "INSERT INTO extraction_settings (id, backend, strategy, ocr_languages, extract_tables) "
            "VALUES (:id, 'unstructured', 'auto', '{eng,ara}', true)"
        ).bindparams(id=uuid.uuid4())
    )


def downgrade() -> None:
    op.drop_table("extraction_settings")
