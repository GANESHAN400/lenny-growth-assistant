from sqlalchemy import String
from sqlalchemy.orm import Mapped, mapped_column

from app.database.model import BaseModel


class ChatSession(BaseModel):
    __tablename__ = "chat_sessions"

    title: Mapped[str] = mapped_column(String(255), nullable=False)
    provider: Mapped[str] = mapped_column(String(50), nullable=False)
    model_name: Mapped[str] = mapped_column(String(100), nullable=False)
    is_active: Mapped[bool] = mapped_column(default=True, nullable=False)
