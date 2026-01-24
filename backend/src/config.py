"""Application configuration from environment variables.

Uses pydantic-settings for type-safe configuration with .env file support.
"""

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Application configuration from environment variables."""

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
    )

    # Database - use str instead of PostgresDsn for simpler default handling
    database_url: str = Field(
        default="postgresql+asyncpg://postgres:postgres@localhost:5432/loan_extraction",
        description="Async PostgreSQL connection URL",
    )
    db_pool_size: int = Field(default=20, ge=1, le=100)
    db_max_overflow: int = Field(default=10, ge=0, le=50)

    # Redis - use str instead of RedisDsn for simpler default handling
    redis_url: str = Field(
        default="redis://localhost:6379/0",
        description="Redis connection URL",
    )

    # API
    api_host: str = Field(default="0.0.0.0")
    api_port: int = Field(default=8000, ge=1, le=65535)
    debug: bool = Field(default=False)

    # Gemini (for later phases)
    gemini_api_key: str = Field(default="", description="Google AI API key")

    # GCS (for later phases)
    gcs_bucket: str = Field(default="", description="Google Cloud Storage bucket name")

    # Cloud Tasks configuration
    gcp_project_id: str = Field(default="", description="GCP project ID for Cloud Tasks")
    gcp_location: str = Field(default="us-central1", description="GCP region for Cloud Tasks queue")
    cloud_tasks_queue: str = Field(
        default="document-processing", description="Cloud Tasks queue name"
    )
    cloud_run_service_url: str = Field(
        default="", description="Cloud Run backend service URL for task callbacks"
    )
    cloud_run_service_account: str = Field(
        default="", description="Service account email for OIDC token"
    )


settings = Settings()
