import datetime
from typing import Any

from pydantic import BaseModel, Field, model_validator


class ProjectCreate(BaseModel):
    name: str = Field(min_length=1, max_length=255)
    root_path: str | None = Field(
        default=None, description="Absolute path to local source (when not using GitHub sync only)"
    )
    github_repo_url: str | None = Field(default=None, description="https://github.com/org/repo or git@github.com:org/repo")
    default_branch: str = Field(default="main", max_length=255)

    @model_validator(mode="after")
    def require_source(self) -> Any:
        if not (self.root_path and self.root_path.strip()) and not (
            self.github_repo_url and self.github_repo_url.strip()
        ):
            raise ValueError("Provide root_path (local project) and/or github_repo_url")
        return self


class ProjectOut(BaseModel):
    id: int
    name: str
    root_path: str
    github_repo_url: str | None = None
    default_branch: str = "main"
    last_commit_sha: str | None = None
    last_sync_at: datetime.datetime | None = None

    model_config = {"from_attributes": True}
