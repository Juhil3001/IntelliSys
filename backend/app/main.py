from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.core.config import get_settings
from app.db.session import SessionLocal
from app.modules.monitoring.request_middleware import RequestLogMiddleware
from app.routes import (
    alerts,
    apis,
    automation,
    chat,
    health,
    insights,
    issues,
    monitoring,
    projects,
    scans,
    snapshots,
    ai_insights as ai_insights_route,
)

settings = get_settings()


@asynccontextmanager
async def lifespan(_: FastAPI):
    yield
    # Engine dispose optional on shutdown


app = FastAPI(title="IntelliSys API", version="0.1.0", lifespan=lifespan)

app.add_middleware(RequestLogMiddleware, session_factory=SessionLocal)
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origin_list,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(health.router, tags=["health"])
app.include_router(alerts.router, prefix="/alerts", tags=["alerts"])
app.include_router(projects.router, prefix="/projects", tags=["projects"])
app.include_router(scans.router, prefix="/scans", tags=["scans"])
app.include_router(apis.router, prefix="/apis", tags=["apis"])
app.include_router(monitoring.router, prefix="/monitor", tags=["monitoring"])
app.include_router(snapshots.router, prefix="/snapshots", tags=["snapshots"])
app.include_router(insights.router, prefix="/insights", tags=["insights"])
app.include_router(issues.router, prefix="/issues", tags=["issues"])
app.include_router(ai_insights_route.router, prefix="/ai", tags=["ai"])
app.include_router(chat.router, prefix="/chat", tags=["chat"])
app.include_router(automation.router, prefix="/automation", tags=["automation"])
