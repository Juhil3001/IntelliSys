from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.db.session import get_db
from app.models import AiInsight, Project
from app.modules.ai_engine import generate_insight_for_project

router = APIRouter()


@router.post("/generate")
def generate(
    project_id: int = Query(...),
    db: Session = Depends(get_db),
) -> dict:
    p = db.get(Project, project_id)
    if not p:
        raise HTTPException(status_code=404, detail="Project not found")
    try:
        ins = generate_insight_for_project(db, project_id)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e)) from e
    return {
        "id": ins.id,
        "summary": ins.summary,
        "recommendation": ins.recommendation,
        "model": ins.model,
    }


@router.get("/latest")
def latest(
    project_id: int = Query(...),
    db: Session = Depends(get_db),
) -> dict:
    p = db.get(Project, project_id)
    if not p:
        raise HTTPException(status_code=404, detail="Project not found")
    q = (
        select(AiInsight)
        .where(AiInsight.project_id == project_id)
        .order_by(AiInsight.id.desc())
        .limit(1)
    )
    ins = db.execute(q).scalar_one_or_none()
    if not ins:
        return {"summary": None, "recommendation": None}
    return {
        "id": ins.id,
        "summary": ins.summary,
        "recommendation": ins.recommendation,
        "model": ins.model,
    }
