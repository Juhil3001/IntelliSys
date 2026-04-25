from __future__ import annotations

import datetime

from sqlalchemy import Boolean, DateTime, Float, ForeignKey, Integer, String, Text, func
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base


class ApiCall(Base):
    __tablename__ = "api_calls"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    api_id: Mapped[int] = mapped_column(ForeignKey("apis.id", ondelete="CASCADE"), index=True)
    timestamp: Mapped[datetime.datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), index=True
    )
    response_time_ms: Mapped[float] = mapped_column(Float, default=0.0)
    status_code: Mapped[int | None] = mapped_column(Integer, nullable=True)
    is_error: Mapped[bool] = mapped_column(Boolean, default=False)
    # Denormalized for analytics when API row is from older scan
    method: Mapped[str | None] = mapped_column(String(32), nullable=True, index=True)
    path: Mapped[str | None] = mapped_column(Text, nullable=True)
    project_id: Mapped[int | None] = mapped_column(
        ForeignKey("projects.id", ondelete="SET NULL"), nullable=True, index=True
    )
    extra: Mapped[dict | None] = mapped_column(JSONB, nullable=True)

    api: Mapped["Api"] = relationship("Api", back_populates="calls")
