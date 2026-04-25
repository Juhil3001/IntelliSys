from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.db.session import get_db
from app.models import Issue, Project

router = APIRouter()


@router.get("", response_model=list[dict])
def list_issues(
    project_id: int = Query(...),
    limit: int = Query(200, le=2000),
    db: Session = Depends(get_db),
) -> list[dict]:
    p = db.get(Project, project_id)
    if not p:
        raise HTTPException(status_code=404, detail="Project not found")
    q = (
        select(Issue)
        .where(Issue.project_id == project_id)
        .order_by(Issue.id.desc())
        .limit(limit)
    )
    out = []
    for i in db.execute(q).scalars().all():
        out.append(
            {
                "id": i.id,
                "type": i.type,
                "description": i.description,
                "severity": i.severity.value if i.severity else None,
                "resolved": i.resolved,
                "api_id": i.api_id,
                "created_at": i.created_at.isoformat() if i.created_at else None,
            }
        )
    return out
