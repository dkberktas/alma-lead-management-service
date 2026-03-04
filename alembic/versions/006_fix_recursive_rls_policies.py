"""fix RLS policies — eliminate recursion and handle empty settings

Revision ID: 006
Revises: 005
Create Date: 2026-03-04

Problems fixed:
1. users_admin_all queried users from within a policy on users,
   causing infinite recursion.  Now checks app.current_user_role.
2. audit_logs_admin_select had the same subquery issue.
3. All policies that cast current_setting to uuid now use NULLIF to
   guard against empty-string defaults (PostgreSQL returns '' for
   unset custom GUCs, not NULL).
"""
from typing import Sequence, Union

from alembic import op

revision: str = "006"
down_revision: Union[str, None] = "005"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

_UID_EXPR = "nullif(current_setting('app.current_user_id', true), '')::uuid"


def upgrade() -> None:
    # -- users table policies --
    op.execute("DROP POLICY IF EXISTS users_admin_all ON users")
    op.execute("""
        CREATE POLICY users_admin_all ON users
        FOR ALL
        USING (
            current_setting('app.current_user_role', true) = 'ADMIN'
        )
    """)

    op.execute("DROP POLICY IF EXISTS users_self_select ON users")
    op.execute(f"""
        CREATE POLICY users_self_select ON users
        FOR SELECT
        USING (
            id = {_UID_EXPR}
            AND is_active = true
        )
    """)

    # -- leads table policies --
    op.execute("DROP POLICY IF EXISTS leads_active_users_select ON leads")
    op.execute(f"""
        CREATE POLICY leads_active_users_select ON leads
        FOR SELECT
        USING (
            EXISTS (
                SELECT 1 FROM users
                WHERE users.id = {_UID_EXPR}
                  AND users.is_active = true
            )
        )
    """)

    op.execute("DROP POLICY IF EXISTS leads_active_users_update ON leads")
    op.execute(f"""
        CREATE POLICY leads_active_users_update ON leads
        FOR UPDATE
        USING (
            EXISTS (
                SELECT 1 FROM users
                WHERE users.id = {_UID_EXPR}
                  AND users.is_active = true
            )
        )
    """)

    # -- audit_logs table policies --
    op.execute("DROP POLICY IF EXISTS audit_logs_admin_select ON audit_logs")
    op.execute("""
        CREATE POLICY audit_logs_admin_select ON audit_logs
        FOR SELECT
        USING (
            current_setting('app.current_user_role', true) = 'ADMIN'
        )
    """)


def downgrade() -> None:
    op.execute("DROP POLICY IF EXISTS audit_logs_admin_select ON audit_logs")
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

    op.execute("DROP POLICY IF EXISTS leads_active_users_update ON leads")
    op.execute("""
        CREATE POLICY leads_active_users_update ON leads
        FOR UPDATE
        USING (
            EXISTS (
                SELECT 1 FROM users
                WHERE users.id = current_setting('app.current_user_id', true)::uuid
                  AND users.is_active = true
            )
        )
    """)

    op.execute("DROP POLICY IF EXISTS leads_active_users_select ON leads")
    op.execute("""
        CREATE POLICY leads_active_users_select ON leads
        FOR SELECT
        USING (
            EXISTS (
                SELECT 1 FROM users
                WHERE users.id = current_setting('app.current_user_id', true)::uuid
                  AND users.is_active = true
            )
        )
    """)

    op.execute("DROP POLICY IF EXISTS users_self_select ON users")
    op.execute("""
        CREATE POLICY users_self_select ON users
        FOR SELECT
        USING (
            id = current_setting('app.current_user_id', true)::uuid
            AND is_active = true
        )
    """)

    op.execute("DROP POLICY IF EXISTS users_admin_all ON users")
    op.execute("""
        CREATE POLICY users_admin_all ON users
        FOR ALL
        USING (
            EXISTS (
                SELECT 1 FROM users u
                WHERE u.id = current_setting('app.current_user_id', true)::uuid
                  AND u.role = 'ADMIN'
                  AND u.is_active = true
            )
        )
    """)
