from fastapi import APIRouter, WebSocket, WebSocketDisconnect
from app.websocket.manager import manager
from app.game.game_manager import GameManager
import json
from datetime import datetime
from enum import Enum
from pydantic import BaseModel, ValidationError
import logging

logger = logging.getLogger(__name__)

router = APIRouter(tags=["实时通信"])


class MessageType(str, Enum):
    """消息类型枚举"""
    CHAT = "chat"
    GAME_ACTION = "game_action"
    SYSTEM = "system"
    PING = "ping"
    PONG = "pong"
    ERROR = "error"


class GameMessage(BaseModel):
    """消息结构验证模型"""
    type: MessageType
    content: dict = {}
    timestamp: str = None


async def validate_player(game_id: str, player_id: str) -> bool:
    """验证玩家是否属于指定游戏
    
    由于当前项目没有用户登录注册系统，此验证仅检查玩家是否在游戏中
    
    Args:
        game_id: 游戏ID
        player_id: 玩家ID
    
    Returns:
        bool: 玩家是否有效
    """
    # 检查游戏是否存在
    game_data = GameManager.get_game(game_id)
    if not game_data:
        return False
    
    # 检查玩家是否在游戏中
    game_dict = game_data.to_dict()
    game_data.close()
    
    for player in game_dict["players"]:
        if player["player_id"] == player_id:
            return True
    
    return False


@router.websocket("/ws/{game_id}/{player_id}")
async def websocket_endpoint(websocket: WebSocket, game_id: str, player_id: str):
    """WebSocket 游戏实时通信端点
    用于多人游戏状态实时同步
    
    Args:
        game_id: 游戏房间ID
        player_id: 玩家ID
    """
    # 验证玩家是否属于该游戏（可选功能，根据需要启用）
    # if not await validate_player(game_id, player_id):
    #     await websocket.close(code=1008)  # 策略性关闭
    #     return
    
    # 尝试连接
    success = await manager.connect(game_id, player_id, websocket)
    if not success:
        return
    
    try:
        while True:
            data = await websocket.receive_text()
            
            # 消息格式验证
            try:
                message = json.loads(data)
            except json.JSONDecodeError:
                await websocket.send_text(json.dumps({
                    "type": "error",
                    "message": "Invalid JSON format",
                    "timestamp": datetime.now().isoformat()
                }))
                continue
            
            # 使用 Pydantic 验证消息结构
            try:
                validated_msg = GameMessage(**message)
            except ValidationError as e:
                await websocket.send_text(json.dumps({
                    "type": "error",
                    "message": f"Invalid message structure: {str(e)}",
                    "timestamp": datetime.now().isoformat()
                }))
                continue
            
            # 处理心跳响应
            if message.get("type") == "pong":
                continue  # 心跳响应无需广播
            
            # 添加元数据
            message["player_id"] = player_id
            message["timestamp"] = datetime.now().isoformat()
            
            # 获取玩家名称
            player_name = manager.get_player_name(game_id, player_id)
            if player_name:
                message["player_name"] = player_name
            
            # 安全广播
            try:
                await manager.broadcast(game_id, message)
            except Exception as e:
                logger.error(f"Broadcast error: {e}")
                
    except WebSocketDisconnect:
        logger.info(f"Player {player_id} disconnected from game {game_id}")
        manager.disconnect(game_id, player_id, websocket)
    except Exception as e:
        logger.error(f"WebSocket error for player {player_id}: {e}")
        manager.disconnect(game_id, player_id, websocket)
