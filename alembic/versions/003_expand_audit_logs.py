"""Expand audit_logs for full entity audit trail.

Make lead_id, user_id, old_state, new_state nullable.
Add entity_type, entity_id columns for generic auditing.

Revision ID: 003
Revises: 002
Create Date: 2026-03-04
"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

revision: str = "003"
down_revision: Union[str, None] = "002"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column(
        "audit_logs",
        sa.Column("entity_type", sa.String(50), nullable=True, index=True),
    )
    op.add_column(
        "audit_logs",
        sa.Column("entity_id", sa.Uuid(), nullable=True, index=True),
    )

    # Backfill existing rows: they are all lead state changes
    op.execute("UPDATE audit_logs SET entity_type = 'lead', entity_id = lead_id")

    op.alter_column("audit_logs", "entity_type", nullable=False)
    op.alter_column("audit_logs", "entity_id", nullable=False)

    op.alter_column("audit_logs", "lead_id", nullable=True)
    op.alter_column("audit_logs", "user_id", nullable=True)
    op.alter_column("audit_logs", "user_email", nullable=True)
    op.alter_column("audit_logs", "old_state", nullable=True)
    op.alter_column("audit_logs", "new_state", nullable=True)

    op.create_index("ix_audit_logs_action", "audit_logs", ["action"])


def downgrade() -> None:
    op.drop_index("ix_audit_logs_action", table_name="audit_logs")

    op.alter_column("audit_logs", "new_state", nullable=False)
    op.alter_column("audit_logs", "old_state", nullable=False)
    op.alter_column("audit_logs", "user_email", nullable=False)
    op.alter_column("audit_logs", "user_id", nullable=False)
    op.alter_column("audit_logs", "lead_id", nullable=False)

    op.drop_column("audit_logs", "entity_id")
    op.drop_column("audit_logs", "entity_type")
