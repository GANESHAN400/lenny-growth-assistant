"""Chat API router - streaming chat endpoint with SSE support."""
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.responses import StreamingResponse
from sqlalchemy.orm import Session

from app.database import get_db
from app.schemas.chat import ChatHistoryResponse, ChatRequest, MessageResponse
from app.services.chat_service import ChatService
from app.services.session_service import SessionService

chat_router = APIRouter(prefix="/chat", tags=["Chat"])


def get_chat_service(db: Session = Depends(get_db)) -> ChatService:
    return ChatService(db)


def get_session_service(db: Session = Depends(get_db)) -> SessionService:
    return SessionService(db)


@chat_router.post(
    "/stream",
    summary="Send a message and get a streaming response (SSE)",
    response_description="Server-Sent Events stream of tokens",
)
async def chat_stream(
    request: ChatRequest,
    service: ChatService = Depends(get_chat_service),
) -> StreamingResponse:
    """Send a message and receive a real-time streaming response via SSE.
    
    The response is a stream of `data: {...}\\n\\n` events. Event types:
    - `session`: Contains `session_id` (created or existing)
    - `metadata`: Contains `skill` (qa|ship30|artifact|chat) and `artifact_type`
    - `token`: Contains a `content` text chunk
    - `artifact_ready`: Contains full `content` of the artifact
    - `title_update`: Contains updated `title` for the session
    - `error`: Contains `error` message
    - `done`: Signals end of stream
    """
    async def event_generator():
        async for event in service.stream_chat(
            session_id=request.session_id,
            user_message=request.message,
            provider_name=request.provider,
            model=request.model,
            skill=request.skill,
        ):
            yield event

    return StreamingResponse(
        event_generator(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "X-Accel-Buffering": "no",
            "Connection": "keep-alive",
        },
    )


@chat_router.get(
    "/{session_id}/history",
    response_model=ChatHistoryResponse,
    summary="Get chat history for a session",
)
async def get_chat_history(
    session_id: UUID,
    session_service: SessionService = Depends(get_session_service),
    chat_service: ChatService = Depends(get_chat_service),
) -> ChatHistoryResponse:
    """Retrieve full message history for a chat session."""
    session = session_service.get_session(session_id)
    if not session:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Session {session_id} not found",
        )
    messages = chat_service.get_history(session_id)
    return ChatHistoryResponse(
        session_id=session_id,
        messages=[
            MessageResponse(
                id=m.id,
                session_id=m.session_id,
                role=m.role,
                content=m.content,
                skill_used=m.skill_used,
                artifact_type=m.artifact_type,
                artifact_content=m.artifact_content,
                created_at=m.created_at,
            )
            for m in messages
        ],
    )
