from fastapi import WebSocket
from uuid import UUID

class ConnectionManager:
    def __init__(self):
        self.active_connections: dict[UUID, set[WebSocket]] = {}

    async def connect(self, user_id: UUID, websocket: WebSocket):
        await websocket.accept()
        self.active_connections.setdefault(user_id, set()).add(websocket)

    def disconnect(self, user_id: UUID, websocket: WebSocket):
        if user_id in self.active_connections:
            self.active_connections[user_id].discard(websocket)
            if not self.active_connections[user_id]:
                del self.active_connections[user_id]
    
    def is_online(self, user_id: UUID) -> bool:
        return user_id in self.active_connections   

    async def send_to_user(self, user_id: UUID, payload: dict):
        for ws in self.active_connections.get(user_id, []):
            await ws.send_json(payload)
            
    
    