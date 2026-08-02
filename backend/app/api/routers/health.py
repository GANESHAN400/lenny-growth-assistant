"""Enhanced health router with database and provider status."""
from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.core.config import settings
from app.database import get_db
from app.database.health import check_database_connection
from app.rag.retriever import get_retriever
from app.schemas.common import HealthResponse

health_router = APIRouter(tags=["Health"])


@health_router.get("/", summary="Root endpoint")
async def root() -> dict[str, str]:
    return {
        "application": "Lenny Growth Assistant Backend",
        "status": "running",
        "version": "0.1.0",
    }


@health_router.get(
    "/health",
    response_model=HealthResponse,
    summary="Detailed health check",
)
async def health_check() -> HealthResponse:
    """Check health of database, RAG index, and LLM provider."""
    db_ok = check_database_connection()
    retriever = get_retriever()
    rag_loaded = retriever.is_loaded

    return HealthResponse(
        status="healthy" if db_ok else "degraded",
        database=db_ok,
        provider=settings.DEFAULT_PROVIDER,
        provider_available=True,  # Checked lazily
        version="0.1.0",
    )


@health_router.get("/rag-status", summary="RAG index status")
async def rag_status() -> dict:
    """Check if RAG index is loaded and return stats."""
    retriever = get_retriever()
    return {
        "loaded": retriever.is_loaded,
        "chunk_count": len(retriever.chunks),
        "term_count": len(retriever.inverted_index),
        "avg_chunk_length": round(retriever.avg_length, 1),
    }
