import redis
import redis.asyncio as aioredis
from typing import Optional, Callable, Any
import json
import asyncio
import logging
from app.core.config import settings

logger = logging.getLogger(__name__)

# 尝试导入嵌入式 Redis
try:
    from app.db.embedded_redis import start_embedded_redis, is_redis_embedded_running
    _HAS_EMBEDDED = True
except ImportError:
    _HAS_EMBEDDED = False


class RedisClient:
    _instance: Optional['RedisClient'] = None
    _initialized = False
    
    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
        return cls._instance
    
    def __init__(self):
        if RedisClient._initialized:
            return
        
        # 先尝试连接外部 Redis
        if not self._try_connect_external_redis():
            # 外部 Redis 不可用，尝试启动嵌入式 Redis
            if _HAS_EMBEDDED:
                logger.info("外部 Redis 不可用，正在启动嵌入式 Redis...")
                if start_embedded_redis():
                    # 嵌入式 Redis 启动成功，重新连接
                    self._try_connect_external_redis()
                else:
                    logger.error("嵌入式 Redis 启动失败！")
            else:
                logger.warning("未找到嵌入式 Redis 模块")
        
        RedisClient._initialized = True
    
    def _try_connect_external_redis(self) -> bool:
        """尝试连接外部 Redis"""
        try:
            # 同步客户端
            self._client = redis.Redis(
                host=settings.REDIS_HOST,
                port=settings.REDIS_PORT,
                password=settings.REDIS_PASSWORD,
                db=settings.REDIS_DB,
                decode_responses=True,
                socket_connect_timeout=2,
                socket_timeout=2
            )
            # 测试连接
            self._client.ping()
            
            # 异步客户端
            self._async_client = aioredis.Redis(
                host=settings.REDIS_HOST,
                port=settings.REDIS_PORT,
                password=settings.REDIS_PASSWORD,
                db=settings.REDIS_DB,
                decode_responses=True,
                socket_connect_timeout=2,
                socket_timeout=2
            )
            
            logger.info("✅ Redis 连接成功！")
            return True
            
        except Exception as e:
            logger.warning(f"连接 Redis 失败: {e}")
            self._client = None
            self._async_client = None
            return False
    
    def get_client(self) -> Optional[redis.Redis]:
        return self._client
    
    def get_async_client(self) -> Optional[aioredis.Redis]:
        return self._async_client
    
    def set(self, key: str, value: str, expire: int = None):
        if self._client:
            try:
                self._client.set(key, value, ex=expire)
            except Exception as e:
                logger.warning(f"Redis set 操作失败: {e}")
    
    def get(self, key: str) -> Optional[str]:
        if self._client:
            try:
                return self._client.get(key)
            except Exception as e:
                logger.warning(f"Redis get 操作失败: {e}")
        return None
    
    def delete(self, key: str):
        if self._client:
            try:
                self._client.delete(key)
            except Exception as e:
                logger.warning(f"Redis delete 操作失败: {e}")
    
    def exists(self, key: str) -> bool:
        if self._client:
            try:
                return self._client.exists(key) > 0
            except Exception as e:
                logger.warning(f"Redis exists 操作失败: {e}")
        return False
    
    def hset(self, name: str, key: str, value: str):
        if self._client:
            try:
                self._client.hset(name, key, value)
            except Exception as e:
                logger.warning(f"Redis hset 操作失败: {e}")
    
    def hget(self, name: str, key: str) -> Optional[str]:
        if self._client:
            try:
                return self._client.hget(name, key)
            except Exception as e:
                logger.warning(f"Redis hget 操作失败: {e}")
        return None
    
    def hgetall(self, name: str) -> dict:
        if self._client:
            try:
                return self._client.hgetall(name)
            except Exception as e:
                logger.warning(f"Redis hgetall 操作失败: {e}")
        return {}
    
    def hdel(self, name: str, *keys):
        if self._client:
            try:
                self._client.hdel(name, *keys)
            except Exception as e:
                logger.warning(f"Redis hdel 操作失败: {e}")
    
    def expire(self, name: str, time: int):
        if self._client:
            try:
                self._client.expire(name, time)
            except Exception as e:
                logger.warning(f"Redis expire 操作失败: {e}")
    
    async def publish(self, channel: str, message: dict):
        """发布消息到指定频道"""
        if self._async_client:
            try:
                await self._async_client.publish(channel, json.dumps(message))
            except Exception as e:
                logger.warning(f"Redis publish 操作失败: {e}")
    
    async def subscribe(self, channel: str, callback: Callable[[dict], Any]):
        """订阅频道消息"""
        if self._async_client:
            try:
                if not hasattr(self, '_subscribers'):
                    self._subscribers = {}
                    self._pubsub = None
                    self._pubsub_task = None
                
                if channel not in self._subscribers:
                    self._subscribers[channel] = []
                
                self._subscribers[channel].append(callback)
                
                if self._pubsub is None:
                    self._pubsub = self._async_client.pubsub()
                    self._pubsub_task = asyncio.create_task(self._listen())
                
                await self._pubsub.subscribe(channel)
            except Exception as e:
                logger.warning(f"Redis subscribe 操作失败: {e}")
    
    async def unsubscribe(self, channel: str, callback: Callable[[dict], Any] = None):
        """取消订阅频道"""
        if self._async_client and hasattr(self, '_subscribers'):
            try:
                if callback is None:
                    if channel in self._subscribers:
                        del self._subscribers[channel]
                else:
                    if channel in self._subscribers:
                        if callback in self._subscribers[channel]:
                            self._subscribers[channel].remove(callback)
                        if not self._subscribers[channel]:
                            del self._subscribers[channel]
                
                if channel not in self._subscribers and self._pubsub:
                    await self._pubsub.unsubscribe(channel)
            except Exception as e:
                logger.warning(f"Redis unsubscribe 操作失败: {e}")
    
    async def _listen(self):
        """监听 Pub/Sub 消息"""
        try:
            async for message in self._pubsub.listen():
                if message['type'] == 'message':
                    channel = message['channel']
                    data = json.loads(message['data'])
                    
                    if channel in self._subscribers:
                        for callback in self._subscribers[channel]:
                            try:
                                asyncio.create_task(callback(data))
                            except Exception as e:
                                logger.warning(f"订阅者回调错误: {e}")
        except Exception as e:
            logger.warning(f"Pub/Sub 监听错误: {e}")


# 全局实例 - 延迟初始化
redis_client = None


def get_redis_client() -> RedisClient:
    """获取 Redis 客户端实例（单例）"""
    global redis_client
    if redis_client is None:
        redis_client = RedisClient()
    return redis_client

