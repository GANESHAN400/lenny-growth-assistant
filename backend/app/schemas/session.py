"""Session Pydantic schemas for request validation and response serialization."""
from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, Field


class SessionCreate(BaseModel):
    """Request schema for creating a new chat session."""

    title: str = Field(
        default="New Chat",
        max_length=255,
        description="Title of the chat session",
    )
    provider: str = Field(
        default="ollama",
        description="LLM provider to use (ollama or anthropic)",
    )
    model_name: str = Field(
        default="qwen2.5:7b",
        description="Model name to use for this session",
    )


class SessionUpdate(BaseModel):
    """Request schema for updating an existing session."""

    title: str | None = Field(
        default=None,
        max_length=255,
        description="Updated title for the session",
    )
    is_active: bool | None = Field(
        default=None,
        description="Set session active/inactive state",
    )


class SessionResponse(BaseModel):
    """Response schema for a chat session."""

    id: UUID
    title: str
    provider: str
    model_name: str
    is_active: bool
    created_at: datetime
    updated_at: datetime
    message_count: int = 0

    model_config = {"from_attributes": True}


class SessionListResponse(BaseModel):
    """Response schema for listing sessions."""

    sessions: list[SessionResponse]
    total: int
