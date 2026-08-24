from functools import lru_cache
from typing import Literal

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_prefix="YARD_", env_file=".env", extra="ignore")

    environment: Literal["development", "test", "production"] = "development"
    log_level: str = "INFO"
    database_url: str = "postgresql+asyncpg://yard:yard@localhost:5432/yard"
    redis_url: str = "redis://localhost:6379/0"
    api_prefix: str = "/api/v1"
    cors_origins: list[str] = Field(default_factory=lambda: ["http://localhost:3000"])
    apple_audience: str = "com.santinomarial.yard"
    access_token_secret: str = "development-only-access-secret-change-me"
    verification_pepper: str = "development-only-verification-pepper-change-me"
    allowed_harvard_domains: list[str] = Field(
        default_factory=lambda: ["harvard.edu", "college.harvard.edu", "g.harvard.edu"]
    )
    verification_code_minutes: int = 10
    s3_public_endpoint: str = "http://localhost:9000"
    s3_internal_endpoint: str = "http://localhost:9000"
    s3_access_key: str = "yard"
    s3_secret_key: str = "yard-development-only"
    s3_region: str = "us-east-1"
    s3_bucket: str = "yard"
    asset_base_url: str = "http://localhost:9000/yard"
    upload_expiration_seconds: int = 900
    analytics_enabled: bool = True


@lru_cache
def get_settings() -> Settings:
    return Settings()
