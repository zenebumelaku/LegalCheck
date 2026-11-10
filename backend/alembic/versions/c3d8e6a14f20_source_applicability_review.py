"""record source applicability reviews separately from provenance verification

Revision ID: c3d8e6a14f20
Revises: b8c2f18a4d63
Create Date: 2026-11-10 03:00:00
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "c3d8e6a14f20"
down_revision: Union[str, None] = "b8c2f18a4d63"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column(
        "legal_sources",
        sa.Column("applicability_reviewed_by", sa.Uuid(), nullable=True),
    )
    op.add_column(
        "legal_sources",
        sa.Column("applicability_reviewed_at", sa.DateTime(timezone=True), nullable=True),
    )
    op.add_column(
        "legal_sources",
        sa.Column("applicability_review_notes", sa.Text(), nullable=True),
    )
    op.create_foreign_key(
        "fk_legal_sources_applicability_reviewed_by_users",
        "legal_sources",
        "users",
        ["applicability_reviewed_by"],
        ["id"],
        ondelete="RESTRICT",
    )


def downgrade() -> None:
    op.drop_constraint(
        "fk_legal_sources_applicability_reviewed_by_users",
        "legal_sources",
        type_="foreignkey",
    )
    op.drop_column("legal_sources", "applicability_review_notes")
    op.drop_column("legal_sources", "applicability_reviewed_at")
    op.drop_column("legal_sources", "applicability_reviewed_by")
