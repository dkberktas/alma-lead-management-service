"""Add is_active column to users and RLS policies for attorney access control.

Revision ID: 002
Revises: 001
Create Date: 2026-03-04
"""

from alembic import op
import sqlalchemy as sa

revision = "002"
down_revision = "001"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "users",
        sa.Column("is_active", sa.Boolean(), nullable=False, server_default="true"),
    )

    # RLS: only active users can read leads
    op.execute("ALTER TABLE leads ENABLE ROW LEVEL SECURITY")
    op.execute("ALTER TABLE leads FORCE ROW LEVEL SECURITY")

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

    op.execute("""
        CREATE POLICY leads_active_users_insert ON leads
        FOR INSERT
        WITH CHECK (true)
    """)

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

    # RLS on users table: admins see all, others see only themselves
    op.execute("ALTER TABLE users ENABLE ROW LEVEL SECURITY")
    op.execute("ALTER TABLE users FORCE ROW LEVEL SECURITY")

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

    op.execute("""
        CREATE POLICY users_self_select ON users
        FOR SELECT
        USING (
            id = current_setting('app.current_user_id', true)::uuid
            AND is_active = true
        )
    """)


def downgrade() -> None:
    op.execute("DROP POLICY IF EXISTS users_self_select ON users")
    op.execute("DROP POLICY IF EXISTS users_admin_all ON users")
    op.execute("ALTER TABLE users DISABLE ROW LEVEL SECURITY")

    op.execute("DROP POLICY IF EXISTS leads_active_users_update ON leads")
    op.execute("DROP POLICY IF EXISTS leads_active_users_insert ON leads")
    op.execute("DROP POLICY IF EXISTS leads_active_users_select ON leads")
    op.execute("ALTER TABLE leads DISABLE ROW LEVEL SECURITY")

    op.drop_column("users", "is_active")
