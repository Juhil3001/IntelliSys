from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session

from app.db.session import get_db
from app.models import Project
from app.modules.insights import recompute_issues_for_project

router = APIRouter()


@router.post("/recompute")
def recompute(project_id: int = Query(...), db: Session = Depends(get_db)) -> dict:
    p = db.get(Project, project_id)
    if not p:
        raise HTTPException(status_code=404, detail="Project not found")
    n = recompute_issues_for_project(db, project_id)
    return {"issues_created": n}
