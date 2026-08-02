"""Generic base repository implementing common CRUD operations."""
from typing import Any, Generic, TypeVar
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.database.model import BaseModel

T = TypeVar("T", bound=BaseModel)


class BaseRepository(Generic[T]):
    """Generic repository with CRUD operations."""

    def __init__(self, model: type[T], db: Session) -> None:
        self.model = model
        self.db = db

    def get_by_id(self, record_id: UUID) -> T | None:
        """Get a record by primary key."""
        return self.db.get(self.model, record_id)

    def get_all(self, limit: int = 100, offset: int = 0) -> list[T]:
        """Get all records with pagination."""
        stmt = select(self.model).limit(limit).offset(offset)
        return list(self.db.execute(stmt).scalars().all())

    def count(self) -> int:
        """Count total records."""
        from sqlalchemy import func
        result = self.db.execute(select(func.count()).select_from(self.model))
        return result.scalar() or 0

    def create(self, **kwargs: Any) -> T:
        """Create a new record."""
        instance = self.model(**kwargs)
        self.db.add(instance)
        self.db.commit()
        self.db.refresh(instance)
        return instance

    def update(self, record: T, **kwargs: Any) -> T:
        """Update an existing record."""
        for key, value in kwargs.items():
            if hasattr(record, key) and value is not None:
                setattr(record, key, value)
        self.db.commit()
        self.db.refresh(record)
        return record

    def delete(self, record: T) -> None:
        """Delete a record."""
        self.db.delete(record)
        self.db.commit()
