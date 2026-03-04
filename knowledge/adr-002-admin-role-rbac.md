# ADR-002: Admin Role and Role-Based Access Control

## Status
Accepted

## Context
The original spec mentions attorneys accessing an internal UI. We needed to decide how attorney accounts are managed and whether a privileged admin role is required.

Open question #9 from our analysis: "Do we need admin and/or recruiter roles?"

## Decision
Introduce a **two-role system**: `ADMIN` and `ATTORNEY`.

- **First registered user** automatically becomes `ADMIN` (bootstrap without manual DB seeding)
- Admin can create attorney accounts, list all users, and delete users
- Attorneys can view/update leads but cannot manage users
- Admins cannot delete their own account (safety guard)
- Only admins can delete admin accounts (RLS at the service layer)
- Role is embedded in the JWT token for fast checks, but the `require_admin` dependency re-validates against the database

## Alternatives Considered

| Option | Pros | Cons |
|--------|------|------|
| Single role (everyone is equal) | Simplest | No access control for user management |
| Open registration (anyone can register) | Zero admin overhead | No control over who accesses internal data |
| Full RBAC with permissions table | Maximally flexible | Over-engineered for two roles |
| Environment-based admin seeding | Explicit | Requires manual config, not self-service |

## Consequences
- The `/api/auth/register` endpoint is still public (for bootstrapping the first admin). In production, this should be locked down after the first admin is created or restricted by network policy.
- Attorney accounts are created exclusively through the admin API (`POST /api/admin/attorneys`)
- Role checking happens at two levels: JWT claim for fast-path and database lookup for authoritative check
- Adding future roles (e.g., `RECRUITER`) is a one-line enum addition + new dependency function
