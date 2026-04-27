from fastapi import APIRouter, HTTPException

from app.core.config import get_settings

router = APIRouter()


@router.get("/github/status")
def github_integration_status() -> dict:
    """Per-install GitHub App OAuth is not configured in this build; use server GITHUB_TOKEN + repo URL."""
    s = get_settings()
    return {
        "github_app_oauth": "not_configured",
        "server_pat_configured": bool(s.github_token_effective),
        "message": "Link projects with github_repo_url and set GITHUB_TOKEN on the API for private clones and GitHub issue export.",
    }


@router.get("/github/callback")
def github_oauth_callback_placeholder() -> None:
    raise HTTPException(
        status_code=501,
        detail="GitHub App OAuth callback is not implemented; use repo URL and GITHUB_TOKEN.",
    )
