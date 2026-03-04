"""initial schema

Revision ID: 001
Revises:
Create Date: 2026-03-04

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

revision: str = "001"
down_revision: Union[str, None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "users",
        sa.Column("id", sa.Uuid(), primary_key=True),
        sa.Column("email", sa.String(255), nullable=False, unique=True, index=True),
        sa.Column("hashed_password", sa.String(255), nullable=False),
        sa.Column(
            "role",
            sa.Enum("ADMIN", "ATTORNEY", name="userrole"),
            nullable=False,
            server_default="ATTORNEY",
        ),
        sa.Column("is_active", sa.Boolean(), nullable=False, server_default="true"),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
    )

    op.create_table(
        "leads",
        sa.Column("id", sa.Uuid(), primary_key=True),
        sa.Column("first_name", sa.String(100), nullable=False),
        sa.Column("last_name", sa.String(100), nullable=False),
        sa.Column("email", sa.String(255), nullable=False),
        sa.Column("resume_path", sa.Text(), nullable=False),
        sa.Column(
            "state",
            sa.Enum("PENDING", "REACHED_OUT", name="leadstate"),
            nullable=False,
            server_default="PENDING",
        ),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
    )

    op.create_table(
        "audit_logs",
        sa.Column("id", sa.Uuid(), primary_key=True),
        sa.Column("entity_type", sa.String(50), nullable=False, index=True),
        sa.Column("entity_id", sa.Uuid(), nullable=False, index=True),
        sa.Column("action", sa.String(50), nullable=False, index=True),
        sa.Column(
            "user_id",
            sa.Uuid(),
            sa.ForeignKey("users.id", ondelete="SET NULL"),
            nullable=True,
            index=True,
        ),
        sa.Column("user_email", sa.String(255), nullable=True),
        sa.Column("old_state", sa.String(50), nullable=True),
        sa.Column("new_state", sa.String(50), nullable=True),
        sa.Column("detail", sa.Text(), nullable=True),
        sa.Column(
            "lead_id",
            sa.Uuid(),
            sa.ForeignKey("leads.id", ondelete="SET NULL"),
            nullable=True,
            index=True,
        ),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
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

    op.drop_table("audit_logs")
    op.drop_table("leads")
    op.drop_table("users")
    sa.Enum(name="leadstate").drop(op.get_bind(), checkfirst=True)
    sa.Enum(name="userrole").drop(op.get_bind(), checkfirst=True)
