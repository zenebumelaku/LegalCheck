"""Add explicit audit lifecycle states and processing warnings.

Revision ID: c814a9d07e32
Revises: b63f1a72c901
Create Date: 2026-10-24 12:00:00.000000
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "c814a9d07e32"
down_revision: Union[str, None] = "b63f1a72c901"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


_AUDIT_STATUS_CHECK = (
    "audit_status IN ('queued', 'extracting', 'retrieving_sources', "
    "'analyzing', 'generating_report', 'completed', 'failed')"
)


def upgrade() -> None:
    with op.batch_alter_table("audits") as batch_op:
        batch_op.drop_constraint("ck_audits_status", type_="check")
        batch_op.add_column(
            sa.Column(
                "processing_warnings",
                sa.JSON(),
                server_default=sa.text("'[]'"),
                nullable=False,
            )
        )
        batch_op.add_column(sa.Column("processing_attempt_id", sa.Uuid(), nullable=True))

    op.execute(
        sa.text(
            "UPDATE audits SET audit_status = 'queued' "
            "WHERE audit_status = 'pending'"
        )
    )
    op.execute(
        sa.text(
            "UPDATE audits SET audit_status = 'failed', "
            "failure_code = 'worker_restarted', "
            "failure_message = 'A prior audit worker stopped before completion.' "
            "WHERE audit_status = 'processing'"
        )
    )

    with op.batch_alter_table("audits") as batch_op:
        batch_op.create_check_constraint("ck_audits_status", _AUDIT_STATUS_CHECK)


def downgrade() -> None:
    with op.batch_alter_table("audits") as batch_op:
        batch_op.drop_constraint("ck_audits_status", type_="check")

    op.execute(
        sa.text(
            "UPDATE audits SET audit_status = 'pending' "
            "WHERE audit_status IN ('queued', 'extracting', 'retrieving_sources', "
            "'analyzing', 'generating_report')"
        )
    )

    with op.batch_alter_table("audits") as batch_op:
        batch_op.create_check_constraint(
            "ck_audits_status",
            "audit_status IN ('pending', 'processing', 'completed', 'failed')",
        )
        batch_op.drop_column("processing_warnings")
        batch_op.drop_column("processing_attempt_id")
