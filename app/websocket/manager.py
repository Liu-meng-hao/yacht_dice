from typing import Dict, List, Optional
from fastapi import WebSocket
import json
import time
import asyncio
import logging
from app.db.redis_client import redis_client

logger = logging.getLogger(__name__)

# 配置常量
MAX_CONNECTIONS_PER_ROOM = 10  # 每个房间最大连接数
PING_INTERVAL = 30  # 心跳间隔（秒）
PONG_TIMEOUT = 60  # 超时时间（秒）
WS_SEND_TIMEOUT = 5  # WebSocket 发送超时时间（秒）


class ConnectionManager:
    def __init__(self):
        self.player_connections: Dict[str, Dict[str, WebSocket]] = {}
        self.connection_timestamps: Dict[str, Dict[WebSocket, float]] = {}
        self.player_info: Dict[str, Dict[str, str]] = {}  # room_id -> {player_id -> player_name}
        self._heartbeat_task_started = False
        self._redis_subscribed = False
        
    async def _ensure_redis_subscription(self):
        """确保 Redis 订阅已启动"""
        if not self._redis_subscribed:
            self._redis_subscribed = True
            # 不需要全局订阅，每个连接自己处理即可
            
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
        
        await self._ensure_redis_subscription()
        self._start_heartbeat_if_needed()
        
        # 检查房间连接数限制
        current_count = self.get_player_count(room_id)
        if current_count >= MAX_CONNECTIONS_PER_ROOM:
            await websocket.send_text(json.dumps({
                "type": "error",
                "message": "Room is full"
            }))
            await websocket.close(code=1008)
            return False
        
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
        """广播消息（优化版本）
        使用 asyncio.gather 并发发送消息，大幅提升性能
        """
        if room_id not in self.player_connections:
            logger.warning(f"Broadcast: No active connections for room/game {room_id}")
            return
        
        message_str = json.dumps(message)
        message_type = message.get("type", "unknown")
        player_count = len(self.player_connections[room_id])
        
        logger.info(f"Broadcasting {message_type} to {player_count} players in room/game {room_id}")
        
        # 使用 asyncio.gather 并发发送消息
        tasks = []
        dead_player_ids = []
        
        for player_id, websocket in list(self.player_connections[room_id].items()):
            tasks.append(self._send_to_player(room_id, player_id, websocket, message_str, dead_player_ids))
        
        # 等待所有发送任务完成
        await asyncio.gather(*tasks, return_exceptions=True)
        
        # 清理无效连接
        for player_id in dead_player_ids:
            websocket = self.player_connections[room_id].get(player_id)
            if websocket:
                self.disconnect(room_id, player_id, websocket)
    
    async def _send_to_player(self, room_id: str, player_id: str, websocket: WebSocket, 
                            message_str: str, dead_player_ids: List[str]):
        """向单个玩家发送消息（供 gather 使用）"""
        try:
            # 添加超时保护，防止单个慢连接阻塞整个广播
            await asyncio.wait_for(
                websocket.send_text(message_str), 
                timeout=WS_SEND_TIMEOUT
            )
        except asyncio.TimeoutError:
            logger.warning(f"Send timeout for player {player_id} in room/game {room_id}")
            dead_player_ids.append(player_id)
        except Exception as e:
            logger.error(f"Broadcast failed for player {player_id} in room/game {room_id}: {e}")
            dead_player_ids.append(player_id)
    
    async def broadcast_with_redis(self, room_id: str, message: dict):
        """使用 Redis Pub/Sub 广播消息（支持多实例部署）"""
        # 先通过 Redis 发布消息
        await redis_client.publish(f"ws:{room_id}", message)
        # 同时直接发送给本实例的连接（优化本地延迟）
        await self.broadcast(room_id, message)
    
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
                if room_id in self.connection_timestamps:
                    self.connection_timestamps[room_id][websocket] = time.time()
            except Exception:
                logger.info(f"Ping failed, connection closed")
                break
    
    async def _check_connections(self):
        """定时检查无效连接"""
        while True:
            await asyncio.sleep(PING_INTERVAL)
            now = time.time()
            
            for room_id in list(self.player_connections.keys()):
                dead_player_ids = []
                
                for player_id, websocket in list(self.player_connections[room_id].items()):
                    last_ping = self.connection_timestamps.get(room_id, {}).get(websocket, 0)
                    if now - last_ping > PONG_TIMEOUT:
                        dead_player_ids.append(player_id)
                
                # 清理无效连接
                for player_id in dead_player_ids:
                    websocket = self.player_connections[room_id].get(player_id)
                    if websocket:
                        self.disconnect(room_id, player_id, websocket)


manager = ConnectionManager()
