from typing import Optional, TYPE_CHECKING, List
from datetime import datetime
from sqlmodel import SQLModel, Field, Relationship, Column, ForeignKey
from sqlalchemy import ARRAY, Text
from sqlalchemy.dialects.postgresql import UUID as PostgresUUID, JSONB
from uuid import UUID, uuid4
from sqlalchemy.orm import Mapped

if TYPE_CHECKING:
    from auth.models import Users
    from event.models import Event


# Conversation Model for Group Chat Support
class Conversation(SQLModel, table=True):
    __tablename__ = "conversations"
    
    id: Optional[UUID] = Field(default_factory=uuid4, primary_key=True, index=True)
    type: str = Field(default="DIRECT")  # DIRECT or GROUP
    
    # PostgreSQL ARRAY for participant UUIDs
    participant_ids: List[UUID] = Field(sa_column=Column(ARRAY(PostgresUUID(as_uuid=True)), nullable=False))
    
    # Group metadata (NULL for direct chats)
    name: Optional[str] = Field(default=None, max_length=100)
    avatar_url: Optional[str] = Field(default=None, max_length=500)
    description: Optional[str] = Field(default=None, sa_column=Column(Text))
    
    created_by_id: Optional[UUID] = Field(default=None, foreign_key="users.id")
    
    # Admin IDs for group chats
    admin_ids: Optional[List[UUID]] = Field(default=None, sa_column=Column(ARRAY(PostgresUUID(as_uuid=True))))
    
    # Per-user unread counts as JSONB
    unread_counts: dict = Field(default_factory=dict, sa_column=Column(JSONB, nullable=False, server_default='{}'))
    
    # FIXED: Remove FK constraint to avoid circular dependency
    last_message_id: Optional[UUID] = Field(default=None)
    last_message_at: datetime = Field(default_factory=datetime.utcnow)
    
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)
    
    # Relationships
    created_by: Optional["Users"] = Relationship(
        back_populates="created_conversations",
        sa_relationship_kwargs={"foreign_keys": "[Conversation.created_by_id]"}
    )
    
    last_message: Optional["Message"] = Relationship(
        sa_relationship_kwargs={
            "primaryjoin": "Conversation.last_message_id == Message.id",
            "foreign_keys": "[Conversation.last_message_id]",
            "post_update": True,
            "uselist": False,
            "viewonly": True  # Prevents circular dependency issues
        }
    )
    
    messages: Mapped[List["Message"]] = Relationship(
        back_populates="conversation",
        sa_relationship_kwargs={
            "foreign_keys": "[Message.conversation_id]",
            "cascade": "all, delete-orphan"
        }
    )


class Message(SQLModel, table=True):
    __tablename__ = "message"

    id: Optional[UUID] = Field(default_factory=uuid4, primary_key=True)
    
    sender_id: UUID = Field(
        sa_column=Column(ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    )
    
    # FIXED: Make receiver_id optional for group chats
    receiver_id: Optional[UUID] = Field(
        default=None,
        sa_column=Column(ForeignKey("users.id", ondelete="CASCADE"), nullable=True)
    )
    
    # FIXED: Add index for performance
    conversation_id: Optional[UUID] = Field(
        default=None,
        sa_column=Column(
            ForeignKey("conversations.id", ondelete="CASCADE"),
            nullable=True,
            index=True  # Performance optimization
        )
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
    type: str = Field(default="TEXT")  # TEXT, IMAGE, or SYSTEM
    
    # Arrays for read receipts (for group chats)
    read_by: List[UUID] = Field(
        default_factory=list,
        sa_column=Column(ARRAY(PostgresUUID(as_uuid=True)), nullable=False, server_default='{}')
    )
    delivered_to: List[UUID] = Field(
        default_factory=list,
        sa_column=Column(ARRAY(PostgresUUID(as_uuid=True)), nullable=False, server_default='{}')
    )
    
    sent_at: datetime = Field(default_factory=datetime.utcnow)
    edited_at: Optional[datetime] = None
    deleted_at: Optional[datetime] = None
    is_read: bool = False
    is_delivered: bool = False

    # Relationships
    sender: Mapped["Users"] = Relationship(
        back_populates="sent_messages",
        sa_relationship_kwargs={"foreign_keys": "[Message.sender_id]"}
    )
    
    receiver: Mapped[Optional["Users"]] = Relationship(
        back_populates="received_messages",
        sa_relationship_kwargs={"foreign_keys": "[Message.receiver_id]"}
    )
    
    conversation: Optional["Conversation"] = Relationship(
        back_populates="messages",
        sa_relationship_kwargs={"foreign_keys": "[Message.conversation_id]"}
    )
    
    application: Mapped[Optional["EventApplication"]] = Relationship(
        back_populates="messages",
        sa_relationship_kwargs={"foreign_keys": "[Message.application_id]"}
    )


# Resolve forward references
from src.auth.models import Users
from src.event.models import EventApplication

Conversation.update_forward_refs()
Message.update_forward_refs()