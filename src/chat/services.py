from src.chat.models import Message
from src.event.models import EventApplication, Event
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import distinct, select, or_, and_
from uuid import UUID
from typing import List


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


