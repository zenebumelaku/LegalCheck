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
    with op.batch_alter_table("legal_sources", schema=None) as batch_op:
        batch_op.add_column(
            sa.Column("applicability_reviewed_by", sa.Uuid(), nullable=True),
        )
        batch_op.add_column(
            sa.Column("applicability_reviewed_at", sa.DateTime(timezone=True), nullable=True),
        )
        batch_op.add_column(
            sa.Column("applicability_review_notes", sa.Text(), nullable=True),
        )
        batch_op.create_foreign_key(
            "fk_legal_sources_applicability_reviewed_by_users",
            "users",
            ["applicability_reviewed_by"],
            ["id"],
            ondelete="RESTRICT",
        )


def downgrade() -> None:
    with op.batch_alter_table("legal_sources", schema=None) as batch_op:
        batch_op.drop_constraint(
            "fk_legal_sources_applicability_reviewed_by_users",
            type_="foreignkey",
        )
        batch_op.drop_column("applicability_review_notes")
        batch_op.drop_column("applicability_reviewed_at")
        batch_op.drop_column("applicability_reviewed_by")
