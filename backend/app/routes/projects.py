from typing import Any

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.config import get_settings
from app.db.session import get_db
from app.models import IssuePattern, Project, ScanRun, ScanStatus, Snapshot
from app.modules.project_pipeline import execute_project_scan_pipeline
from app.schemas.project import ProjectCreate, ProjectOut, ProjectPatch

router = APIRouter()
settings = get_settings()


@router.get("", response_model=list[ProjectOut])
def list_projects(db: Session = Depends(get_db)) -> list[Project]:
    return list(db.execute(select(Project).order_by(Project.id.desc())).scalars().all())


@router.post("", response_model=ProjectOut, status_code=status.HTTP_201_CREATED)
def create_project(body: ProjectCreate, db: Session = Depends(get_db)) -> Project:
    if body.github_repo_url and body.github_repo_url.strip():
        existing = db.execute(
            select(Project).where(Project.github_repo_url == body.github_repo_url.strip())
        ).scalar_one_or_none()
        if existing:
            return existing
    if body.root_path and body.root_path.strip():
        existing = db.execute(
            select(Project).where(Project.root_path == body.root_path.strip())
        ).scalar_one_or_none()
        if existing:
            return existing

    branch = (body.default_branch or "main").strip() or "main"
    if body.github_repo_url and body.github_repo_url.strip():
        p = Project(
            name=body.name.strip(),
            github_repo_url=body.github_repo_url.strip(),
            default_branch=branch,
            root_path="",
        )
        db.add(p)
        db.flush()
        p.root_path = str(settings.workspace_base_resolved / "projects" / str(p.id) / "repo")
    else:
        p = Project(
            name=body.name.strip(),
            github_repo_url=None,
            default_branch=branch,
            root_path=(body.root_path or "").strip(),
        )
        db.add(p)
    db.commit()
    db.refresh(p)
    return p


@router.get("/{project_id}", response_model=ProjectOut)
def get_project(project_id: int, db: Session = Depends(get_db)) -> Project:
    p = db.get(Project, project_id)
    if not p:
        raise HTTPException(status_code=404, detail="Project not found")
    return p


@router.patch("/{project_id}", response_model=ProjectOut)
def patch_project(
    project_id: int, body: ProjectPatch, db: Session = Depends(get_db)
) -> Project:
    p = db.get(Project, project_id)
    if not p:
        raise HTTPException(status_code=404, detail="Project not found")
    if body.alert_webhook_url is not None:
        p.alert_webhook_url = body.alert_webhook_url.strip() or None
    if body.github_app_installation_id is not None:
        p.github_app_installation_id = (body.github_app_installation_id or "").strip() or None
    db.add(p)
    db.commit()
    db.refresh(p)
    return p


@router.get("/{project_id}/timeline")
def project_timeline(
    project_id: int, limit: int = 50, db: Session = Depends(get_db)
) -> dict[str, Any]:
    p = db.get(Project, project_id)
    if not p:
        raise HTTPException(status_code=404, detail="Project not found")
    snaps = list(
        db.execute(
            select(Snapshot)
            .where(Snapshot.project_id == project_id)
            .order_by(Snapshot.id.desc())
            .limit(max(1, min(limit, 200)))
        )
        .scalars()
        .all()
    )
    timeline = []
    for s in reversed(snaps):
        d = s.data or {}
        api_list = d.get("api_list") or []
        timeline.append(
            {
                "snapshot_id": s.id,
                "created_at": s.created_at.isoformat() if s.created_at else None,
                "scan_run_id": s.scan_run_id,
                "file_count": d.get("file_count", 0),
                "api_count": len(api_list),
            }
        )
    patterns = list(
        db.execute(
            select(IssuePattern)
            .where(IssuePattern.project_id == project_id)
            .order_by(IssuePattern.hit_count.desc())
            .limit(50)
        )
        .scalars()
        .all()
    )
    return {
        "project_id": project_id,
        "snapshots": timeline,
        "recurring_patterns": [
            {
                "issue_type": x.issue_type,
                "fingerprint": x.fingerprint,
                "hit_count": x.hit_count,
                "last_seen_at": x.last_seen_at.isoformat() if x.last_seen_at else None,
            }
            for x in patterns
        ],
    }


@router.get("/{project_id}/graph")
def project_graph(project_id: int, db: Session = Depends(get_db)) -> dict[str, Any]:
    p = db.get(Project, project_id)
    if not p:
        raise HTTPException(status_code=404, detail="Project not found")
    sub = (
        select(ScanRun)
        .where(ScanRun.project_id == project_id, ScanRun.status == ScanStatus.completed)
        .order_by(ScanRun.id.desc())
        .limit(1)
    )
    run = db.execute(sub).scalar_one_or_none()
    if not run or not run.artifacts:
        return {
            "project_id": project_id,
            "nodes": [],
            "import_sample": [],
            "summary": None,
        }
    art = run.artifacts
    return {
        "project_id": project_id,
        "scan_run_id": run.id,
        "nodes": art.get("nodes") or [],
        "import_sample": (art.get("import_edges") or [])[:200],
        "summary": art.get("summary"),
    }


@router.delete("/{project_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_project(project_id: int, db: Session = Depends(get_db)) -> None:
    p = db.get(Project, project_id)
    if not p:
        raise HTTPException(status_code=404, detail="Project not found")
    db.delete(p)
    db.commit()


@router.post("/{project_id}/sync-and-scan", response_model=dict)
def sync_and_scan(
    project_id: int,
    with_snapshot: bool = True,
    db: Session = Depends(get_db),
) -> dict:
    """Manually run Git sync (if configured), full scan, recompute issues, and optional snapshot."""
    p = db.get(Project, project_id)
    if not p:
        raise HTTPException(status_code=404, detail="Project not found")
    try:
        return execute_project_scan_pipeline(db, p, with_snapshot=with_snapshot)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e)) from e
