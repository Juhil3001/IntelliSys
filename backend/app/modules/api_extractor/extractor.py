import ast
import re

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models import Api, FileRecord


_METHOD_RE = re.compile(
    r'@(?:app|router)\.(get|post|put|delete|patch|options|head|trace)\s*\(\s*["\']([^"\']+)["\']',
    re.IGNORECASE,
)


def _extract_from_python_source(source: str, file_id: int, scan_run_id: int) -> list[Api]:
    out: list[Api] = []
    try:
        tree = ast.parse(source)
    except SyntaxError:
        for m in _METHOD_RE.finditer(source):
            method, path = m.group(1).upper(), m.group(2)
            out.append(
                Api(
                    scan_run_id=scan_run_id,
                    file_id=file_id,
                    name=f"{method} {path}",
                    method=method,
                    endpoint=path,
                    path_pattern=path,
                )
            )
        return out

    for node in ast.walk(tree):
        if isinstance(node, ast.Call):
            method = None
            path_arg = None
            if isinstance(node.func, ast.Attribute):
                if node.func.attr.lower() in (
                    "get",
                    "post",
                    "put",
                    "delete",
                    "patch",
                    "options",
                    "head",
                    "trace",
                ):
                    method = node.func.attr.upper()
            if method and node.args:
                first = node.args[0]
                if isinstance(first, ast.Constant) and isinstance(first.value, str):
                    path_arg = first.value
                elif isinstance(first, ast.JoinedStr) and first.values:
                    path_arg = _fstring_to_pattern(first)
            if method and path_arg:
                out.append(
                    Api(
                        scan_run_id=scan_run_id,
                        file_id=file_id,
                        name=f"{method} {path_arg}",
                        method=method,
                        endpoint=path_arg,
                        path_pattern=path_arg,
                    )
                )
    if not out:
        for m in _METHOD_RE.finditer(source):
            method, path = m.group(1).upper(), m.group(2)
            out.append(
                Api(
                    scan_run_id=scan_run_id,
                    file_id=file_id,
                    name=f"{method} {path}",
                    method=method,
                    endpoint=path,
                    path_pattern=path,
                )
            )
    return out


def _fstring_to_pattern(node: ast.JoinedStr) -> str:
    parts: list[str] = []
    for v in node.values:
        if isinstance(v, ast.Constant) and isinstance(v.value, str):
            parts.append(v.value)
        elif isinstance(v, ast.FormattedValue):
            parts.append("{param}")
    return "".join(parts) or "/"


def extract_apis_for_scan(db: Session, scan_run_id: int) -> int:
    q = select(FileRecord).where(FileRecord.scan_run_id == scan_run_id)
    files = list(db.execute(q).scalars())
    n = 0
    for fr in files:
        if not fr.path.lower().endswith(".py"):
            continue
        raw = _extract_from_python_source(fr.content, fr.id, scan_run_id)
        seen: set[tuple[str, str, int]] = set()
        for a in raw:
            key = (a.method, a.endpoint, fr.id)
            if key in seen:
                continue
            seen.add(key)
            db.add(a)
            n += 1
    db.flush()
    return n
