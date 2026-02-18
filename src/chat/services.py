from src.chat.models import Message
from src.event.models import EventApplication
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, or_, and_
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
    from src.influencer.models import Influencer
    from src.brand.models import Brand
    
    # Get current user
    result = await db.execute(select(Users).where(Users.id == user_id))
    current_user = result.scalar_one_or_none()
    if not current_user:
        return []
    
    chatable_user_ids = []
    
    # If brand, get influencers from accepted applications
    if current_user.role == "brand":
        result = await db.execute(
            select(Brand).where(Brand.user_id == user_id)
        )
        brand = result.scalar_one_or_none()
        if brand:
            result = await db.execute(
                select(EventApplication)
                .where(
                    and_(
                        EventApplication.brand_id == brand.id,
                        EventApplication.status == "accepted"
                    )
                )
            )
            applications = result.scalars().all()
            for app in applications:
                # Get influencer's user_id
                result = await db.execute(
                    select(Influencer).where(Influencer.id == app.influencer_id)
                )
                influencer = result.scalar_one_or_none()
                if influencer:
                    chatable_user_ids.append(influencer.user_id)
    
    # If influencer, get brands from accepted applications
    elif current_user.role == "influencer":
        result = await db.execute(
            select(Influencer).where(Influencer.user_id == user_id)
        )
        influencer = result.scalar_one_or_none()
        if influencer:
            result = await db.execute(
                select(EventApplication)
                .where(
                    and_(
                        EventApplication.influencer_id == influencer.id,
                        EventApplication.status == "accepted"
                    )
                )
            )
            applications = result.scalars().all()
            for app in applications:
                # Get brand's user_id
                result = await db.execute(
                    select(Brand).where(Brand.id == app.brand_id)
                )
                brand = result.scalar_one_or_none()
                if brand:
                    chatable_user_ids.append(brand.user_id)
    
    return chatable_user_ids


