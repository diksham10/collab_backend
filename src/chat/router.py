# filepath: /home/dick_endra/Documents/collab-backend/src/chat/router.py
from fastapi import APIRouter, WebSocket, WebSocketDisconnect, Depends, HTTPException, status
from src.auth.models import Users
from src.chat.connection import manager
from src.auth.dependencies import get_current_user,get_current_user_ws
from src.database import get_session, AsyncSessionLocal
from sqlalchemy.ext.asyncio import AsyncSession
from src.chat.services import (
    get_chatable_users, create_message, get_undeliverd_messages,
    get_or_create_direct_conversation, create_group_conversation,
    get_user_conversations, get_conversation_messages,
    create_message_in_conversation, mark_conversation_as_read,
    add_participants_to_conversation, remove_participant_from_conversation
)
from src.chat.schema import (
    DirectConversationCreate, GroupConversationCreate, ConversationResponse,
    MessageCreate, MessageResponse, AddParticipantsRequest, ParticipantInfo
)
from uuid import UUID
from src.database import get_session as get_db
from typing import List
from sqlalchemy import select
from src.chat.models import Conversation, Message
import json

router = APIRouter(prefix="/chat", tags=["Chat"])


# ==================== HELPER FUNCTION ====================

async def build_conversation_response(
    conv: Conversation,
    current_user_id: UUID,
    db: AsyncSession
) -> ConversationResponse:
    """
    Build ConversationResponse manually to avoid lazy loading issues.
    Also resolves display name dynamically for DIRECT chats.
    """
    # Get participant details
    result = await db.execute(
        select(Users).where(Users.id.in_(conv.participant_ids))
    )
    participants = result.scalars().all()
    
    # Get last message if exists (avoid lazy loading)
    last_msg = None
    if conv.last_message_id:
        msg_result = await db.execute(
            select(Message).where(Message.id == conv.last_message_id)
        )
        last_msg = msg_result.scalar_one_or_none()
    
    # Resolve conversation name dynamically for DIRECT chats
    display_name = conv.name
    display_avatar = conv.avatar_url
    
    if conv.type == "DIRECT":
        # For DIRECT chats, show the OTHER person's name from their profile
        for p in participants:
            if p.id != current_user_id:
                print(f"🔍 Current user: {current_user_id}, Other user: {p.id}, Role: {p.role}")
                # Get profile-specific name based on role
                if p.role == "brand":
                    from src.brand.models import BrandProfile
                    brand_result = await db.execute(
                        select(BrandProfile).where(BrandProfile.user_id == p.id)
                    )
                    brand_profile = brand_result.scalars().first()
                    if brand_profile:
                        display_name = brand_profile.name
                        print(f"✅ Brand profile found: {display_name}")
                        # display_avatar = brand_profile.logo_url or brand_profile.profile_image
                    else:
                        display_name = p.username
                        print(f"⚠️ No brand profile, using username: {display_name}")
                elif p.role == "influencer":
                    from src.influencer.models import InfluencerProfile
                    influencer_result = await db.execute(
                        select(InfluencerProfile).where(InfluencerProfile.user_id == p.id)
                    )
                    influencer_profile = influencer_result.scalars().first()
                    if influencer_profile:
                        display_name = influencer_profile.name 
                        print(f"✅ Influencer profile found: {display_name}")
                        # display_avatar = influencer_profile.profile_image
                    else:
                        display_name = p.username
                        print(f"⚠️ No influencer profile, using username: {display_name}")
                else:
                    display_name = p.username
                    print(f"⚠️ Unknown role, using username: {display_name}")
                break
    
    conv_dict = {
        'id': conv.id,
        'type': conv.type,
        'participant_ids': conv.participant_ids,
        'name': display_name,
        'avatar_url': display_avatar,
        'description': conv.description,
        'created_by_id': conv.created_by_id,
        'admin_ids': conv.admin_ids,
        'unread_counts': conv.unread_counts,
        'last_message_id': conv.last_message_id,
        'last_message_at': conv.last_message_at,
        'created_at': conv.created_at,
        'updated_at': conv.updated_at,
        'participants': [
            ParticipantInfo.model_validate(p).model_dump() for p in participants
        ],
        'last_message': MessageResponse.model_validate(last_msg).model_dump() if last_msg else None,
        'unread_count': conv.unread_counts.get(str(current_user_id), 0)
    }
    
    return ConversationResponse(**conv_dict)


