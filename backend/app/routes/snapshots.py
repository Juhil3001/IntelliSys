from pydantic import BaseModel

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.db.session import get_db
from app.models import Project, ScanRun, Snapshot
from app.modules.change_detection import create_snapshot, diff_snapshots

router = APIRouter()


class SnapshotCreate(BaseModel):
    project_id: int
    scan_run_id: int | None = None
    name: str = ""
    label: str | None = None


class DiffRequest(BaseModel):
    snapshot_a_id: int
    snapshot_b_id: int


@router.post("", status_code=201)
def create_snapshot_route(body: SnapshotCreate, db: Session = Depends(get_db)) -> dict:
    p = db.get(Project, body.project_id)
    if not p:
        raise HTTPException(status_code=404, detail="Project not found")
    if body.scan_run_id is not None:
        scan = db.get(ScanRun, body.scan_run_id)
        if not scan or scan.project_id != p.id:
            raise HTTPException(status_code=400, detail="Invalid scan_run_id")
    else:
        sub = (
            select(ScanRun)
            .where(ScanRun.project_id == p.id)
            .order_by(ScanRun.id.desc())
            .limit(1)
        )
        scan = db.execute(sub).scalar_one_or_none()
        if not scan:
            raise HTTPException(status_code=400, detail="No scan run for project")
    snap = create_snapshot(db, p, scan, name=body.name, label=body.label)
    return {"id": snap.id, "created_at": snap.created_at.isoformat() if snap.created_at else None}


@router.get("", response_model=list[dict])
def list_snapshots(
    project_id: int = Query(...), limit: int = Query(50, le=500), db: Session = Depends(get_db)
) -> list[dict]:
    q = (
        select(Snapshot)
        .where(Snapshot.project_id == project_id)
        .order_by(Snapshot.id.desc())
        .limit(limit)
    )
    out = []
    for s in db.execute(q).scalars().all():
        out.append(
            {
                "id": s.id,
                "project_id": s.project_id,
                "scan_run_id": s.scan_run_id,
                "name": s.name,
                "label": s.label,
                "created_at": s.created_at.isoformat() if s.created_at else None,
            }
        )
    return out


@router.post("/diff")
def snapshot_diff(body: DiffRequest, db: Session = Depends(get_db)) -> dict:
    a = db.get(Snapshot, body.snapshot_a_id)
    b = db.get(Snapshot, body.snapshot_b_id)
    if not a or not b:
        raise HTTPException(status_code=404, detail="Snapshot not found")
    return diff_snapshots(a.data, b.data)
