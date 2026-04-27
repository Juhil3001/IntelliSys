from __future__ import annotations

import datetime

from sqlalchemy import DateTime, String, Text, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base


class Project(Base):
    __tablename__ = "projects"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    root_path: Mapped[str] = mapped_column(Text, nullable=False)
    github_repo_url: Mapped[str | None] = mapped_column(Text, nullable=True)
    default_branch: Mapped[str] = mapped_column(String(255), nullable=False, default="main")
    last_commit_sha: Mapped[str | None] = mapped_column(String(64), nullable=True)
    last_sync_at: Mapped[datetime.datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    created_at: Mapped[datetime.datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )
    updated_at: Mapped[datetime.datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )
    alert_webhook_url: Mapped[str | None] = mapped_column(Text, nullable=True)
    github_app_installation_id: Mapped[str | None] = mapped_column(String(64), nullable=True)

    scan_runs: Mapped[list["ScanRun"]] = relationship(
        "ScanRun", back_populates="project", cascade="all, delete-orphan"
    )
    snapshots: Mapped[list["Snapshot"]] = relationship("Snapshot", back_populates="project")
    issues: Mapped[list["Issue"]] = relationship("Issue", back_populates="project")
    issue_patterns: Mapped[list["IssuePattern"]] = relationship(
        "IssuePattern", back_populates="project", cascade="all, delete-orphan"
    )
    chat_messages: Mapped[list["ChatMessage"]] = relationship(
        "ChatMessage", back_populates="project", cascade="all, delete-orphan"
    )
