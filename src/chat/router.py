from fastapi import APIRouter, Depends, WebSocket, WebSocketDisconnect
from uuid import UUID
from sqlalchemy import and_, or_, desc, select
from sqlalchemy.ext.asyncio import AsyncSession
from src.auth.dependencies import get_current_user
from src.auth.models import Users
from src.chat.services import create_message, get_undeliverd_messages
from src.chat.connection import ConnectionManager
from src.chat.models import Message
from src.database import get_session
from contextlib import asynccontextmanager

router = APIRouter()

manager = ConnectionManager()

@router.websocket("/ws/{user_id}/{other_user_id}")
async def websocket_endpoint(websocket: WebSocket, user_id: UUID, other_user_id: UUID):

    await manager.connect(user_id, websocket)

    #Send undelivered messages
    async with get_session() as db:
        result = await get_undeliverd_messages(user_id, other_user_id, db)
        for message in result:
            payload = {
                "id": str(message.id),
                "sender_id": str(message.sender_id),
                "receiver_id": str(message.receiver_id),
                "content": message.content,
                "sent_at": message.sent_at.isoformat(),
                "is_read": message.is_read,
                "is_delivered": message.is_delivered
            }
            await websocket.send_json(payload)
            message.is_delivered = True
        await db.commit()
        
    try:
        while True:
            data = await websocket.receive_json()

            #Store delivered message in DB
            async with get_session() as db:
                message = await create_message(
                    sender_id=data["sender_id"],
                    receiver_id=data["receiver_id"],
                    content=data["content"],
                    db=db,
                )
            
                
            payload = {
                "id": str(message.id),
                "sender_id": str(message.sender_id),
                "receiver_id": str(message.receiver_id),
                "content": message.content,
                "sent_at": message.sent_at.isoformat(),
                "is_read": message.is_read,
                "is_delivered": False
            }
            if manager.is_online(data["receiver_id"]):
                await manager.send_to_user(data["receiver_id"], payload)
                message.is_delivered = True
                payload["is_delivered"] = True

            await websocket.send_json(payload)

    except WebSocketDisconnect:
        manager.disconnect(user_id)




@router.get("/get_messages/{other_user_id}")
async def get_messages(other_user_id: UUID, limit:int = 10, offset:int = 0, db: AsyncSession = Depends(get_session), current_user: Users = Depends(get_current_user)):
    stmt =(
        select(Message)
        .where(
            or_(
                and_(Message.sender_id == current_user.id, Message.receiver_id == other_user_id),
                and_(Message.sender_id == other_user_id, Message.receiver_id == current_user.id)
            )
        )
        .order_by(desc(Message.sent_at))
        .limit(limit)
        .offset(offset)
    )

    result = await db.execute(stmt)
    messages = result.scalars().all()

    return list(reversed(messages))
