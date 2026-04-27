from __future__ import annotations

from sqlalchemy import ForeignKey, String, Text, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base


class Api(Base):
    __tablename__ = "apis"
    __table_args__ = (
        UniqueConstraint(
            "scan_run_id",
            "method",
            "endpoint",
            "file_id",
            name="uq_api_scan_method_endpoint_file",
        ),
    )

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    scan_run_id: Mapped[int] = mapped_column(
        ForeignKey("scan_runs.id", ondelete="CASCADE"), index=True
    )
    file_id: Mapped[int] = mapped_column(ForeignKey("files.id", ondelete="CASCADE"), index=True)
    name: Mapped[str] = mapped_column(String(512), default="")
    method: Mapped[str] = mapped_column(String(32), default="GET")
    endpoint: Mapped[str] = mapped_column(Text, nullable=False)
    # Optional: router prefix + path for display
    path_pattern: Mapped[str | None] = mapped_column(Text, nullable=True)
    content_hash: Mapped[str | None] = mapped_column(String(64), nullable=True, index=True)

    scan_run: Mapped["ScanRun"] = relationship("ScanRun", back_populates="apis")
    file: Mapped["FileRecord"] = relationship("FileRecord", back_populates="apis")
    calls: Mapped[list["ApiCall"]] = relationship(
        "ApiCall", back_populates="api", cascade="all, delete-orphan"
    )
