from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    database_url: str = "postgresql+asyncpg://alma:alma_dev_password@localhost:5432/alma_leads"
    secret_key: str = "local-dev-secret-key-not-for-production"
    access_token_expire_minutes: int = 60

    smtp_host: str = ""
    smtp_port: int = 587
    smtp_user: str = ""
    smtp_password: str = ""
    email_from: str = "noreply@alma.com"
    attorney_email: str = "attorney@alma.com"

    upload_dir: str = "uploads"
    max_upload_size_mb: int = 10

    storage_backend: str = "local"  # "local" or "s3"
    s3_bucket: str = ""
    s3_prefix: str = "resumes"
    s3_region: str = ""
    s3_endpoint_url: str = ""  # for S3-compatible services (MinIO, LocalStack)

    admin_email: str = ""
    admin_password: str = ""

    model_config = {"env_file": ".env", "extra": "ignore"}


settings = Settings()
