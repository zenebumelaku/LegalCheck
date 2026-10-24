from functools import lru_cache
from pathlib import Path
from typing import Literal, Optional

from pydantic import Field, SecretStr, model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    app_name: str = "LegalCheck Ethiopia"
    app_environment: Literal["development", "test", "production"] = "development"
    api_v1_prefix: str = "/api/v1"
    database_url: Optional[str] = None
    redis_url: str = "redis://localhost:6379/0"
    cors_origins: list[str] = Field(default_factory=list)
    log_level: str = "INFO"
    access_token_expire_minutes: int = Field(default=60, gt=0, le=1440)
    max_upload_size_mb: int = Field(default=10, gt=0, le=100)
    max_docx_uncompressed_size_mb: int = Field(default=50, gt=0, le=500)
    private_storage_path: Path = Path("var/private-documents")
    ocr_enabled: bool = False
    embedding_provider: Literal["disabled", "openai_compatible"] = "disabled"
    embedding_api_url: Optional[str] = None
    embedding_api_key: Optional[SecretStr] = None
    embedding_model_name: str = Field(
        default="text-embedding-3-small",
        min_length=1,
        max_length=255,
    )
    embedding_model_version: str = Field(default="v1", min_length=1, max_length=100)
    llm_provider: Literal["disabled", "openai_compatible"] = "disabled"
    llm_api_url: Optional[str] = None
    llm_api_key: Optional[SecretStr] = None
    llm_model_name: str = Field(default="not-configured", min_length=1, max_length=255)
    llm_model_version: str = Field(default="v1", min_length=1, max_length=100)
    llm_timeout_seconds: int = Field(default=90, gt=0, le=300)
    audit_job_timeout_seconds: int = Field(default=1800, gt=0, le=7200)
    audit_stale_after_seconds: int = Field(default=2100, gt=0, le=14400)
    rate_limit_login_per_minute: int = Field(default=10, gt=0, le=1000)
    rate_limit_auth_per_minute: int = Field(default=10, gt=0, le=1000)
    rate_limit_upload_per_minute: int = Field(default=10, gt=0, le=1000)
    rate_limit_audit_per_minute: int = Field(default=5, gt=0, le=1000)
    max_contract_analysis_characters: int = Field(
        default=500_000,
        gt=0,
        le=2_000_000,
    )

    @model_validator(mode="after")
    def validate_audit_timeouts(self) -> "Settings":
        if self.audit_stale_after_seconds <= self.audit_job_timeout_seconds:
            raise ValueError(
                "AUDIT_STALE_AFTER_SECONDS must exceed AUDIT_JOB_TIMEOUT_SECONDS."
            )
        if "*" in self.cors_origins:
            raise ValueError("Wildcard CORS origins are not permitted.")
        return self

    @property
    def max_upload_size_bytes(self) -> int:
        return self.max_upload_size_mb * 1024 * 1024

    @property
    def max_docx_uncompressed_size_bytes(self) -> int:
        return self.max_docx_uncompressed_size_mb * 1024 * 1024

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )


@lru_cache
def get_settings() -> Settings:
    return Settings()


settings = get_settings()
