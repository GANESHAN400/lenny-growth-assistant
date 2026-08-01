from collections.abc import AsyncIterator
from contextlib import asynccontextmanager

from fastapi import FastAPI

from app.api.middleware import configure_cors
from app.api.routers import health_router


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncIterator[None]:
    yield


app = FastAPI(
    title="Lenny Growth Assistant Backend",
    description="Backend API service for Lenny Growth Assistant AI platform.",
    version="0.1.0",
    lifespan=lifespan,
)

configure_cors(app)

app.include_router(health_router)
