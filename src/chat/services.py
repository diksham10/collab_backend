from src.chat.models import Message
from src.event.models import EventApplication
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select


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

