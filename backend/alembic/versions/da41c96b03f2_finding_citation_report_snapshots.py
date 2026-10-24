"""Snapshot cited source details for historical audit reports.

Revision ID: da41c96b03f2
Revises: c814a9d07e32
Create Date: 2026-10-24 12:46:00.000000
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "da41c96b03f2"
down_revision: Union[str, None] = "c814a9d07e32"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    with op.batch_alter_table("finding_citations") as batch_op:
        batch_op.add_column(sa.Column("source_title_snapshot", sa.String(500)))
        batch_op.add_column(sa.Column("source_version_snapshot", sa.String(100)))
        batch_op.add_column(sa.Column("source_url_snapshot", sa.String(2048)))
        batch_op.add_column(sa.Column("article_number_snapshot", sa.String(100)))
        batch_op.add_column(
            sa.Column("sub_article_reference_snapshot", sa.String(100))
        )
        batch_op.add_column(sa.Column("provision_text_snapshot", sa.Text()))
    op.execute(
        sa.text(
            """
            UPDATE finding_citations
            SET source_title_snapshot = (
                    SELECT legal_sources.title
                    FROM legal_provisions
                    JOIN legal_sources
                      ON legal_sources.id = legal_provisions.legal_source_id
                    WHERE legal_provisions.id = finding_citations.legal_provision_id
                ),
                source_version_snapshot = (
                    SELECT legal_sources.version_label
                    FROM legal_provisions
                    JOIN legal_sources
                      ON legal_sources.id = legal_provisions.legal_source_id
                    WHERE legal_provisions.id = finding_citations.legal_provision_id
                ),
                source_url_snapshot = (
                    SELECT legal_sources.original_source_url
                    FROM legal_provisions
                    JOIN legal_sources
                      ON legal_sources.id = legal_provisions.legal_source_id
                    WHERE legal_provisions.id = finding_citations.legal_provision_id
                ),
                article_number_snapshot = (
                    SELECT legal_provisions.article_number
                    FROM legal_provisions
                    WHERE legal_provisions.id = finding_citations.legal_provision_id
                ),
                sub_article_reference_snapshot = (
                    SELECT legal_provisions.sub_article_reference
                    FROM legal_provisions
                    WHERE legal_provisions.id = finding_citations.legal_provision_id
                ),
                provision_text_snapshot = (
                    SELECT legal_provisions.text
                    FROM legal_provisions
                    WHERE legal_provisions.id = finding_citations.legal_provision_id
                )
            """
        )
    )


def downgrade() -> None:
    with op.batch_alter_table("finding_citations") as batch_op:
        batch_op.drop_column("provision_text_snapshot")
        batch_op.drop_column("sub_article_reference_snapshot")
        batch_op.drop_column("article_number_snapshot")
        batch_op.drop_column("source_url_snapshot")
        batch_op.drop_column("source_version_snapshot")
        batch_op.drop_column("source_title_snapshot")
