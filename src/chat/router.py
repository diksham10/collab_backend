# filepath: /home/dick_endra/Documents/collab-backend/src/chat/router.py
from fastapi import APIRouter, WebSocket, WebSocketDisconnect, Depends, HTTPException, status
from src.chat.connection import manager
from src.auth.dependencies import get_current_user,get_current_user_ws
from src.database import get_session, AsyncSessionLocal
from sqlalchemy.ext.asyncio import AsyncSession
from src.chat.services import get_chatable_users, create_message, get_undeliverd_messages
from uuid import UUID
from src.database import get_session as get_db
import json

router = APIRouter(prefix="/chat", tags=["Chat"])


@router.websocket("/ws/chat/{other_user_id}")
async def chat_ws(
    websocket: WebSocket,
    other_user_id: UUID,
):
    """WebSocket endpoint for real-time chat"""
    
    print(f"🔗 WebSocket connection attempt to chat with {other_user_id}")
    print(f"📋 Query params: {dict(websocket.query_params)}")
    print(f"🍪 Cookies: {list(websocket.cookies.keys())}")
    
    #Authenticate user via cookie or query param
    async with AsyncSessionLocal() as db:
        try:
            # Try cookie first
            user = await get_current_user_ws(websocket, db)
            
            # If cookie auth fails, try query param token
            if not user:
                token = websocket.query_params.get("token")
                if token:
                    print(f"🔑 Trying token from query params")
                    from src.auth.service import verify_access_token
                    user = await verify_access_token(token, db)
            
            if not user:
                print(f"❌ WebSocket auth failed: No valid token found")
                await websocket.close(code=1008)
                return
            
            print(f"✅ WebSocket authenticated: User {user.id} ({user.role})")
        except Exception as e:
            print(f"❌ WebSocket auth exception: {e}")
            import traceback
            traceback.print_exc()
            await websocket.close(code=1008)
            return
    
    # Verify users can chat
    async with AsyncSessionLocal() as db:
        # ✅ Check if other_user_id is a BrandProfile.id and convert to user_id
        from src.brand.models import BrandProfile
        from src.influencer.models import InfluencerProfile
        from sqlalchemy import select
        
        actual_user_id = other_user_id
        
        # Try to find if it's a brand profile ID
        result = await db.execute(
            select(BrandProfile.user_id).where(BrandProfile.id == other_user_id)
        )
        brand_user_id = result.scalar_one_or_none()
        
        if brand_user_id:
            print(f"🔄 Converted BrandProfile.id {other_user_id} → user_id {brand_user_id}")
            actual_user_id = brand_user_id
        else:
            # Try to find if it's an influencer profile ID
            result = await db.execute(
                select(InfluencerProfile.user_id).where(InfluencerProfile.id == other_user_id)
            )
            influencer_user_id = result.scalar_one_or_none()
            
            if influencer_user_id:
                print(f"🔄 Converted InfluencerProfile.id {other_user_id} → user_id {influencer_user_id}")
                actual_user_id = influencer_user_id
        
        # Now verify with converted user_id
        chatable_users = await get_chatable_users(user.id, db)
        
        print(f"🔍 User {user.id} ({user.role}) trying to chat with {actual_user_id}")
        print(f"📋 Chatable users: {[str(u) for u in chatable_users]}")
        
        if actual_user_id not in chatable_users:
            print(f"❌ User {user.id} cannot chat with {actual_user_id}")
            await websocket.close(code=status.WS_1003_UNSUPPORTED_DATA)
            return
        
        print(f"✅ User {user.id} authorized to chat with {actual_user_id}")
        other_user_id = actual_user_id  # Use converted ID for rest of function

    
    # Connect
    await manager.connect(user.id, websocket)
    
    try:
        # Send undelivered messages
        async with AsyncSessionLocal() as db:
            undelivered = await get_undeliverd_messages(user.id, other_user_id, db)
            for msg in undelivered:
                await websocket.send_json({
                    "type": "message",
                    "id": str(msg.id),
                    "sender_id": str(msg.sender_id),
                    "receiver_id": str(msg.receiver_id),
                    "content": msg.content,
                    "sent_at": msg.sent_at.isoformat(),
                    "is_delivered": msg.is_delivered,
                    "is_read": msg.is_read
                })
        
        # Main loop
        while True:
            data = await websocket.receive_json()
            message_type = data.get("type", "message")  # Default to message for backward compatibility
            
            if message_type == "message":
                content = data.get("content")
                if not content:
                    continue
                
                # Save to DB
                async with AsyncSessionLocal() as db:
                    new_msg = await create_message(
                        sender_id=user.id,
                        receiver_id=other_user_id,
                        content=content,
                        db=db
                    )
                    await db.commit()
                
                # Prepare payload
                payload = {
                    "type": "message",  # ✅ ADDED
                    "id": str(new_msg.id),
                    "sender_id": str(new_msg.sender_id),
                    "receiver_id": str(new_msg.receiver_id),
                    "content": new_msg.content,
                    "sent_at": new_msg.sent_at.isoformat(),
                    "is_read": new_msg.is_read,
                    "is_delivered": new_msg.is_delivered
                }
                
                # Send to receiver via Redis
                await manager.send_message(other_user_id, payload)  # ✅ FIXED method name
                
                # Echo back to sender
                await websocket.send_json(payload)  # ✅ ADDED
                
                print(f"💬 Message sent: {user.id} → {other_user_id}")
            
            elif message_type == "typing":
                await manager.send_typing_indicator(
                    from_user_id=user.id,
                    to_user_id=other_user_id,
                    is_typing=data.get("is_typing", False)
                )
            
            elif message_type == "read":
                message_id = UUID(data.get("message_id"))
                
                # Update DB
                from sqlalchemy import update
                from src.chat.models import Message
                async with AsyncSessionLocal() as db:
                    await db.execute(
                        update(Message)
                        .where(Message.id == message_id)
                        .values(is_read=True)
                    )
                    await db.commit()
                
                # Send read receipt
                await manager.send_read_receipt(
                    message_id=message_id,
                    sender_id=other_user_id,
                    receiver_id=user.id
                )
            
            elif message_type == "heartbeat":
                await manager.heartbeat(user.id)
    
    except WebSocketDisconnect:
        print(f"🔌 User {user.id} WebSocket disconnected")
    except Exception as e:
        print(f"❌ WebSocket error for user {user.id}: {e}")
    finally:
        await manager.disconnect(user.id, websocket)


