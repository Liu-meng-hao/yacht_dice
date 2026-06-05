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
from app.game.ai_player import AIPlayer
from app.game.ai_task_manager import ai_task_manager
from app.websocket.manager import manager
from app.game.scoring import ScoreCalculator
from app.db.session import SessionLocal
from app.models.player_score_detail import PlayerScoreDetail
from app.models.score_item import ScoreItem
from app.models.user import User

logger = logging.getLogger(__name__)

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
            # 获取游戏锁，防止并发
            async with ai_task_manager.get_game_lock(game_id):
                # 再次检查AI回合是否正在运行
                if ai_task_manager.is_ai_turn_running(game_id):
                    logger.warning(f"AI turn already running for game {game_id}")
                    return
                
                ai_task_manager.set_ai_turn_running(game_id, True)
                
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
            ai_task_manager.set_ai_turn_running(game_id, False)
    
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
                await asyncio.sleep(0.6)  # 模拟思考时间
                
                # 执行投骰
                locked_indices = [i for i, locked in enumerate(locked_dice) if locked]
                dice = _get_game_manager().roll_dice(game_data, str(ai_player_id), locked_indices)
                rolls_left = game_data.db_round.reroll_count
                
                # 广播投骰结果
                game_dict = game_data.to_dict()
                broadcast_msg = {
                    "type": "game_action",
                    "action": "roll",
                    "player_id": str(ai_player_id),
                    "dice": dice,
                    "dice_locked": game_dict["dice_locked"],
                    "rolls_left": rolls_left,
                    "current_player": str(ai_player_id),
                    "game_state": game_dict,
                    "timestamp": datetime.now().isoformat()
                }
                await manager.broadcast(game_id, broadcast_msg)
                
                # 更新可用计分项
                available_categories = AIGameController._get_available_categories(game_data, ai_player_id)
                
                if not available_categories:
                    break
        
        # 如果用完了投骰次数，必须计分
        if available_categories:
            await asyncio.sleep(0.5)
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
                    await ai_task_manager.start_ai_task(game_id, AIGameController.execute_ai_turn(game_id))
            
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
        
        # 获取玩家已使用的计分项
        used_details = game_data.db.query(PlayerScoreDetail).filter(
            PlayerScoreDetail.game_id == game_data.db_game_id,
            PlayerScoreDetail.player_id == player_id
        ).all()
        
        used_category_names = set()
        for detail in used_details:
            score_item = game_data.db.query(ScoreItem).filter(ScoreItem.id == detail.score_item_id).first()
            if score_item:
                used_category_names.add(score_item.item_name)
        
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
            
            game_dict = game_data.to_dict()
            
            # 检查游戏是否在进行中
            if game_dict["status"] != "playing":
                game_data.close()
                return
            
            # 检查当前玩家是否是AI
            current_player = game_data.get_current_player()
            if not current_player or not current_player.is_ai:
                game_data.close()
                return
            
            # 检查是否已经有AI任务在运行
            if ai_task_manager.is_ai_turn_running(game_id):
                game_data.close()
                return
            
            logger.info(f"Resuming AI turn for game {game_id}")
            game_data.close()
            
            # 启动AI任务
            await ai_task_manager.start_ai_task(game_id, AIGameController.execute_ai_turn(game_id))
            
        except Exception as e:
            logger.error(f"Error resuming AI turn for game {game_id}: {e}")

