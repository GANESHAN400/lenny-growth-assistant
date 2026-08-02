"""Common Pydantic response schemas used across the API."""
from typing import Any, Generic, TypeVar

from pydantic import BaseModel

T = TypeVar("T")


class SuccessResponse(BaseModel, Generic[T]):
    """Generic success response wrapper."""

    success: bool = True
    data: T


class ErrorResponse(BaseModel):
    """Error response schema."""

    success: bool = False
    error: str


class PaginatedResponse(BaseModel, Generic[T]):
    """Paginated response wrapper."""

    success: bool = True
    data: list[T]
    total: int
    page: int
    page_size: int
    has_more: bool


class MessageResponse(BaseModel):
    """Simple message response."""

    success: bool = True
    message: str


class HealthResponse(BaseModel):
    """Health check response."""

    status: str
    database: bool
    provider: str
    provider_available: bool
    version: str = "0.1.0"
