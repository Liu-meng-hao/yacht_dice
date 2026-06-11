"""
AI游戏控制器
负责执行完整的AI回合流程
"""
import asyncio
import json
import logging
from datetime import datetime
from typing import List, Optional

# 延迟导入以避免循环导入
from app.ai.player import AIPlayer
from app.ai.task_manager import ai_task_manager
from app.websocket.manager import manager
from app.game.scoring import ScoreCalculator
from app.db.session import SessionLocal
from app.models.player_score_detail import PlayerScoreDetail
from app.models.score_item import ScoreItem
from app.models.user import User

logger = logging.getLogger(__name__)

# 配置常量
BROADCAST_TIMEOUT = 10  # 广播超时时间（秒）


def _get_game_manager():
    from app.game.game_manager import GameManager
    return GameManager

def _get_game_data():
    from app.game.game_manager import GameData
    return GameData


class AIGameController:
    """AI游戏控制器"""
    
    @staticmethod
    async def execute_ai_turn(game_id: str):
        """
        执行AI的完整回合
        
        Args:
            game_id: 游戏ID
        """
        game_data = None
        try:
            # 注意：锁已经在 start_ai_task 中获取，这里不需要再次获取
            # 只需在开始时再次检查状态以确保安全
            if ai_task_manager.is_ai_turn_running(game_id):
                logger.warning(f"AI turn already running for game {game_id}")
                return
            
            # 获取游戏数据
            game_data = _get_game_manager().get_game(game_id)
            if not game_data:
                logger.error(f"Game {game_id} not found")
                return
            
            game_dict = game_data.to_dict()
            
            # 检查游戏状态
            if game_dict["status"] != "playing":
                logger.info(f"Game {game_id} is not in playing state")
                return
            
            # 获取当前玩家
            current_player = game_data.get_current_player()
            if not current_player:
                logger.error(f"No current player for game {game_id}")
                return
            
            # 检查是否是AI玩家
            if not current_player.is_ai:
                logger.info(f"Current player {current_player.user_id} is not AI")
                return
            
            logger.info(f"Starting AI turn for player {current_player.user_id} in game {game_id}")
            
            # 获取AI玩家的难度
            user = game_data.db.query(User).filter(
                User.id == current_player.user_id
            ).first()
            difficulty = user.ai_difficulty if user and hasattr(user, 'ai_difficulty') else 2
            
            # 创建AI玩家实例
            ai_player = AIPlayer(difficulty=difficulty)
            
            # 获取当前骰子状态
            dice = json.loads(game_data.db_round.dice_data) if game_data.db_round.dice_data else [1, 1, 1, 1, 1]
            rolls_left = game_data.db_round.reroll_count
            
            # 获取AI玩家可用的计分项
            available_categories = AIGameController._get_available_categories(game_data, current_player.user_id)
            
            if not available_categories:
                logger.error(f"No available categories for AI player {current_player.user_id}")
                return
            
            # 执行AI回合流程
            await AIGameController._run_ai_actions(
                game_data,
                game_id,
                ai_player,
                current_player.user_id,
                dice,
                rolls_left,
                available_categories
            )
            
            game_data.commit()
            
        except Exception as e:
            logger.error(f"Error executing AI turn for game {game_id}: {e}")
            import traceback
            logger.error(traceback.format_exc())
        finally:
            if game_data:
                game_data.close()
            # 注意：ai_turn_running 标志的重置由 ai_task_manager 的 _on_task_done 回调统一处理
    
    @staticmethod
    async def _run_ai_actions(
        game_data,
        game_id: str,
        ai_player: AIPlayer,
        ai_player_id: int,
        initial_dice: List[int],
        initial_rolls_left: int,
        available_categories: List[str]
    ):
        """
        运行AI的行动
        
        Args:
            game_data: 游戏数据
            game_id: 游戏ID
            ai_player: AI玩家实例
            ai_player_id: AI玩家ID
            initial_dice: 初始骰子
            initial_rolls_left: 初始剩余投骰次数
            available_categories: 可用计分项
        """
        dice = initial_dice.copy()
        rolls_left = initial_rolls_left
        current_locked = [False] * 5
        
        # 最多3次投骰机会
        while rolls_left > 0:
            # 让AI决定下一步行动
            action, locked_dice, category = ai_player.decide_action(dice, rolls_left, available_categories)
            
            if action == 'score':
                # AI决定计分
                await asyncio.sleep(0.8)  # 模拟思考时间
                await AIGameController._ai_submit_score(game_data, game_id, str(ai_player_id), category or available_categories[0])
                return
            
            elif action == 'roll':
                # AI决定继续投骰
                await asyncio.sleep(0.5)  # 模拟思考时间
                
                # 步骤1: 广播锁定骰子的动作（让前端显示锁定动画）
                game_dict = game_data.to_dict()
                lock_broadcast_msg = {
                    "type": "game_action",
                    "action": "dice_toggle_batch",
                    "player_id": str(ai_player_id),
                    "dice": dice,
                    "dice_locked": locked_dice,
                    "rolls_left": rolls_left,
                    "current_player": str(ai_player_id),
                    "game_state": game_dict,
                    "timestamp": datetime.now().isoformat()
                }
                await manager.broadcast(game_id, lock_broadcast_msg)
                
                # 等待一下，让前端有时间显示锁定动画
                await asyncio.sleep(0.3)
                
                # 步骤2: 执行投骰
                locked_indices = [i for i, locked in enumerate(locked_dice) if locked]
                dice = _get_game_manager().roll_dice(game_data, str(ai_player_id), locked_indices)
                rolls_left = game_data.db_round.reroll_count
                current_locked = locked_dice
                
                # 步骤3: 广播投骰结果（骰子跳动动画）
                game_dict = game_data.to_dict()
                # 确保 game_dict 中的 dice_locked 是正确的
                game_dict["dice_locked"] = current_locked
                
                roll_broadcast_msg = {
                    "type": "game_action",
                    "action": "roll",
                    "player_id": str(ai_player_id),
                    "dice": dice,
                    "dice_locked": current_locked,
                    "rolls_left": rolls_left,
                    "current_player": str(ai_player_id),
                    "game_state": game_dict,
                    "timestamp": datetime.now().isoformat()
                }
                await manager.broadcast(game_id, roll_broadcast_msg)
                
                # 更新可用计分项
                available_categories = AIGameController._get_available_categories(game_data, ai_player_id)
                
                if not available_categories:
                    break
        
        # 如果用完了投骰次数，必须计分
        if available_categories:
            await asyncio.sleep(0.6)
            # 选择最好的计分项
            _, _, best_category = ai_player.decide_action(dice, 0, available_categories)
            await AIGameController._ai_submit_score(game_data, game_id, str(ai_player_id), best_category or available_categories[0])
    
    @staticmethod
    async def _ai_submit_score(game_data, game_id: str, player_id: str, category: str):
        """
        AI提交分数
        
        Args:
            game_data: 游戏数据
            game_id: 游戏ID
            player_id: 玩家ID
            category: 计分项
        """
        try:
            result = _get_game_manager().submit_score(game_data, player_id, category)
            game_dict = game_data.to_dict()
            
            next_player = game_dict["current_player"] if game_dict["status"] != "finished" else None
            
            # 广播计分结果
            broadcast_msg = {
                "type": "game_action",
                "action": "score_submit",
                "player_id": player_id,
                "category": category,
                "score": result["score"],
                "total_score": result["total_score"],
                "game_state": game_dict,
                "next_player": next_player,
                "is_game_finished": (game_dict["status"] == "finished"),
                "timestamp": datetime.now().isoformat()
            }
            await manager.broadcast(game_id, broadcast_msg)
            
            logger.info(f"AI player {player_id} scored {result['score']} in {category}")
            
            # 如果游戏未结束且下一玩家是AI，继续执行AI回合
            if game_dict["status"] == "playing" and next_player:
                # 检查下一玩家是否是AI
                next_player_data = next((p for p in game_dict["players"] if p["player_id"] == next_player), None)
                if next_player_data and next_player_data.get("is_ai"):
                    # 短暂延迟后启动下一个AI回合
                    await asyncio.sleep(0.5)
                    # 注意：这里不能使用 await，否则会阻塞当前任务
                    # 使用 asyncio.create_task 异步启动，不阻塞当前协程
                    ai_coro = AIGameController.execute_ai_turn(game_id)
                    asyncio.create_task(ai_task_manager.start_ai_task(game_id, ai_coro))
            
        except Exception as e:
            logger.error(f"Error submitting score for AI player {player_id}: {e}")
            raise
    
    @staticmethod
    def _get_available_categories(game_data, player_id: int) -> List[str]:
        """
        获取玩家可用的计分项
        
        Args:
            game_data: 游戏数据
            player_id: 玩家ID
        
        Returns:
            可用计分项列表
        """
        # 获取所有计分项
        all_categories = ScoreCalculator.CATEGORIES
        
        # 一次性获取所有相关数据，避免循环查询
        used_details = game_data.db.query(PlayerScoreDetail).filter(
            PlayerScoreDetail.game_id == game_data.db_game_id,
            PlayerScoreDetail.player_id == player_id
        ).all()
        
        # 如果没有已使用的计分项，直接返回所有
        if not used_details:
            return all_categories
        
        # 获取所有需要的 score_item_id
        used_score_item_ids = [detail.score_item_id for detail in used_details]
        
        # 一次性查询所有相关的 ScoreItem
        used_score_items = game_data.db.query(ScoreItem).filter(
            ScoreItem.id.in_(used_score_item_ids)
        ).all()
        
        # 构建已使用的类别名称集合
        used_category_names = {item.item_name for item in used_score_items}
        
        # 返回未使用的计分项
        return [cat for cat in all_categories if cat not in used_category_names]
    
    @staticmethod
    async def check_and_resume_ai_turn(game_id: str):
        """
        检查并恢复AI回合
        
        Args:
            game_id: 游戏ID
        """
        try:
            game_data = _get_game_manager().get_game(game_id)
            if not game_data:
                return
            
            try:
                game_dict = game_data.to_dict()
                
                # 检查游戏是否在进行中
                if game_dict["status"] != "playing":
                    return
                
                # 检查当前玩家是否是AI
                current_player = game_data.get_current_player()
                if not current_player or not current_player.is_ai:
                    return
                
                logger.info(f"Resuming AI turn for game {game_id}")
            finally:
                game_data.close()
            
            # 启动AI任务（内部会通过锁防止重复）
            await ai_task_manager.start_ai_task(game_id, AIGameController.execute_ai_turn(game_id))
            
        except Exception as e:
            logger.error(f"Error resuming AI turn for game {game_id}: {e}")
