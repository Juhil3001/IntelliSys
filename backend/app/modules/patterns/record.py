from __future__ import annotations

import hashlib
import datetime

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models import IssuePattern


def record_issue_pattern(db: Session, project_id: int, issue_type: str, description: str, api_id: int | None) -> None:
    raw = f"{issue_type}|{api_id or ''}|{description[:240]}"
    fp = hashlib.sha256(raw.encode()).hexdigest()[:32]
    row = db.execute(
        select(IssuePattern).where(
            IssuePattern.project_id == project_id, IssuePattern.fingerprint == fp
        )
    ).scalar_one_or_none()
    if row:
        row.hit_count = (row.hit_count or 0) + 1
        row.last_seen_at = datetime.datetime.now(datetime.UTC)
        db.add(row)
    else:
        db.add(
            IssuePattern(
                project_id=project_id,
                fingerprint=fp,
                issue_type=issue_type,
                hit_count=1,
            )
        )
    db.commit()
