"""ChatMessage repository - data access layer for message persistence."""
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.message import ChatMessage
from app.repositories.base import BaseRepository


class ChatMessageRepository(BaseRepository[ChatMessage]):
    """Repository for ChatMessage CRUD operations."""

    def __init__(self, db: Session) -> None:
        super().__init__(ChatMessage, db)

    def get_session_messages(
        self, session_id: UUID, limit: int = 100
    ) -> list[ChatMessage]:
        """Get all messages for a session ordered by creation time."""
        stmt = (
            select(ChatMessage)
            .where(ChatMessage.session_id == session_id)
            .order_by(ChatMessage.created_at.asc())
            .limit(limit)
        )
        return list(self.db.execute(stmt).scalars().all())

    def get_recent_messages(
        self, session_id: UUID, limit: int = 20
    ) -> list[ChatMessage]:
        """Get most recent messages for context window."""
        stmt = (
            select(ChatMessage)
            .where(ChatMessage.session_id == session_id)
            .order_by(ChatMessage.created_at.desc())
            .limit(limit)
        )
        return list(reversed(self.db.execute(stmt).scalars().all()))

    def add_message(
        self,
        session_id: UUID,
        role: str,
        content: str,
        skill_used: str | None = None,
        artifact_type: str | None = None,
        artifact_content: str | None = None,
    ) -> ChatMessage:
        """Add a new message to a session."""
        return self.create(
            session_id=session_id,
            role=role,
            content=content,
            skill_used=skill_used,
            artifact_type=artifact_type,
            artifact_content=artifact_content,
        )

    def count_session_messages(self, session_id: UUID) -> int:
        """Count messages in a session."""
        from sqlalchemy import func

        result = self.db.execute(
            select(func.count()).select_from(ChatMessage).where(
                ChatMessage.session_id == session_id
            )
        )
        return result.scalar() or 0

    def delete_session_messages(self, session_id: UUID) -> None:
        """Delete all messages in a session."""
        stmt = select(ChatMessage).where(ChatMessage.session_id == session_id)
        messages = list(self.db.execute(stmt).scalars().all())
        for msg in messages:
            self.db.delete(msg)
        self.db.commit()
