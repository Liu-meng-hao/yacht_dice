from typing import Dict, List, Optional
from fastapi import WebSocket
import json
import time
import asyncio
import logging

logger = logging.getLogger(__name__)

# 配置常量
MAX_CONNECTIONS_PER_ROOM = 10  # 每个房间最大连接数
PING_INTERVAL = 30  # 心跳间隔（秒）
PONG_TIMEOUT = 60  # 超时时间（秒）


class ConnectionManager:
    def __init__(self):
        self.active_connections: Dict[str, List[WebSocket]] = {}
        self.player_connections: Dict[str, Dict[str, WebSocket]] = {}
        self.connection_timestamps: Dict[str, Dict[WebSocket, float]] = {}
        self.player_info: Dict[str, Dict[str, str]] = {}  # room_id -> {player_id -> player_name}
        self._heartbeat_task_started = False
        
    def _start_heartbeat_if_needed(self):
        """延迟启动心跳检测协程，避免初始化时没有事件循环"""
        if not self._heartbeat_task_started:
            try:
                asyncio.create_task(self._check_connections())
                self._heartbeat_task_started = True
            except RuntimeError:
                # 如果没有运行的事件循环，忽略，等待第一个连接时再尝试
                pass
    
    async def connect(self, room_id: str, player_id: str, websocket: WebSocket, player_name: str = None):
        """建立连接"""
        await websocket.accept()
        
        # 延迟启动心跳检测
        self._start_heartbeat_if_needed()
        
        # 检查房间连接数限制
        if room_id in self.active_connections:
            if len(self.active_connections[room_id]) >= MAX_CONNECTIONS_PER_ROOM:
                await websocket.send_text(json.dumps({
                    "type": "error",
                    "message": "Room is full"
                }))
                await websocket.close(code=1008)
                return False
        
        if room_id not in self.active_connections:
            self.active_connections[room_id] = []
        self.active_connections[room_id].append(websocket)
        
        if room_id not in self.player_connections:
            self.player_connections[room_id] = {}
        self.player_connections[room_id][player_id] = websocket
        
        if room_id not in self.connection_timestamps:
            self.connection_timestamps[room_id] = {}
        self.connection_timestamps[room_id][websocket] = time.time()
        
        if room_id not in self.player_info:
            self.player_info[room_id] = {}
        if player_name:
            self.player_info[room_id][player_id] = player_name
        
        # 启动心跳发送协程
        asyncio.create_task(self._send_ping(room_id, websocket))
        
        logger.info(f"Player {player_id} connected to room {room_id}")
        return True
    
    def disconnect(self, room_id: str, player_id: str, websocket: WebSocket):
        """断开连接"""
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
        
        if room_id in self.connection_timestamps:
            if websocket in self.connection_timestamps[room_id]:
                del self.connection_timestamps[room_id][websocket]
            if not self.connection_timestamps[room_id]:
                del self.connection_timestamps[room_id]
        
        if room_id in self.player_info:
            if player_id in self.player_info[room_id]:
                del self.player_info[room_id][player_id]
            if not self.player_info[room_id]:
                del self.player_info[room_id]
        
        logger.info(f"Player {player_id} disconnected from room {room_id}")
    
    async def send_personal_message(self, room_id: str, player_id: str, message: dict):
        """单播消息"""
        if room_id in self.player_connections and player_id in self.player_connections[room_id]:
            websocket = self.player_connections[room_id][player_id]
            try:
                await websocket.send_text(json.dumps(message))
            except Exception as e:
                logger.error(f"Failed to send message to {player_id}: {e}")
                self.disconnect(room_id, player_id, websocket)
    
    async def broadcast(self, room_id: str, message: dict):
        """广播消息（安全版本）"""
        if room_id not in self.active_connections:
            return
        
        message_str = json.dumps(message)
        dead_connections = []
        
        for connection in self.active_connections[room_id]:
            try:
                await connection.send_text(message_str)
            except Exception as e:
                logger.error(f"Broadcast failed for connection: {e}")
                dead_connections.append(connection)
        
        # 清理无效连接
        for conn in dead_connections:
            if conn in self.active_connections[room_id]:
                self.active_connections[room_id].remove(conn)
        
        # 检查房间是否为空
        if not self.active_connections[room_id]:
            del self.active_connections[room_id]
            if room_id in self.player_connections:
                del self.player_connections[room_id]
    
    def get_player_count(self, room_id: str) -> int:
        """获取房间玩家数量"""
        if room_id in self.player_connections:
            return len(self.player_connections[room_id])
        return 0
    
    def get_player_name(self, room_id: str, player_id: str) -> Optional[str]:
        """获取玩家名称"""
        return self.player_info.get(room_id, {}).get(player_id)
    
    async def _send_ping(self, room_id: str, websocket: WebSocket):
        """发送心跳包"""
        while True:
            await asyncio.sleep(PING_INTERVAL)
            try:
                await websocket.send_text(json.dumps({"type": "ping"}))
                self.connection_timestamps[room_id][websocket] = time.time()
            except Exception:
                logger.info(f"Ping failed, connection closed")
                break
    
    async def _check_connections(self):
        """定时检查无效连接"""
        while True:
            await asyncio.sleep(PING_INTERVAL)
            now = time.time()
            
            for room_id in list(self.active_connections.keys()):
                dead_connections = []
                dead_player_ids = []
                
                for conn in self.active_connections[room_id]:
                    last_ping = self.connection_timestamps.get(room_id, {}).get(conn, 0)
                    if now - last_ping > PONG_TIMEOUT:
                        dead_connections.append(conn)
                
                # 查找对应的 player_id
                for conn in dead_connections:
                    for player_id, ws in self.player_connections.get(room_id, {}).items():
                        if ws == conn:
                            dead_player_ids.append(player_id)
                            break
                
                # 清理无效连接
                for conn in dead_connections:
                    if conn in self.active_connections.get(room_id, {}):
                        self.active_connections[room_id].remove(conn)
                
                for player_id in dead_player_ids:
                    if player_id in self.player_connections.get(room_id, {}):
                        del self.player_connections[room_id][player_id]
                
                # 检查房间是否为空
                if not self.active_connections[room_id]:
                    del self.active_connections[room_id]
                    if room_id in self.player_connections:
                        del self.player_connections[room_id]
                    if room_id in self.connection_timestamps:
                        del self.connection_timestamps[room_id]


manager = ConnectionManager()
