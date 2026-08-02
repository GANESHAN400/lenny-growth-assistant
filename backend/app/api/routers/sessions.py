"""Sessions API router - CRUD endpoints for chat session management."""
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.database import get_db
from app.schemas.session import (
    SessionCreate,
    SessionListResponse,
    SessionResponse,
    SessionUpdate,
)
from app.services.session_service import SessionService

sessions_router = APIRouter(prefix="/sessions", tags=["Sessions"])


def get_session_service(db: Session = Depends(get_db)) -> SessionService:
    return SessionService(db)


@sessions_router.post(
    "/",
    response_model=SessionResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Create a new chat session",
)
async def create_session(
    data: SessionCreate,
    service: SessionService = Depends(get_session_service),
) -> SessionResponse:
    """Create a new chat session with a specified provider and model."""
    session = service.create_session(data)
    return service.to_response(session)


@sessions_router.get(
    "/",
    response_model=SessionListResponse,
    summary="List all active chat sessions",
)
async def list_sessions(
    limit: int = 50,
    offset: int = 0,
    service: SessionService = Depends(get_session_service),
) -> SessionListResponse:
    """List all active chat sessions ordered by most recent activity."""
    sessions, total = service.list_sessions(limit=limit, offset=offset)
    return SessionListResponse(
        sessions=[service.to_response(s) for s in sessions],
        total=total,
    )


@sessions_router.get(
    "/{session_id}",
    response_model=SessionResponse,
    summary="Get a specific chat session",
)
async def get_session(
    session_id: UUID,
    service: SessionService = Depends(get_session_service),
) -> SessionResponse:
    """Get a chat session by its ID."""
    session = service.get_session(session_id)
    if not session:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Session {session_id} not found",
        )
    return service.to_response(session)


@sessions_router.patch(
    "/{session_id}",
    response_model=SessionResponse,
    summary="Update a chat session",
)
async def update_session(
    session_id: UUID,
    data: SessionUpdate,
    service: SessionService = Depends(get_session_service),
) -> SessionResponse:
    """Update session title or active state."""
    session = service.get_session(session_id)
    if not session:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Session {session_id} not found",
        )
    session = service.update_session(session, data)
    return service.to_response(session)


@sessions_router.delete(
    "/{session_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Delete a chat session",
)
async def delete_session(
    session_id: UUID,
    service: SessionService = Depends(get_session_service),
) -> None:
    """Delete a session and all its messages."""
    session = service.get_session(session_id)
    if not session:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Session {session_id} not found",
        )
    service.delete_session(session)
