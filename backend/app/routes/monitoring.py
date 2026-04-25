from pydantic import BaseModel, Field

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.db.session import get_db
from app.models import Api, ApiCall, Project

router = APIRouter()


class IngestItem(BaseModel):
    method: str = "GET"
    path: str
    response_time_ms: float = 0.0
    status_code: int = 200
    api_id: int


class IngestBody(BaseModel):
    project_id: int
    items: list[IngestItem] = Field(default_factory=list)


@router.post("/ingest", status_code=201)
def ingest_metrics(body: IngestBody, db: Session = Depends(get_db)) -> dict:
    p = db.get(Project, body.project_id)
    if not p:
        raise HTTPException(status_code=404, detail="Project not found")
    n = 0
    for it in body.items:
        a = db.get(Api, it.api_id)
        if not a:
            raise HTTPException(status_code=400, detail=f"Unknown api_id {it.api_id}")
        db.add(
            ApiCall(
                api_id=it.api_id,
                response_time_ms=it.response_time_ms,
                status_code=it.status_code,
                is_error=it.status_code >= 400,
                method=it.method,
                path=it.path,
                project_id=body.project_id,
            )
        )
        n += 1
    db.commit()
    return {"recorded": n}


@router.get("/calls", response_model=list[dict])
def list_calls(
    project_id: int = Query(...),
    limit: int = Query(100, le=2000),
    db: Session = Depends(get_db),
) -> list[dict]:
    p = db.get(Project, project_id)
    if not p:
        raise HTTPException(status_code=404, detail="Project not found")
    q = (
        select(ApiCall)
        .where(ApiCall.project_id == project_id)
        .order_by(ApiCall.id.desc())
        .limit(limit)
    )
    out = []
    for c in db.execute(q).scalars().all():
        out.append(
            {
                "id": c.id,
                "api_id": c.api_id,
                "response_time_ms": c.response_time_ms,
                "status_code": c.status_code,
                "method": c.method,
                "path": c.path,
                "timestamp": c.timestamp.isoformat() if c.timestamp else None,
            }
        )
    return out
