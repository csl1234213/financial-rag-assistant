from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from agent.__version__ import __version__
from api.routers.agent import router as agent_router
from api.routers.auth import router as auth_router
from api.routers.billing import router as billing_router
from api.routers.chat import router as chat_router
from api.routers.health import router as health_router
from api.routers.knowledge import router as knowledge_router
from api.routers.monitoring import router as monitoring_router
from api.routers.refresh import router as refresh_router
from api.routers.subscription import router as subscription_router
from api.routers.tasks import router as tasks_router
from api.routers.tenant import router as tenant_router
from api.routers.upload import router as upload_router
from api.routers.usage import router as usage_router
from middleware.security import (
    RateLimitMiddleware,
    RequestIDMiddleware,
    RequestTimingMiddleware,
    SecurityHeadersMiddleware,
)

app = FastAPI(
    title="Financial Research Copilot API",
    description="Production API for Financial Research Copilot",
    version=__version__,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173"],
    allow_methods=["*"],
    allow_headers=["*"],
)

app.add_middleware(RequestIDMiddleware)
app.add_middleware(RequestTimingMiddleware)
app.add_middleware(SecurityHeadersMiddleware)
app.add_middleware(
    RateLimitMiddleware,
    requests_per_window=100,
    window_seconds=60,
)

app.include_router(health_router, prefix="/api/v1")
app.include_router(chat_router, prefix="/api/v1")
app.include_router(knowledge_router, prefix="/api/v1")
app.include_router(upload_router, prefix="/api/v1")
app.include_router(refresh_router, prefix="/api/v1")
app.include_router(auth_router, prefix="/api/v1/auth")
app.include_router(tasks_router, prefix="/api/v1")
app.include_router(usage_router, prefix="/api/v1")
app.include_router(subscription_router, prefix="/api/v1")
app.include_router(tenant_router, prefix="/api/v1")
app.include_router(agent_router, prefix="/api/v1")
app.include_router(billing_router, prefix="/api/v1")
app.include_router(monitoring_router, prefix="/api/v1")


@app.get("/")
def root():
    return {"service": "Financial Research Copilot", "version": __version__}


@app.get("/health")
def health_root():
    from api.routers.health import _check_database, _check_redis

    db_status = _check_database()
    redis_status = _check_redis()

    overall = "ok" if db_status == "ok" else "degraded"

    return {
        "status": overall,
        "service": "Financial Research Copilot",
        "version": __version__,
        "api": "ok",
        "database": db_status,
        "redis": redis_status,
    }