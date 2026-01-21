from fastapi import APIRouter, Depends, WebSocket, WebSocketDisconnect
from uuid import UUID
from sqlalchemy import and_, or_, desc, select
from sqlalchemy.ext.asyncio import AsyncSession
from src.auth.dependencies import get_current_user_ws, get_current_user
from src.auth.models import Users
from src.chat.services import create_message, get_undeliverd_messages
from src.chat.connection import ConnectionManager
from src.chat.models import Message

from src.database import get_session


router = APIRouter()

manager = ConnectionManager()

@router.websocket("/ws/chat/{other_user_id}")
async def chat_ws(
    websocket: WebSocket,
    other_user_id: UUID
):
    #Authenticate user via cookie
    async with get_session() as db:
        user = await get_current_user_ws(websocket, db)
        if not user:
            await websocket.close(code=1008)
            return
        
    # Connect socket
    await manager.connect(user.id, websocket)

    # get undeliverd messages
    
    try:
        async with get_session() as db:
            undelivered_messages = await get_undeliverd_messages(
                user.id,
                other_user_id,
                db
            )
            for msg in undelivered_messages:
                msg.is_delivered = True
                await websocket.send_json({
                    "id": str(msg.id),
                    "sender_id": str(msg.sender_id),
                    "receiver_id": str(msg.receiver_id),
                    "content": msg.content,
                    "sent_at": msg.sent_at.isoformat(),
                    "is_read": msg.is_read,
                    "is_delivered": msg.is_delivered
                })
            await db.commit()
    except Exception as e:
        print(f"Error fetching undelivered messages: {e}")

    #need to get each session for each websocket because they are independent we cannot share session beacause of concurrency issues
    try:
        while True:
            data = await websocket.receive_json()
            receiver_id = other_user_id
            content = data.get("content")
            if not content:
                continue
            
            # # Save message to DB
            async with get_session() as db:

                new_msg = await create_message(
                    sender_id=user.id,
                    receiver_id=receiver_id,
                    content=content,
                    db=db
                )
                await db.commit()

            payload = {
                "id": str(new_msg.id),
                "sender_id": str(new_msg.sender_id),
                "receiver_id": str(new_msg.receiver_id),
                "content": new_msg.content,
                "sent_at": new_msg.sent_at.isoformat(),
                "is_read": new_msg.is_read,
                "is_delivered": new_msg.is_delivered
            }

            # Send to receiver if online
            await manager.send_to_user(receiver_id,payload)

            await websocket.send_json(payload)

    except WebSocketDisconnect:
        await manager.disconnect(user.id, websocket)




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