# ==================== CONVERSATION ENDPOINTS ====================

@router.post("/conversations/direct", response_model=ConversationResponse)
async def create_direct_conversation(
    data: DirectConversationCreate,
    current_user:Users = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """Create or get existing direct conversation"""
    # Verify users can chat
    chatable_users = await get_chatable_users(current_user.id, db)
    if data.other_user_id not in chatable_users:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Cannot chat with this user"
        )
    
    conversation = await get_or_create_direct_conversation(
        user1_id=current_user.id,
        user2_id=data.other_user_id,
        db=db
    )
    
    return await build_conversation_response(conversation, current_user.id, db)


@router.post("/conversations/group", response_model=ConversationResponse)
async def create_group_chat(
    data: GroupConversationCreate,
    current_user: Users = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """Create a group conversation"""
    # Verify all participants are chatable
    chatable_users = await get_chatable_users(current_user.id, db)
    for participant_id in data.participant_ids:
        if participant_id not in chatable_users and participant_id != current_user.id:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"Cannot add user {participant_id} to group"
            )
    
    conversation = await create_group_conversation(
        name=data.name,
        creator_id=current_user.id,
        participant_ids=data.participant_ids,
        description=data.description,
        avatar_url=data.avatar_url,
        db=db
    )
    
    return await build_conversation_response(conversation, current_user.id, db)


