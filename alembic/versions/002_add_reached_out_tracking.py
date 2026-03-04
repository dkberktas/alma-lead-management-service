"""add reached_out tracking columns to leads

Revision ID: 002
Revises: 001
Create Date: 2026-03-04

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

revision: str = "002"
down_revision: Union[str, None] = "001"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column(
        "leads",
        sa.Column("reached_out_at", sa.DateTime(timezone=True), nullable=True),
    )
    op.add_column(
        "leads",
        sa.Column(
            "reached_out_by_id",
            sa.Uuid(),
            sa.ForeignKey("users.id", ondelete="SET NULL"),
            nullable=True,
        ),
    )
    op.create_index("ix_leads_reached_out_by_id", "leads", ["reached_out_by_id"])


def downgrade() -> None:
    op.drop_index("ix_leads_reached_out_by_id", table_name="leads")
    op.drop_column("leads", "reached_out_by_id")
    op.drop_column("leads", "reached_out_at")
