from typing import Optional, TYPE_CHECKING
from datetime import datetime
from sqlmodel import SQLModel, Field, Relationship
from uuid import UUID, uuid4

if TYPE_CHECKING:
    from auth.models import Users  # type hint only
    from event.models import Event

class Message(SQLModel, table=True):
    id: Optional[UUID] = Field(default_factory=uuid4, primary_key=True)
    sender_id: UUID = Field(foreign_key="users.id")
    receiver_id: UUID = Field(foreign_key="users.id")
    event_id: Optional[UUID] = Field(default=None, foreign_key="event.id")
    application_id: Optional[UUID] = Field(default=None, foreign_key="eventapplication.id")
    content: str
    sent_at: datetime = Field(default_factory=datetime.utcnow)
    is_read: bool = False

    # Relationships (use forward references as strings)
    sender: "Users" = Relationship(
        back_populates="sent_messages",
        sa_relationship_kwargs={"foreign_keys": "[Message.sender_id]"}
    )
    receiver: "Users" = Relationship(
        back_populates="received_messages",
        sa_relationship_kwargs={"foreign_keys": "[Message.receiver_id]"}
    )
    application: Optional["EventApplication"] = Relationship(back_populates="messages")
      # forward reference

# Resolve forward references at the end
from src.auth.models import Users
from src.event.models import EventApplication

Message.update_forward_refs()
