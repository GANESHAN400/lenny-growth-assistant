"""Update ChatSession model with relationship to messages."""
from sqlalchemy import String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database.model import BaseModel


class ChatSession(BaseModel):
    __tablename__ = "chat_sessions"

    title: Mapped[str] = mapped_column(String(255), nullable=False)
    provider: Mapped[str] = mapped_column(String(50), nullable=False)
    model_name: Mapped[str] = mapped_column(String(100), nullable=False)
    is_active: Mapped[bool] = mapped_column(default=True, nullable=False)

    # Relationships
    messages: Mapped[list["ChatMessage"]] = relationship(  # type: ignore[name-defined]
        back_populates="session",
        cascade="all, delete-orphan",
        order_by="ChatMessage.created_at",
    )
