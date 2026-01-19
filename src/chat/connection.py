from fastapi import WebSocket
from uuid import UUID

class ConnectionManager:
    def __init__(self):
        self.active_connections: dict[UUID, WebSocket] = {}

    async def connect(self, user_id: UUID, websocket: WebSocket):
        await websocket.accept()
        self.active_connections[user_id] = websocket

    def disconnect(self, user_id: UUID):
        if user_id in self.active_connections:
            del self.active_connections[user_id]
    
    def is_online(self, user_id: UUID) -> bool:
        return user_id in self.active_connections   

    async def send_to_user(self, user_id: UUID, payload: dict):
        websocket = self.active_connections.get(user_id)
        if websocket:
            await websocket.send_json(payload)
    
    