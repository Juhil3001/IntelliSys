from __future__ import annotations

import datetime
from typing import Any

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models import Api, ApiCall, FileRecord, Project, ScanRun, Snapshot


def build_snapshot_data(db: Session, project: Project, scan: ScanRun) -> dict[str, Any]:
    files = list(
        db.execute(select(FileRecord).where(FileRecord.scan_run_id == scan.id)).scalars()
    )
    apis = list(db.execute(select(Api).where(Api.scan_run_id == scan.id)).scalars())
    from_ts = datetime.datetime.now(datetime.UTC) - datetime.timedelta(days=30)
    call_stats: dict[str, list[float]] = {}
    for a in apis:
        q = select(ApiCall.response_time_ms).where(
            ApiCall.api_id == a.id, ApiCall.timestamp >= from_ts
        )
        times = [float(t[0]) for t in db.execute(q).all()]
        key = f"{a.method} {a.endpoint}"
        call_stats[key] = times
    return {
        "version": 1,
        "project_id": project.id,
        "scan_run_id": scan.id,
        "file_count": len(files),
        "api_list": [
            {
                "method": a.method,
                "endpoint": a.endpoint,
                "name": a.name,
                "file_id": a.file_id,
                "content_hash": a.content_hash,
            }
            for a in apis
        ],
        "file_paths": sorted(f.path for f in files),
        "call_stats_sample": {k: v[:5] for k, v in call_stats.items() if v},
    }


def create_snapshot(
    db: Session,
    project: Project,
    scan: ScanRun,
    name: str = "",
    label: str | None = None,
) -> Snapshot:
    data = build_snapshot_data(db, project, scan)
    s = Snapshot(
        project_id=project.id,
        scan_run_id=scan.id,
        name=name,
        data=data,
        label=label,
    )
    db.add(s)
    db.commit()
    db.refresh(s)
    return s


def diff_snapshots(
    old: dict[str, Any] | None, new: dict[str, Any] | None
) -> dict[str, Any]:
    if not old and not new:
        return {"added_apis": [], "removed_apis": [], "changed_files": 0, "updated_apis": []}
    if not old:
        new_apis = new.get("api_list", []) if new else []
        return {
            "added_apis": new_apis,
            "removed_apis": [],
            "changed_files": new.get("file_count", 0) if new else 0,
            "updated_apis": [],
        }
    if not new:
        return {
            "added_apis": [],
            "removed_apis": old.get("api_list", []),
            "changed_files": 0,
            "updated_apis": [],
        }
    oa = {(_a["method"], _a["endpoint"]): _a for _a in old.get("api_list", [])}
    na = {(_a["method"], _a["endpoint"]): _a for _a in new.get("api_list", [])}
    added = [na[k] for k in na if k not in oa]
    removed = [oa[k] for k in oa if k not in na]
    updated_apis: list[dict[str, Any]] = []
    for k in oa:
        if k in na:
            h0 = oa[k].get("content_hash")
            h1 = na[k].get("content_hash")
            if h0 and h1 and h0 != h1:
                updated_apis.append(
                    {
                        "method": k[0],
                        "endpoint": k[1],
                        "previous_hash": h0,
                        "current_hash": h1,
                    }
                )
    of = set(old.get("file_paths", []))
    nf = set(new.get("file_paths", []))
    changed_files = len(of.symmetric_difference(nf))
    return {
        "added_apis": added,
        "removed_apis": removed,
        "changed_files": changed_files,
        "updated_apis": updated_apis,
    }
