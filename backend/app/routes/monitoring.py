import datetime
import math
from collections import defaultdict

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


@router.get("/metrics")
def metrics_aggregate(
    project_id: int = Query(..., description="IntelliSys project id"),
    hours: int = Query(24 * 7, le=24 * 90, description="Lookback in hours (max ~90d)"),
    db: Session = Depends(get_db),
) -> list[dict]:
    """Per-API call counts, error rate, p95 and avg latency in the time window."""
    p = db.get(Project, project_id)
    if not p:
        raise HTTPException(status_code=404, detail="Project not found")
    since = datetime.datetime.now(datetime.UTC) - datetime.timedelta(hours=hours)
    q = (
        select(ApiCall)
        .where(ApiCall.project_id == project_id, ApiCall.timestamp >= since)
        .order_by(ApiCall.id).limit(50_000)
    )
    calls = list(db.execute(q).scalars().all())
    by_api: dict[int, list[float]] = defaultdict(list)
    err_n: dict[int, int] = defaultdict(int)
    for c in calls:
        by_api[c.api_id].append(float(c.response_time_ms))
        if c.is_error:
            err_n[c.api_id] += 1
    out: list[dict] = []
    for api_id, times in by_api.items():
        times.sort()
        n = len(times)
        p95 = times[min(n - 1, max(0, math.ceil(0.95 * n) - 1))] if n else 0.0
        out.append(
            {
                "api_id": api_id,
                "call_count": n,
                "error_count": err_n[api_id],
                "error_rate": err_n[api_id] / n if n else 0.0,
                "avg_response_ms": sum(times) / n if n else 0.0,
                "p95_response_ms": p95,
            }
        )
    return sorted(out, key=lambda r: r["api_id"])


@router.get("/error-summary")
def error_rate_summary(
    project_id: int = Query(...),
    hours: int = Query(24, le=24 * 30),
    db: Session = Depends(get_db),
) -> dict:
    p = db.get(Project, project_id)
    if not p:
        raise HTTPException(status_code=404, detail="Project not found")
    since = datetime.datetime.now(datetime.UTC) - datetime.timedelta(hours=hours)
    calls = list(
        db.execute(
            select(ApiCall).where(
                ApiCall.project_id == project_id, ApiCall.timestamp >= since
            )
        )
        .scalars()
        .all()
    )
    n = len(calls)
    err = sum(1 for c in calls if c.is_error)
    return {
        "project_id": project_id,
        "hours": hours,
        "total_calls": n,
        "error_count": err,
        "error_rate": err / n if n else 0.0,
    }
