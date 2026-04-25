from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import JSONResponse

from app.core.security import decode_token


def _is_public_path(path: str) -> bool:
    if path in ("/health", "/docs", "/openapi.json", "/redoc"):
        return True
    if path.startswith("/docs") or path.startswith("/redoc"):
        return True
    if path in ("/auth/register", "/auth/login"):
        return True
    return False


class AuthMiddleware(BaseHTTPMiddleware):
    """Require Bearer JWT for all routes except whitelisted and OPTIONS."""

    async def dispatch(self, request: Request, call_next):
        path = request.url.path
        if request.method == "OPTIONS" or _is_public_path(path):
            return await call_next(request)
        auth = request.headers.get("Authorization")
        if not auth or not auth.startswith("Bearer "):
            return JSONResponse(status_code=401, content={"detail": "Not authenticated"})
        token = auth.removeprefix("Bearer ").strip()
        if not token:
            return JSONResponse(status_code=401, content={"detail": "Not authenticated"})
        user_id = decode_token(token)
        if user_id is None:
            return JSONResponse(status_code=401, content={"detail": "Invalid or expired token"})
        request.state.user_id = user_id
        return await call_next(request)
