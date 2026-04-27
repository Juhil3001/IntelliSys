from __future__ import annotations

import hashlib
import json
import re
from pathlib import Path
from typing import Any

from sqlalchemy import delete, select
from sqlalchemy.orm import Session

from app.models import Api, FileRecord, ProjectDependency, ScanRun

_PY_IMPORT = re.compile(
    r"^(?:from\s+([\w.]+)\s+import|import\s+([\w.]+))", re.MULTILINE
)


def _hash_for_api(api: Api, file_text: str) -> str:
    block = f"{api.method}\n{api.endpoint}\n{file_text[:12000]}"
    return hashlib.sha256(block.encode("utf-8", errors="replace")).hexdigest()[:48]


def _parse_package_json(text: str) -> list[tuple[str, str | None]]:
    out: list[tuple[str, str | None]] = []
    try:
        data = json.loads(text)
    except (json.JSONDecodeError, TypeError):
        return out
    deps: dict[str, str] = {}
    for key in ("dependencies", "devDependencies", "peerDependencies"):
        block = data.get(key) if isinstance(data, dict) else None
        if isinstance(block, dict):
            deps.update(block)
    for name, ver in deps.items():
        if isinstance(name, str):
            out.append((name, str(ver) if ver is not None else None))
    return out


def _parse_requirements(text: str) -> list[tuple[str, str | None]]:
    out: list[tuple[str, str | None]] = []
    for line in text.splitlines():
        s = line.strip()
        if not s or s.startswith("#") or s.startswith("-"):
            continue
        # name==1.0 or name>=1
        m = re.match(r"^([a-zA-Z0-9_.\-]+)(.*)$", s)
        if m:
            name, rest = m.group(1), m.group(2).strip()
            ver = rest.lstrip("=<>!~") if rest else None
            out.append((name, ver or None))
    return out


def _python_import_edges(sources: dict[str, str]) -> list[dict[str, str]]:
    """Approximate import graph: module -> set of first segment targets."""
    edges: list[dict[str, str]] = []
    for path, text in sources.items():
        if not path.endswith(".py"):
            continue
        for m in _PY_IMPORT.finditer(text):
            g1, g2 = m.group(1), m.group(2)
            mod = (g1 or g2 or "").split(".")[0] if (g1 or g2) else ""
            if mod and not mod.startswith("_"):
                edges.append(
                    {
                        "from_file": path,
                        "import": mod,
                    }
                )
    return edges


def run_post_scan_artifacts(db: Session, run: ScanRun) -> None:
    """Set API content hashes, index lockfile deps, build coarse import list; store on scan.artifacts."""
    files = list(db.execute(select(FileRecord).where(FileRecord.scan_run_id == run.id)).scalars())
    path_to_text: dict[str, str] = {f.path: f.content or "" for f in files}
    apis = list(db.execute(select(Api).where(Api.scan_run_id == run.id)).scalars())
    by_file: dict[int, str] = {}
    for f in files:
        by_file[f.id] = f.content or ""

    for a in apis:
        text = by_file.get(a.file_id) or ""
        a.content_hash = _hash_for_api(a, text)
    db.add_all(apis)

    db.execute(delete(ProjectDependency).where(ProjectDependency.scan_run_id == run.id))
    seen: set[tuple[str, str, str | None]] = set()
    for rel_path, text in path_to_text.items():
        name = Path(rel_path).name.lower()
        if name == "package.json":
            for pkg, ver in _parse_package_json(text):
                key = ("npm", pkg, ver)
                if key not in seen:
                    seen.add(key)
                    db.add(ProjectDependency(scan_run_id=run.id, ecosystem="npm", name=pkg, version=ver))
        elif name in ("requirements.txt", "requirements-dev.txt") or rel_path.endswith("requirements.txt"):
            for pkg, ver in _parse_requirements(text):
                key = ("pip", pkg, ver)
                if key not in seen:
                    seen.add(key)
                    db.add(ProjectDependency(scan_run_id=run.id, ecosystem="pip", name=pkg, version=ver))

    edges = _python_import_edges(path_to_text)
    dep_rows = list(
        db.execute(
            select(ProjectDependency).where(ProjectDependency.scan_run_id == run.id)
        )
        .scalars()
        .all()
    )
    nodes: list[dict[str, Any]] = [
        {
            "id": f"dep:{d.ecosystem}:{d.name}",
            "label": f"{d.name}@{d.version or '?'}",
            "kind": "package",
        }
        for d in dep_rows[:400]
    ]
    for p in sorted(path_to_text)[:200]:
        nodes.append({"id": f"file:{p}", "label": p, "kind": "file"})

    run.artifacts = {
        "import_edges": edges[:5000],
        "lockfile_count": len(dep_rows),
        "nodes": nodes[:500],
        "summary": {
            "file_count": len(files),
            "api_count": len(apis),
            "package_nodes": min(len(dep_rows), 400),
        },
    }
    db.add(run)
    db.commit()
    db.refresh(run)
