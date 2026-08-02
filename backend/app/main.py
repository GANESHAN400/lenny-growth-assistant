"""Lenny Growth Assistant - FastAPI application entrypoint."""
import asyncio
from collections.abc import AsyncIterator
from contextlib import asynccontextmanager

from fastapi import FastAPI
from loguru import logger

from app.api.middleware import configure_cors, register_exception_handlers
from app.api.routers import api_router
from app.core.config import settings
from app.core.logging import configure_logging
from app.database import engine
from app.database.base import Base


async def _initialize_rag() -> None:
    """Initialize RAG index from local transcript files (or cache)."""
    try:
        from app.rag.retriever import build_retriever_from_files
        await asyncio.get_event_loop().run_in_executor(
            None, build_retriever_from_files
        )
        logger.info("RAG index ready")
    except Exception as e:
        logger.warning(f"RAG initialization failed (will retry): {e}")


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncIterator[None]:
    """Application lifespan: startup and shutdown handlers."""
    configure_logging()
    logger.info(f"Starting Lenny Growth Assistant (provider: {settings.DEFAULT_PROVIDER})")

    # Create all database tables (idempotent)
    try:
        Base.metadata.create_all(bind=engine)
        logger.info("Database tables verified")
    except Exception as e:
        logger.error(f"Database initialization failed: {e}")

    # Initialize RAG index in background
    asyncio.create_task(_initialize_rag())

    yield

    logger.info("Lenny Growth Assistant shutting down")


app = FastAPI(
    title="Lenny Growth Assistant API",
    description="""
## Lenny Growth Assistant

An AI-powered product growth strategy assistant backed by Lenny's podcast transcripts.

### Skills
- **Q&A** — RAG-grounded answers strictly from Lenny's transcripts
- **Ship30** — Ship30for30 style essay generation (~1250 words)
- **Artifact** — Generates HTML/CSS or Markdown artifacts with in-app viewer

### Providers
- **Ollama** (local) — default, no API key required
- **Anthropic Claude** — cloud, requires ANTHROPIC_API_KEY
""",
    version="0.1.0",
    lifespan=lifespan,
    docs_url="/docs",
    redoc_url="/redoc",
)

from fastapi.staticfiles import StaticFiles
from pathlib import Path

configure_cors(app)
register_exception_handlers(app)
app.include_router(api_router)

# Mount frontend static directory
frontend_dir = Path(__file__).resolve().parent.parent.parent / "frontend"
if frontend_dir.exists():
    app.mount("/", StaticFiles(directory=str(frontend_dir), html=True), name="frontend")

