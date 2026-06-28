from fastapi import FastAPI

from api.routers.chat import router as chat_router
from api.routers.health import router as health_router
from api.routers.knowledge import router as knowledge_router
from api.routers.refresh import router as refresh_router
from api.routers.upload import router as upload_router

app = FastAPI(
    title="Financial Research Copilot API",
    description="Production API for Financial Research Copilot",
    version="4.0.0"
)

app.include_router(health_router, prefix="/api/v1")
app.include_router(chat_router, prefix="/api/v1")
app.include_router(knowledge_router, prefix="/api/v1")
app.include_router(upload_router, prefix="/api/v1")
app.include_router(refresh_router, prefix="/api/v1")


@app.get("/")
def root():
    return {
        "service": "Financial Research Copilot",
        "version": "4.0.0"
    }
