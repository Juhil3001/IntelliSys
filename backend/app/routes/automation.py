import secrets
import time

from pydantic import BaseModel, Field

from fastapi import APIRouter, Depends, Header, HTTPException
from sqlalchemy.orm import Session

from app.core.config import get_settings
from app.db.session import get_db
from app.models import LogRecord, Project
from app.modules.project_pipeline import execute_project_scan_pipeline

settings = get_settings()
router = APIRouter()


class N8NWebhookBody(BaseModel):
    action: str = Field(default="ping", description="ping | daily_scan | full_scan")
    project_id: int | None = None
    with_snapshot: bool = True


@router.post("/n8n-webhook")
def n8n_webhook(
    body: N8NWebhookBody,
    x_intellisys_secret: str | None = Header(default=None, alias="X-IntelliSys-Secret"),
    db: Session = Depends(get_db),
) -> dict:
    if not x_intellisys_secret or not settings.automation_webhook_secret:
        raise HTTPException(status_code=401, detail="Secret required")
    if not _secrets_equal(x_intellisys_secret, settings.automation_webhook_secret):
        raise HTTPException(status_code=401, detail="Invalid secret")

    if body.action == "ping":
        return {"ok": True, "ts": int(time.time()), "pong": True}

    result: dict | None = None
    if body.action not in ("daily_scan", "full_scan"):
        db.add(
            LogRecord(
                message=f"automation webhook: unknown action {body.action}",
                level="warning",
            )
        )
        db.commit()
        raise HTTPException(status_code=400, detail="Use ping, daily_scan, or full_scan")

    if body.project_id is None:
        raise HTTPException(status_code=400, detail="project_id required for daily_scan/full_scan")
    p = db.get(Project, body.project_id)
    if not p:
        raise HTTPException(status_code=404, detail="Project not found")

    try:
        result = execute_project_scan_pipeline(
            db,
            p,
            with_snapshot=body.with_snapshot,
        )
    except ValueError as e:
        db.add(
            LogRecord(
                message=f"automation pipeline failed: {e}",
                level="error",
            )
        )
        db.commit()
        raise HTTPException(status_code=400, detail=str(e)) from e

    db.add(
        LogRecord(
            message=f"automation webhook: {body.action} project_id={body.project_id} result={result}",
            level="info",
        )
    )
    db.commit()
    return {"ok": True, "ts": int(time.time()), "result": result}


def _secrets_equal(a: str, b: str) -> bool:
    if len(a) != len(b):
        return False
    return secrets.compare_digest(a, b)
