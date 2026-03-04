-- Non-superuser role for the FastAPI application.
-- The alma superuser (created by POSTGRES_USER) owns tables and runs migrations.
-- alma_app connects at runtime so PostgreSQL RLS policies are enforced.

CREATE ROLE alma_app WITH LOGIN PASSWORD 'alma_app_dev_password';

GRANT CONNECT ON DATABASE alma_leads TO alma_app;
GRANT USAGE ON SCHEMA public TO alma_app;

-- Any tables created by alma (via Alembic) automatically grant DML to alma_app.
ALTER DEFAULT PRIVILEGES FOR ROLE alma IN SCHEMA public
  GRANT SELECT, INSERT, UPDATE, DELETE ON TABLES TO alma_app;
ALTER DEFAULT PRIVILEGES FOR ROLE alma IN SCHEMA public
  GRANT USAGE, SELECT ON SEQUENCES TO alma_app;
