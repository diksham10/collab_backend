from collections import defaultdict
import asyncio
from uuid import UUID

class NotificationSSEManager:
    def __init__(self):
        self.connections: dict[UUID, asyncio.Queue] = defaultdict(asyncio.Queue)

    async def connect(self, user_id: UUID):
        return self.connections[user_id]

    async def push(self, user_id: UUID, data: dict):
        if user_id in self.connections:
            await self.connections[user_id].put(data)

sse_manager = NotificationSSEManager()
