from typing import Optional, TYPE_CHECKING
from datetime import datetime
from sqlmodel import SQLModel, Field, Relationship, Column, ForeignKey
from uuid import UUID, uuid4
from sqlalchemy.orm import Mapped

if TYPE_CHECKING:
    from auth.models import Users  # type hint only
    from event.models import Event

class Message(SQLModel, table=True):
    __tablename__ = "message"

    id: Optional[UUID] = Field(default_factory=uuid4, primary_key=True)
    sender_id: UUID = Field(
        sa_column=Column(ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    )
    receiver_id: UUID = Field(
        sa_column=Column(ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    )
    event_id: Optional[UUID] = Field(
        default=None,
        sa_column=Column(ForeignKey("event.id", ondelete="CASCADE"), nullable=True)
    )
    application_id: Optional[UUID] = Field(
        default=None,
        sa_column=Column(ForeignKey("eventapplication.id", ondelete="CASCADE"), nullable=True)
    )
    content: str
    sent_at: datetime = Field(default_factory=datetime.utcnow)
    is_read: bool = False
    is_delivered: bool = False

    # Relationships (use forward references as strings)
    sender: Mapped["Users"] = Relationship(
        back_populates="sent_messages",
        sa_relationship_kwargs={"foreign_keys": "[Message.sender_id]"}
    )
    receiver: Mapped["Users"] = Relationship(
        back_populates="received_messages",
        sa_relationship_kwargs={"foreign_keys": "[Message.receiver_id]"}
    )
    application: Mapped[Optional["EventApplication"]] = Relationship(
            back_populates="messages",
            sa_relationship_kwargs={"foreign_keys": "[Message.application_id]"}
        )     
     # forward reference

# Resolve forward references at the end
from src.auth.models import Users
from src.event.models import EventApplication

Message.update_forward_refs()
