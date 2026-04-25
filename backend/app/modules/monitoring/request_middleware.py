import time
from collections.abc import Callable

from sqlalchemy import select
from starlette.concurrency import run_in_threadpool
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import Response
from starlette.types import ASGIApp

from app.models import Api, ApiCall, ScanRun, ScanStatus
from app.modules.monitoring.path_match import find_best_api


class RequestLogMiddleware(BaseHTTPMiddleware):
    """
    Records API calls when X-Project-Id is set and the path matches a route
    from the latest completed scan for that project.
    """

    def __init__(self, app: ASGIApp, session_factory: Callable):
        super().__init__(app)
        self._session_factory = session_factory

    def _log_call(
        self,
        project_id: int,
        method: str,
        path: str,
        status_code: int,
        duration_ms: float,
    ) -> None:
        db = self._session_factory()
        try:
            sub = (
                select(ScanRun.id)
                .where(
                    ScanRun.project_id == project_id,
                    ScanRun.status == ScanStatus.completed,
                )
                .order_by(ScanRun.id.desc())
                .limit(1)
            )
            row = db.execute(sub).first()
            if not row:
                return
            scan_id = row[0]
            q = select(Api).where(Api.scan_run_id == scan_id)
            apis = list(db.execute(q).scalars().all())
            routes = [(a.id, a.method, a.endpoint) for a in apis]
            api_id = find_best_api(method, path, routes)
            if api_id is None:
                return
            call = ApiCall(
                api_id=api_id,
                response_time_ms=duration_ms,
                status_code=status_code,
                is_error=status_code >= 400,
                method=method,
                path=path,
                project_id=project_id,
            )
            db.add(call)
            db.commit()
        except Exception:  # noqa: BLE001
            db.rollback()
        finally:
            db.close()

    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        if request.url.path in ("/health", "/docs", "/openapi.json", "/redoc"):
            return await call_next(request)

        start = time.perf_counter()
        response = await call_next(request)
        dur_ms = (time.perf_counter() - start) * 1000

        raw = request.headers.get("x-project-id")
        if not raw or not raw.strip().isdigit():
            return response
        project_id = int(raw.strip())
        await run_in_threadpool(
            self._log_call,
            project_id,
            request.method,
            request.url.path,
            response.status_code,
            dur_ms,
        )
        return response
