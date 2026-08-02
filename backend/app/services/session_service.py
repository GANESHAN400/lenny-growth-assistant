"""Session service - business logic for chat session management."""
from uuid import UUID

from sqlalchemy.orm import Session

from app.models.chat_session import ChatSession
from app.repositories.chat_session_repository import ChatSessionRepository
from app.repositories.message_repository import ChatMessageRepository
from app.schemas.session import SessionCreate, SessionResponse, SessionUpdate


class SessionService:
    """Handles session creation, listing, and management."""

    def __init__(self, db: Session) -> None:
        self.session_repo = ChatSessionRepository(db)
        self.message_repo = ChatMessageRepository(db)

    def create_session(self, data: SessionCreate) -> ChatSession:
        """Create a new chat session."""
        return self.session_repo.create_session(
            title=data.title,
            provider=data.provider,
            model_name=data.model_name,
        )

    def get_session(self, session_id: UUID) -> ChatSession | None:
        """Get a session by ID."""
        return self.session_repo.get_by_id(session_id)

    def get_session_with_messages(self, session_id: UUID) -> ChatSession | None:
        """Get session with all messages eagerly loaded."""
        return self.session_repo.get_with_messages(session_id)

    def list_sessions(
        self, limit: int = 50, offset: int = 0
    ) -> tuple[list[ChatSession], int]:
        """List active sessions with total count."""
        sessions = self.session_repo.get_active_sessions(limit=limit, offset=offset)
        total = self.session_repo.count_active()
        return sessions, total

    def update_session(
        self, session: ChatSession, data: SessionUpdate
    ) -> ChatSession:
        """Update session title or active state."""
        kwargs = {}
        if data.title is not None:
            kwargs["title"] = data.title
        if data.is_active is not None:
            kwargs["is_active"] = data.is_active
        return self.session_repo.update(session, **kwargs)

    def delete_session(self, session: ChatSession) -> None:
        """Delete a session and all its messages (cascade)."""
        self.session_repo.delete(session)

    def update_title(self, session: ChatSession, title: str) -> ChatSession:
        """Update session title."""
        return self.session_repo.update_title(session, title)

    def get_message_count(self, session_id: UUID) -> int:
        """Get message count for a session."""
        return self.message_repo.count_session_messages(session_id)

    def to_response(self, session: ChatSession) -> SessionResponse:
        """Convert ORM session to response schema."""
        msg_count = self.get_message_count(session.id)
        return SessionResponse(
            id=session.id,
            title=session.title,
            provider=session.provider,
            model_name=session.model_name,
            is_active=session.is_active,
            created_at=session.created_at,
            updated_at=session.updated_at,
            message_count=msg_count,
        )
