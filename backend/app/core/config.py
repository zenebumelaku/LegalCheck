import os
from functools import lru_cache
from pathlib import Path
from typing import Literal, Optional
from urllib.parse import urlsplit

from pydantic import EmailStr, Field, SecretStr, field_validator, model_validator
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
    password_reset_email_provider: Literal["disabled", "resend"] = "disabled"
    resend_api_key: Optional[SecretStr] = None
    password_reset_from_email: Optional[EmailStr] = None
    password_reset_frontend_url: str = "http://localhost:3000"
    password_reset_token_expire_minutes: int = Field(default=30, gt=0, le=1440)
    max_upload_size_mb: int = Field(default=10, gt=0, le=100)
    max_docx_uncompressed_size_mb: int = Field(default=50, gt=0, le=500)
    private_storage_path: Path = Path("var/private-documents")
    report_unicode_font_path: Optional[Path] = None
    ocr_enabled: bool = False
    embedding_provider: Literal[
        "disabled",
        "openai_compatible",
        "sentence_transformers",
    ] = "disabled"
    embedding_api_url: Optional[str] = None
    embedding_api_key: Optional[SecretStr] = None
    embedding_local_model_path: Optional[Path] = None
    embedding_model_name: str = Field(
        default="text-embedding-3-small",
        min_length=1,
        max_length=255,
    )
    embedding_model_version: str = Field(default="v1", min_length=1, max_length=100)
    legal_retrieval_mode: Literal["baseline", "hybrid"] = "hybrid"
    legal_retrieval_candidate_k: int = Field(default=20, gt=0, le=250)
    legal_retrieval_rrf_offset: int = Field(default=60, gt=0, le=1000)
    legal_qa_top_k: int = Field(default=5, gt=0, le=100)
    legal_reranker_enabled: bool = False
    legal_reranker_model_path: Optional[Path] = None
    legal_reranker_model_version: str = Field(
        default="v1",
        min_length=1,
        max_length=100,
    )
    llm_provider: Literal[
        "disabled",
        "openai_compatible",
        "ollama",
        "gemini",
    ] = "disabled"
    legal_qa_llm_provider: Optional[
        Literal["disabled", "openai_compatible", "ollama", "gemini"]
    ] = None
    llm_api_url: Optional[str] = None
    llm_api_key: Optional[SecretStr] = None
    llm_model_name: str = Field(default="not-configured", min_length=1, max_length=255)
    llm_model_version: str = Field(default="v1", min_length=1, max_length=100)
    contract_analysis_llm_provider: Optional[
        Literal["disabled", "openai_compatible", "ollama", "gemini"]
    ] = None
    llm_timeout_seconds: int = Field(default=90, gt=0, le=300)
    legal_qa_cache_version: str = Field(default="v1", min_length=1, max_length=100)
    legal_qa_cache_ttl_seconds: int = Field(default=3600, ge=0, le=2_592_000)
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

    @field_validator("report_unicode_font_path", mode="before")
    @classmethod
    def empty_report_font_path_is_unset(cls, value: object) -> object:
        return None if value == "" else value

    @field_validator("embedding_local_model_path", mode="before")
    @classmethod
    def empty_embedding_model_path_is_unset(cls, value: object) -> object:
        return None if value == "" else value

    @field_validator("legal_reranker_model_path", mode="before")
    @classmethod
    def empty_reranker_model_path_is_unset(cls, value: object) -> object:
        return None if value == "" else value

    @field_validator(
        "resend_api_key",
        "password_reset_from_email",
        "legal_qa_llm_provider",
        "contract_analysis_llm_provider",
        "llm_api_key",
        "llm_api_url",
        "embedding_api_key",
        "embedding_api_url",
        mode="before",
    )
    @classmethod
    def empty_password_reset_values_are_unset(cls, value: object) -> object:
        return None if value == "" else value

    @model_validator(mode="after")
    def validate_audit_timeouts(self) -> "Settings":
        if self.audit_stale_after_seconds <= self.audit_job_timeout_seconds:
            raise ValueError(
                "AUDIT_STALE_AFTER_SECONDS must exceed AUDIT_JOB_TIMEOUT_SECONDS."
            )
        if "*" in self.cors_origins:
            raise ValueError("Wildcard CORS origins are not permitted.")
        parsed_reset_url = urlsplit(self.password_reset_frontend_url)
        if (
            parsed_reset_url.scheme not in {"http", "https"}
            or not parsed_reset_url.netloc
            or parsed_reset_url.username
            or parsed_reset_url.password
            or parsed_reset_url.query
            or parsed_reset_url.fragment
        ):
            raise ValueError(
                "PASSWORD_RESET_FRONTEND_URL must be an HTTP(S) origin or base path."
            )
        if (
            self.app_environment == "production"
            and self.password_reset_email_provider == "resend"
            and parsed_reset_url.scheme != "https"
        ):
            raise ValueError(
                "PASSWORD_RESET_FRONTEND_URL must use HTTPS in production."
            )
        return self

    @property
    def max_upload_size_bytes(self) -> int:
        return self.max_upload_size_mb * 1024 * 1024

    @property
    def max_docx_uncompressed_size_bytes(self) -> int:
        return self.max_docx_uncompressed_size_mb * 1024 * 1024

    model_config = SettingsConfigDict(
        env_file=None if os.getenv("APP_ENVIRONMENT") == "test" else ".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )


@lru_cache
def get_settings() -> Settings:
    return Settings()


settings = get_settings()