@router.get("/online/{user_id}")
async def check_online_status(
    user_id: UUID,
    current_user = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """Check if user is online"""
    chatable_users = await get_chatable_users(current_user.id, db)
    if user_id not in chatable_users:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Cannot check status"
        )
    
    is_online = await manager.is_online(user_id)
    return {"user_id": str(user_id), "is_online": is_online}


@router.get("/get_messages/{other_user_id}")
async def get_chat_history(
    other_user_id: UUID,
    limit: int = 50,
    offset: int = 0,
    current_user = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """Get chat history"""
    from src.chat.models import Message
    from sqlalchemy import select, or_, and_
    
    chatable_users = await get_chatable_users(current_user.id, db)
    if other_user_id not in chatable_users:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Cannot view history"
        )
    
    result = await db.execute(
        select(Message)
        .where(
            or_(
                and_(
                    Message.sender_id == current_user.id,
                    Message.receiver_id == other_user_id
                ),
                and_(
                    Message.sender_id == other_user_id,
                    Message.receiver_id == current_user.id
                )
            )
        )
        .order_by(Message.sent_at.desc())
        .limit(limit)
        .offset(offset)
    )
    
    messages = result.scalars().all()
    
    return {
        "messages": [
            {
                "id": str(msg.id),
                "sender_id": str(msg.sender_id),
                "receiver_id": str(msg.receiver_id),
                "content": msg.content,
                "sent_at": msg.sent_at.isoformat(),
                "is_delivered": msg.is_delivered,
                "is_read": msg.is_read
            }
            for msg in reversed(messages)
        ]
    }