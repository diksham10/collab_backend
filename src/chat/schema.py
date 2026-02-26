from pydantic import BaseModel
from uuid import UUID
from datetime import datetime
from typing import List, Optional, Dict


# ==================== MESSAGE SCHEMAS ====================

class MessageCreate(BaseModel):
    content: str
    type: str = "TEXT"


class MessageResponse(BaseModel):
    id: UUID
    conversation_id: Optional[UUID]
    sender_id: UUID
    receiver_id: Optional[UUID]
    content: str
    type: str
    sent_at: datetime
    edited_at: Optional[datetime]
    deleted_at: Optional[datetime]
    read_by: List[UUID]
    delivered_to: List[UUID]
    is_read: bool
    is_delivered: bool

    class Config:
        from_attributes = True


# ==================== CONVERSATION SCHEMAS ====================

class ConversationCreate(BaseModel):
    type: str  # "DIRECT" or "GROUP"
    participant_ids: List[UUID]
    name: Optional[str] = None
    description: Optional[str] = None
    avatar_url: Optional[str] = None


class DirectConversationCreate(BaseModel):
    other_user_id: UUID


class GroupConversationCreate(BaseModel):
    name: str
    participant_ids: List[UUID]
    description: Optional[str] = None
    avatar_url: Optional[str] = None


class ParticipantInfo(BaseModel):
    id: UUID
    username: str
    email: str
    role: str
    
    class Config:
        from_attributes = True


class ConversationResponse(BaseModel):
    id: UUID
    type: str
    participant_ids: List[UUID]
    name: Optional[str]
    avatar_url: Optional[str]
    description: Optional[str]
    created_by_id: UUID
    admin_ids: Optional[List[UUID]]
    unread_counts: Dict[str, int]
    last_message_id: Optional[UUID]
    last_message_at: datetime
    created_at: datetime
    updated_at: datetime
    
    # Optional fields populated by router
    participants: Optional[List[ParticipantInfo]] = None
    last_message: Optional[MessageResponse] = None
    unread_count: Optional[int] = None  # For current user
    
    class Config:
        from_attributes = True


class ConversationWithMessagesResponse(BaseModel):
    conversation: ConversationResponse
    messages: List[MessageResponse]
    total_messages: int


class AddParticipantsRequest(BaseModel):
    user_ids: List[UUID]
