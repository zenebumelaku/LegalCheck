"""preserve source applicability review history

Revision ID: d4e9f7b25a31
Revises: c3d8e6a14f20
Create Date: 2026-11-10 03:10:00
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "d4e9f7b25a31"
down_revision: Union[str, None] = "c3d8e6a14f20"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "legal_source_applicability_reviews",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("source_id", sa.Uuid(), nullable=False),
        sa.Column("reviewer_id", sa.Uuid(), nullable=False),
        sa.Column("legal_status", sa.String(length=30), nullable=False),
        sa.Column("effective_date", sa.Date(), nullable=True),
        sa.Column("end_date", sa.Date(), nullable=True),
        sa.Column("verification_notes", sa.Text(), nullable=False),
        sa.Column(
            "reviewed_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
        sa.CheckConstraint(
            "legal_status IN ('unknown', 'current', 'amended', 'repealed', 'superseded')",
            name="ck_legal_source_applicability_reviews_status",
        ),
        sa.CheckConstraint(
            "end_date IS NULL OR effective_date IS NULL OR end_date >= effective_date",
            name="ck_legal_source_applicability_reviews_dates",
        ),
        sa.ForeignKeyConstraint(
            ["reviewer_id"],
            ["users.id"],
            ondelete="RESTRICT",
        ),
        sa.ForeignKeyConstraint(
            ["source_id"],
            ["legal_sources.id"],
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        "ix_legal_source_applicability_reviews_source_time",
        "legal_source_applicability_reviews",
        ["source_id", "reviewed_at"],
    )


def downgrade() -> None:
    op.drop_index(
        "ix_legal_source_applicability_reviews_source_time",
        table_name="legal_source_applicability_reviews",
    )
    op.drop_table("legal_source_applicability_reviews")
