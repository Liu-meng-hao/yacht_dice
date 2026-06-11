"""
Redis 缓存层（带嵌入式 Redis 支持）
用于高频访问数据的缓存，减少数据库压力。
优先使用外部 Redis，如果不可用则启动嵌入式 Redis。
"""
import json
import logging
from typing import Dict, List, Optional, Any
from datetime import datetime, timedelta
from app.models.online_room import OnlineRoom
from app.models.room_player import RoomPlayer
from sqlalchemy.orm import Session

logger = logging.getLogger(__name__)

# 获取 Redis 客户端
from app.db.redis_client import get_redis_client

# 缓存 key 前缀
CACHE_PREFIX_ROOM = "room:"
CACHE_PREFIX_ROOM_PLAYERS = "room:players:"
CACHE_PREFIX_GAME = "game:"
CACHE_PREFIX_GAME_STATE = "game:state:"
CACHE_PREFIX_ONLINE_ROOMS = "online_rooms"

# 缓存过期时间（秒）
ROOM_CACHE_TTL = 3600  # 1 小时
GAME_CACHE_TTL = 7200  # 2 小时
ONLINE_LIST_CACHE_TTL = 60  # 1 分钟


class RedisCache:
    """Redis 缓存管理器（使用嵌入式或外部 Redis）"""
    
    def __init__(self):
        self._redis_client = None
    
    def _get_redis(self):
        """获取 Redis 客户端（延迟初始化）"""
        if self._redis_client is None:
            self._redis_client = get_redis_client()
        return self._redis_client
    
    @staticmethod
    def _serialize(obj: Any) -> str:
        """序列化对象"""
        if isinstance(obj, dict):
            return json.dumps(obj, ensure_ascii=False, default=str)
        return str(obj)
    
    @staticmethod
    def _deserialize(data: Optional[str]) -> Optional[Any]:
        """反序列化数据"""
        if not data:
            return None
        try:
            return json.loads(data)
        except (json.JSONDecodeError, TypeError):
            return data
    
    # ==================== 房间缓存 ====================
    
    async def cache_room(self, room: OnlineRoom) -> None:
        """缓存房间信息"""
        key = f"{CACHE_PREFIX_ROOM}{room.room_code}"
        room_data = {
            "id": room.id,
            "room_code": room.room_code,
            "room_name": room.room_name,
            "host_id": room.host_id,
            "max_player_count": room.max_player_count,
            "current_player_count": room.current_player_count,
            "room_status": room.room_status,
            "game_id": room.game_id,
            "game_mode": room.game_mode,
            "create_time": room.create_time.isoformat() if room.create_time else None,
            "is_deleted": room.is_deleted
        }
        
        redis_client = self._get_redis()
        async_redis = redis_client.get_async_client()
        
        if async_redis:
            await async_redis.setex(
                name=key,
                time=ROOM_CACHE_TTL,
                value=self._serialize(room_data)
            )
        
        logger.debug(f"Cached room: {room.room_code}")
    
    async def get_cached_room(self, room_code: str) -> Optional[Dict]:
        """获取缓存的房间信息"""
        key = f"{CACHE_PREFIX_ROOM}{room_code}"
        
        redis_client = self._get_redis()
        async_redis = redis_client.get_async_client()
        
        if async_redis:
            data = await async_redis.get(key)
            return self._deserialize(data)
        
        return None
    
    async def invalidate_room(self, room_code: str) -> None:
        """使房间缓存失效"""
        key = f"{CACHE_PREFIX_ROOM}{room_code}"
        
        redis_client = self._get_redis()
        async_redis = redis_client.get_async_client()
        
        if async_redis:
            await async_redis.delete(key)
        
        logger.debug(f"Invalidated room cache: {room_code}")
    
    # ==================== 房间玩家缓存 ====================
    
    async def cache_room_players(self, room_code: str, players: List[RoomPlayer]) -> None:
        """缓存房间玩家列表"""
        key = f"{CACHE_PREFIX_ROOM_PLAYERS}{room_code}"
        players_data = []
        for p in players:
            players_data.append({
                "user_id": p.user_id,
                "player_name": p.player_name,
                "is_host": p.is_host,
                "is_ready": p.is_ready,
                "create_time": p.create_time.isoformat() if p.create_time else None
            })
        
        redis_client = self._get_redis()
        async_redis = redis_client.get_async_client()
        
        if async_redis:
            await async_redis.setex(
                name=key,
                time=ROOM_CACHE_TTL,
                value=self._serialize(players_data)
            )
        
        logger.debug(f"Cached {len(players_data)} players for room: {room_code}")
    
    async def get_cached_room_players(self, room_code: str) -> Optional[List[Dict]]:
        """获取缓存的房间玩家列表"""
        key = f"{CACHE_PREFIX_ROOM_PLAYERS}{room_code}"
        
        redis_client = self._get_redis()
        async_redis = redis_client.get_async_client()
        
        if async_redis:
            data = await async_redis.get(key)
            return self._deserialize(data)
        
        return None
    
    async def invalidate_room_players(self, room_code: str) -> None:
        """使房间玩家缓存失效"""
        key = f"{CACHE_PREFIX_ROOM_PLAYERS}{room_code}"
        
        redis_client = self._get_redis()
        async_redis = redis_client.get_async_client()
        
        if async_redis:
            await async_redis.delete(key)
        
        logger.debug(f"Invalidated room players cache: {room_code}")
    
    # ==================== 房间完整数据缓存 ====================
    
    async def get_room_with_cache(self, room_code: str, db: Session) -> Optional[Dict]:
        """
        获取房间完整信息（优先从缓存获取）
        返回格式与 build_room_response 兼容
        """
        # 先尝试从缓存获取
        cached_room = await self.get_cached_room(room_code)
        cached_players = await self.get_cached_room_players(room_code)
        
        if cached_room and cached_players is not None:
            logger.debug(f"Cache hit for room: {room_code}")
            return {
                "room_code": cached_room["room_code"],
                "room_name": cached_room["room_name"],
                "max_players": cached_room["max_player_count"],
                "players": cached_players,
                "status": cached_room["room_status"],
                "host_id": cached_room["host_id"],
                "game_id": cached_room["game_id"]
            }
        
        # 缓存未命中，从数据库加载
        logger.debug(f"Cache miss for room: {room_code}")
        room = db.query(OnlineRoom).filter(
            OnlineRoom.room_code == room_code,
            OnlineRoom.is_deleted == 0
        ).first()
        
        if not room:
            return None
        
        # 重新填充缓存
        await self.cache_room(room)
        await self.cache_room_players(room_code, room.players)
        
        players_data = []
        for p in room.players:
            players_data.append({
                "user_id": p.user_id,
                "player_name": p.player_name,
                "is_host": p.is_host,
                "is_ready": p.is_ready,
                "create_time": p.create_time.isoformat() if p.create_time else None
            })
        
        return {
            "room_code": room.room_code,
            "room_name": room.room_name,
            "max_players": room.max_player_count,
            "players": players_data,
            "status": room.room_status,
            "host_id": room.host_id,
            "game_id": room.game_id
        }
    
    # ==================== 游戏状态缓存 ====================
    
    async def cache_game_state(self, game_id: str, state: Dict) -> None:
        """缓存游戏实时状态（骰子、回合等）"""
        key = f"{CACHE_PREFIX_GAME_STATE}{game_id}"
        
        redis_client = self._get_redis()
        async_redis = redis_client.get_async_client()
        
        if async_redis:
            await async_redis.setex(
                name=key,
                time=GAME_CACHE_TTL,
                value=self._serialize(state)
            )
        
        logger.debug(f"Cached game state for game: {game_id}")
    
    async def get_cached_game_state(self, game_id: str) -> Optional[Dict]:
        """获取缓存的游戏状态"""
        key = f"{CACHE_PREFIX_GAME_STATE}{game_id}"
        
        redis_client = self._get_redis()
        async_redis = redis_client.get_async_client()
        
        if async_redis:
            data = await async_redis.get(key)
            return self._deserialize(data)
        
        return None
    
    async def invalidate_game_state(self, game_id: str) -> None:
        """使游戏状态缓存失效"""
        key = f"{CACHE_PREFIX_GAME_STATE}{game_id}"
        
        redis_client = self._get_redis()
        async_redis = redis_client.get_async_client()
        
        if async_redis:
            await async_redis.delete(key)
        
        logger.debug(f"Invalidated game state cache: {game_id}")
    
    # ==================== 房间列表缓存 ====================
    
    async def cache_online_rooms(self, rooms: List[Dict]) -> None:
        """缓存在线房间列表"""
        redis_client = self._get_redis()
        async_redis = redis_client.get_async_client()
        
        if async_redis:
            await async_redis.setex(
                name=CACHE_PREFIX_ONLINE_ROOMS,
                time=ONLINE_LIST_CACHE_TTL,
                value=self._serialize(rooms)
            )
        
        logger.debug(f"Cached {len(rooms)} online rooms")
    
    async def get_cached_online_rooms(self) -> Optional[List[Dict]]:
        """获取缓存的在线房间列表"""
        redis_client = self._get_redis()
        async_redis = redis_client.get_async_client()
        
        if async_redis:
            data = await async_redis.get(CACHE_PREFIX_ONLINE_ROOMS)
            return self._deserialize(data)
        
        return None
    
    async def invalidate_online_rooms(self) -> None:
        """使房间列表缓存失效"""
        redis_client = self._get_redis()
        async_redis = redis_client.get_async_client()
        
        if async_redis:
            await async_redis.delete(CACHE_PREFIX_ONLINE_ROOMS)
        
        logger.debug("Invalidated online rooms cache")
    
    # ==================== 批量操作 ====================
    
    async def update_room_and_players(self, room: OnlineRoom, players: List[RoomPlayer]) -> None:
        """同时更新房间和玩家缓存"""
        await self.cache_room(room)
        await self.cache_room_players(room.room_code, players)
        await self.invalidate_online_rooms()
    
    async def invalidate_all_room_cache(self, room_code: str) -> None:
        """使房间相关的所有缓存失效"""
        await self.invalidate_room(room_code)
        await self.invalidate_room_players(room_code)
        await self.invalidate_online_rooms()


# 全局缓存实例
cache = RedisCache()

