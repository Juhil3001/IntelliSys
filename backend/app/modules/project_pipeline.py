"""Orchestrates Git sync, scan, recompute, and optional snapshot for a project."""

from __future__ import annotations

import datetime
from typing import Any

from sqlalchemy.orm import Session as OrmSession

from app.core.config import get_settings
from app.models import Project, ScanRun, ScanStatus
from app.modules.ai_insights import generate_ai_issues_for_project
from app.modules.change_detection import create_snapshot
from app.modules.git_sync.service import GitSyncError, ensure_path_in_workspace, sync_repo_to_path
from app.modules.insights.service import recompute_issues_for_project
from app.modules.post_scan import run_post_scan_artifacts
from app.modules.scanner.service import run_scan


def finalize_completed_scan(
    db: OrmSession,
    project: Project,
    run: ScanRun,
    *,
    with_snapshot: bool = True,
) -> tuple[int, int, int | None]:
    """
    Post-scan: artifacts, heuristic issues, AI issues, optional snapshot.
    Returns (issues_recomputed, ai_issues_created, snapshot_id or None).
    """
    settings = get_settings()
    issues_n = 0
    ai_n = 0
    snap_id: int | None = None
    if run.status != ScanStatus.completed:
        return 0, 0, None
    r0 = db.get(ScanRun, run.id)
    if r0:
        run_post_scan_artifacts(db, r0)
    if settings.use_heuristic_issues:
        issues_n = recompute_issues_for_project(db, project.id)
    if settings.openai_api_key_effective and settings.ai_issues_enabled:
        r_scan = db.get(ScanRun, run.id)
        if r_scan:
            ai_n = generate_ai_issues_for_project(db, project.id, r_scan)
    if with_snapshot:
        p2 = db.get(Project, project.id)
        r2 = db.get(ScanRun, run.id)
        if p2 and r2:
            snap = create_snapshot(db, p2, r2, name="pipeline", label="automation")
            snap_id = snap.id
    return issues_n, ai_n, snap_id


def execute_project_scan_pipeline(
    db: OrmSession,
    project: Project,
    *,
    with_snapshot: bool = True,
) -> dict[str, Any]:
    """
    For GitHub-backed projects: sync repo, update metadata, scan, recompute issues, optional snapshot.
    For local-only projects: scan `root_path`, recompute, optional snapshot.
    """
    settings = get_settings()
    ws = settings.workspace_base_resolved

    if project.github_repo_url:
        # Public repos clone over HTTPS without a token. Private repos need GITHUB_TOKEN on the server.
        dest = ws / "projects" / str(project.id) / "repo"
        ensure_path_in_workspace(dest, ws)
        try:
            sha = sync_repo_to_path(
                project.github_repo_url,
                (project.default_branch or "main").strip() or "main",
                dest,
                settings.github_token_effective,
            )
        except GitSyncError as e:
            raise ValueError(str(e)) from e
        project.last_commit_sha = sha
        project.last_sync_at = datetime.datetime.now(datetime.UTC)
        project.root_path = str(dest.resolve())
        db.add(project)
        db.commit()
        scan_root = str(dest.resolve())
    else:
        scan_root = project.root_path

    run = run_scan(db, project, scan_root)
    issues_n, ai_n, snap_id = finalize_completed_scan(
        db, project, run, with_snapshot=with_snapshot
    )
    pf = db.get(Project, project.id)
    return {
        "scan_run_id": run.id,
        "scan_status": run.status.value,
        "issues_recomputed": issues_n,
        "ai_issues_created": ai_n,
        "snapshot_id": snap_id,
        "last_commit_sha": pf.last_commit_sha if pf else None,
    }
