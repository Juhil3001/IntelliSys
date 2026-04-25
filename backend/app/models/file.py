from __future__ import annotations

from sqlalchemy import ForeignKey, String, Text, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base


class FileRecord(Base):
    __tablename__ = "files"
    __table_args__ = (UniqueConstraint("scan_run_id", "path", name="uq_files_scan_path"),)

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    scan_run_id: Mapped[int] = mapped_column(
        ForeignKey("scan_runs.id", ondelete="CASCADE"), index=True
    )
    file_name: Mapped[str] = mapped_column(String(1024), nullable=False)
    path: Mapped[str] = mapped_column(Text, nullable=False)  # relative to scan root
    content: Mapped[str] = mapped_column(Text, nullable=False, default="")

    scan_run: Mapped["ScanRun"] = relationship("ScanRun", back_populates="files")
    apis: Mapped[list["Api"]] = relationship("Api", back_populates="file", cascade="all, delete-orphan")
