"""Persist owned legal-question conversations and answer snapshots.

Revision ID: f1a4c8d2b907
Revises: da41c96b03f2
Create Date: 2026-11-09 11:40:00.000000
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "f1a4c8d2b907"
down_revision: Union[str, None] = "da41c96b03f2"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "legal_question_conversations",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("user_id", sa.Uuid(), nullable=False),
        sa.Column("title", sa.String(length=500), nullable=False),
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
        sa.CheckConstraint(
            "length(trim(title)) > 0",
            name="ck_legal_question_conversations_title_nonempty",
        ),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        "ix_legal_question_conversations_user_updated",
        "legal_question_conversations",
        ["user_id", "updated_at"],
        unique=False,
    )
    op.create_table(
        "legal_question_messages",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("conversation_id", sa.Uuid(), nullable=False),
        sa.Column("turn_index", sa.Integer(), nullable=False),
        sa.Column("role", sa.String(length=20), nullable=False),
        sa.Column("content", sa.Text(), nullable=False),
        sa.Column("answer_status", sa.String(length=30), nullable=True),
        sa.Column("review_date", sa.Date(), nullable=True),
        sa.Column(
            "citations_snapshot",
            sa.JSON(),
            server_default=sa.text("'[]'"),
            nullable=False,
        ),
        sa.Column("model_name", sa.String(length=255), nullable=True),
        sa.Column("model_version", sa.String(length=100), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
        sa.CheckConstraint(
            "role IN ('user', 'assistant')",
            name="ck_legal_question_messages_role",
        ),
        sa.CheckConstraint(
            "turn_index >= 0",
            name="ck_legal_question_messages_turn_index",
        ),
        sa.CheckConstraint(
            "length(content) > 0",
            name="ck_legal_question_messages_content_nonempty",
        ),
        sa.ForeignKeyConstraint(
            ["conversation_id"],
            ["legal_question_conversations.id"],
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint(
            "conversation_id",
            "turn_index",
            "role",
            name="uq_legal_question_message_turn_role",
        ),
    )
    op.create_index(
        "ix_legal_question_messages_conversation_turn",
        "legal_question_messages",
        ["conversation_id", "turn_index"],
        unique=False,
    )


def downgrade() -> None:
    op.drop_index(
        "ix_legal_question_messages_conversation_turn",
        table_name="legal_question_messages",
    )
    op.drop_table("legal_question_messages")
    op.drop_index(
        "ix_legal_question_conversations_user_updated",
        table_name="legal_question_conversations",
    )
    op.drop_table("legal_question_conversations")
