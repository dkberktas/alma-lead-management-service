"""add missing indexes

Revision ID: 003
Revises: 002
Create Date: 2026-03-04
"""
from typing import Sequence, Union

from alembic import op

revision: str = "003"
down_revision: Union[str, None] = "002"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_index("ix_leads_created_at", "leads", ["created_at"])
    op.create_index("ix_leads_state", "leads", ["state"])
    op.create_index("ix_audit_logs_created_at", "audit_logs", ["created_at"])
    op.create_index(
        "ix_audit_logs_entity_type_created_at",
        "audit_logs",
        ["entity_type", "created_at"],
    )


def downgrade() -> None:
    op.drop_index("ix_audit_logs_entity_type_created_at", table_name="audit_logs")
    op.drop_index("ix_audit_logs_created_at", table_name="audit_logs")
    op.drop_index("ix_leads_state", table_name="leads")
    op.drop_index("ix_leads_created_at", table_name="leads")
