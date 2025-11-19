"""
Worker configuration and constants.
"""
import os
import boto3
import json
import logging
from typing import Optional
from dataclasses import dataclass

logger = logging.getLogger(__name__)


@dataclass
class WorkerConfig:
    """Worker configuration loaded from environment variables."""
    
    # Database
    db_secret_arn: str
    db_host: Optional[str] = None
    db_name: Optional[str] = None
    db_user: Optional[str] = None
    db_password: Optional[str] = None
    
    # Timeouts (seconds)
    whois_timeout: int = 30
    dns_timeout: int = 30
    http_timeout: int = 30
    mx_timeout: int = 30
    
    # Retry settings
    max_retries: int = 3
    
    # OpenAI configuration
    openai_api_key: Optional[str] = None
    openai_model: str = "gpt-4"
    openai_timeout: int = 30
    algorithm_version: str = "1.0.0"
    
    # Logging
    log_level: str = "INFO"
    environment: str = "development"
    
    # Rate limiting configuration
    openai_rate_limit: int = 3  # requests per second
    whois_rate_limit: int = 1
    dns_rate_limit: int = 5
    http_rate_limit: int = 10
    
    @classmethod
    def from_env(cls) -> "WorkerConfig":
        """Load configuration from environment variables."""
        # Try to get OpenAI API key from Secrets Manager or environment
        openai_api_key = os.getenv("OPENAI_API_KEY")
        openai_secret_arn = os.getenv("OPENAI_SECRET_ARN")
        
        if not openai_api_key and openai_secret_arn:
            try:
                secrets_client = boto3.client('secretsmanager', region_name=os.getenv('AWS_REGION', 'us-east-1'))
                response = secrets_client.get_secret_value(SecretId=openai_secret_arn)
                secret = json.loads(response['SecretString'])
                openai_api_key = secret.get('OPENAI_API_KEY') or secret.get('api_key')
                logger.info("Retrieved OpenAI API key from Secrets Manager")
            except Exception as e:
                logger.warning(f"Failed to retrieve OpenAI API key from Secrets Manager: {e}")
        
        return cls(
            db_secret_arn=os.getenv("DB_SECRET_ARN", ""),
            db_host=os.getenv("DB_HOST"),
            db_name=os.getenv("DB_NAME", "intellicheck"),
            db_user=os.getenv("DB_USER"),
            db_password=os.getenv("DB_PASSWORD"),
            whois_timeout=int(os.getenv("WHOIS_TIMEOUT", "30")),
            dns_timeout=int(os.getenv("DNS_TIMEOUT", "30")),
            http_timeout=int(os.getenv("HTTP_TIMEOUT", "30")),
            mx_timeout=int(os.getenv("MX_TIMEOUT", "30")),
            max_retries=int(os.getenv("MAX_RETRIES", "3")),
            openai_api_key=openai_api_key,
            openai_model=os.getenv("OPENAI_MODEL", "gpt-4"),
            openai_timeout=int(os.getenv("OPENAI_TIMEOUT", "30")),
            algorithm_version=os.getenv("ALGORITHM_VERSION", "1.0.0"),
            log_level=os.getenv("LOG_LEVEL", "INFO"),
            environment=os.getenv("ENVIRONMENT", "development"),
            openai_rate_limit=int(os.getenv("OPENAI_RATE_LIMIT", "3")),
            whois_rate_limit=int(os.getenv("WHOIS_RATE_LIMIT", "1")),
            dns_rate_limit=int(os.getenv("DNS_RATE_LIMIT", "5")),
            http_rate_limit=int(os.getenv("HTTP_RATE_LIMIT", "10")),
        )


# Rule weights from PRD Section 13
RULE_WEIGHTS = {
    "domain_age_lt_1_year": 20,
    "whois_privacy_enabled": 10,
    "address_mismatch": 15,
    "email_mismatch": 10,
    "phone_region_mismatch": 10,
    "website_unreachable": 25,
    "no_mx_records": 15,
}

