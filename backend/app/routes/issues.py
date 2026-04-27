import re

import httpx
from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel, Field
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.config import get_settings
from app.db.session import get_db
from app.models import Issue, Project

router = APIRouter()


class IssueResolvedPatch(BaseModel):
    resolved: bool = Field(..., description="Whether the issue is resolved (dismissed from alerts).")

_GH_REPO = re.compile(r"github\.com[:/]([^/]+)/([^/\.]+)", re.I)


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
                "source": getattr(i, "source", "heuristic") or "heuristic",
                "evidence": getattr(i, "evidence", None),
                "llm_model": getattr(i, "llm_model", None),
                "external_url": getattr(i, "external_url", None),
            }
        )
    return out


@router.patch("/{issue_id}", response_model=dict)
def patch_issue(
    issue_id: int,
    body: IssueResolvedPatch,
    db: Session = Depends(get_db),
) -> dict:
    """Mark an issue resolved or reopen it (alerts list only shows unresolved)."""
    issue = db.get(Issue, issue_id)
    if not issue:
        raise HTTPException(status_code=404, detail="Issue not found")
    issue.resolved = body.resolved
    db.add(issue)
    db.commit()
    db.refresh(issue)
    return {
        "id": issue.id,
        "type": issue.type,
        "description": issue.description,
        "severity": issue.severity.value if issue.severity else None,
        "resolved": issue.resolved,
        "api_id": issue.api_id,
        "created_at": issue.created_at.isoformat() if issue.created_at else None,
        "source": getattr(issue, "source", "heuristic") or "heuristic",
        "evidence": getattr(issue, "evidence", None),
        "llm_model": getattr(issue, "llm_model", None),
        "external_url": getattr(issue, "external_url", None),
    }


@router.post("/{issue_id}/github-export")
def export_issue_to_github(
    issue_id: int,
    db: Session = Depends(get_db),
) -> dict:
    """Create a GitHub issue in the linked repository (uses server GITHUB_TOKEN)."""
    settings = get_settings()
    tok = settings.github_token_effective
    if not tok:
        raise HTTPException(status_code=400, detail="Server GITHUB_TOKEN is not configured")
    issue = db.get(Issue, issue_id)
    if not issue:
        raise HTTPException(status_code=404, detail="Issue not found")
    proj = issue.project
    if not proj or not proj.github_repo_url:
        raise HTTPException(status_code=400, detail="Project has no github_repo_url")
    m = _GH_REPO.search(proj.github_repo_url)
    if not m:
        raise HTTPException(status_code=400, detail="Could not parse GitHub owner/repo from URL")
    owner, repo = m.group(1), m.group(2)
    url = f"https://api.github.com/repos/{owner}/{repo}/issues"
    body = {
        "title": f"[IntelliSys] {issue.type}"[:256],
        "body": (issue.description or "")[:60000],
    }
    try:
        r = httpx.post(
            url,
            json=body,
            headers={
                "Authorization": f"Bearer {tok}",
                "Accept": "application/vnd.github+json",
            },
            timeout=30.0,
        )
    except httpx.HTTPError as e:
        raise HTTPException(status_code=502, detail=str(e)) from e
    if r.status_code not in (200, 201):
        raise HTTPException(status_code=502, detail=r.text[:800])
    data = r.json()
    issue.external_url = data.get("html_url")
    db.add(issue)
    db.commit()
    return {
        "html_url": issue.external_url,
        "github_number": data.get("number"),
        "issue_id": issue.id,
    }
