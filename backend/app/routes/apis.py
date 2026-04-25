from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.db.session import get_db
from app.models import Api, Project, ScanRun, ScanStatus

router = APIRouter()


@router.get("")
def list_apis(
    project_id: int = Query(..., description="IntelliSys project id"),
    db: Session = Depends(get_db),
) -> list[dict]:
    p = db.get(Project, project_id)
    if not p:
        raise HTTPException(status_code=404, detail="Project not found")
    sub = (
        select(ScanRun.id)
        .where(ScanRun.project_id == project_id, ScanRun.status == ScanStatus.completed)
        .order_by(ScanRun.id.desc())
        .limit(1)
    )
    row = db.execute(sub).first()
    if not row:
        return []
    scan_id = row[0]
    q = select(Api).where(Api.scan_run_id == scan_id)
    out = []
    for a in db.execute(q).scalars().all():
        out.append(
            {
                "id": a.id,
                "name": a.name,
                "method": a.method,
                "endpoint": a.endpoint,
                "path_pattern": a.path_pattern,
                "file_id": a.file_id,
            }
        )
    return out
