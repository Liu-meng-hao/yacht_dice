"""
AI任务管理器
管理异步AI回合执行，防止重复执行
"""
import asyncio
import logging
from typing import Dict, Optional
from datetime import datetime

logger = logging.getLogger(__name__)


class AITaskManager:
    """AI任务管理器单例"""
    
    _instance = None
    _lock = asyncio.Lock()
    
    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
            cls._instance._initialized = False
        return cls._instance
    
    def __init__(self):
        if self._initialized:
            return
        self._initialized = True
        self.running_tasks: Dict[str, asyncio.Task] = {}  # game_id -> task
        self.ai_turn_running: Dict[str, bool] = {}  # game_id -> 是否正在执行AI回合
        self._game_locks: Dict[str, asyncio.Lock] = {}  # game_id -> 锁
    
    def get_game_lock(self, game_id: str) -> asyncio.Lock:
        """获取游戏级别的锁"""
        if game_id not in self._game_locks:
            self._game_locks[game_id] = asyncio.Lock()
        return self._game_locks[game_id]
    
    def is_ai_turn_running(self, game_id: str) -> bool:
        """检查AI回合是否正在执行"""
        return self.ai_turn_running.get(game_id, False)
    
    def set_ai_turn_running(self, game_id: str, running: bool):
        """设置AI回合状态"""
        self.ai_turn_running[game_id] = running
    
    async def start_ai_task(self, game_id: str, ai_coro):
        """
        启动AI任务
        
        Args:
            game_id: 游戏ID
            ai_coro: AI协程
        """
        # 检查是否已有任务在运行
        if game_id in self.running_tasks and not self.running_tasks[game_id].done():
            logger.warning(f"AI task already running for game {game_id}")
            return
        
        # 设置AI回合正在运行标记
        self.set_ai_turn_running(game_id, True)
        
        # 创建并启动任务
        task = asyncio.create_task(self._run_ai_task(game_id, ai_coro))
        self.running_tasks[game_id] = task
        
        # 添加任务完成回调
        task.add_done_callback(lambda t: self._on_task_done(game_id, t))
        
        logger.info(f"Started AI task for game {game_id}")
    
    async def _run_ai_task(self, game_id: str, ai_coro):
        """运行AI任务"""
        try:
            await ai_coro
        except Exception as e:
            logger.error(f"AI task error for game {game_id}: {e}")
            import traceback
            logger.error(traceback.format_exc())
        finally:
            self.set_ai_turn_running(game_id, False)
    
    def _on_task_done(self, game_id: str, task: asyncio.Task):
        """任务完成回调"""
        try:
            task.result()
            logger.info(f"AI task completed for game {game_id}")
        except asyncio.CancelledError:
            logger.info(f"AI task cancelled for game {game_id}")
        except Exception as e:
            logger.error(f"AI task failed for game {game_id}: {e}")
        finally:
            self.set_ai_turn_running(game_id, False)
            if game_id in self.running_tasks:
                del self.running_tasks[game_id]
    
    async def cancel_ai_task(self, game_id: str):
        """取消AI任务"""
        if game_id in self.running_tasks:
            task = self.running_tasks[game_id]
            if not task.done():
                task.cancel()
                try:
                    await task
                except asyncio.CancelledError:
                    pass
            del self.running_tasks[game_id]
            self.set_ai_turn_running(game_id, False)
            logger.info(f"Cancelled AI task for game {game_id}")
    
    async def cancel_all_tasks(self):
        """取消所有AI任务"""
        game_ids = list(self.running_tasks.keys())
        for game_id in game_ids:
            await self.cancel_ai_task(game_id)
    
    def cleanup_game(self, game_id: str):
        """清理游戏相关数据"""
        if game_id in self.running_tasks:
            del self.running_tasks[game_id]
        if game_id in self.ai_turn_running:
            del self.ai_turn_running[game_id]
        if game_id in self._game_locks:
            del self._game_locks[game_id]


# 全局单例实例
ai_task_manager = AITaskManager()

