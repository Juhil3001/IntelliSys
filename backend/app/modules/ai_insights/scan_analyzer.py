from __future__ import annotations

import json
import logging
import math
import re
from datetime import UTC, datetime, timedelta
from typing import Any

from sqlalchemy import delete, func, select
from sqlalchemy.orm import Session

from app.core.config import get_settings
from app.models import Api, ApiCall, FileRecord, Issue, IssueSeverity, Project, ScanRun, ScanStatus, Snapshot
from app.modules.alerts.dispatch import dispatch_alert_webhook
from app.modules.change_detection.service import diff_snapshots
from app.modules.patterns.record import record_issue_pattern

logger = logging.getLogger(__name__)

_JSON_FENCE = re.compile(r"```(?:json)?\s*([\s\S]*?)```", re.I)


def _sever(s: str | None) -> IssueSeverity:
    if not s:
        return IssueSeverity.medium
    m = {x.value for x in IssueSeverity}
    sl = (s or "").strip().lower()
    if sl in m:
        return IssueSeverity(sl)
    return IssueSeverity.medium


def build_scan_context_for_llm(
    db: Session,
    project_id: int,
    scan: ScanRun,
    *,
    max_file_paths: int,
) -> dict[str, Any]:
    settings = get_settings()
    p = db.get(Project, project_id)
    files = list(
        db.execute(select(FileRecord).where(FileRecord.scan_run_id == scan.id)).scalars().all()
    )
    apis = list(db.execute(select(Api).where(Api.scan_run_id == scan.id)).scalars().all())
    paths_sorted = sorted(f.path for f in files)
    total_paths = len(paths_sorted)
    trimmed = paths_sorted[: max(0, max_file_paths)]

    api_rows: list[dict[str, Any]] = []
    from_ts = datetime.now(UTC) - timedelta(days=30)
    for a in apis:
        fr = db.get(FileRecord, a.file_id)
        path = fr.path if fr else ""
        q = select(ApiCall).where(ApiCall.api_id == a.id, ApiCall.timestamp >= from_ts)
        calls = list(db.execute(q).scalars().all())
        times = sorted(c.response_time_ms for c in calls)
        n_ct = len(times)
        p95 = (
            times[min(n_ct - 1, max(0, math.ceil(0.95 * n_ct) - 1))]
            if n_ct
            else None
        )
        err_n = sum(1 for c in calls if c.is_error)
        api_rows.append(
            {
                "id": a.id,
                "method": a.method,
                "endpoint": a.endpoint,
                "name": a.name,
                "file_path": path,
                "content_hash": a.content_hash,
                "call_count_30d": n_ct,
                "p95_ms_30d": round(p95, 1) if p95 is not None else None,
                "error_count_30d": err_n,
            }
        )

    snap_diff: dict[str, Any] | None = None
    snaps = list(
        db.execute(
            select(Snapshot)
            .where(Snapshot.project_id == project_id)
            .order_by(Snapshot.id.desc())
            .limit(2)
        )
        .scalars()
        .all()
    )
    if len(snaps) >= 2:
        snap_diff = diff_snapshots(snaps[1].data, snaps[0].data)

    return {
        "project": {
            "id": p.id if p else project_id,
            "name": p.name if p else "",
            "github_repo_url": (p.github_repo_url or "") if p else "",
        },
        "scan": {"id": scan.id, "source_root": scan.source_root},
        "totals": {
            "files": total_paths,
            "apis": len(apis),
            "file_paths_included": len(trimmed),
            "max_file_paths_setting": max_file_paths,
        },
        "file_paths_sample": trimmed,
        "apis": api_rows,
        "snapshot_vs_previous": snap_diff,
        "heuristic_settings": {
            "dead_api_days": settings.default_dead_api_days,
            "slow_p95_ms": settings.slow_api_p95_ms,
        },
    }


def _parse_json_response(text: str) -> dict[str, Any]:
    t = text.strip()
    m = _JSON_FENCE.search(t)
    if m:
        t = m.group(1).strip()
    return json.loads(t)


def generate_ai_issues_for_project(db: Session, project_id: int, scan: ScanRun) -> int:
    settings = get_settings()
    if not settings.openai_api_key_effective or not settings.ai_issues_enabled:
        return 0

    max_paths = max(32, settings.ai_max_file_paths)
    ctx = build_scan_context_for_llm(db, project_id, scan, max_file_paths=max_paths)
    raw = json.dumps(ctx, ensure_ascii=False)
    if len(raw) > 120_000:
        ctx["file_paths_sample"] = ctx.get("file_paths_sample", [])[: max_paths // 2]
        ctx["note"] = "Context trimmed for size"
        raw = json.dumps(ctx, ensure_ascii=False)

    try:
        from openai import OpenAI

        client = OpenAI(api_key=settings.openai_api_key_effective)
        resp = client.chat.completions.create(
            model=settings.ai_issues_model,
            response_format={"type": "json_object"},
            messages=[
                {
                    "role": "system",
                    "content": (
                        "You analyze API and codebase scan data. Respond with a single JSON object "
                        'with key "issues" only. Each issue: type (string, prefix ai_), description, '
                        "severity (low|medium|high|critical), api_id (must be an integer from the "
                        'provided apis[].id list, or null), evidence (object). Maximum 20 issues. '
                        "Focus on risks, missing auth hints, inconsistent patterns, performance, "
                        "and design smells. Do not invent api_id values that are not in apis[].id."
                    ),
                },
                {
                    "role": "user",
                    "content": raw,
                },
            ],
            max_tokens=4000,
        )
        text = (resp.choices[0].message.content or "").strip()
        data = _parse_json_response(text)
    except Exception as e:  # noqa: BLE001
        logger.warning("AI issues generation failed: %s", e)
        return 0

    items = data.get("issues")
    if not isinstance(items, list):
        return 0

    valid_api_ids = {a.id for a in db.execute(select(Api).where(Api.scan_run_id == scan.id)).scalars().all()}

    db.execute(delete(Issue).where(Issue.project_id == project_id, Issue.source == "ai"))
    db.commit()

    p = db.get(Project, project_id)
    if not p:
        return 0

    created: list[Issue] = []
    for it in items[:25]:
        if not isinstance(it, dict):
            continue
        desc = str(it.get("description") or "").strip()[:8000]
        if not desc:
            continue
        typ = str(it.get("type") or "ai_finding").strip()[:128]
        sev = _sever(str(it.get("severity") or "medium"))
        ev = it.get("evidence")
        if not isinstance(ev, dict):
            ev = {}
        api_id = it.get("api_id")
        if api_id is not None:
            try:
                aid = int(api_id)
            except (TypeError, ValueError):
                aid = None
            else:
                api_id = aid if aid in valid_api_ids else None
        else:
            api_id = None

        row = Issue(
            project_id=project_id,
            api_id=api_id,
            type=typ,
            description=desc,
            severity=sev,
            source="ai",
            evidence=ev,
            llm_model=settings.ai_issues_model,
        )
        db.add(row)
        created.append(row)

    db.commit()
    for row in created:
        db.refresh(row)
        record_issue_pattern(
            db,
            project_id,
            row.type,
            row.description,
            row.api_id,
        )

    alertables = [r for r in created if r.severity in (IssueSeverity.critical, IssueSeverity.high)]
    if alertables and p:
        dispatch_alert_webhook(p, alertables)

    return len(created)
