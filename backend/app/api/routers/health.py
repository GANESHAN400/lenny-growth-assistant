from fastapi import APIRouter

health_router = APIRouter(tags=["Health"])


@health_router.get("/")
async def root() -> dict[str, str]:
    return {
        "application": "Lenny Growth Assistant Backend",
        "status": "running",
        "version": "0.1.0",
    }


@health_router.get("/health")
async def health_check() -> dict[str, str]:
    return {
        "status": "healthy",
    }
