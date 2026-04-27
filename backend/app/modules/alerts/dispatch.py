from __future__ import annotations

import logging
from typing import Any

import httpx

from app.models import Issue, Project

logger = logging.getLogger(__name__)


def dispatch_alert_webhook(project: Project, issues: list[Issue]) -> None:
    url = (project.alert_webhook_url or "").strip()
    if not url or not issues:
        return
    payload: dict[str, Any] = {
        "project_id": project.id,
        "project_name": project.name,
        "issues": [
            {
                "id": i.id,
                "type": i.type,
                "severity": i.severity.value if i.severity else None,
                "description": i.description[:2000],
            }
            for i in issues
        ],
    }
    try:
        httpx.post(url, json=payload, timeout=15.0)
    except Exception:  # noqa: BLE001
        logger.exception("alert webhook failed for project %s", project.id)
