from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from agent.__version__ import __version__
from api.routers.chat import router as chat_router
from api.routers.health import router as health_router
from api.routers.knowledge import router as knowledge_router
from api.routers.refresh import router as refresh_router
from api.routers.upload import router as upload_router
from api.routers.auth import router as auth_router
from api.routers.tasks import router as tasks_router
from api.routers.usage import router as usage_router
from api.routers.subscription import router as subscription_router
from api.routers.tenant import router as tenant_router


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



@app.get("/")
def root():
    return {"service": "Financial Research Copilot", "version": __version__}