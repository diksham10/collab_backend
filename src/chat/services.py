from src.chat.models import Message, Conversation
from src.event.models import EventApplication, Event
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import distinct, select, or_, and_, func, any_
from uuid import UUID
from typing import List, Optional
from datetime import datetime


async def create_message(
    *,
    sender_id,
    receiver_id,
    content,
    db: AsyncSession,
    event_id=None,
    application_id=None
):
    message = Message(
        sender_id=sender_id,
        receiver_id=receiver_id,
        content=content,
        event_id=event_id,
        application_id=application_id
    )

    try:
        db.add(message)
        await db.commit()
        await db.refresh(message)
    except Exception as e:
        await db.rollback()
        raise e
    return message

async def get_undeliverd_messages(
    user_id,
    other_user_id,
    db: AsyncSession
):
    result = await db.execute(
        select(Message).where(
            Message.receiver_id == user_id,
            Message.sender_id == other_user_id,
            Message.is_delivered == False
        )
    )
    messages = result.scalars().all()
    await db.commit()
    return messages


async def get_chatable_users(user_id: UUID, db: AsyncSession) -> List[UUID]:
    """Get list of user IDs that this user can chat with (based on accepted applications)"""
    from src.auth.models import Users
    from src.influencer.models import InfluencerProfile
    from src.brand.models import BrandProfile
    
    # Get current user
    result = await db.execute(select(Users).where(Users.id == user_id))
    current_user = result.scalar_one_or_none()
    if not current_user:
        return []
    
    chatable_user_ids = []
    
    if current_user.role == "brand":
        # ✅ FIXED: Use scalars().first() instead of scalar_one_or_none()
        brand_result = await db.execute(
            select(BrandProfile.id).where(BrandProfile.user_id == user_id)
        )
        brand_profile_id = brand_result.scalars().first()
        
        if not brand_profile_id:
            return []
        
        result = await db.execute(
            select(distinct(InfluencerProfile.user_id))
            .join(EventApplication, EventApplication.influencer_id == InfluencerProfile.id)
            .join(Event, Event.id == EventApplication.event_id)
            .where(
                and_(
                    Event.brand_id == brand_profile_id,
                    EventApplication.status == "accepted"
                )
            )
        )
        chatable_user_ids = list(result.scalars().all())
    
    elif current_user.role == "influencer":
        # ✅ FIXED: Use scalars().first() instead of scalar_one_or_none()
        influencer_result = await db.execute(
            select(InfluencerProfile.id).where(InfluencerProfile.user_id == user_id)
        )
        influencer_profile_id = influencer_result.scalars().first()
        
        if not influencer_profile_id:
            return []
        
        result = await db.execute(
            select(distinct(BrandProfile.user_id))
            .join(Event, Event.brand_id == BrandProfile.id)
            .join(EventApplication, EventApplication.event_id == Event.id)
            .where(
                and_(
                    EventApplication.influencer_id == influencer_profile_id,
                    EventApplication.status == "accepted"
                )
            )
        )
        chatable_user_ids = list(result.scalars().all())
    
    return chatable_user_ids


# ==================== CONVERSATION SERVICES ====================

async def get_or_create_direct_conversation(
    user1_id: UUID,
    user2_id: UUID,
    db: AsyncSession
) -> Conversation:
    """Get existing direct conversation between two users or create new one"""
    # Sort user IDs to ensure consistent ordering
    participant_ids = sorted([user1_id, user2_id], key=str)
    
    # Check if conversation already exists
    result = await db.execute(
        select(Conversation).where(
            and_(
                Conversation.type == "DIRECT",
                Conversation.participant_ids == participant_ids
            )
        )
    )
    conversation = result.scalar_one_or_none()
    
    if conversation:
        return conversation
    
    # Create new direct conversation
    conversation = Conversation(
        type="DIRECT",
        participant_ids=participant_ids,
        created_by_id=user1_id,
        last_message_at=datetime.utcnow()
    )
    
    db.add(conversation)
    await db.commit()
    await db.refresh(conversation)
    return conversation


async def create_group_conversation(
    name: str,
    creator_id: UUID,
    participant_ids: List[UUID],
    db: AsyncSession,
    description: Optional[str] = None,
    avatar_url: Optional[str] = None
) -> Conversation:
    """Create a new group conversation"""
    # Ensure creator is in participants
    if creator_id not in participant_ids:
        participant_ids.append(creator_id)
    
    conversation = Conversation(
        type="GROUP",
        name=name,
        description=description,
        avatar_url=avatar_url,
        participant_ids=participant_ids,
        admin_ids=[creator_id],
        created_by_id=creator_id,
        last_message_at=datetime.utcnow()
    )
    
    db.add(conversation)
    await db.commit()
    await db.refresh(conversation)
    return conversation


