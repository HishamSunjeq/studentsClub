"""ai_runs telemetry table

Records every LLM provider call for cost rollups, replay, debugging,
and budget enforcement. Created as part of the Phase 1 AI overhaul.

Revision ID: 0009
Revises: 0008
Create Date: 2026-05-24
"""

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision = "0009"
down_revision = "0008"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.execute(
        "CREATE TYPE ai_run_status AS ENUM ('ok','error','timeout','rate_limited')"
    )

    op.create_table(
        "ai_runs",
        sa.Column(
            "id",
            postgresql.UUID(as_uuid=True),
            primary_key=True,
            server_default=sa.text("gen_random_uuid()"),
        ),
        sa.Column(
            "parent_run_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("ai_runs.id", ondelete="SET NULL"),
            nullable=True,
        ),
        sa.Column(
            "question_set_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("question_sets.id", ondelete="SET NULL"),
            nullable=True,
        ),
        sa.Column(
            "user_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("users.id", ondelete="SET NULL"),
            nullable=True,
        ),
        sa.Column("task_name", sa.Text(), nullable=False),
        sa.Column("provider", sa.Text(), nullable=False),
        sa.Column("model", sa.Text(), nullable=False),
        sa.Column("credential_alias", sa.Text(), nullable=True),
        sa.Column("prompt_version_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("input_tokens", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("output_tokens", sa.Integer(), nullable=False, server_default="0"),
        sa.Column(
            "cost_usd",
            sa.Numeric(10, 6),
            nullable=False,
            server_default="0",
        ),
        sa.Column("latency_ms", sa.Integer(), nullable=True),
        sa.Column(
            "cache_hit",
            sa.Boolean(),
            nullable=False,
            server_default="false",
        ),
        sa.Column(
            "status",
            postgresql.ENUM(
                "ok",
                "error",
                "timeout",
                "rate_limited",
                name="ai_run_status",
                create_type=False,
            ),
            nullable=False,
            server_default="ok",
        ),
        sa.Column("error", sa.Text(), nullable=True),
        sa.Column(
            "meta",
            postgresql.JSONB(),
            nullable=False,
            server_default=sa.text("'{}'::jsonb"),
        ),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.text("now()"),
        ),
    )

    op.create_index("ix_ai_runs_question_set_id", "ai_runs", ["question_set_id"])
    op.create_index("ix_ai_runs_user_id", "ai_runs", ["user_id"])
    op.create_index("ix_ai_runs_created_at", "ai_runs", ["created_at"])
    op.create_index("ix_ai_runs_provider_model", "ai_runs", ["provider", "model"])


def downgrade() -> None:
    op.drop_index("ix_ai_runs_provider_model", table_name="ai_runs")
    op.drop_index("ix_ai_runs_created_at", table_name="ai_runs")
    op.drop_index("ix_ai_runs_user_id", table_name="ai_runs")
    op.drop_index("ix_ai_runs_question_set_id", table_name="ai_runs")
    op.drop_table("ai_runs")
    op.execute("DROP TYPE ai_run_status")
