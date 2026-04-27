from __future__ import annotations

from sqlalchemy import ForeignKey, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base


class ProjectDependency(Base):
    __tablename__ = "project_dependencies"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    scan_run_id: Mapped[int] = mapped_column(ForeignKey("scan_runs.id", ondelete="CASCADE"), index=True)
    ecosystem: Mapped[str] = mapped_column(String(32), nullable=False)  # npm, pip, etc.
    name: Mapped[str] = mapped_column(String(512), nullable=False)
    version: Mapped[str | None] = mapped_column(Text, nullable=True)

    scan_run: Mapped["ScanRun"] = relationship("ScanRun", back_populates="dependencies")
