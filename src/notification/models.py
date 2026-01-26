from typing import Optional, TYPE_CHECKING
from datetime import datetime
from sqlmodel import SQLModel, Field, Relationship, Column, ForeignKey
from uuid import UUID, uuid4
from src.myenums import NotificationType
from sqlalchemy.orm import Mapped
from sqlalchemy.dialects.postgresql import JSONB
if TYPE_CHECKING:
    from auth.models import Users  # type hint only

class Notification(SQLModel, table=True):
    __tablename__ = "notification"

    id: Optional[UUID] = Field(default_factory=uuid4, primary_key=True)
    user_id: UUID = Field(sa_column=Column(ForeignKey("users.id", ondelete="CASCADE"), nullable=False))
    type: NotificationType
    title: Optional[str] = None
    message: str
    data: Optional[dict] = Field(sa_column=Column(JSONB), default=None)
    is_read: bool = False
    created_at: datetime = Field(default_factory=datetime.utcnow)

    # Relationship using forward reference
    user: Mapped["Users"] = Relationship(back_populates="notifications")

# Resolve forward references at the end
from src.auth.models import Users
Notification.update_forward_refs()
