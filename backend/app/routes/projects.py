from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.config import get_settings
from app.db.session import get_db
from app.models import Project
from app.modules.project_pipeline import execute_project_scan_pipeline
from app.schemas.project import ProjectCreate, ProjectOut

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
