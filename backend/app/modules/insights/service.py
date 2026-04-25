from __future__ import annotations

import datetime
import math

from sqlalchemy import delete, select
from sqlalchemy.orm import Session

from app.core.config import get_settings
from app.models import Api, ApiCall, Issue, IssueSeverity, Project, ScanRun, ScanStatus

settings = get_settings()


def recompute_issues_for_project(db: Session, project_id: int) -> int:
    """
    Marks dead (no recent calls) and slow (p95) APIs as issues. Clears old auto issues first.
    """
    p = db.get(Project, project_id)
    if not p:
        return 0
    sub = (
        select(ScanRun.id)
        .where(ScanRun.project_id == project_id, ScanRun.status == ScanStatus.completed)
        .order_by(ScanRun.id.desc())
        .limit(1)
    )
    row = db.execute(sub).first()
    if not row:
        return 0
    scan_id = row[0]
    apis = list(db.execute(select(Api).where(Api.scan_run_id == scan_id)).scalars().all())
    from_ts = datetime.datetime.now(datetime.UTC) - datetime.timedelta(days=settings.default_dead_api_days)
    n = 0
    db.execute(
        delete(Issue).where(
            Issue.project_id == project_id, Issue.type.in_(("dead_api", "slow_api"))
        )
    )
    for a in apis:
        qct = select(ApiCall).where(
            ApiCall.api_id == a.id,
            ApiCall.timestamp >= from_ts,
        )
        calls = list(db.execute(qct).scalars().all())
        key = f"{a.method} {a.endpoint}"
        if len(calls) == 0:
            db.add(
                Issue(
                    project_id=project_id,
                    api_id=a.id,
                    type="dead_api",
                    description=f"No calls recorded in the last {settings.default_dead_api_days} days for {key}",
                    severity=IssueSeverity.medium,
                )
            )
            n += 1
            continue
        times = sorted(c.response_time_ms for c in calls)
        n_ct = len(times)
        p95 = times[min(n_ct - 1, max(0, math.ceil(0.95 * n_ct) - 1))] if n_ct else 0.0
        if p95 > settings.slow_api_p95_ms:
            db.add(
                Issue(
                    project_id=project_id,
                    api_id=a.id,
                    type="slow_api",
                    description=(
                        f"p95 latency {p95:.0f}ms (threshold {settings.slow_api_p95_ms}ms) for {key}"
                    ),
                    severity=IssueSeverity.high,
                )
            )
            n += 1
    db.commit()
    return n
