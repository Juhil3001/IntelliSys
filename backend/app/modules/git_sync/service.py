from __future__ import annotations

import os
import re
import subprocess
from pathlib import Path

_GITHUB_HTTPS = re.compile(
    r"^https://([^/@]+/){1,2}[^/]+/[^/]+(?:\.git)?/?$", re.IGNORECASE
)
# Browser URLs like https://github.com/org/repo/tree/main — not valid for git clone
_GITHUB_TREE_BLOB = re.compile(
    r"^(https?://(?:www\.)?github\.com/[^/]+/[^/]+)(?:/tree/[^/]+(?:/.*)?|/blob/[^/]+(?:/.*)?)?/?$",
    re.IGNORECASE,
)


class GitSyncError(Exception):
    pass


def _strip_github_browser_path(url: str) -> str:
    """Reduce .../org/repo/tree/branch/... or .../blob/... to .../org/repo for git remote."""
    m = _GITHUB_TREE_BLOB.match(url.strip())
    if m:
        return m.group(1).rstrip("/")
    return url.strip().rstrip("/")


def _normalize_to_https(github_url: str) -> str:
    s = _strip_github_browser_path(github_url)
    if s.startswith("git@github.com:"):
        path = s.replace("git@github.com:", "", 1).rstrip()
        if not path.endswith(".git"):
            path = path + ".git"
        return f"https://github.com/{path}"
    if s.startswith("https://github.com/") or s.startswith("https://www.github.com/"):
        s = s.replace("https://www.github.com/", "https://github.com/", 1)
        if not s.endswith(".git"):
            s = s.rstrip("/") + ".git"
        return s
    if _GITHUB_HTTPS.match(s):
        if not s.endswith(".git"):
            s = s.rstrip("/") + ".git"
        return s
    raise GitSyncError("Only https://github.com/... or git@github.com:org/repo URLs are allowed")


def _embed_token(https_url: str, token: str) -> str:
    t = token.strip()
    if not t:
        return https_url
    if https_url.startswith("https://") and "@" not in https_url.split("://", 1)[1][:30]:
        rest = https_url[8:]
        return f"https://oauth2:{t}@{rest}"
    return https_url


def ensure_path_in_workspace(path: Path, workspace_base: Path) -> None:
    try:
        path = path.resolve()
        workspace_base = workspace_base.resolve()
        path.relative_to(workspace_base)
    except ValueError as e:
        raise GitSyncError("Refusing to sync outside workspace base") from e


def sync_repo_to_path(
    github_url: str,
    branch: str,
    dest: Path,
    token: str,
) -> str:
    """
    Shallow clone or fetch+reset into dest. Returns current commit SHA.
    """
    https_url = _normalize_to_https(github_url)
    clone_url = _embed_token(https_url, token)
    env = os.environ.copy()
    env["GIT_TERMINAL_PROMPT"] = "0"

    if not (dest / ".git").is_dir():
        r = subprocess.run(
            [
                "git",
                "clone",
                "--depth",
                "1",
                "-b",
                branch,
                clone_url,
                str(dest),
            ],
            capture_output=True,
            text=True,
            timeout=600,
            env=env,
        )
        if r.returncode != 0:
            raise GitSyncError((r.stderr or r.stdout or "git clone failed")[:2000])
    else:
        r = subprocess.run(
            ["git", "-C", str(dest), "fetch", "origin", branch, "--depth", "1"],
            capture_output=True,
            text=True,
            timeout=300,
            env=env,
        )
        if r.returncode != 0:
            raise GitSyncError((r.stderr or r.stdout or "git fetch failed")[:2000])
        r2 = subprocess.run(
            ["git", "-C", str(dest), "reset", "--hard", f"origin/{branch}"],
            capture_output=True,
            text=True,
            timeout=120,
            env=env,
        )
        if r2.returncode != 0:
            r3 = subprocess.run(
                ["git", "-C", str(dest), "pull", "--ff-only", "origin", branch],
                capture_output=True,
                text=True,
                timeout=300,
                env=env,
            )
            if r3.returncode != 0:
                raise GitSyncError((r3.stderr or r3.stdout or "git update failed")[:2000])
    r_sha = subprocess.run(
        ["git", "-C", str(dest), "rev-parse", "HEAD"],
        capture_output=True,
        text=True,
        timeout=30,
        env=env,
    )
    if r_sha.returncode != 0 or not (r_sha.stdout or "").strip():
        raise GitSyncError("Could not read commit SHA after sync")
    return (r_sha.stdout or "").strip()
