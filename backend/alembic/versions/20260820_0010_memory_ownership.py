"""Add structural user ownership to episodic and semantic memory.

Revision ID: 20260820_0010
Revises: 20260820_0009
Create Date: 2026-08-20
"""

from __future__ import annotations

import os

from alembic import op
import sqlalchemy as sa

revision = "20260820_0010"
down_revision = "20260820_0009"
branch_labels = None
depends_on = None

_TABLES = ("post_episodes", "thread_episodes", "semantic_memory_records")


def _resolve_owner(connection: sa.engine.Connection) -> str | None:
    username = os.environ.get("DASHBOARD_ADMIN_USERNAME", "").strip().lower()
    if username:
        owner = connection.execute(
            sa.text("SELECT id FROM dashboard_users WHERE username = :username"),
            {"username": username},
        ).scalar()
        if owner is not None:
            return str(owner)
    owner = connection.execute(sa.text("SELECT id FROM dashboard_users LIMIT 1")).scalar()
    return str(owner) if owner is not None else None


def upgrade() -> None:
    connection = op.get_bind()
    owner: str | None = None
    for table in _TABLES:
        with op.batch_alter_table(table) as batch_op:
            batch_op.add_column(sa.Column("user_id", sa.String(), nullable=True))
        count = connection.execute(sa.text(f"SELECT COUNT(*) FROM {table}")).scalar() or 0
        if count:
            owner = owner or _resolve_owner(connection)
            if owner is None:
                raise RuntimeError(
                    f"Cannot assign existing {table} rows because no dashboard user exists"
                )
            connection.execute(
                sa.text(f"UPDATE {table} SET user_id = :owner WHERE user_id IS NULL"),
                {"owner": owner},
            )
        with op.batch_alter_table(table) as batch_op:
            batch_op.alter_column("user_id", existing_type=sa.String(), nullable=False)
            batch_op.create_foreign_key(
                f"fk_{table}_user_id", "dashboard_users", ["user_id"], ["id"], ondelete="CASCADE"
            )
            batch_op.create_index(f"ix_{table}_user_id", ["user_id"])


def downgrade() -> None:
    for table in reversed(_TABLES):
        with op.batch_alter_table(table) as batch_op:
            batch_op.drop_index(f"ix_{table}_user_id")
            batch_op.drop_constraint(f"fk_{table}_user_id", type_="foreignkey")
            batch_op.drop_column("user_id")