@router.get("/conversations", response_model=List[ConversationResponse])
async def list_conversations(
    current_user: Users = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """Get all conversations for current user"""
    conversations = await get_user_conversations(current_user.id, db)
    
    enriched = []
    for conv in conversations:
        enriched.append(
            await build_conversation_response(conv, current_user.id, db)
        )
    
    return enriched


@router.get("/conversations/{conversation_id}/messages", response_model=List[MessageResponse])
async def get_messages(
    conversation_id: UUID,
    limit: int = 50,
    offset: int = 0,
    current_user: Users = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """Get messages from a conversation"""
    from src.chat.models import Conversation
    from sqlalchemy import select
    
    # Verify user is participant
    result = await db.execute(
        select(Conversation).where(Conversation.id == conversation_id)
    )
    conversation = result.scalar_one_or_none()
    
    if not conversation:
        raise HTTPException(status_code=404, detail="Conversation not found")
    
    if current_user.id not in conversation.participant_ids:
        raise HTTPException(status_code=403, detail="Not a participant")
    
    messages = await get_conversation_messages(conversation_id, db, limit, offset)
    return messages


@router.post("/conversations/{conversation_id}/messages", response_model=MessageResponse)
async def send_message_to_conversation(
    conversation_id: UUID,
    data: MessageCreate,
    current_user: Users = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """Send a message to a conversation"""
    try:
        message = await create_message_in_conversation(
            conversation_id=conversation_id,
            sender_id=current_user.id,
            content=data.content,
            message_type=data.type,
            db=db
        )
        
        # Broadcast to all participants via WebSocket
        from src.chat.models import Conversation
        from sqlalchemy import select
        
        result = await db.execute(
            select(Conversation).where(Conversation.id == conversation_id)
        )
        conversation = result.scalar_one_or_none()
        
        if conversation:
            payload = {
                "type": "message",
                "id": str(message.id),
                "conversation_id": str(conversation_id),
                "sender_id": str(message.sender_id),
                "content": message.content,
                "sent_at": message.sent_at.isoformat(),
                "message_type": message.type
            }
            
            # Send to all participants except sender
            for participant_id in conversation.participant_ids:
                if participant_id != current_user.id:
                    await manager.send_message(participant_id, payload)
        
        return message
        
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


# ==================== WEBSOCKET ENDPOINT====================

@router.websocket("/ws/conversation/{conversation_id}")
async def conversation_websocket(
    websocket: WebSocket,
    conversation_id: UUID,
):
    """
    WebSocket endpoint for real-time chat in a conversation.
    
    This handles:
    - Step 3: Authenticate → Verify participant → Connect → Send history
    - Step 4: Receive messages → Save → Broadcast → Echo
    """
    
    print(f"🔗 WebSocket connection attempt to conversation {conversation_id}")
    
    # ============ STEP 3.1: AUTHENTICATE ============
    async with AsyncSessionLocal() as db:
        try:
            # Try cookie authentication first
            user = await get_current_user_ws(websocket, db)
            
            if not user:
                # Fallback to query parameter token
                token = websocket.query_params.get("token")
                if token:
                    from src.auth.service import verify_access_token
                    user = await verify_access_token(token, db)
            
            if not user:
                print("❌ Authentication failed")
                await websocket.close(code=1008)  # Policy Violation
                return
            
            print(f"✅ User authenticated: {user.username} ({user.id})")
            
        except Exception as e:
            print(f"❌ Authentication error: {e}")
            await websocket.close(code=1008)
            return
    
    # ============ STEP 3.2: VERIFY PARTICIPANT ============
    async with AsyncSessionLocal() as db:
        from src.chat.models import Conversation
        from sqlalchemy import select
        
        result = await db.execute(
            select(Conversation).where(Conversation.id == conversation_id)
        )
        conversation = result.scalar_one_or_none()
        
        if not conversation:
            print(f"❌ Conversation {conversation_id} not found")
            await websocket.close(code=1003)  # Unsupported Data
            return
        
        if user.id not in conversation.participant_ids:
            print(f"❌ User {user.id} is not a participant in conversation {conversation_id}")
            await websocket.close(code=1003)
            return
        
        print(f"✅ User {user.username} is a participant in conversation {conversation_id}")
    
    # ============ STEP 3.3: CONNECT ============
    await manager.connect(user.id, websocket)
    print(f"✅ WebSocket connected: {user.username} → conversation {conversation_id}")
    
    try:
        # ============ STEP 3.4: SEND HISTORY ============
        async with AsyncSessionLocal() as db:
            # Get last 50 messages
            messages = await get_conversation_messages(conversation_id, db, limit=50)
            
            print(f"📤 Sending {len(messages)} historical messages to {user.username}")
            
            for msg in messages:
                await websocket.send_json({
                    "type": "message",
                    "id": str(msg.id),
                    "conversation_id": str(msg.conversation_id),
                    "sender_id": str(msg.sender_id),
                    "content": msg.content,
                    "sent_at": msg.sent_at.isoformat(),
                    "message_type": msg.type,
                    "read_by": [str(uid) for uid in msg.read_by],
                    "delivered_to": [str(uid) for uid in msg.delivered_to]
                })
        
        print(f"✅ History sent to {user.username}")
        
        # ============ STEP 3.5: ENTER MESSAGE LOOP ============
        while True:
            # Wait for incoming message from client
            data = await websocket.receive_json()
            message_type = data.get("type", "message")
            
            print(f"📨 Received {message_type} from {user.username}: {data}")
            
            # ============ STEP 4: HANDLE MESSAGE TYPES ============
            
            if message_type == "message":
                # ============ STEP 4.1: EXTRACT CONTENT ============
                content = data.get("content")
                if not content:
                    print("⚠️ Empty content, skipping")
                    continue
                
                msg_type = data.get("message_type", "TEXT")
                
                # ============ STEP 4.2: SAVE TO DATABASE ============
                async with AsyncSessionLocal() as db:
                    new_msg = await create_message_in_conversation(
                        conversation_id=conversation_id,
                        sender_id=user.id,
                        content=content,
                        message_type=msg_type,
                        db=db
                    )
                    
                    print(f"✅ Message saved to DB: {new_msg.id}")
                    
                    # ============ STEP 4.3: GET PARTICIPANTS ============
                    result = await db.execute(
                        select(Conversation).where(Conversation.id == conversation_id)
                    )
                    conversation = result.scalar_one_or_none()
                    
                    # ============ STEP 4.4: PREPARE PAYLOAD ============
                    payload = {
                        "type": "message",
                        "id": str(new_msg.id),
                        "conversation_id": str(conversation_id),
                        "sender_id": str(new_msg.sender_id),
                        "content": new_msg.content,
                        "sent_at": new_msg.sent_at.isoformat(),
                        "message_type": new_msg.type,
                        "read_by": [str(uid) for uid in new_msg.read_by],
                        "delivered_to": [str(uid) for uid in new_msg.delivered_to]
                    }
                    
                    # ============ STEP 4.5: BROADCAST TO PARTICIPANTS ============
                    if conversation:
                        for participant_id in conversation.participant_ids:
                            if participant_id != user.id:
                                await manager.send_message(participant_id, payload)
                                print(f"📤 Broadcast to participant {participant_id}")
                    
                    # ============ STEP 4.6: ECHO TO SENDER ============
                    await websocket.send_json(payload)
                    print(f"✅ Echo sent to sender {user.username}")
            
            elif message_type == "typing":
                # ============ TYPING INDICATOR (NOT SAVED) ============
                async with AsyncSessionLocal() as db:
                    result = await db.execute(
                        select(Conversation).where(Conversation.id == conversation_id)
                    )
                    conversation = result.scalar_one_or_none()
                    
                    if conversation:
                        typing_payload = {
                            "type": "typing",
                            "conversation_id": str(conversation_id),
                            "user_id": str(user.id),
                            "is_typing": data.get("is_typing", False)
                        }
                        
                        # Broadcast to all except sender
                        for participant_id in conversation.participant_ids:
                            if participant_id != user.id:
                                await manager.send_message(participant_id, typing_payload)
                        
                        print(f"📢 Typing indicator broadcast from {user.username}")
            
            elif message_type == "read":
                # ============ MARK AS READ ============
                async with AsyncSessionLocal() as db:
                    await mark_conversation_as_read(
                        conversation_id=conversation_id,
                        user_id=user.id,
                        db=db
                    )
                    
                    print(f"✅ Conversation marked as read by {user.username}")
                    
                    # Broadcast read receipt
                    result = await db.execute(
                        select(Conversation).where(Conversation.id == conversation_id)
                    )
                    conversation = result.scalar_one_or_none()
                    
                    if conversation:
                        read_payload = {
                            "type": "read_receipt",
                            "conversation_id": str(conversation_id),
                            "user_id": str(user.id)
                        }
                        
                        for participant_id in conversation.participant_ids:
                            if participant_id != user.id:
                                await manager.send_message(participant_id, read_payload)
                        
                        print(f"📢 Read receipt broadcast from {user.username}")
            
            elif message_type == "heartbeat":
                # ============ KEEP ALIVE ============
                await manager.heartbeat(user.id)
                print(f"💓 Heartbeat from {user.username}")
    
    except WebSocketDisconnect:
        print(f"🔌 User {user.username} disconnected from conversation {conversation_id}")
    
    except Exception as e:
        print(f"❌ WebSocket error for user {user.username}: {e}")
        import traceback
        traceback.print_exc()
    
    finally:
        # ============ CLEANUP ============
        await manager.disconnect(user.id, websocket)
        print(f"🧹 Cleaned up connection for {user.username}")


@router.patch("/conversations/{conversation_id}/read", response_model=ConversationResponse)
async def mark_as_read(
    conversation_id: UUID,
    current_user: Users = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """Mark conversation as read"""
    try:
        conversation = await mark_conversation_as_read(
            conversation_id=conversation_id,
            user_id=current_user.id,
            db=db
        )
        return await build_conversation_response(conversation, current_user.id, db)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.post("/conversations/{conversation_id}/participants")
async def add_participants(
    conversation_id: UUID,
    data: AddParticipantsRequest,
    current_user: Users = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """Add participants to a group conversation"""
    from src.chat.models import Conversation
    from sqlalchemy import select
    
    # Verify user is admin
    result = await db.execute(
        select(Conversation).where(Conversation.id == conversation_id)
    )
    conversation = result.scalar_one_or_none()
    
    if not conversation:
        raise HTTPException(status_code=404, detail="Conversation not found")
    
    if conversation.admin_ids and current_user.id not in conversation.admin_ids:
        raise HTTPException(status_code=403, detail="Only admins can add participants")
    
    conversation = await add_participants_to_conversation(
        conversation_id=conversation_id,
        user_ids=data.user_ids,
        db=db
    )
    
    return {"message": "Participants added", "participant_ids": conversation.participant_ids}


@router.delete("/conversations/{conversation_id}/participants/{user_id}")
async def remove_participant(
    conversation_id: UUID,
    user_id: UUID,
    current_user: Users = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """Remove a participant from conversation"""
    from src.chat.models import Conversation
    from sqlalchemy import select
    
    result = await db.execute(
        select(Conversation).where(Conversation.id == conversation_id)
    )
    conversation = result.scalar_one_or_none()
    
    if not conversation:
        raise HTTPException(status_code=404, detail="Conversation not found")
    
    # Can remove self, or admin can remove others
    if user_id != current_user.id:
        if not conversation.admin_ids or current_user.id not in conversation.admin_ids:
            raise HTTPException(status_code=403, detail="Only admins can remove participants")
    
    conversation = await remove_participant_from_conversation(
        conversation_id=conversation_id,
        user_id=user_id,
        db=db
    )
    
    return {"message": "Participant removed"}