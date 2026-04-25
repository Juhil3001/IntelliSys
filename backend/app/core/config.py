import os
from functools import lru_cache
from pathlib import Path

from pydantic import AliasChoices, Field, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    database_url: str = "postgresql+psycopg2://postgres:password@127.0.0.1:5432/intellisys"

    @field_validator("database_url", mode="before")
    @classmethod
    def normalize_postgres_url(cls, v: object) -> object:
        """Render and others often use postgres:// or postgresql:// without a driver; require psycopg2."""
        if v is None or not isinstance(v, str):
            return v
        s = v.strip()
        if s.startswith("postgresql+") or s.lower().startswith("sqlite"):
            return s
        if s.startswith("postgres://"):
            return "postgresql+psycopg2://" + s[len("postgres://") :]
        if s.startswith("postgresql://"):
            return "postgresql+psycopg2://" + s[len("postgresql://") :]
        return s
    # Comma-separated; include 127.0.0.1 and localhost (browser treats them as different Origins)
    cors_origins: str = "http://localhost:4200,http://127.0.0.1:4200"
    # Extra allowed origins (e.g. custom domain for the static app). Comma-separated. Env: CORS_ADDITIONAL_ORIGINS
    cors_additional_origins: str = ""
    # Matches local dev OR any Render static/web *.onrender.com (HTTPS). Set to "" to disable regex.
    # For a custom domain front-end, add its exact https:// origin to cors_origins above.
    cors_origin_regex: str = (
        r"(^https?://(localhost|127\.0\.0\.1|0\.0\.0\.0)(:\d+)?$)|"
        r"(^https://[a-zA-Z0-9.-]+\.onrender\.com$)"
    )
    openai_api_key: str = ""
    automation_webhook_secret: str = "change-me-in-production"
    log_level: str = "INFO"
    default_dead_api_days: int = 14
    slow_api_p95_ms: int = 2000
    n8n_webhook_base: str = ""  # e.g. http://localhost:8000
    # Optional PAT for private GitHub repos; never commit. Set env GITHUB_TOKEN on Render.
    # AliasChoices: pydantic-settings does not always map GITHUB_TOKEN -> github_token without this.
    github_token: str = Field(
        default="",
        validation_alias=AliasChoices("GITHUB_TOKEN", "github_token"),
    )
    # Directory under which project workspaces (cloned repos) are stored; must be absolute on the server.
    workspace_base: str = ""
    # JWT (change in production)
    jwt_secret: str = "intellisys-dev-secret-change-in-production"
    jwt_algorithm: str = "HS256"
    jwt_exp_hours: int = 24 * 7

    @property
    def github_token_effective(self) -> str:
        """PAT for git clone; prefer explicit env if the field is empty (deploy quirks)."""
        t = (self.github_token or "").strip()
        if t:
            return t
        return (os.environ.get("GITHUB_TOKEN") or os.environ.get("github_token") or "").strip()

    @property
    def cors_origin_list(self) -> list[str]:
        parts: list[str] = [o.strip() for o in self.cors_origins.split(",") if o.strip()]
        if (self.cors_additional_origins or "").strip():
            parts.extend(
                o.strip() for o in self.cors_additional_origins.split(",") if o.strip()
            )
        seen: set[str] = set()
        out: list[str] = []
        for o in parts:
            if o not in seen:
                seen.add(o)
                out.append(o)
        return out

    @property
    def cors_origin_regex_effective(self) -> str | None:
        s = (self.cors_origin_regex or "").strip()
        return s if s else None

    @property
    def workspace_base_resolved(self) -> Path:
        if self.workspace_base.strip():
            return Path(self.workspace_base).resolve()
        return (Path(__file__).resolve().parent.parent.parent / "data" / "workspaces").resolve()


@lru_cache
def get_settings() -> Settings:
    return Settings()
