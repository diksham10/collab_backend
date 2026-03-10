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
from sqlalchemy import select, and_, not_, func, any_, update
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
    """Get all conversations - OPTIMIZED to prevent duplicate queries"""
    conversations = await get_user_conversations(current_user.id, db)
    
    if not conversations:
        return []
    
    # ============ BATCH FETCH ALL PARTICIPANTS (Single Query) ============
    all_participant_ids = set()
    for conv in conversations:
        all_participant_ids.update(conv.participant_ids)
    
    participants_result = await db.execute(
        select(Users).where(Users.id.in_(list(all_participant_ids)))
    )
    all_participants = {p.id: p for p in participants_result.scalars().all()}
    
    # ============ BATCH FETCH ALL LAST MESSAGES (Single Query) ============
    last_message_ids = [conv.last_message_id for conv in conversations if conv.last_message_id]
    if last_message_ids:
        messages_result = await db.execute(
            select(Message).where(Message.id.in_(last_message_ids))
        )
        # Force load all fields immediately to prevent lazy loading
        all_messages = {}
        for msg in messages_result.scalars().all():
            # Access all fields to force load them
            all_messages[msg.id] = {
                'id': msg.id,
                'conversation_id': msg.conversation_id,
                'sender_id': msg.sender_id,
                'receiver_id': msg.receiver_id,
                'content': msg.content,
                'type': msg.type,
                'sent_at': msg.sent_at,
                'edited_at': msg.edited_at,
                'deleted_at': msg.deleted_at,
                'read_by': msg.read_by or [],
                'delivered_to': msg.delivered_to or []
            }
    else:
        all_messages = {}
    
    # ============ BATCH FETCH PROFILE NAMES (Optimized) ============
    brand_user_ids = [p.id for p in all_participants.values() if p.role == "brand"]
    influencer_user_ids = [p.id for p in all_participants.values() if p.role == "influencer"]
    
    profile_names = {}
    
    if brand_user_ids:
        from src.brand.models import BrandProfile
        brand_result = await db.execute(
            select(BrandProfile.user_id, BrandProfile.name).where(BrandProfile.user_id.in_(brand_user_ids))
        )
        for user_id, name in brand_result.all():
            profile_names[user_id] = name
    
    if influencer_user_ids:
        from src.influencer.models import InfluencerProfile
        influencer_result = await db.execute(
            select(InfluencerProfile.user_id, InfluencerProfile.name).where(InfluencerProfile.user_id.in_(influencer_user_ids))
        )
        for user_id, name in influencer_result.all():
            profile_names[user_id] = name
    
    # ============ MARK UNDELIVERED MESSAGES (Single Update Query) ============
    undelivered_result = await db.execute(
        select(Message)
        .join(Conversation, Message.conversation_id == Conversation.id)
        .where(
            and_(
                current_user.id == any_(Conversation.participant_ids),
                Message.sender_id != current_user.id,
                not_(current_user.id == any_(Message.delivered_to))
            )
        )
    )
    undelivered_messages = undelivered_result.scalars().all()
    
    if undelivered_messages:
        undelivered_ids = [msg.id for msg in undelivered_messages]
        await db.execute(
            update(Message)
            .where(Message.id.in_(undelivered_ids))
            .values(delivered_to=func.array_append(Message.delivered_to, current_user.id))
        )
        await db.commit()
        
        # Send delivery receipts
        for msg in undelivered_messages:
            delivery_payload = {
                "type": "delivery_receipt",
                "message_id": str(msg.id),
                "delivered_to_user_id": str(current_user.id),
                "conversation_id": str(msg.conversation_id)
            }
            await manager.send_message(msg.sender_id, delivery_payload)
        
        print(f"✅ Marked {len(undelivered_messages)} messages as delivered")
    
    # ============ BUILD RESPONSES (No More DB Queries) ============
    enriched = []
    for conv in conversations:
        # Get participants from cache
        conv_participants = [all_participants[pid] for pid in conv.participant_ids if pid in all_participants]
        
        # Get last message from cache (now it's a dict, not a model)
        last_msg_dict = all_messages.get(conv.last_message_id) if conv.last_message_id else None
        
        # Resolve display name
        display_name = conv.name
        if conv.type == "DIRECT":
            for p in conv_participants:
                if p.id != current_user.id:
                    # Use cached profile name if available, otherwise username
                    display_name = profile_names.get(p.id, p.username)
                    break
        
        enriched.append(ConversationResponse(
            id=conv.id,
            type=conv.type,
            participant_ids=conv.participant_ids,
            name=display_name,
            avatar_url=conv.avatar_url,
            description=conv.description,
            created_by_id=conv.created_by_id,
            admin_ids=conv.admin_ids,
            unread_counts=conv.unread_counts,
            last_message_id=conv.last_message_id,
            last_message_at=conv.last_message_at,
            created_at=conv.created_at,
            updated_at=conv.updated_at,
            participants=[ParticipantInfo.model_validate(p) for p in conv_participants],
            last_message=MessageResponse(
                id=last_msg_dict['id'],
                conversation_id=last_msg_dict['conversation_id'],
                sender_id=last_msg_dict['sender_id'],
                receiver_id=last_msg_dict['receiver_id'],
                content=last_msg_dict['content'],
                type=last_msg_dict['type'],
                sent_at=last_msg_dict['sent_at'],
                edited_at=last_msg_dict['edited_at'],
                deleted_at=last_msg_dict['deleted_at'],
                read_by=last_msg_dict['read_by'],
                delivered_to=last_msg_dict['delivered_to'],
                is_read=current_user.id in last_msg_dict['read_by'] if last_msg_dict['sender_id'] != current_user.id else True,
                is_delivered=current_user.id in last_msg_dict['delivered_to'] if last_msg_dict['sender_id'] != current_user.id else True
            ) if last_msg_dict else None,
            unread_count=conv.unread_counts.get(str(current_user.id), 0)
        ))
    
    return enriched


