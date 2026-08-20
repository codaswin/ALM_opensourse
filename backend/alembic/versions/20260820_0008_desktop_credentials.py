"""Allow desktop credential rows to contain metadata without secret ciphertext.

Revision ID: 20260820_0008
Revises: 20260819_0007
Create Date: 2026-08-20
"""

from alembic import op
import sqlalchemy as sa

revision = "20260820_0008"
down_revision = "20260819_0007"
branch_labels = None
depends_on = None


def upgrade() -> None:
    with op.batch_alter_table("platform_credentials") as batch_op:
        batch_op.alter_column("encrypted_value", existing_type=sa.String(), nullable=True)


def downgrade() -> None:
    connection = op.get_bind()
    missing = connection.execute(
        sa.text("SELECT COUNT(*) FROM platform_credentials WHERE encrypted_value IS NULL")
    ).scalar() or 0
    if missing:
        raise RuntimeError(
            "Cannot downgrade: desktop credential metadata rows contain no database ciphertext"
        )
    with op.batch_alter_table("platform_credentials") as batch_op:
        batch_op.alter_column("encrypted_value", existing_type=sa.String(), nullable=False)
