"""
嵌入式 Redis 服务器
用于在没有外部 Redis 的情况下提供 Redis 功能
"""
import logging
from typing import Optional
from app.db.mini_redis import start_server, stop_server

logger = logging.getLogger(__name__)


class EmbeddedRedis:
    """嵌入式 Redis 服务器管理类（使用纯 Python 实现）"""
    
    _instance: Optional['EmbeddedRedis'] = None
    _running = False
    
    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
        return cls._instance
    
    def __init__(self):
        pass
    
    def start(self) -> bool:
        """启动嵌入式 Redis 服务器"""
        if self._running:
            logger.info("嵌入式 Redis 已在运行中")
            return True
        
        try:
            logger.info("正在启动嵌入式 Redis...")
            if start_server():
                self._running = True
                logger.info("✅ 嵌入式 Redis 启动成功！监听端口: 6379")
                return True
            else:
                logger.error("❌ 嵌入式 Redis 启动失败")
                return False
        except Exception as e:
            logger.error(f"❌ 嵌入式 Redis 启动异常: {e}")
            self._running = False
            return False
    
    def stop(self) -> None:
        """停止嵌入式 Redis 服务器"""
        if not self._running:
            return
        
        try:
            logger.info("正在停止嵌入式 Redis...")
            stop_server()
            self._running = False
            logger.info("嵌入式 Redis 已停止")
        except Exception as e:
            logger.error(f"停止嵌入式 Redis 失败: {e}")
    
    def is_running(self) -> bool:
        """检查 Redis 是否在运行"""
        return self._running
    
    def get_connection_info(self) -> dict:
        """获取连接信息"""
        return {
            'host': 'localhost',
            'port': 6379,
            'db': 0,
            'password': None
        }


# 全局实例
_embedded_redis = EmbeddedRedis()


def start_embedded_redis() -> bool:
    """启动嵌入式 Redis（单例模式）"""
    return _embedded_redis.start()


def stop_embedded_redis() -> None:
    """停止嵌入式 Redis"""
    _embedded_redis.stop()


def is_redis_embedded_running() -> bool:
    """检查嵌入式 Redis 是否在运行"""
    return _embedded_redis.is_running()
