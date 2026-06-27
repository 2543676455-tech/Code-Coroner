from functools import lru_cache

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    app_name: str = "RepoJudge"
    app_env: str = "development"
    database_url: str = "sqlite:///./repojudge.db"
    llm_base_url: str = ""
    llm_api_key: str = ""
    llm_model: str = ""
    cors_origins: str = "http://localhost:5173"
    max_concurrent_audits: int = Field(default=2, ge=1, le=8)
    max_queued_audits: int = Field(default=20, ge=1, le=1000)
    max_repository_mb: int = Field(default=100, ge=1, le=1000)
    max_repository_files: int = Field(default=20_000, ge=100, le=1_000_000)
    clone_timeout_seconds: int = Field(default=120, ge=10, le=600)
    analysis_timeout_seconds: int = Field(default=600, ge=30, le=3600)
    max_file_bytes: int = Field(default=524_288, ge=1024, le=5_242_880)
    sandbox_timeout_seconds: int = Field(default=300, ge=10, le=1800)
    sandbox_image: str = "repojudge-sandbox:py312-v1"
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    @property
    def llm_enabled(self) -> bool:
        return bool(self.llm_base_url and self.llm_api_key and self.llm_model)

    @property
    def cors_origin_list(self) -> list[str]:
        return [origin.strip() for origin in self.cors_origins.split(",") if origin.strip()]


@lru_cache
def get_settings() -> Settings:
    return Settings()
