from pydantic import model_validator
from pydantic_settings import BaseSettings

_DEFAULT_SECRET_KEY = "local-dev-secret-key-not-for-production"


class Settings(BaseSettings):
    environment: str = "development"  # "development", "staging", "production"

    database_url: str = "postgresql+asyncpg://alma_app:alma_app_dev_password@localhost:5432/alma_leads"
    database_admin_url: str = "postgresql+asyncpg://alma:alma_dev_password@localhost:5432/alma_leads"
    secret_key: str = _DEFAULT_SECRET_KEY
    access_token_expire_minutes: int = 60

    @model_validator(mode="after")
    def _reject_default_secret_in_production(self) -> "Settings":
        if self.environment != "development" and self.secret_key == _DEFAULT_SECRET_KEY:
            raise ValueError(
                f"SECRET_KEY must be set to a strong, unique value in "
                f"'{self.environment}' — the default dev key is not allowed "
                f"outside the development environment."
            )
        return self

    cors_origins: str = "http://localhost:3000,http://localhost:5173,http://localhost:8080"

    @property
    def cors_origin_list(self) -> list[str]:
        return [o.strip() for o in self.cors_origins.split(",") if o.strip()]

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
