"""API router registry - registers all routers under /api/v1."""
from fastapi import APIRouter

from app.api.routers.chat import chat_router
from app.api.routers.health import health_router
from app.api.routers.sessions import sessions_router

api_router = APIRouter(prefix="/api/v1")
api_router.include_router(health_router)
api_router.include_router(sessions_router)
api_router.include_router(chat_router)

__all__ = ["api_router", "chat_router", "health_router", "sessions_router"]
