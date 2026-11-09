"""add hashed, one-time password reset tokens

Revision ID: b8c2f18a4d63
Revises: f1a4c8d2b907
Create Date: 2026-11-18 09:00:00
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "b8c2f18a4d63"
down_revision: Union[str, None] = "f1a4c8d2b907"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "password_reset_tokens",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("user_id", sa.Uuid(), nullable=False),
        sa.Column("token_hash", sa.String(length=64), nullable=False),
        sa.Column("expires_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("consumed_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("revoked_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("token_hash"),
    )
    op.create_index(
        "ix_password_reset_tokens_user_expiry",
        "password_reset_tokens",
        ["user_id", "expires_at"],
        unique=False,
    )
    op.create_index(
        "ix_password_reset_tokens_expiry",
        "password_reset_tokens",
        ["expires_at"],
        unique=False,
    )


def downgrade() -> None:
    op.drop_index(
        "ix_password_reset_tokens_expiry",
        table_name="password_reset_tokens",
    )
    op.drop_index(
        "ix_password_reset_tokens_user_expiry",
        table_name="password_reset_tokens",
    )
    op.drop_table("password_reset_tokens")
