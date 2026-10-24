from functools import lru_cache
from pathlib import Path
from typing import Optional

from pydantic import Field
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
