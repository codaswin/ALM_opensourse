"""Drop dashboard_sessions and login_audit — dead in a desktop-only build.

Password login/session/CSRF (app/safety/api_auth.py) and login auditing
were the self-hosted/server-mode dashboard login system; that deployment
now lives in a separate repository. dashboard_users stays untouched — it's
still the FK target for the desktop build's single local-owner row (see
app/local_identity.py) and every tenant-scoped table.

Revision ID: 20260821_0011
Revises: 20260820_0010
Create Date: 2026-08-21
"""

from __future__ import annotations

from alembic import op
import sqlalchemy as sa

revision = "20260821_0011"
down_revision = "20260820_0010"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.drop_table("login_audit")
    op.drop_table("dashboard_sessions")


def downgrade() -> None:
    op.create_table(
        "dashboard_sessions",
        sa.Column("id", sa.String(), primary_key=True),
        sa.Column("user_id", sa.String(), nullable=False),
        sa.Column("token_hash", sa.String(), nullable=False),
        sa.Column("csrf_hash", sa.String(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("expires_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("last_seen_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("revoked_at", sa.DateTime(timezone=True), nullable=True),
        sa.ForeignKeyConstraint(["user_id"], ["dashboard_users.id"], ondelete="CASCADE"),
    )
    op.create_index("ix_dashboard_sessions_user_id", "dashboard_sessions", ["user_id"])
    op.create_index("ix_dashboard_sessions_token_hash", "dashboard_sessions", ["token_hash"], unique=True)
    op.create_index("ix_dashboard_sessions_expires_at", "dashboard_sessions", ["expires_at"])

    op.create_table(
        "login_audit",
        sa.Column("id", sa.String(), primary_key=True),
        sa.Column("username", sa.String(), nullable=False),
        sa.Column("succeeded", sa.Boolean(), nullable=False),
        sa.Column("remote_address", sa.String(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
    )
    op.create_index("ix_login_audit_username", "login_audit", ["username"])
