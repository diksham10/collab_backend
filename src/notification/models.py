from typing import Optional, TYPE_CHECKING
from datetime import datetime
from sqlmodel import SQLModel, Field, Relationship
from uuid import UUID, uuid4
from src.myenums import NotificationType

if TYPE_CHECKING:
    from auth.models import Users  # type hint only

class Notification(SQLModel, table=True):
    id: Optional[UUID] = Field(default_factory=uuid4, primary_key=True)
    user_id: UUID = Field(foreign_key="users.id")
    type: NotificationType
    title: Optional[str] = None
    message: str
    is_read: bool = False
    created_at: datetime = Field(default_factory=datetime.utcnow)

    # Relationship using forward reference
    user: "Users" = Relationship(back_populates="notifications")

# Resolve forward references at the end
from src.auth.models import Users
Notification.update_forward_refs()
