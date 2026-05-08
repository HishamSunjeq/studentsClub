"""user_settings + notifications tables

Revision ID: 0007
Revises: 0006
Create Date: 2026-05-04
"""

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision = "0007"
down_revision = "0006"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # create_type=False so create_table below doesn't try to CREATE TYPE a second
    # time after the explicit .create() call.
    theme_enum = postgresql.ENUM(
        "system", "light", "dark", name="theme_preference", create_type=False
    )
    density_enum = postgresql.ENUM(
        "comfortable", "compact", name="density_preference", create_type=False
    )
    notif_enum = postgresql.ENUM(
        "draft_ready",
        "question_set_published",
        "question_set_voted",
        "new_material_in_subject",
        name="notification_type",
        create_type=False,
    )
    bind = op.get_bind()
    sa.Enum("system", "light", "dark", name="theme_preference").create(bind, checkfirst=True)
    sa.Enum("comfortable", "compact", name="density_preference").create(bind, checkfirst=True)
    sa.Enum(
        "draft_ready",
        "question_set_published",
        "question_set_voted",
        "new_material_in_subject",
        name="notification_type",
    ).create(bind, checkfirst=True)

    op.create_table(
        "user_settings",
        sa.Column(
            "id",
            sa.UUID(),
            nullable=False,
            server_default=sa.text("gen_random_uuid()"),
        ),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("user_id", sa.UUID(), nullable=False),
        sa.Column(
            "theme",
            theme_enum,
            nullable=False,
            server_default="system",
        ),
        sa.Column("accent_color", sa.Text(), nullable=False, server_default="indigo"),
        sa.Column(
            "density",
            density_enum,
            nullable=False,
            server_default="comfortable",
        ),
        sa.Column("language", sa.Text(), nullable=False, server_default="en"),
        sa.Column(
            "notification_prefs",
            postgresql.JSONB(),
            nullable=False,
            server_default=sa.text("'{}'::jsonb"),
        ),
        sa.PrimaryKeyConstraint("id"),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="CASCADE"),
        sa.UniqueConstraint("user_id"),
    )

    op.create_table(
        "notifications",
        sa.Column(
            "id",
            sa.UUID(),
            nullable=False,
            server_default=sa.text("gen_random_uuid()"),
        ),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("user_id", sa.UUID(), nullable=False),
        sa.Column("type", notif_enum, nullable=False),
        sa.Column("title", sa.Text(), nullable=False),
        sa.Column("body", sa.Text(), nullable=True),
        sa.Column(
            "payload",
            postgresql.JSONB(),
            nullable=False,
            server_default=sa.text("'{}'::jsonb"),
        ),
        sa.Column("read_at", sa.DateTime(timezone=True), nullable=True),
        sa.PrimaryKeyConstraint("id"),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="CASCADE"),
    )
    op.create_index("ix_notifications_user_id", "notifications", ["user_id"])
    op.create_index("ix_notifications_read_at", "notifications", ["read_at"])


def downgrade() -> None:
    op.drop_index("ix_notifications_read_at", table_name="notifications")
    op.drop_index("ix_notifications_user_id", table_name="notifications")
    op.drop_table("notifications")
    op.drop_table("user_settings")
    sa.Enum(name="notification_type").drop(op.get_bind(), checkfirst=True)
    sa.Enum(name="density_preference").drop(op.get_bind(), checkfirst=True)
    sa.Enum(name="theme_preference").drop(op.get_bind(), checkfirst=True)