@router.post("/mark-all-delivered")
async def mark_all_messages_delivered(
    current_user: Users = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """
    Mark all undelivered messages as delivered when user comes online/logs in.
    This endpoint should be called immediately after successful login.
    """
    # Find all undelivered messages for this user across ALL conversations
    undelivered_result = await db.execute(
        select(Message)
        .join(Conversation, Message.conversation_id == Conversation.id)
        .where(
            and_(
                current_user.id == any_(Conversation.participant_ids),  # User is participant
                Message.sender_id != current_user.id,  # Not sent by user
                not_(current_user.id == any_(Message.delivered_to))  # Not yet delivered
            )
        )
    )
    undelivered_messages = undelivered_result.scalars().all()
    
    if not undelivered_messages:
        return {
            "message": "No undelivered messages",
            "count": 0
        }
    
    # Batch update all messages as delivered
    undelivered_ids = [msg.id for msg in undelivered_messages]
    await db.execute(
        update(Message)
        .where(Message.id.in_(undelivered_ids))
        .values(delivered_to=func.array_append(Message.delivered_to, current_user.id))
    )
    await db.commit()
    
    # Send delivery receipts to all senders via WebSocket
    for msg in undelivered_messages:
        delivery_payload = {
            "type": "delivery_receipt",
            "message_id": str(msg.id),
            "delivered_to_user_id": str(current_user.id),
            "conversation_id": str(msg.conversation_id)
        }
        await manager.send_message(msg.sender_id, delivery_payload)
    
    print(f"✅ Marked {len(undelivered_messages)} messages as delivered for {current_user.username} on login")
    
    return {
        "message": "Messages marked as delivered",
        "count": len(undelivered_messages)
    }


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
                "message_type": message.type,
                "read_by": [str(uid) for uid in message.read_by],
                "delivered_to": [str(uid) for uid in message.delivered_to]
            }
            
            print(f"📤 Broadcasting message {message.id} to conversation {conversation_id}")
            
            # Send to all participants except sender
            for participant_id in conversation.participant_ids:
                if participant_id != current_user.id:
                    await manager.send_message(participant_id, payload)
                    print(f"📨 Sent to participant {participant_id}")
        
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
    
    # ============ STEP 3.3.5: MARK ALL PENDING MESSAGES AS DELIVERED ============
    async with AsyncSessionLocal() as db_delivery:
        # Get all undelivered messages for this user across ALL conversations
        undelivered_result = await db_delivery.execute(
            select(Message)
            .join(Conversation, Message.conversation_id == Conversation.id)
            .where(
                and_(
                    user.id == any_(Conversation.participant_ids),  # User is participant
                    Message.sender_id != user.id,  # Not sent by user
                    not_(user.id == any_(Message.delivered_to))  # Not yet delivered to user
                )
            )
        )
        undelivered_messages = undelivered_result.scalars().all()
        
        if undelivered_messages:
            print(f"📬 Found {len(undelivered_messages)} undelivered messages for {user.username}")
            
            # Batch update all messages
            undelivered_ids = [msg.id for msg in undelivered_messages]
            await db_delivery.execute(
                update(Message)
                .where(Message.id.in_(undelivered_ids))
                .values(delivered_to=func.array_append(Message.delivered_to, user.id))
            )
            await db_delivery.commit()
            
            # Send delivery receipts to senders
            for msg in undelivered_messages:
                delivery_payload = {
                    "type": "delivery_receipt",
                    "message_id": str(msg.id),
                    "delivered_to_user_id": str(user.id),
                    "conversation_id": str(msg.conversation_id)
                }
                await manager.send_message(msg.sender_id, delivery_payload)
            
            print(f"✅ Marked {len(undelivered_messages)} messages as delivered on reconnect")
    
    try:
        # ============ STEP 3.4: SEND HISTORY ============
        async with AsyncSessionLocal() as db:
            # Get last 50 messages
            messages = await get_conversation_messages(conversation_id, db, limit=50)
            
            print(f"📤 Sending {len(messages)} historical messages to {user.username}")
            
            # Track undelivered messages
            undelivered_message_ids = []
            
            for msg in messages:
                # Mark as delivered if not already delivered to this user
                if user.id != msg.sender_id and user.id not in msg.delivered_to:
                    undelivered_message_ids.append(msg.id)
                
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
            
            # Batch update delivered_to for all undelivered messages
            if undelivered_message_ids:
                await db.execute(
                    update(Message)
                    .where(Message.id.in_(undelivered_message_ids))
                    .values(delivered_to=func.array_append(Message.delivered_to, user.id))
                )
                await db.commit()
                
                print(f"✅ Marked {len(undelivered_message_ids)} messages as delivered to {user.username}")
                
                # Send delivery receipts to senders
                for msg_id in undelivered_message_ids:
                    msg_result = await db.execute(
                        select(Message).where(Message.id == msg_id)
                    )
                    msg = msg_result.scalar_one_or_none()
                    if msg and msg.sender_id != user.id:
                        delivery_payload = {
                            "type": "delivery_receipt",
                            "message_id": str(msg_id),
                            "delivered_to_user_id": str(user.id),
                            "conversation_id": str(conversation_id)
                        }
                        await manager.send_message(msg.sender_id, delivery_payload)
        
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
                    
                    # ============ STEP 4.4: PREPARE INITIAL PAYLOAD ============
                    # Note: read_by and delivered_to will be updated as we broadcast
                    current_read_by = list(new_msg.read_by) if new_msg.read_by else []
                    current_delivered_to = list(new_msg.delivered_to) if new_msg.delivered_to else []
                    
                    payload = {
                        "type": "message",
                        "id": str(new_msg.id),
                        "conversation_id": str(conversation_id),
                        "sender_id": str(new_msg.sender_id),
                        "content": new_msg.content,
                        "sent_at": new_msg.sent_at.isoformat(),
                        "message_type": new_msg.type,
                        "read_by": [str(uid) for uid in current_read_by],
                        "delivered_to": [str(uid) for uid in current_delivered_to]
                    }
                    
                    # ============ STEP 4.5: BROADCAST TO PARTICIPANTS ============
                    if conversation:
                        print(f"📢 Broadcasting message to {len(conversation.participant_ids)} participants in conversation {conversation_id}")
                        for participant_id in conversation.participant_ids:
                            if participant_id != user.id:
                                delivered = await manager.send_message(participant_id, payload)
                                print(f"📨 Message for conversation {conversation_id} sent to user {participant_id} (online: {delivered})")
                                
                                if delivered:
                                    # Mark as delivered AND read immediately if user is online in this conversation
                                    async with AsyncSessionLocal() as db2:
                                        await db2.execute(
                                            update(Message)
                                            .where(Message.id == new_msg.id)
                                            .values(
                                                delivered_to=func.array_append(Message.delivered_to, participant_id),
                                                read_by=func.array_append(Message.read_by, participant_id)
                                            )
                                        )
                                        await db2.commit()
                                        
                                        # Update payload arrays for echo to sender
                                        current_delivered_to.append(participant_id)
                                        current_read_by.append(participant_id)
                                        payload["delivered_to"] = [str(uid) for uid in current_delivered_to]
                                        payload["read_by"] = [str(uid) for uid in current_read_by]
                                        
                                        # Send delivery receipt to sender
                                        delivery_payload = {
                                            "type": "delivery_receipt",
                                            "message_id": str(new_msg.id),
                                            "delivered_to_user_id": str(participant_id),
                                            "conversation_id": str(conversation_id)
                                        }
                                        await manager.send_message(user.id, delivery_payload)
                                        
                                        # Send read receipt to sender
                                        read_payload = {
                                            "type": "read_receipt",
                                            "message_id": str(new_msg.id),
                                            "user_id": str(participant_id),
                                            "conversation_id": str(conversation_id)
                                        }
                                        await manager.send_message(user.id, read_payload)
                                        print(f"✅ Message delivered AND read by online user {participant_id}")
                                
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
            
            elif message_type == "delivered":
                # ============ MARK MESSAGE AS DELIVERED ============
                message_id = data.get("message_id")
                if message_id:
                    async with AsyncSessionLocal() as db:
                        from uuid import UUID as PyUUID
                        
                        msg_uuid = PyUUID(message_id)
                        
                        # Mark as delivered if not already
                        await db.execute(
                            update(Message)
                            .where(
                                and_(
                                    Message.id == msg_uuid,
                                    not_(user.id == any_(Message.delivered_to))
                                )
                            )
                            .values(delivered_to=func.array_append(Message.delivered_to, user.id))
                        )
                        await db.commit()
                        
                        print(f"✅ Message {message_id} marked as delivered by {user.username}")
                        
                        # Send delivery receipt to sender
                        result = await db.execute(
                            select(Message).where(Message.id == msg_uuid)
                        )
                        msg = result.scalar_one_or_none()
                        
                        if msg and msg.sender_id != user.id:
                            delivery_payload = {
                                "type": "delivery_receipt",
                                "message_id": str(message_id),
                                "delivered_to_user_id": str(user.id),
                                "conversation_id": str(conversation_id)
                            }
                            
                            await manager.send_message(msg.sender_id, delivery_payload)
                            print(f"📢 Delivery receipt sent to sender {msg.sender_id}")
            
            elif message_type == "read":
                # ============ MARK AS READ ============
                message_ids = data.get("message_ids", [])  # Optional: specific message IDs
                
                async with AsyncSessionLocal() as db:
                    if message_ids:
                        # Mark specific messages as read
                        from uuid import UUID as PyUUID
                        
                        msg_uuids = [PyUUID(mid) for mid in message_ids]
                        
                        # Only mark messages not already read by this user
                        await db.execute(
                            update(Message)
                            .where(
                                and_(
                                    Message.id.in_(msg_uuids),
                                    Message.sender_id != user.id,
                                    not_(user.id == any_(Message.read_by))
                                )
                            )
                            .values(read_by=func.array_append(Message.read_by, user.id))
                        )
                        await db.commit()
                        
                        print(f"✅ Marked {len(message_ids)} specific messages as read by {user.username}")
                    else:
                        # Mark entire conversation as read (existing behavior)
                        await mark_conversation_as_read(
                            conversation_id=conversation_id,
                            user_id=user.id,
                            db=db
                        )
                        
                        print(f"✅ Entire conversation marked as read by {user.username}")
                    
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
                # print(f"💓 Heartbeat from {user.username}")
    
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
    """Mark conversation as read and send read receipts"""
    try:
        conversation = await mark_conversation_as_read(
            conversation_id=conversation_id,
            user_id=current_user.id,
            db=db
        )
        
        # Send read receipts to other participants
        read_payload = {
            "type": "read_receipt",
            "conversation_id": str(conversation_id),
            "user_id": str(current_user.id)
        }
        
        for participant_id in conversation.participant_ids:
            if participant_id != current_user.id:
                await manager.send_message(participant_id, read_payload)
        
        print(f"📢 Read receipt sent for conversation {conversation_id} by {current_user.username}")
        
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