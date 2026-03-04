from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    environment: str = "development"  # "development", "staging", "production"

    database_url: str = "postgresql+asyncpg://alma:alma_dev_password@localhost:5432/alma_leads"
    secret_key: str = "local-dev-secret-key-not-for-production"
    access_token_expire_minutes: int = 60

    resend_api_key: str = ""  # set to enable email via Resend
    smtp_host: str = ""  # set to enable email via SMTP (e.g. smtp.gmail.com)
    smtp_port: int = 587
    smtp_user: str = ""
    smtp_password: str = ""
    smtp_use_tls: bool = True
    email_from: str = "noreply@alma.com"
    attorney_email: str = "attorney@alma.com"

    storage_backend: str = "local"  # "local" or "s3"
    upload_dir: str = "uploads"
    max_upload_size_mb: int = 10

    s3_bucket: str = ""
    s3_prefix: str = "resumes"
    s3_region: str = ""
    s3_endpoint_url: str = ""  # for S3-compatible services (MinIO, LocalStack)

    admin_email: str = ""
    admin_password: str = ""

    seed_attorney_email: str = ""
    seed_attorney_password: str = ""

    rate_limit_per_minute: int = 5
    rate_limit_per_hour: int = 20

    model_config = {"env_file": ".env", "extra": "ignore"}


settings = Settings()
