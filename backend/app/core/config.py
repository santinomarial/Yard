from functools import lru_cache
from typing import Literal

from pydantic import Field, model_validator
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
    apns_team_id: str | None = None
    apns_key_id: str | None = None
    apns_private_key: str | None = None
    apns_bundle_id: str = "com.santinomarial.yard"
    apns_sandbox: bool = True
    rate_limit_enabled: bool = True
    max_request_bytes: int = 1_048_576
    trusted_proxy_ips: list[str] = Field(default_factory=list)

    @model_validator(mode="after")
    def validate_production_secrets(self) -> "Settings":
        if self.environment != "production":
            return self
        insecure = (
            len(self.access_token_secret) < 32
            or "development-only" in self.access_token_secret
            or len(self.verification_pepper) < 32
            or "development-only" in self.verification_pepper
            or "development-only" in self.s3_secret_key
            or "*" in self.cors_origins
        )
        if insecure:
            raise ValueError("Production secrets and CORS origins must be explicitly configured")
        return self


@lru_cache
def get_settings() -> Settings:
    return Settings()
