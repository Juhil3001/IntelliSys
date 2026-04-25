import datetime
import os
from pathlib import Path

from sqlalchemy.orm import Session

from app.models import FileRecord, Project, ScanRun, ScanStatus
from app.modules.api_extractor import extract_apis_for_scan
from app.modules.scanner.ignore import should_skip_dir, should_skip_file


def _read_text_limited(p: Path, max_bytes: int = 1_000_000) -> str:
    try:
        data = p.read_bytes()[:max_bytes]
        return data.decode("utf-8", errors="replace")
    except OSError:
        return ""


def run_scan(
    db: Session,
    project: Project,
    source_root: str,
) -> ScanRun:
    root = Path(source_root).resolve()
    if not root.is_dir():
        raise ValueError(f"source_root is not a directory: {root}")

    # Prevent scanning outside a reasonable boundary — caller must pass trusted path
    run = ScanRun(
        project_id=project.id,
        status=ScanStatus.running,
        started_at=datetime.datetime.now(datetime.UTC),
        source_root=str(root),
    )
    db.add(run)
    db.flush()

    try:
        for dirpath, dirnames, filenames in os.walk(root, topdown=True):
            parts = Path(dirpath).parts
            if any(should_skip_dir(p) for p in parts):
                dirnames[:] = []
                continue
            dirnames[:] = [d for d in dirnames if not should_skip_dir(d)]

            for name in filenames:
                fp = Path(dirpath) / name
                if should_skip_file(fp):
                    continue
                try:
                    rel = fp.resolve().relative_to(root)
                except ValueError:
                    continue
                rel_posix = rel.as_posix()
                if fp.is_file():
                    text = _read_text_limited(fp) if is_text_candidate(fp) else ""
                    rec = FileRecord(
                        scan_run_id=run.id,
                        file_name=fp.name,
                        path=rel_posix,
                        content=text,
                    )
                    db.add(rec)
        db.flush()
        extract_apis_for_scan(db, run.id)
        run.status = ScanStatus.completed
    except Exception as e:  # noqa: BLE001
        run.status = ScanStatus.failed
        run.error_message = str(e)[:8000]
    finally:
        run.finished_at = datetime.datetime.now(datetime.UTC)
    db.commit()
    db.refresh(run)
    return run


def is_text_candidate(p: Path) -> bool:
    ex = {".py", ".ts", ".tsx", ".js", ".jsx", ".mjs", ".cjs", ".json", ".yaml", ".yml", ".html", ""}
    return p.suffix.lower() in ex
