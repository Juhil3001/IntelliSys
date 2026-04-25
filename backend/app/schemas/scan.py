import datetime

from pydantic import BaseModel, Field

from app.models.scan import ScanStatus


class ScanRequest(BaseModel):
    project_id: int
    source_root: str | None = Field(
        default=None, description="Override path; default is project root_path"
    )
    with_snapshot: bool = Field(
        default=True,
        description="After scan, recompute issues and create snapshot (Git projects with no override use full pipeline)",
    )


class ScanRunOut(BaseModel):
    id: int
    project_id: int
    status: ScanStatus
    source_root: str
    started_at: datetime.datetime | None
    finished_at: datetime.datetime | None
    error_message: str | None

    model_config = {"from_attributes": True}
