from __future__ import annotations

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.core.config import get_settings
from app.models import AiInsight, Api, ApiCall, Issue, Project, ScanRun, ScanStatus, Snapshot
from app.modules.change_detection.service import diff_snapshots

settings = get_settings()


def build_project_context(db: Session, project_id: int) -> str:
    p = db.get(Project, project_id)
    if not p:
        return ""
    sub = (
        select(ScanRun)
        .where(ScanRun.project_id == project_id, ScanRun.status == ScanStatus.completed)
        .order_by(ScanRun.id.desc())
        .limit(1)
    )
    scan = db.execute(sub).scalar_one_or_none()
    if not scan:
        return f"Project: {p.name}\nRoot: {p.root_path}\nNo completed scans."
    apis = list(db.execute(select(Api).where(Api.scan_run_id == scan.id)).scalars().all())
    issues = list(
        db.execute(
            select(Issue)
            .where(Issue.project_id == project_id, Issue.resolved.is_(False))
            .order_by(Issue.id.desc())
            .limit(30)
        )
        .scalars()
        .all()
    )
    # Sample recent calls count per API
    lines = [
        f"Project: {p.name}",
        f"Root: {p.root_path}",
        f"Latest scan: {scan.id}, APIs: {len(apis)}",
    ]
    for a in apis[:40]:
        n = (
            db.execute(
                select(func.count())
                .select_from(ApiCall)
                .where(ApiCall.api_id == a.id)
            ).scalar()
            or 0
        )
        err_n = (
            db.execute(
                select(func.count())
                .select_from(ApiCall)
                .where(ApiCall.api_id == a.id, ApiCall.is_error.is_(True))
            ).scalar()
            or 0
        )
        h = a.content_hash or "n/a"
        lines.append(
            f"- {a.method} {a.endpoint} (total calls: {n}, errors: {err_n}, hash: {h})"
        )
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
        d = diff_snapshots(snaps[1].data, snaps[0].data)
        upd = d.get("updated_apis") or []
        lines.append(
            f"Snapshot diff: {len(d.get('added_apis', []))} added, "
            f"{len(d.get('removed_apis', []))} removed, "
            f"{len(upd)} APIs with changed hash, changed_files={d.get('changed_files', 0)}"
        )
    lines.append("Open issues:")
    for i in issues:
        src = getattr(i, "source", "heuristic") or "heuristic"
        lines.append(f"- [{i.severity}] ({src}) {i.type}: {i.description[:200]}")
    return "\n".join(lines)


def generate_insight_for_project(db: Session, project_id: int) -> AiInsight:
    p = db.get(Project, project_id)
    if not p:
        raise ValueError("Project not found")
    context = build_project_context(db, project_id)
    summary = "Set OPENAI_API_KEY to generate AI insights."
    rec = "Configure the OpenAI API key in your environment, then re-run this endpoint."
    model_name = "none"

    if settings.openai_api_key_effective:
        try:
            from openai import OpenAI

            client = OpenAI(api_key=settings.openai_api_key_effective)
            model_name = (settings.ai_issues_model or "gpt-4o-mini").strip() or "gpt-4o-mini"
            resp = client.chat.completions.create(
                model=model_name,
                messages=[
                    {
                        "role": "system",
                        "content": (
                            "You are a senior platform engineer. Given telemetry about APIs, "
                            "return concise root-cause style insights and 2–3 actionable next steps. "
                            "Plain text only, under 500 words."
                        ),
                    },
                    {
                        "role": "user",
                        "content": f"Context:\n{context}",
                    },
                ],
                max_tokens=800,
            )
            text = (resp.choices[0].message.content or "").strip()
            parts = text.split("\n\n", 1)
            summary = parts[0][:2000] if parts else text[:2000]
            rec = parts[1][:4000] if len(parts) > 1 else ""
        except Exception as e:  # noqa: BLE001
            summary = f"OpenAI call failed: {e}"
            rec = "Check API key, network, and model availability."
            model_name = "error"
    else:
        summary = f"Heuristic summary: {context[:1000]}"
        rec = "Enable OPENAI_API_KEY for model-generated recommendations."

    row = AiInsight(
        project_id=project_id,
        summary=summary,
        recommendation=rec,
        model=model_name,
        extra={"context_chars": len(context)},
    )
    db.add(row)
    db.commit()
    db.refresh(row)
    return row
