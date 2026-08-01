from app.database.base import Base
from app.database.mixins import TimestampMixin, UUIDMixin


class BaseModel(Base, UUIDMixin, TimestampMixin):
    __abstract__ = True
