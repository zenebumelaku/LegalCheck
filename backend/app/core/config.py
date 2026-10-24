from functools import lru_cache
from pathlib import Path
from typing import Literal, Optional

from pydantic import Field, SecretStr
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    app_name: str = "LegalCheck Ethiopia"
    api_v1_prefix: str = "/api/v1"
    database_url: Optional[str] = None
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
    max_contract_analysis_characters: int = Field(
        default=500_000,
        gt=0,
        le=2_000_000,
    )

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
