"""Scope processed notification identity to its owning user.

Revision ID: 20260820_0009
Revises: 20260820_0008
Create Date: 2026-08-20
"""

from alembic import op
import sqlalchemy as sa

revision = "20260820_0009"
down_revision = "20260820_0008"
branch_labels = None
depends_on = None


def upgrade() -> None:
    connection = op.get_bind()
    op.create_table(
        "processed_notifications_new",
        sa.Column("id", sa.String(), primary_key=True),
        sa.Column("notification_id", sa.String(), nullable=False),
        sa.Column(
            "user_id",
            sa.String(),
            sa.ForeignKey("dashboard_users.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("outcome", sa.String(), nullable=False),
        sa.Column("processed_at", sa.DateTime(timezone=True), nullable=True),
        sa.UniqueConstraint(
            "user_id", "notification_id", name="uq_processed_notification_owner"
        ),
    )
    connection.execute(
        sa.text(
            "INSERT INTO processed_notifications_new "
            "(id, notification_id, user_id, outcome, processed_at) "
            "SELECT user_id || ':' || notification_id, notification_id, user_id, outcome, processed_at "
            "FROM processed_notifications"
        )
    )
    op.drop_table("processed_notifications")
    op.rename_table("processed_notifications_new", "processed_notifications")
    op.create_index(
        "ix_processed_notifications_user_id", "processed_notifications", ["user_id"]
    )
    op.create_index(
        "ix_processed_notifications_notification_id",
        "processed_notifications",
        ["notification_id"],
    )


def downgrade() -> None:
    connection = op.get_bind()
    duplicates = connection.execute(
        sa.text(
            "SELECT COUNT(*) FROM (SELECT notification_id FROM processed_notifications "
            "GROUP BY notification_id HAVING COUNT(*) > 1) AS duplicate_ids"
        )
    ).scalar() or 0
    if duplicates:
        raise RuntimeError(
            "Cannot downgrade processed notifications with duplicate IDs across users"
        )
    op.create_table(
        "processed_notifications_old",
        sa.Column("notification_id", sa.String(), primary_key=True),
        sa.Column(
            "user_id",
            sa.String(),
            sa.ForeignKey("dashboard_users.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("outcome", sa.String(), nullable=False),
        sa.Column("processed_at", sa.DateTime(timezone=True), nullable=True),
    )
    connection.execute(
        sa.text(
            "INSERT INTO processed_notifications_old "
            "(notification_id, user_id, outcome, processed_at) "
            "SELECT notification_id, user_id, outcome, processed_at FROM processed_notifications"
        )
    )
    op.drop_table("processed_notifications")
    op.rename_table("processed_notifications_old", "processed_notifications")
    op.create_index(
        "ix_processed_notifications_user_id", "processed_notifications", ["user_id"]
    )
