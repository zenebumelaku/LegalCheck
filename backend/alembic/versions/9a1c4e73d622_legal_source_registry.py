"""Add source provenance, review attribution, and sub-article references.

Revision ID: 9a1c4e73d622
Revises: 84a910ce2761
Create Date: 2026-10-24 10:50:00.000000
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "9a1c4e73d622"
down_revision: Union[str, None] = "84a910ce2761"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    with op.batch_alter_table("legal_sources") as batch_op:
        batch_op.add_column(sa.Column("source_file_storage_key", sa.String(1024)))
        batch_op.add_column(sa.Column("ingested_by", sa.Uuid(), nullable=True))
        batch_op.add_column(sa.Column("verified_by", sa.Uuid(), nullable=True))
        batch_op.add_column(sa.Column("verification_notes", sa.Text(), nullable=True))
        batch_op.create_foreign_key(
            "fk_legal_sources_ingested_by_users",
            "users",
            ["ingested_by"],
            ["id"],
            ondelete="RESTRICT",
        )
        batch_op.create_foreign_key(
            "fk_legal_sources_verified_by_users",
            "users",
            ["verified_by"],
            ["id"],
            ondelete="RESTRICT",
        )
        batch_op.drop_constraint("ck_legal_sources_status", type_="check")
        batch_op.create_check_constraint(
            "ck_legal_sources_status",
            "legal_status IN "
            "('unknown', 'current', 'active', 'amended', 'repealed', 'superseded')",
        )
        batch_op.create_unique_constraint(
            "uq_legal_sources_storage_key",
            ["source_file_storage_key"],
        )

    op.create_index(
        "uq_legal_sources_file_checksum",
        "legal_sources",
        ["file_checksum"],
        unique=True,
    )

    with op.batch_alter_table("legal_provisions") as batch_op:
        batch_op.add_column(sa.Column("sub_article_reference", sa.String(100)))
        batch_op.drop_constraint(
            "uq_legal_provision_source_article_section",
            type_="unique",
        )
        batch_op.create_unique_constraint(
            "uq_legal_provision_source_article_section",
            [
                "legal_source_id",
                "article_number",
                "sub_article_reference",
                "section_title",
            ],
        )


def downgrade() -> None:
    with op.batch_alter_table("legal_provisions") as batch_op:
        batch_op.drop_constraint(
            "uq_legal_provision_source_article_section",
            type_="unique",
        )
        batch_op.create_unique_constraint(
            "uq_legal_provision_source_article_section",
            ["legal_source_id", "article_number", "section_title"],
        )
        batch_op.drop_column("sub_article_reference")

    op.drop_index("uq_legal_sources_file_checksum", table_name="legal_sources")

    with op.batch_alter_table("legal_sources") as batch_op:
        batch_op.drop_constraint("uq_legal_sources_storage_key", type_="unique")
        batch_op.drop_constraint("ck_legal_sources_status", type_="check")
        batch_op.create_check_constraint(
            "ck_legal_sources_status",
            "legal_status IN ('unknown', 'active', 'amended', 'repealed', 'superseded')",
        )
        batch_op.drop_constraint(
            "fk_legal_sources_verified_by_users",
            type_="foreignkey",
        )
        batch_op.drop_constraint(
            "fk_legal_sources_ingested_by_users",
            type_="foreignkey",
        )
        batch_op.drop_column("verification_notes")
        batch_op.drop_column("verified_by")
        batch_op.drop_column("ingested_by")
        batch_op.drop_column("source_file_storage_key")