async def add_participants_to_conversation(
    conversation_id: UUID,
    user_ids: List[UUID],
    db: AsyncSession
) -> Conversation:
    """Add participants to a conversation"""
    result = await db.execute(
        select(Conversation).where(Conversation.id == conversation_id)
    )
    conversation = result.scalar_one_or_none()
    
    if not conversation:
        raise ValueError("Conversation not found")
    
    # Add new participants (avoiding duplicates)
    current_participants = set(conversation.participant_ids)
    current_participants.update(user_ids)
    conversation.participant_ids = list(current_participants)
    
    await db.commit()
    await db.refresh(conversation)
    return conversation


async def remove_participant_from_conversation(
    conversation_id: UUID,
    user_id: UUID,
    db: AsyncSession
) -> Conversation:
    """Remove a participant from a conversation"""
    result = await db.execute(
        select(Conversation).where(Conversation.id == conversation_id)
    )
    conversation = result.scalar_one_or_none()
    
    if not conversation:
        raise ValueError("Conversation not found")
    
    if user_id in conversation.participant_ids:
        conversation.participant_ids = [
            pid for pid in conversation.participant_ids if pid != user_id
        ]
    
    # Remove from admins too if present
    if conversation.admin_ids and user_id in conversation.admin_ids:
        conversation.admin_ids = [
            aid for aid in conversation.admin_ids if aid != user_id
        ]
    
    await db.commit()
    await db.refresh(conversation)
    return conversation


async def create_message_in_conversation(
    conversation_id: UUID,
    sender_id: UUID,
    content: str,
    db: AsyncSession,
    message_type: str = "TEXT"
) -> Message:
    """Create a message in a conversation"""
    # Verify conversation exists and user is participant
    result = await db.execute(
        select(Conversation).where(Conversation.id == conversation_id)
    )
    conversation = result.scalar_one_or_none()
    
    if not conversation:
        raise ValueError("Conversation not found")
    
    if sender_id not in conversation.participant_ids:
        raise ValueError("User is not a participant in this conversation")
    
    # For direct chats, set receiver_id for backward compatibility
    receiver_id = None
    if conversation.type == "DIRECT":
        receiver_id = next(
            (uid for uid in conversation.participant_ids if uid != sender_id),
            None
        )
    
    message = Message(
        conversation_id=conversation_id,
        sender_id=sender_id,
        receiver_id=receiver_id,  # For backward compatibility
        content=content,
        type=message_type,
        delivered_to=[],
        read_by=[sender_id]  # Sender auto-reads their own message
    )
    
    db.add(message)
    await db.flush()  # Flush to generate message.id before using it
    
    # Update conversation's last message (now that message.id exists)
    conversation.last_message_id = message.id
    conversation.last_message_at = datetime.utcnow()
    
    # Increment unread counts for all participants except sender
    unread_counts = conversation.unread_counts or {}
    for participant_id in conversation.participant_ids:
        if participant_id != sender_id:
            current_count = unread_counts.get(str(participant_id), 0)
            unread_counts[str(participant_id)] = current_count + 1
    
    conversation.unread_counts = unread_counts
    
    await db.commit()
    await db.refresh(message)
    await db.refresh(conversation)
    
    return message


async def mark_conversation_as_read(
    conversation_id: UUID,
    user_id: UUID,
    db: AsyncSession
) -> Conversation:
    """Mark all messages in a conversation as read for a user"""
    result = await db.execute(
        select(Conversation).where(Conversation.id == conversation_id)
    )
    conversation = result.scalar_one_or_none()
    
    if not conversation:
        raise ValueError("Conversation not found")
    
    if user_id not in conversation.participant_ids:
        raise ValueError("User is not a participant")
    
    # Reset unread count for this user
    unread_counts = conversation.unread_counts or {}
    unread_counts[str(user_id)] = 0
    conversation.unread_counts = unread_counts
    
    # Update read_by arrays (PostgreSQL array append) only for messages not already read
    from sqlalchemy import update, not_
    await db.execute(
        update(Message)
        .where(
            and_(
                Message.conversation_id == conversation_id,
                Message.sender_id != user_id,
                not_(user_id == any_(Message.read_by))
            )
        )
        .values(read_by=func.array_append(Message.read_by, user_id))
    )
    
    await db.commit()
    await db.refresh(conversation)
    return conversation


async def get_conversation_messages(
    conversation_id: UUID,
    db: AsyncSession,
    limit: int = 50,
    offset: int = 0
) -> List[Message]:
    """Get messages from a conversation with pagination"""
    result = await db.execute(
        select(Message)
        .where(Message.conversation_id == conversation_id)
        .order_by(Message.sent_at.desc())
        .limit(limit)
        .offset(offset)
    )
    messages = result.scalars().all()
    return list(reversed(messages))  # Return in chronological order


async def get_user_conversations(
    user_id: UUID,
    db: AsyncSession
) -> List[Conversation]:
    """Get all conversations for a user"""
    result = await db.execute(
        select(Conversation)
        .where(user_id == any_(Conversation.participant_ids))
        .order_by(Conversation.last_message_at.desc())
    )
    conversations = result.scalars().all()
    return list(conversations)

