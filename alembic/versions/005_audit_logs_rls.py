"""add RLS policies to audit_logs table

Revision ID: 005
Revises: 004
Create Date: 2026-03-04

Admin-only SELECT; unrestricted INSERT (background tasks write
without user context).
"""
from typing import Sequence, Union

from alembic import op

revision: str = "005"
down_revision: Union[str, None] = "004"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.execute("ALTER TABLE audit_logs ENABLE ROW LEVEL SECURITY")
    op.execute("ALTER TABLE audit_logs FORCE ROW LEVEL SECURITY")

    op.execute("""
        CREATE POLICY audit_logs_admin_select ON audit_logs
        FOR SELECT
        USING (
            EXISTS (
                SELECT 1 FROM users
                WHERE users.id = current_setting('app.current_user_id', true)::uuid
                  AND users.role = 'ADMIN'
                  AND users.is_active = true
            )
        )
    """)

    op.execute("""
        CREATE POLICY audit_logs_insert ON audit_logs
        FOR INSERT
        WITH CHECK (true)
    """)


def downgrade() -> None:
    op.execute("DROP POLICY IF EXISTS audit_logs_insert ON audit_logs")
    op.execute("DROP POLICY IF EXISTS audit_logs_admin_select ON audit_logs")
    op.execute("ALTER TABLE audit_logs DISABLE ROW LEVEL SECURITY")
    op.execute("ALTER TABLE audit_logs NO FORCE ROW LEVEL SECURITY")
