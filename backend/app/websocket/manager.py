import logging
from typing import Dict, List, Set
from fastapi import WebSocket

logger = logging.getLogger("uvicorn")

class ConnectionManager:
    def __init__(self):
        # Maps room_id -> list of active WebSockets
        self.active_connections: Dict[str, List[WebSocket]] = {}
        # Maps room_id -> set of active user names (presence fallback)
        self.user_presence: Dict[str, Set[str]] = {}

    async def connect(self, websocket: WebSocket, room_id: str, user_name: str):
        await websocket.accept()
        
        if room_id not in self.active_connections:
            self.active_connections[room_id] = []
        if room_id not in self.user_presence:
            self.user_presence[room_id] = set()
            
        self.active_connections[room_id].append(websocket)
        self.user_presence[room_id].add(user_name)
        
        logger.info(f"WebSocket client connected: user '{user_name}' in room '{room_id}'")
        
        # Broadcast presence list
        await self.broadcast_presence(room_id)

    async def disconnect(self, websocket: WebSocket, room_id: str, user_name: str):
        if room_id in self.active_connections:
            if websocket in self.active_connections[room_id]:
                self.active_connections[room_id].remove(websocket)
            if not self.active_connections[room_id]:
                del self.active_connections[room_id]
                
        if room_id in self.user_presence:
            if user_name in self.user_presence[room_id]:
                self.user_presence[room_id].remove(user_name)
            if not self.user_presence[room_id]:
                del self.user_presence[room_id]
                
        logger.info(f"WebSocket client disconnected: user '{user_name}' in room '{room_id}'")
        
        # Broadcast presence list
        await self.broadcast_presence(room_id)

    async def broadcast_to_room(self, room_id: str, message: dict):
        if room_id in self.active_connections:
            for connection in list(self.active_connections[room_id]):
                try:
                    await connection.send_json(message)
                except Exception as e:
                    logger.debug(f"Dead socket encountered during broadcast: {e}")

    async def broadcast_presence(self, room_id: str):
        """Query MongoDB for all currently online participants and broadcast list"""
        try:
            from app.database import get_db
            db = get_db()
            if db is not None:
                cursor = db["room_participants"].find({"room_id": room_id, "is_online": True})
                participants = await cursor.to_list(length=100)
                presence_users = [p["username"] for p in participants]
            else:
                presence_users = list(self.user_presence.get(room_id, []))
        except Exception as e:
            logger.error(f"Error loading participants presence from DB: {e}")
            presence_users = list(self.user_presence.get(room_id, []))
            
        message = {
            "type": "presence",
            "active_users": presence_users
        }
        await self.broadcast_to_room(room_id, message)

manager = ConnectionManager()
