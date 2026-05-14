import redis
from typing import Optional
from app.core.config import settings


class RedisClient:
    _instance: Optional['RedisClient'] = None
    
    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
        return cls._instance
    
    def __init__(self):
        if not hasattr(self, '_client'):
            self._client = redis.Redis(
                host=settings.REDIS_HOST,
                port=settings.REDIS_PORT,
                password=settings.REDIS_PASSWORD,
                db=settings.REDIS_DB,
                decode_responses=True
            )
    
    def get_client(self) -> redis.Redis:
        return self._client
    
    def set(self, key: str, value: str, expire: int = None):
        self._client.set(key, value, ex=expire)
    
    def get(self, key: str) -> Optional[str]:
        return self._client.get(key)
    
    def delete(self, key: str):
        self._client.delete(key)
    
    def exists(self, key: str) -> bool:
        return self._client.exists(key) > 0
    
    def hset(self, name: str, key: str, value: str):
        self._client.hset(name, key, value)
    
    def hget(self, name: str, key: str) -> Optional[str]:
        return self._client.hget(name, key)
    
    def hgetall(self, name: str) -> dict:
        return self._client.hgetall(name)
    
    def hdel(self, name: str, *keys):
        self._client.hdel(name, *keys)
    
    def expire(self, name: str, time: int):
        self._client.expire(name, time)


redis_client = RedisClient()
