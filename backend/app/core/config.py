from functools import lru_cache
from pathlib import Path

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    database_url: str = "postgresql+psycopg2://postgres:password@127.0.0.1:5432/intellisys"
    cors_origins: str = "http://localhost:4200"
    openai_api_key: str = ""
    automation_webhook_secret: str = "change-me-in-production"
    log_level: str = "INFO"
    default_dead_api_days: int = 14
    slow_api_p95_ms: int = 2000
    n8n_webhook_base: str = ""  # e.g. http://localhost:8000
    # Optional PAT for private GitHub repos; never commit. Used only for git fetch/clone on the API host.
    github_token: str = ""
    # Directory under which project workspaces (cloned repos) are stored; must be absolute on the server.
    workspace_base: str = ""

    @property
    def cors_origin_list(self) -> list[str]:
        return [o.strip() for o in self.cors_origins.split(",") if o.strip()]

    @property
    def workspace_base_resolved(self) -> Path:
        if self.workspace_base.strip():
            return Path(self.workspace_base).resolve()
        return (Path(__file__).resolve().parent.parent.parent / "data" / "workspaces").resolve()


@lru_cache
def get_settings() -> Settings:
    return Settings()
