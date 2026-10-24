"""Add versioned legal provision chunks and pgvector embeddings.

Revision ID: b63f1a72c901
Revises: 9a1c4e73d622
Create Date: 2026-10-24 11:10:00.000000
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from pgvector.sqlalchemy import Vector


revision: str = "b63f1a72c901"
down_revision: Union[str, None] = "9a1c4e73d622"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    bind = op.get_bind()
    vector_type = (
        Vector(384)
        if bind.dialect.name == "postgresql"
        else sa.JSON()
    )
    if bind.dialect.name == "postgresql":
        op.execute("CREATE EXTENSION IF NOT EXISTS vector")

    op.create_table(
        "legal_provision_chunks",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("provision_id", sa.Uuid(), nullable=False),
        sa.Column("chunk_index", sa.Integer(), nullable=False),
        sa.Column("chunk_text", sa.Text(), nullable=False),
        sa.Column("content_checksum", sa.String(length=64), nullable=False),
        sa.Column("page_number", sa.Integer(), nullable=True),
        sa.Column("source_version_label", sa.String(length=100), nullable=True),
        sa.Column("embedding_model", sa.String(length=255), nullable=False),
        sa.Column("embedding_version", sa.String(length=100), nullable=False),
        sa.Column("embedding", vector_type, nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
        sa.CheckConstraint("chunk_index >= 0", name="ck_provision_chunks_index"),
        sa.CheckConstraint("length(chunk_text) > 0", name="ck_provision_chunks_text"),
        sa.CheckConstraint(
            "length(embedding_model) > 0",
            name="ck_provision_chunks_embedding_model",
        ),
        sa.CheckConstraint(
            "length(embedding_version) > 0",
            name="ck_provision_chunks_embedding_version",
        ),
        sa.CheckConstraint(
            "page_number IS NULL OR page_number > 0",
            name="ck_provision_chunks_page_number",
        ),
        sa.ForeignKeyConstraint(
            ["provision_id"],
            ["legal_provisions.id"],
            ondelete="RESTRICT",
        ),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint(
            "provision_id",
            "chunk_index",
            "embedding_model",
            "embedding_version",
            name="uq_provision_chunk_model_version",
        ),
    )
    op.create_index(
        "ix_provision_chunks_provision_id",
        "legal_provision_chunks",
        ["provision_id"],
    )
    op.create_index(
        "ix_provision_chunks_embedding_model_version",
        "legal_provision_chunks",
        ["embedding_model", "embedding_version"],
    )
    if bind.dialect.name == "postgresql":
        op.execute(
            "CREATE INDEX ix_provision_chunks_embedding_search "
            "ON legal_provision_chunks USING hnsw "
            "(embedding vector_cosine_ops) WHERE embedding IS NOT NULL"
        )
        op.execute(
            "CREATE INDEX ix_legal_provisions_text_search "
            "ON legal_provisions USING gin (to_tsvector('simple', text))"
        )
    else:
        op.create_index(
            "ix_provision_chunks_embedding_search",
            "legal_provision_chunks",
            ["embedding"],
        )


def downgrade() -> None:
    bind = op.get_bind()
    if bind.dialect.name == "postgresql":
        op.execute("DROP INDEX IF EXISTS ix_legal_provisions_text_search")
        op.execute("DROP INDEX IF EXISTS ix_provision_chunks_embedding_search")
    else:
        op.drop_index(
            "ix_provision_chunks_embedding_search",
            table_name="legal_provision_chunks",
        )
    op.drop_index(
        "ix_provision_chunks_embedding_model_version",
        table_name="legal_provision_chunks",
    )
    op.drop_index(
        "ix_provision_chunks_provision_id",
        table_name="legal_provision_chunks",
    )
    op.drop_table("legal_provision_chunks")
