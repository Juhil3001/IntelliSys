from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.db.session import get_db
from app.models import Project, ScanRun
from app.modules.project_pipeline import execute_project_scan_pipeline, finalize_completed_scan
from app.modules.scanner import run_scan
from app.schemas.scan import ScanRequest, ScanRunOut

router = APIRouter()


@router.post("", response_model=ScanRunOut, status_code=201)
def start_scan(body: ScanRequest, db: Session = Depends(get_db)) -> ScanRun:
    p = db.get(Project, body.project_id)
    if not p:
        raise HTTPException(status_code=404, detail="Project not found")

    if p.github_repo_url and body.source_root is None:
        try:
            out = execute_project_scan_pipeline(
                db, p, with_snapshot=body.with_snapshot
            )
        except ValueError as e:
            raise HTTPException(status_code=400, detail=str(e)) from e
        run = db.get(ScanRun, out["scan_run_id"])
        if not run:
            raise HTTPException(status_code=500, detail="Scan run missing after pipeline")
        return run

    root = body.source_root or p.root_path
    try:
        run = run_scan(db, p, root)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e)) from e
    finalize_completed_scan(db, p, run, with_snapshot=body.with_snapshot)
    r2 = db.get(ScanRun, run.id)
    if not r2:
        raise HTTPException(status_code=500, detail="Scan run missing after finalize")
    return r2


@router.get("/{scan_id}", response_model=ScanRunOut)
def get_scan(scan_id: int, db: Session = Depends(get_db)) -> ScanRun:
    s = db.get(ScanRun, scan_id)
    if not s:
        raise HTTPException(status_code=404, detail="Scan not found")
    return s


@router.get("", response_model=list[ScanRunOut])
def list_scans(project_id: int | None = None, db: Session = Depends(get_db)) -> list[ScanRun]:
    q = select(ScanRun).order_by(ScanRun.id.desc())
    if project_id is not None:
        q = q.where(ScanRun.project_id == project_id)
    return list(db.execute(q).scalars().all())
