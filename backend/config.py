from functools import lru_cache
from typing import Optional

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """
    Application settings loaded from environment variables or .env file.
    """

    # Database
    db_url: str

    # API
    api_version: str = "1.0.0"
    environment: str = "development"

    # Server
    host: str = "0.0.0.0"
    port: int = 8000

    # Authentication (AWS Cognito) - Optional for PR #4, required for PR #5+
    cognito_region: str = "us-east-1"
    cognito_user_pool_id: Optional[str] = None
    cognito_app_client_id: Optional[str] = None
    cognito_issuer: Optional[str] = None

    # Optional build metadata
    git_sha: Optional[str] = None
    build_timestamp: Optional[str] = None

    # SQS Configuration
    sqs_queue_url: str = ""
    aws_region: str = "us-east-1"

    # S3 Configuration
    s3_bucket_name: str = ""
    s3_upload_expiration: int = 3600  # Seconds; default 1 hour for uploads
    s3_download_expiration: int = 900  # Seconds; default 15 minutes for downloads
    
    # Rate Limiting Configuration
    openai_rate_limit: int = 3  # requests per second
    whois_rate_limit: int = 1   # requests per second
    dns_rate_limit: int = 5     # requests per second
    http_rate_limit: int = 10   # requests per second

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
    )

    @property
    def cognito_issuer_url(self) -> Optional[str]:
        """
        Resolve the Cognito issuer URL, deriving it from region and pool ID when
        not explicitly provided. Returns None if Cognito is not configured.
        """
        if not self.cognito_user_pool_id:
            return None

        if self.cognito_issuer:
            return self.cognito_issuer.rstrip("/")

        return (
            f"https://cognito-idp.{self.cognito_region}.amazonaws.com/"
            f"{self.cognito_user_pool_id}"
        )


@lru_cache
def get_settings() -> Settings:
    """
    Cached settings instance to avoid re-reading environment variables.
    """

    return Settings()

