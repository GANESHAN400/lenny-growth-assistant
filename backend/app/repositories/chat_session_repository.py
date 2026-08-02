"""ChatSession repository - data access layer for session management."""
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.chat_session import ChatSession
from app.repositories.base import BaseRepository


class ChatSessionRepository(BaseRepository[ChatSession]):
    """Repository for ChatSession CRUD operations."""

    def __init__(self, db: Session) -> None:
        super().__init__(ChatSession, db)

    def get_active_sessions(
        self, limit: int = 50, offset: int = 0
    ) -> list[ChatSession]:
        """Get all active chat sessions, newest first."""
        stmt = (
            select(ChatSession)
            .where(ChatSession.is_active == True)  # noqa: E712
            .order_by(ChatSession.updated_at.desc())
            .limit(limit)
            .offset(offset)
        )
        return list(self.db.execute(stmt).scalars().all())

    def count_active(self) -> int:
        """Count active sessions."""
        from sqlalchemy import func

        result = self.db.execute(
            select(func.count()).select_from(ChatSession).where(
                ChatSession.is_active == True  # noqa: E712
            )
        )
        return result.scalar() or 0

    def create_session(
        self,
        title: str = "New Chat",
        provider: str = "ollama",
        model_name: str = "qwen2.5:7b",
    ) -> ChatSession:
        """Create a new chat session."""
        return self.create(
            title=title,
            provider=provider,
            model_name=model_name,
            is_active=True,
        )

    def deactivate(self, session: ChatSession) -> ChatSession:
        """Mark a session as inactive."""
        return self.update(session, is_active=False)

    def update_title(self, session: ChatSession, title: str) -> ChatSession:
        """Update session title."""
        return self.update(session, title=title)

    def get_with_messages(self, session_id: UUID) -> ChatSession | None:
        """Load session with all messages eagerly."""
        from sqlalchemy.orm import selectinload

        stmt = (
            select(ChatSession)
            .options(selectinload(ChatSession.messages))
            .where(ChatSession.id == session_id)
        )
        return self.db.execute(stmt).scalar_one_or_none()
