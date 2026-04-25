from datetime import datetime

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.db.session import get_db
from app.models import Issue, IssueSeverity, Project

router = APIRouter()

_SEVERITY_RANK: dict[str, int] = {
    IssueSeverity.critical.value: 0,
    IssueSeverity.high.value: 1,
    IssueSeverity.medium.value: 2,
    IssueSeverity.low.value: 3,
}


def _parse_ts(s: str | None) -> float:
    if not s:
        return 0.0
    try:
        return datetime.fromisoformat(s.replace("Z", "+00:00")).timestamp()
    except ValueError:
        return 0.0


@router.get("")
def list_alerts(
    project_id: int = Query(..., description="IntelliSys project id"),
    db: Session = Depends(get_db),
) -> dict:
    """
    Active alerts for a project: unresolved issues (dead API, slow API, etc.)
    with counts by severity. Sorted: more severe first, then newest first.
    """
    p = db.get(Project, project_id)
    if not p:
        raise HTTPException(status_code=404, detail="Project not found")
    q = select(Issue).where(Issue.project_id == project_id, Issue.resolved.is_(False))
    issues = list(db.execute(q).scalars().all())

    summary: dict[str, int] = {"critical": 0, "high": 0, "medium": 0, "low": 0, "total": 0}
    items: list[dict] = []
    for i in issues:
        sev = i.severity.value if i.severity else IssueSeverity.medium.value
        if sev in ("critical", "high", "medium", "low"):
            summary[sev] += 1
        items.append(
            {
                "id": i.id,
                "type": i.type,
                "description": i.description,
                "severity": sev,
                "api_id": i.api_id,
                "created_at": i.created_at.isoformat() if i.created_at else None,
            }
        )
    summary["total"] = len(issues)

    items.sort(
        key=lambda it: (
            _SEVERITY_RANK.get(it["severity"], 9),
            -_parse_ts(it.get("created_at")),
        )
    )

    return {"project_id": project_id, "summary": summary, "items": items}
