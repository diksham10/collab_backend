from collections import defaultdict
import asyncio
import json
from uuid import UUID
from typing import Dict
from src.redis import redis, pubsub_redis

class NotificationSSEManager:
    def __init__(self):
        # In-memory connections for this worker
        self.connections: Dict[UUID, asyncio.Queue] = {}
        
        # Track active subscribers
        self.active_users: set[UUID] = set()
        
        # Redis pub/sub channel name
        self.channel_prefix = "notification:"
        
        # Background task for listening to Redis
        self._listener_task = None

    async def start(self):
        """Start the Redis listener task when the app starts"""
        if self._listener_task is None:
            self._listener_task = asyncio.create_task(self._redis_listener())
            print("✅ Redis notification listener started")

    async def stop(self):
        """Stop the Redis listener task when the app shuts down"""
        if self._listener_task:
            self._listener_task.cancel()
            try:
                await self._listener_task
            except asyncio.CancelledError:
                pass
            print("🛑 Redis notification listener stopped")

    async def _redis_listener(self):
        """Background task that listens to Redis pub/sub for all users"""
        try:
            # Subscribe to notification channels
            pubsub = pubsub_redis.pubsub()
            await pubsub.psubscribe("notification:*")  # Pattern subscribe to all user channels
            
            print("🎧 Listening to Redis pub/sub for notifications...")
            
            async for message in pubsub.listen():
                if message["type"] == "pmessage":
                    # Extract user_id from channel name: "notification:user_id"
                    channel = message["channel"]
                    user_id = UUID(channel.split(":", 1)[1])
                    
                    # If this worker has a connection for this user, push notification
                    if user_id in self.connections:
                        try:
                            data = json.loads(message["data"])
                            await self.connections[user_id].put(data)
                            print(f"📨 Pushed notification to user {user_id} on this worker")
                        except Exception as e:
                            print(f"❌ Error pushing notification: {e}")
        except asyncio.CancelledError:
            print("Listener task cancelled")
            raise
        except Exception as e:
            print(f"❌ Redis listener error: {e}")
            # Restart listener after error
            await asyncio.sleep(5)
            await self._redis_listener()

    async def connect(self, user_id: UUID) -> asyncio.Queue:
        """Called when a user connects to the SSE endpoint"""
        queue = asyncio.Queue(maxsize=100)  # Limit queue size
        self.connections[user_id] = queue
        self.active_users.add(user_id)
        
        # Mark user as connected in Redis (for presence tracking)
        await redis.setex(f"sse_connected:{user_id}", 3600, "1")  # Expire in 1 hour
        
        print(f"✅ User {user_id} connected to SSE (Total connections: {len(self.connections)})")
        
        # Send any cached notifications from Redis
        await self._send_cached_notifications(user_id, queue)
        
        return queue

    async def disconnect(self, user_id: UUID):
        """Called when a user disconnects from SSE"""
        if user_id in self.connections:
            del self.connections[user_id]
        
        if user_id in self.active_users:
            self.active_users.remove(user_id)
        
        # Remove presence tracking
        await redis.delete(f"sse_connected:{user_id}")
        
        print(f"🔌 User {user_id} disconnected from SSE (Total connections: {len(self.connections)})")

    async def push(self, user_id: UUID, data: dict):
        """
        Push notification to a user via Redis pub/sub.
        This works across all workers!
        """
        channel = f"{self.channel_prefix}{user_id}"
        
        # Publish to Redis - all workers will receive this
        await redis.publish(channel, json.dumps(data))
        
        # Also cache the notification in Redis for 24 hours
        await self._cache_notification(user_id, data)
        
        print(f"📢 Published notification to Redis channel: {channel}")

    async def _cache_notification(self, user_id: UUID, data: dict):
        """Cache notifications in Redis for 24 hours"""
        cache_key = f"notification_cache:{user_id}"
        
        # Store as a list with max 50 notifications
        await redis.lpush(cache_key, json.dumps(data))
        await redis.ltrim(cache_key, 0, 49)  # Keep only last 50
        await redis.expire(cache_key, 86400)  # 24 hours

    async def _send_cached_notifications(self, user_id: UUID, queue: asyncio.Queue):
        """Send cached notifications when user reconnects"""
        cache_key = f"notification_cache:{user_id}"
        
        # Get cached notifications (newest first)
        cached = await redis.lrange(cache_key, 0, -1)
        
        if cached:
            print(f"📦 Sending {len(cached)} cached notifications to user {user_id}")
            for notification_json in reversed(cached):  # Send oldest first
                try:
                    data = json.loads(notification_json)
                    await queue.put(data)
                except Exception as e:
                    print(f"❌ Error sending cached notification: {e}")

    async def is_user_connected(self, user_id: UUID) -> bool:
        """Check if user is connected to SSE on any worker"""
        exists = await redis.exists(f"sse_connected:{user_id}")
        return bool(exists)

    async def get_connected_users_count(self) -> int:
        """Get total number of connected users across all workers"""
        keys = await redis.keys("sse_connected:*")
        return len(keys)


# Global singleton
sse_manager = NotificationSSEManager()