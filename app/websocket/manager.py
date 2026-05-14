from typing import Dict, List, Optional
from fastapi import WebSocket
import json


class ConnectionManager:
    def __init__(self):
        self.active_connections: Dict[str, List[WebSocket]] = {}
        self.player_connections: Dict[str, Dict[str, WebSocket]] = {}
    
    async def connect(self, room_id: str, player_id: str, websocket: WebSocket):
        await websocket.accept()
        if room_id not in self.active_connections:
            self.active_connections[room_id] = []
        self.active_connections[room_id].append(websocket)
        
        if room_id not in self.player_connections:
            self.player_connections[room_id] = {}
        self.player_connections[room_id][player_id] = websocket
    
    def disconnect(self, room_id: str, player_id: str, websocket: WebSocket):
        if room_id in self.active_connections:
            if websocket in self.active_connections[room_id]:
                self.active_connections[room_id].remove(websocket)
            if not self.active_connections[room_id]:
                del self.active_connections[room_id]
        
        if room_id in self.player_connections:
            if player_id in self.player_connections[room_id]:
                del self.player_connections[room_id][player_id]
            if not self.player_connections[room_id]:
                del self.player_connections[room_id]
    
    async def send_personal_message(self, room_id: str, player_id: str, message: dict):
        if room_id in self.player_connections and player_id in self.player_connections[room_id]:
            websocket = self.player_connections[room_id][player_id]
            await websocket.send_text(json.dumps(message))
    
    async def broadcast(self, room_id: str, message: dict):
        if room_id in self.active_connections:
            for connection in self.active_connections[room_id]:
                await connection.send_text(json.dumps(message))


manager = ConnectionManager()
