"""Chat Pydantic schemas for request validation and response serialization."""
from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, Field


class MessageCreate(BaseModel):
    """Request schema for creating a new message."""

    content: str = Field(..., min_length=1, description="User message content")
    skill: str | None = Field(
        default=None,
        description="Explicit skill to invoke: 'qa', 'ship30', 'artifact'. If None, auto-detected.",
    )


class ChatRequest(BaseModel):
    """Request schema for sending a chat message."""

    message: str = Field(..., min_length=1, description="User message content")
    session_id: UUID | None = Field(
        default=None,
        description="Session ID. If None, creates a new session.",
    )
    provider: str = Field(
        default="ollama",
        description="LLM provider: 'ollama' or 'anthropic'",
    )
    model: str | None = Field(
        default=None,
        description="Override model name",
    )
    skill: str | None = Field(
        default=None,
        description="Force a specific skill: 'qa', 'ship30', 'artifact'. Auto-detects if None.",
    )
    stream: bool = Field(
        default=True,
        description="Whether to stream the response (SSE)",
    )


class MessageResponse(BaseModel):
    """Response schema for a single message."""

    id: UUID
    session_id: UUID
    role: str
    content: str
    skill_used: str | None
    artifact_type: str | None
    artifact_content: str | None
    created_at: datetime

    model_config = {"from_attributes": True}


class ChatHistoryResponse(BaseModel):
    """Response schema for chat history."""

    session_id: UUID
    messages: list[MessageResponse]


class StreamEvent(BaseModel):
    """SSE event schema for streaming responses."""

    type: str  # "token", "done", "error", "metadata"
    content: str | None = None
    session_id: str | None = None
    skill: str | None = None
    artifact_type: str | None = None
    error: str | None = None
