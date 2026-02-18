from fastapi import WebSocket
from uuid import UUID
from src.redis import redis, pubsub_redis
import asyncio
import json
from typing import Dict, Set
from datetime import datetime, timezone

class ConnectionManager:
    def __init__(self):
        # Local connections for this worker
        self.active_connections: Dict[UUID, Set[WebSocket]] = {}
        
        # Track typing status per user
        self.typing_status: Dict[UUID, Dict[UUID, bool]] = {}  # {user_id: {other_user_id: is_typing}}
        
        # Redis pub/sub listener task
        self._listener_task = None
        
    async def start(self):
        """Start Redis listener when app starts"""
        if self._listener_task is None:
            self._listener_task = asyncio.create_task(self._redis_listener())
            print("✅ Chat Redis listener started")
    
    async def stop(self):
        """Stop Redis listener when app shuts down"""
        if self._listener_task:
            self._listener_task.cancel()
            try:
                await self._listener_task
            except asyncio.CancelledError:
                pass
            print("🛑 Chat Redis listener stopped")

    async def _redis_listener(self):
        """Listen to Redis pub/sub for chat events across workers"""
        try:
            pubsub = pubsub_redis.pubsub()
            # Subscribe to multiple event types
            await pubsub.psubscribe("chat:*")
            await pubsub.psubscribe("status:*")  # Online/offline status
            await pubsub.psubscribe("typing:*")  # Typing indicators
            await pubsub.psubscribe("receipt:*")  # Delivery/read receipts
            
            print("🎧 Listening to Redis pub/sub for chat events...")
            
            async for message in pubsub.listen():
                if message["type"] == "pmessage":
                    channel = message["channel"]
                    
                    # Handle different event types
                    if channel.startswith("chat:"):
                        await self._handle_chat_message(channel, message["data"])
                    elif channel.startswith("status:"):
                        await self._handle_status_update(channel, message["data"])
                    elif channel.startswith("typing:"):
                        await self._handle_typing_indicator(channel, message["data"])
                    elif channel.startswith("receipt:"):
                        await self._handle_receipt(channel, message["data"])
                        
        except asyncio.CancelledError:
            print("Chat listener task cancelled")
            raise
        except Exception as e:
            print(f"❌ Chat Redis listener error: {e}")
            await asyncio.sleep(5)
            await self._redis_listener()

    async def _handle_chat_message(self, channel: str, data: str):
        """Handle incoming chat message"""
        user_id = UUID(channel.split(":", 1)[1])
        if user_id in self.active_connections:
            try:
                payload = json.loads(data)
                await self._send_to_local_connections(user_id, payload)
                
                # Auto-send delivery receipt
                await self.send_delivery_receipt(
                    message_id=UUID(payload["id"]),
                    sender_id=UUID(payload["sender_id"]),
                    receiver_id=user_id
                )
                print(f"📨 Delivered chat message to user {user_id}")
            except Exception as e:
                print(f"❌ Error delivering chat message: {e}")

    async def _handle_status_update(self, channel: str, data: str):
        """Handle online/offline status updates"""
        user_id = UUID(channel.split(":", 1)[1])
        if user_id in self.active_connections:
            try:
                payload = json.loads(data)
                await self._send_to_local_connections(user_id, {
                    "type": "status_update",
                    "user_id": payload["user_id"],
                    "status": payload["status"],
                    "last_seen": payload.get("last_seen")
                })
            except Exception as e:
                print(f"❌ Error handling status update: {e}")

    async def _handle_typing_indicator(self, channel: str, data: str):
        """Handle typing indicators"""
        user_id = UUID(channel.split(":", 1)[1])
        if user_id in self.active_connections:
            try:
                payload = json.loads(data)
                await self._send_to_local_connections(user_id, {
                    "type": "typing",
                    "user_id": payload["user_id"],
                    "is_typing": payload["is_typing"]
                })
            except Exception as e:
                print(f"❌ Error handling typing indicator: {e}")

    async def _handle_receipt(self, channel: str, data: str):
        """Handle delivery/read receipts"""
        user_id = UUID(channel.split(":", 1)[1])
        if user_id in self.active_connections:
            try:
                payload = json.loads(data)
                await self._send_to_local_connections(user_id, {
                    "type": "receipt",
                    "message_id": payload["message_id"],
                    "receipt_type": payload["receipt_type"],
                    "timestamp": payload["timestamp"]
                })
            except Exception as e:
                print(f"❌ Error handling receipt: {e}")

    async def connect(self, user_id: UUID, websocket: WebSocket):
        """Connect a user's WebSocket"""
        await websocket.accept()
        self.active_connections.setdefault(user_id, set()).add(websocket)
        
        # Mark user as online in Redis (expires in 1 hour, refreshed by heartbeat)
        await redis.setex(f"chat_online:{user_id}", 3600, "1")
        
        # Update last_seen in database
        from src.database import AsyncSessionLocal
        from src.auth.models import Users
        from sqlalchemy import select
        async with AsyncSessionLocal() as db:
            result = await db.execute(select(Users).where(Users.id == user_id))
            user = result.scalar_one_or_none()
            if user:
                user.last_seen = datetime.now(timezone.utc)
                db.add(user)
                await db.commit()
        
        # Broadcast online status to all users who can chat with this user
        await self._broadcast_status(user_id, "online")
        
        print(f"✅ User {user_id} connected to chat")

    async def disconnect(self, user_id: UUID, websocket: WebSocket):
        """Disconnect a user's WebSocket"""
        if user_id in self.active_connections:
            self.active_connections[user_id].discard(websocket)
            if not self.active_connections[user_id]:
                del self.active_connections[user_id]
                
                # Remove online status
                await redis.delete(f"chat_online:{user_id}")
                
                # Update last_seen
                from src.database import AsyncSessionLocal
                from src.auth.models import Users
                from sqlalchemy import select
                async with AsyncSessionLocal() as db:
                    result = await db.execute(select(Users).where(Users.id == user_id))
                    user = result.scalar_one_or_none()
                    if user:
                        user.last_seen = datetime.now(timezone.utc)
                        db.add(user)
                        await db.commit()
                
                # Broadcast offline status
                await self._broadcast_status(user_id, "offline")
                
        print(f"🔌 User {user_id} disconnected from chat")
    
    async def _broadcast_status(self, user_id: UUID, status: str):
        """Broadcast online/offline status to users who can chat with this user"""
        from src.database import AsyncSessionLocal
        from src.chat.services import get_chatable_users
        
        async with AsyncSessionLocal() as db:
            chatable_users = await get_chatable_users(user_id, db)
            
            for other_user_id in chatable_users:
                channel = f"status:{other_user_id}"
                await redis.publish(channel, json.dumps({
                    "user_id": str(user_id),
                    "status": status,
                    "last_seen": datetime.now(timezone.utc).isoformat() if status == "offline" else None
                }))

    async def is_online(self, user_id: UUID) -> bool:
        """Check if user is online (across all workers)"""
        exists = await redis.exists(f"chat_online:{user_id}")
        return bool(exists)

    async def send_message(self, user_id: UUID, payload: dict):
        """Send chat message to user via Redis pub/sub"""
        channel = f"chat:{user_id}"
        await redis.publish(channel, json.dumps(payload))
        print(f"📢 Published chat message to Redis channel: {channel}")

    async def send_typing_indicator(self, from_user_id: UUID, to_user_id: UUID, is_typing: bool):
        """Send typing indicator"""
        channel = f"typing:{to_user_id}"
        await redis.publish(channel, json.dumps({
            "user_id": str(from_user_id),
            "is_typing": is_typing
        }))

    async def send_delivery_receipt(self, message_id: UUID, sender_id: UUID, receiver_id: UUID):
        """Send delivery receipt back to sender"""
        channel = f"receipt:{sender_id}"
        await redis.publish(channel, json.dumps({
            "message_id": str(message_id),
            "receipt_type": "delivered",
            "timestamp": datetime.now(timezone.utc).isoformat()
        }))

    async def send_read_receipt(self, message_id: UUID, sender_id: UUID, receiver_id: UUID):
        """Send read receipt back to sender"""
        channel = f"receipt:{sender_id}"
        await redis.publish(channel, json.dumps({
            "message_id": str(message_id),
            "receipt_type": "read",
            "timestamp": datetime.now(timezone.utc).isoformat()
        }))
    
    async def _send_to_local_connections(self, user_id: UUID, payload: dict):
        """Send to WebSocket connections on this worker"""
        disconnected = []
        for ws in self.active_connections.get(user_id, []):
            try:
                await ws.send_json(payload)
            except Exception as e:
                print(f"Error sending to websocket: {e}")
                disconnected.append(ws)
        
        # Clean up disconnected sockets
        for ws in disconnected:
            await self.disconnect(user_id, ws)

    async def heartbeat(self, user_id: UUID):
        """Refresh online status (called periodically from client)"""
        await redis.expire(f"chat_online:{user_id}", 3600)

    async def send_to_user(self, user_id: UUID, payload: dict):
        """Legacy method - use send_message instead"""
        await self.send_message(user_id, payload)


manager = ConnectionManager()


