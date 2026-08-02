"""ChatMessage ORM model - stores individual messages within a session."""
from uuid import UUID

from sqlalchemy import ForeignKey, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database.model import BaseModel


class ChatMessage(BaseModel):
    __tablename__ = "chat_messages"

    session_id: Mapped[UUID] = mapped_column(
        ForeignKey("chat_sessions.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    role: Mapped[str] = mapped_column(
        String(20), nullable=False
    )  # "user" | "assistant" | "system"
    content: Mapped[str] = mapped_column(Text, nullable=False)
    skill_used: Mapped[str | None] = mapped_column(
        String(50), nullable=True
    )  # "qa", "ship30", "artifact", None
    artifact_type: Mapped[str | None] = mapped_column(
        String(20), nullable=True
    )  # "html", "markdown", None
    artifact_content: Mapped[str | None] = mapped_column(Text, nullable=True)

    # Relationships
    session: Mapped["ChatSession"] = relationship(back_populates="messages")  # type: ignore[name-defined]
